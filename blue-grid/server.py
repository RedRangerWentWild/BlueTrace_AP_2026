#!/usr/bin/env python3
"""Serve the app, and hold the API key so the browser never does.

Everything this tool measures happens client side and stays that way. The one
thing a browser cannot do safely is hold an API key, so this process does: it
serves the same static directory `python3 -m http.server` did, plus a single
POST /ask endpoint that forwards an evidence pack to Claude and returns the
structured answer.

An absent key is a supported way to run this, not an error. /ask then answers
503 and the page stays on the deterministic answer it has already rendered, so
the demo works identically with the network unplugged.

Usage:
    python3 server.py                          # no model, offline answers only
    ANTHROPIC_API_KEY=... python3 server.py    # Claude
    GEMINI_API_KEY=... python3 server.py       # Gemini
    GROQ_API_KEY=... python3 server.py         # Groq
    BLUETRACE_PROVIDER=groq BLUETRACE_MODEL=openai/gpt-oss-20b GROQ_API_KEY=... python3 server.py
    python3 server.py --port 8000 --host 0.0.0.0

The provider follows BLUETRACE_PROVIDER, or whichever key is present. Retrieval,
the arithmetic and the verdict never involve any of them: without a key the
page answers from the corpus alone, which is the supported default.
"""
import argparse
import copy
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
# Two providers, because the key is the only part of this that is anyone's
# property. Whichever is configured, the contract is identical: the model is
# handed the evidence pack and must return the one structured shape the client
# validates. It narrates numbers it cannot change.
ANTHROPIC_API = 'https://api.anthropic.com/v1/messages'
GEMINI_API = ('https://generativelanguage.googleapis.com/v1beta/models/'
              '%s:generateContent')

GROQ_API = 'https://api.groq.com/openai/v1/chat/completions'

# urllib announces itself as "Python-urllib/3.x" unless told otherwise, and
# Cloudflare — which fronts Groq — bans that signature outright: the request
# never reaches the API and comes back as a 403 carrying a plaintext
# "error code: 1010", which is an edge rejection wearing the costume of a
# provider error. Any ordinary agent string gets through. Identifying the
# tool honestly is the right thing to send anyway.
USER_AGENT = 'vanished-blue-grid/1.0 (satellite screening tool; python-urllib)'

PROVIDERS = ('anthropic', 'gemini', 'groq')
KEY_VAR = {'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY',
           'groq': 'GROQ_API_KEY'}
# Groq's json_schema structured output is honoured by only some of the models
# it serves, and strict mode by fewer still, so the default is one that
# supports it rather than the fastest thing on the menu. A model that ignores
# the schema answers in prose, which the client then rejects as a failed
# validation — a configuration mistake wearing the costume of a bad answer.
DEFAULT_MODEL = {'anthropic': 'claude-opus-5', 'gemini': 'gemini-3.5-flash',
                 'groq': 'openai/gpt-oss-120b'}
MAX_BODY = 1 << 20          # an evidence pack is a few KB; this is generous

# Both defaults now think before they answer, and thinking is drawn from the
# SAME output budget as the reply. At the 900 this used to send, a reasoning
# model could spend the entire allowance thinking and return a truncated
# message carrying no tool call at all — which arrived here as
# "the model did not return a structured answer", a message that named the
# symptom and hid the cause. The answer itself is ~180 words plus four short
# arrays, so the generous ceiling costs nothing when it is not used: billing
# is on tokens produced, not on the cap.
MAX_OUTPUT_TOKENS = 8000

# Thinking also takes wall-clock. Eight seconds was never a budget a reasoning
# model could meet, and the deadline is nearly free here: tier 0 is already on
# screen before this request is made, so a slow model costs the reader nothing
# but a late paragraph.
UPSTREAM_TIMEOUT = 25


def key():
    """The configured key, or '' when the server runs answer-less on purpose."""
    return os.environ.get(KEY_VAR[provider()], '').strip()


def provider():
    """Which API to call. Explicit setting wins, otherwise whichever key exists.

    The order on a tie is the order they were added and nothing more; no part
    of the pipeline depends on the choice.
    """
    p = os.environ.get('BLUETRACE_PROVIDER', '').strip().lower()
    if p in PROVIDERS:
        return p
    for name in PROVIDERS:
        if os.environ.get(KEY_VAR[name], '').strip():
            return name
    return 'anthropic'


def model():
    return os.environ.get('BLUETRACE_MODEL', '').strip() or DEFAULT_MODEL[provider()]


def gemini_schema(node):
    """Strip a JSON Schema down to the OpenAPI subset Gemini accepts.

    Anthropic takes a full JSON Schema; Gemini rejects the request outright on
    keywords it does not know, $schema and additionalProperties among them.
    Dropping the unknown keys leaves the same contract, because the fields the
    client validates are all expressible in both.
    """
    if not isinstance(node, dict):
        return node
    keep = ('type', 'description', 'enum', 'nullable', 'format')
    out = {k: node[k] for k in keep if k in node}
    if 'properties' in node:
        out['properties'] = {k: gemini_schema(v)
                             for k, v in node['properties'].items()}
    if 'required' in node:
        out['required'] = node['required']
    if 'items' in node:
        out['items'] = gemini_schema(node['items'])
    return out


def groq_schema(node):
    """The same JSON Schema, tightened to what Groq's strict mode demands.

    Strict mode rejects a schema unless every object closes itself with
    additionalProperties false and lists all of its properties as required.
    The contract's schema already requires all six top-level fields, so this
    changes nothing about what the model may return; it only restates it in
    the form the validator insists on.
    """
    if not isinstance(node, dict):
        return node
    out = dict(node)
    if 'properties' in out:
        out['properties'] = {k: groq_schema(v)
                             for k, v in out['properties'].items()}
        out['required'] = list(out['properties'].keys())
        out['additionalProperties'] = False
    if 'items' in out:
        out['items'] = groq_schema(out['items'])
    return out


def pin_to_pack(schema, pack):
    """Close the citation fields over the ids this pack actually carries.

    The validator already rejects an answer that cites a chunk it was not
    given, and in practice that fires often: a model asked to cite its sources
    will reach for a plausible-looking id it remembers rather than one in front
    of it, and the whole answer is then discarded for a wrong array.

    Catching it afterwards is the weaker half of the job. The ids are known at
    request time, so they become an enum and an invalid citation stops being
    something to detect — the decoder cannot emit one. The validator stays
    exactly as it was; this only removes the most common reason it has to fire.

    Left alone when a list would be empty, because `enum: []` satisfies nothing
    and would fail every answer rather than none.
    """
    chunk_ids = [c['id'] for c in pack.get('chunks', []) if c.get('id')]
    fact_ids = [f['id'] for f in pack.get('facts', []) if f.get('id')]
    fact_ids += [p['id'] for p in pack.get('params', []) if p.get('id')]
    props = (schema or {}).get('properties') or {}

    if chunk_ids and isinstance(props.get('cited'), dict):
        props['cited'].setdefault('items', {})['enum'] = chunk_ids
    if fact_ids and isinstance(props.get('numbers_used'), dict):
        props['numbers_used'].setdefault('items', {})['enum'] = fact_ids
    if chunk_ids and isinstance(props.get('refused'), dict):
        rp = ((props['refused'].get('items') or {}).get('properties') or {})
        if isinstance(rp.get('chunk'), dict):
            rp['chunk']['enum'] = chunk_ids
    return schema


def build_request(payload):
    """Assemble the Messages call from the pack the client sent.

    The contract is static across every question and the pack is not, so the
    contract gets the cache breakpoint and the pack sits after it. Forced tool
    use rather than prose parsing: the shape then comes back guaranteed, and
    the client's validator only has to check that it is true.
    """
    pack = payload['pack']
    chunks = '\n\n'.join(
        '[%s] %s\n(%s — %s%s)\n%s' % (
            c['id'], c['title'], c['authority'], c.get('source') or 'repo',
            '; DRAFTED, NOT YET CHECKED AGAINST THE ORIGINAL' if c.get('verify') else '',
            c['body'])
        for c in pack['chunks'])

    facts = json.dumps({'site': pack['site'], 'verdict': pack['verdict'],
                        'facts': pack['facts'], 'params': pack['params']},
                       ensure_ascii=False, indent=1)

    user = (
        '<site_facts>\n%s\n</site_facts>\n\n'
        '<chunks>\n%s\n</chunks>\n\n'
        '<verdict_code>%s</verdict_code>\n'
        '<intent>%s</intent>\n'
        '<question>%s</question>'
        % (facts, chunks, pack['verdict']['code'], pack['intent'], pack['question'])
    )

    if provider() == 'groq':
        # OpenAI-shaped, and a response schema rather than a forced tool call:
        # Groq does not support tool use and json_schema together, so the
        # schema is the guarantee. Same contract, same validated shape.
        #
        # max_completion_tokens, not max_tokens — the reasoning models served
        # here reject the older field. reasoning_effort is low for the same
        # reason effort is low on the other two: narrating a fixed evidence
        # pack under a contract is not a reasoning problem, and the reasoning
        # comes out of the same completion budget.
        tool = payload['tool']
        schema = copy.deepcopy(tool.get('input_schema') or tool.get('parameters') or {})
        schema = pin_to_pack(schema, pack)
        return {
            'model': model(),
            'max_completion_tokens': MAX_OUTPUT_TOKENS,
            'reasoning_effort': 'low',
            'messages': [
                {'role': 'system', 'content': payload['contract']},
                {'role': 'user', 'content': user},
            ],
            'response_format': {
                'type': 'json_schema',
                'json_schema': {'name': tool['name'], 'strict': True,
                                'schema': groq_schema(schema)},
            },
        }

    if provider() == 'gemini':
        # Gemini reaches the same guarantee through a response schema rather
        # than a forced tool call, so the answer arrives as JSON text.
        tool = copy.deepcopy(payload['tool'])
        pin_to_pack(tool.get('input_schema') or tool.get('parameters') or {}, pack)
        return {
            'systemInstruction': {'parts': [{'text': payload['contract']}]},
            'contents': [{'role': 'user', 'parts': [{'text': user}]}],
            # No temperature, topP or topK: Google explicitly recommends not
            # changing the sampling parameters on the 3.x models, and the
            # response schema already pins the shape this endpoint needs.
            #
            # thinkingLevel defaults to 'medium' on 3.x, and that thinking is
            # drawn from maxOutputTokens — the same trap the Anthropic path
            # fell into at 900. Narrating a fixed evidence pack under a
            # contract is not a reasoning task, so it is turned down to the
            # floor rather than left to spend the budget.
            'generationConfig': {
                'maxOutputTokens': MAX_OUTPUT_TOKENS,
                'thinkingLevel': 'minimal',
                'responseMimeType': 'application/json',
                'responseSchema': gemini_schema(
                    tool.get('input_schema') or tool.get('parameters') or {}),
            },
        }

    # No temperature, top_p or top_k: sampling parameters are rejected outright
    # with a 400 on Opus 5 and the rest of the 4.7-and-later family.
    #
    # No explicit thinking block either. Thinking is on by default on Opus 5,
    # and it is deliberately left on: with thinking disabled these models will
    # occasionally write the tool call into visible prose instead of emitting a
    # tool_use block, which is precisely the failure this endpoint must not
    # have. Effort is turned down instead — narrating an evidence pack under a
    # contract is not a reasoning problem, and low effort buys back the latency.
    # Anthropic takes a forced tool call rather than a response schema, and
    # the tool's input_schema is where the same closed enums go.
    _pinned_tool = copy.deepcopy(payload['tool'])
    pin_to_pack(_pinned_tool.get('input_schema')
                or _pinned_tool.get('parameters') or {}, pack)

    return {
        'model': model(),
        'max_tokens': MAX_OUTPUT_TOKENS,
        'output_config': {'effort': 'low'},
        'system': [
            {'type': 'text', 'text': payload['contract'],
             'cache_control': {'type': 'ephemeral'}},
        ],
        'messages': [{'role': 'user', 'content': user}],
        'tools': [_pinned_tool],
        'tool_choice': {'type': 'tool', 'name': _pinned_tool['name']},
    }


def upstream_request(payload):
    """The provider-shaped HTTP request, key included."""
    body = json.dumps(build_request(payload)).encode()
    # Common to all three, and the User-Agent is not decoration: see the note
    # on USER_AGENT. It is set here, once, so a fourth provider cannot be
    # added without it.
    headers = {'content-type': 'application/json', 'user-agent': USER_AGENT}
    if provider() == 'groq':
        headers['authorization'] = 'Bearer %s' % key()
        return urllib.request.Request(GROQ_API, data=body, headers=headers)
    if provider() == 'gemini':
        # Gemini takes the key in a header too, which keeps it out of the URL
        # and therefore out of any proxy or server log along the way.
        headers['x-goog-api-key'] = key()
        return urllib.request.Request(GEMINI_API % model(), data=body,
                                      headers=headers)
    headers['x-api-key'] = key()
    headers['anthropic-version'] = '2023-06-01'
    return urllib.request.Request(ANTHROPIC_API, data=body, headers=headers)


def upstream_message(detail):
    """The provider's own error sentence, if the body carries one.

    Anthropic returns {"error": {"message": ...}} and Gemini
    {"error": {"message": ...}} inside a differently shaped envelope; both
    reduce to the same lookup. Falls back to the raw body, which is already
    truncated by the caller.
    """
    try:
        err = json.loads(detail).get('error')
    except (ValueError, AttributeError):
        # Not JSON at all. A provider error always is, so this is an edge or
        # proxy in front of the provider answering on its behalf — a different
        # fault with a different fix, and worth saying so rather than handing
        # back an opaque fragment of an HTML page.
        flat = ' '.join(detail.split())
        return ('blocked before it reached the provider (%s)' % flat[:120]
                if flat else 'no detail')
    if isinstance(err, dict):
        return err.get('message') or err.get('status') or detail.strip()
    return str(err) if err else detail.strip()


def structured_answer(out):
    """Pull the one structured object out, whatever shape the provider used.

    Returns (answer, why_not). Only the answer crosses back to the page —
    forwarding a whole response would hand the client fields it has no business
    reading — but a failure has to say what actually came back instead. The
    old version returned a bare None, so every one of these failures reached
    the officer as the same sentence and reached the log as nothing at all.
    """
    if provider() == 'groq':
        choices = out.get('choices', [])
        if not choices:
            return None, 'the model returned no choices'
        top = choices[0]
        text = (top.get('message') or {}).get('content')
        stop = top.get('finish_reason') or 'unknown'
        if not text:
            if stop == 'length':
                return None, ('the model used its whole completion budget '
                              'before answering (finish_reason length) — '
                              'raise MAX_OUTPUT_TOKENS')
            return None, 'the model returned no content (finish_reason %s)' % stop
        try:
            return json.loads(text), None
        except ValueError:
            if stop == 'length':
                return None, ('the reply was cut off mid-JSON (finish_reason '
                              'length) — raise MAX_OUTPUT_TOKENS')
            # A model that does not honour json_schema replies in prose. That
            # is a configuration fault, and naming it here stops the client
            # reporting it as a failed validation of a shape the model was
            # never actually asked for.
            return None, ('the model returned text that is not JSON — %s may '
                          'not support structured outputs' % model())

    if provider() == 'gemini':
        cands = out.get('candidates', [])
        if not cands:
            fb = (out.get('promptFeedback') or {}).get('blockReason')
            return None, ('the request was blocked upstream: %s' % fb if fb
                          else 'the model returned no candidates')
        for cand in cands:
            for part in cand.get('content', {}).get('parts', []):
                if 'text' in part:
                    try:
                        return json.loads(part['text']), None
                    except ValueError:
                        return None, 'the model returned text that is not JSON'
        reason = cands[0].get('finishReason') or 'unknown'
        if reason == 'MAX_OUTPUT_TOKENS' or reason == 'MAX_TOKENS':
            return None, ('the model used its whole output budget before '
                          'answering (finishReason MAX_TOKENS) — raise '
                          'MAX_OUTPUT_TOKENS')
        return None, 'the model returned no text part (finishReason %s)' % reason

    blocks = out.get('content', [])
    for block in blocks:
        if block.get('type') == 'tool_use':
            return block.get('input') or {}, None
    kinds = ', '.join(sorted({b.get('type', '?') for b in blocks})) or 'nothing'
    stop = out.get('stop_reason') or 'unknown'
    if stop == 'max_tokens':
        return None, ('the model used its whole output budget before calling '
                      'the tool (stop_reason max_tokens, returned %s) — raise '
                      'MAX_OUTPUT_TOKENS' % kinds)
    if stop == 'refusal':
        return None, 'the model declined the request (stop_reason refusal)'
    return None, ('no tool call in the reply (stop_reason %s, returned %s)'
                  % (stop, kinds))


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    # The typeface is served from assets/fonts/ rather than a CDN, so a demo
    # that loses the network keeps its typography. mimetypes does not know
    # woff2 on every Python build, and Chrome refuses a font served as
    # application/octet-stream.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.woff2': 'font/woff2', '.woff': 'font/woff'}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if self.path == '/ask' or not self.path.endswith(('.png', '.json')):
            sys.stderr.write('%s %s\n' % (self.command, self.path))

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _drain(self):
        """Read the request body whether or not we intend to use it.

        This is keep-alive hygiene, and skipping it is not a cosmetic bug: an
        unread body stays in the socket, the next request on that connection
        starts mid-JSON, the server answers 400 with an HTML error page, and
        the client reports a model failure that never happened. The 503 path is
        the one that tempts you to skip it and the one where it matters most,
        because with no key every single request takes it.
        """
        try:
            n = int(self.headers.get('content-length') or 0)
        except ValueError:
            return None
        if n <= 0 or n > MAX_BODY:
            return None
        try:
            return self.rfile.read(n)
        except OSError:
            return None

    def do_POST(self):
        raw = self._drain()
        if self.path != '/ask':
            self.send_error(404)
            return
        if not key():
            # First-class state, not a failure. The client renders its own
            # answer before it ever calls here.
            self._json(503, {'reason': 'no %s set on the server'
                             % KEY_VAR[provider()]})
            return
        if raw is None:
            self._json(400, {'reason': 'bad request size'})
            return
        try:
            payload = json.loads(raw)
            for f in ('pack', 'contract', 'tool'):
                if f not in payload:
                    self._json(400, {'reason': 'missing %s' % f})
                    return
        except ValueError as e:
            self._json(400, {'reason': 'unreadable request: %s' % e})
            return

        req = upstream_request(payload)
        try:
            with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors='replace')[:300]
            sys.stderr.write('upstream %s: %s\n' % (e.code, detail))
            # The status alone does not say which of the several things that
            # produce a 400 went wrong, and the operator cannot see this log
            # from the hall. Carry the upstream's own message across.
            self._json(502, {'reason': 'the model API answered %s: %s'
                             % (e.code, upstream_message(detail) or 'no detail')})
            return
        # A deadline and an unreachable host are different faults with
        # different fixes, and collapsing them into "could not be reached"
        # sent the operator looking at their network when the real answer was
        # that the model was still thinking. socket.timeout is an OSError, so
        # it has to be caught before the general case.
        except TimeoutError:
            sys.stderr.write('upstream timed out after %ss\n' % UPSTREAM_TIMEOUT)
            self._json(502, {'reason': 'the model did not answer within %s seconds'
                             % UPSTREAM_TIMEOUT})
            return
        except urllib.error.URLError as e:
            why = getattr(e, 'reason', e)
            if isinstance(why, TimeoutError) or 'timed out' in str(why):
                sys.stderr.write('upstream timed out after %ss\n' % UPSTREAM_TIMEOUT)
                self._json(502, {'reason': 'the model did not answer within %s seconds'
                                 % UPSTREAM_TIMEOUT})
                return
            sys.stderr.write('upstream unreachable: %r\n' % why)
            self._json(502, {'reason': 'could not reach %s: %s'
                             % (provider(), why)})
            return
        except Exception as e:                                   # noqa: BLE001
            sys.stderr.write('upstream failed: %r\n' % e)
            self._json(502, {'reason': 'the call to %s failed: %s'
                             % (provider(), type(e).__name__)})
            return

        answer, why_not = structured_answer(out)
        if answer is None:
            # Named on the page and in the log. A failure the operator cannot
            # diagnose from either one is a failure they will re-run forever.
            sys.stderr.write('no structured answer: %s\n' % why_not)
            self._json(502, {'reason': why_not})
            return
        self._json(200, answer)


def main():
    # A platform that assigns the port sets PORT, and expects the process to
    # bind every interface inside its container. That is the signal used here
    # to tell a deployment apart from someone running this on their laptop:
    # deployed, the defaults follow the platform and the loopback warning is
    # noise; local, nothing changes and the default is still loopback.
    env_port = os.environ.get('PORT')
    deployed = bool(env_port)

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=int(env_port or 8000))
    ap.add_argument('--host', default='0.0.0.0' if deployed else '127.0.0.1',
                    help='default loopback; a hall LAN is not a trusted network')
    a = ap.parse_args()

    if a.host not in ('127.0.0.1', 'localhost') and not deployed:
        sys.stderr.write(
            '\n  WARNING: binding %s exposes this server to the network it is on.\n'
            '  Anyone who can reach it can spend your API key. Loopback plus an\n'
            '  SSH tunnel is the safe way to show this on someone else\'s machine.\n\n'
            % a.host)

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print('serving %s on http://%s:%d' % (os.path.basename(ROOT), a.host, a.port))
    print('model: %s' % ('%s via %s' % (model(), provider()) if key() else
                         'none — no API key set, answers stay local'))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    main()
