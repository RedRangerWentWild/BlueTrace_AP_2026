#!/usr/bin/env python3
"""Cross-consistency checks on the corpus, in the spirit of verify_encoding.py.

verify_encoding.py does not look at a raster and judge it plausible; it asserts
that two files which must agree do agree, and names the transform when they do
not. The same idea applies here. A chunk is not checked for being well written.
It is checked against the code it claims to describe, against the fields it
triggers on, and against the numbers it declares.

Exits 1 on the first category that fails, naming the file.

Usage:  ./check_corpus.py [--verbose]
"""
import itertools
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import build_corpus as bc  # noqa: E402

INDEX = os.path.join(ROOT, 'index.html')

# Years that carry no parametric meaning: they name the epochs of the source
# archive and appear in prose everywhere.
YEAR_WHITELIST = {'1984', '1999', '2000', '2021'}

# Parameters the rest of the tool computes with. Each must exist exactly once.
# build_corpus already rejects a duplicate key; this asserts the key is there at
# all, so deleting the chunk that declares a threshold cannot pass silently.
REQUIRED_PARAMS = [
    'uncertaintyM', 'lakeM_state', 'drainM_state', 'lakeM_ngt', 'drainM_ngt',
    'P_mm', 'P_annualMm', 'C_pre', 'C_post', 'dC', 'tankerL',
    'handAtM', 'handDeepM', 'handLowM', 'handMarginalM',
    'byteCeiling', 'mppM', 'jrcScaleM', 'meritScaleM',
]

EXTERNAL = {'statute', 'court', 'agency-survey', 'dataset-doc'}
NUM = re.compile(r'\d+(?:\.\d+)*')
WORDS = re.compile(r"[A-Za-z0-9'’‐-―-]+")
MAX_WORDS = 120
MAX_PACK_CHUNKS = 12
TOKEN_BUDGET = 3000


def fail(cat, problems):
    sys.stderr.write('\n%s\n' % cat)
    for p in problems:
        sys.stderr.write('  %s\n' % p)
    sys.stderr.write('\n')
    return False


def read(path):
    return open(os.path.join(ROOT, path), encoding='utf-8').read()


# --------------------------------------------------------------------------
# what index.html actually offers a trigger

def site_fields():
    """Scrape the field manifest out of index.html.

    siteContext() declares the record every trigger is evaluated against. The
    manifest is read from the code rather than restated here, so renaming a
    field breaks the corpus loudly instead of disabling its triggers in silence.
    """
    src = read('index.html')
    m = re.search(r'//\s*@site-fields\s*\n(.*?)\n\s*//\s*@end-site-fields',
                  src, re.S)
    if not m:
        return None
    return set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', m.group(1)))


def decide_codes():
    """Every branch of decide() tags itself with a code; the retriever maps each
    code to the chunk that explains it. Both sides are scraped from the code."""
    src = read('index.html')
    body = src.split('function decide(')[1].split('\nvar OUTCOME')[0] \
        if 'function decide(' in src else ''
    codes = set(re.findall(r"code\s*:\s*'([a-z0-9.\-]+)'", body))
    codes |= set(re.findall(r"codes\s*:\s*\['([a-z0-9.\-]+)'\]", body))
    m = re.search(r'var CODE_CHUNK\s*=\s*\{(.*?)\n\};', src, re.S)
    mapping = {}
    if m:
        for k, v in re.findall(r"'([a-z0-9.\-]+)'\s*:\s*'([a-z0-9.\-]+)'", m.group(1)):
            mapping[k] = v
    return codes, mapping


# --------------------------------------------------------------------------
# the trigger channel, mirrored just far enough to sweep for holes

def val(rec, f):
    return rec.get(f, None)


def test(rec, f, op, v):
    x = val(rec, f)
    if op == 'isnull':
        return x is None
    if op == 'notnull':
        return x is not None
    if x is None:
        return False
    if op == 'in':
        if isinstance(x, list):
            return v in x
        return isinstance(v, list) and x in v
    if op == 'between':
        return v[0] <= x <= v[1]
    if op == 'eq':
        return x == v
    if op == 'ne':
        return x != v
    try:
        if op == 'lt':
            return x < v
        if op == 'lte':
            return x <= v
        if op == 'gt':
            return x > v
        if op == 'gte':
            return x >= v
    except TypeError:
        return False
    return False


def fires(chunk, rec):
    for group in chunk['when']:
        if all(test(rec, f, op, v) for f, op, v in group):
            return True
    return False


def triggered(chunks, rec):
    return [c for c in chunks if c['always'] or fires(c, rec)]


# --------------------------------------------------------------------------

def main():
    verbose = '--verbose' in sys.argv
    chunks, errs = bc.load_all()
    if errs:
        return 0 if fail('corpus does not parse:', errs) else 1
    by_id = {c['id']: c for c in chunks}
    ok = True

    # 1. identity ----------------------------------------------------------
    bad = [c['file'] for c in chunks
           if not re.match(r'^[a-z][a-z0-9]*(\.[a-z0-9-]+)+$', c['id'])]
    if bad:
        ok = fail('malformed ids:', bad)

    # 2. every trigger field exists in siteContext --------------------------
    fields = site_fields()
    if fields is None:
        sys.stderr.write('note: no @site-fields manifest in index.html yet — '
                         'trigger fields unchecked\n')
    else:
        bad = []
        for c in chunks:
            for group in c['when']:
                for f, _, _ in group:
                    if f not in fields:
                        bad.append('%s triggers on %r, which siteContext does '
                                   'not produce' % (c['file'], f))
        if bad:
            ok = fail('a trigger names a field that does not exist:', bad)

    # 3. every number in a body is declared ---------------------------------
    bad = []
    for c in chunks:
        allowed = set(YEAR_WHITELIST)
        for spec in c['asserts'].values():
            for key in ('v', 'pm', 'rel'):
                if key in spec:
                    allowed.add(('%g' % spec[key]) if isinstance(spec[key], float)
                                else str(spec[key]))
        for s in (c['source'], c['url'], c['repo_ref']):
            allowed.update(NUM.findall(s or ''))
        nums = set()
        for a in allowed:
            try:
                nums.add(float(a))
            except ValueError:
                pass
        for n in NUM.findall(c['title'] + ' ' + c['body']):
            if n in allowed:
                continue
            try:
                if float(n) in nums:
                    continue
            except ValueError:
                pass
            bad.append('%s states %s but does not declare it' % (c['file'], n))
    if bad:
        ok = fail('a chunk states a number it has not declared '
                  '(add it to asserts, or take it out of the prose):', bad)

    # 4. provenance ---------------------------------------------------------
    bad = []
    for c in chunks:
        if c['authority'] in EXTERNAL and not c['url'].startswith('http'):
            bad.append('%s is %s and carries no url' % (c['file'], c['authority']))
        if c['authority'] == 'repo-derived':
            if not c['repo_ref']:
                bad.append('%s is repo-derived and carries no repo_ref' % c['file'])
                continue
            ref = c['repo_ref']
            path, _, anchor = ref.partition('#')
            full = os.path.join(ROOT, path)
            if not os.path.exists(full):
                bad.append('%s points at %s, which does not exist' % (c['file'], path))
                continue
            lines = sum(1 for _ in open(full, encoding='utf-8', errors='replace'))
            ns = [int(x) for x in re.findall(r'L(\d+)', anchor)]
            if not ns:
                bad.append('%s has a repo_ref with no line range' % c['file'])
            elif max(ns) > lines:
                bad.append('%s points at %s line %d, but that file has %d lines'
                           % (c['file'], path, max(ns), lines))
    if bad:
        ok = fail('provenance is incomplete or stale:', bad)

    # 5. every decide() code has a chunk ------------------------------------
    codes, mapping = decide_codes()
    if not codes:
        sys.stderr.write('note: decide() carries no codes yet — spine unchecked\n')
    else:
        bad = []
        for code in sorted(codes):
            if code not in mapping:
                bad.append('decide() emits %r with no entry in CODE_CHUNK' % code)
            elif mapping[code] not in by_id:
                bad.append('CODE_CHUNK maps %r to %r, which is not a chunk'
                           % (code, mapping[code]))
        for code, cid in sorted(mapping.items()):
            if code not in codes:
                bad.append('CODE_CHUNK maps %r, which decide() never emits' % code)
        if bad:
            ok = fail('the citation spine is broken:', bad)

    # 6. coverage sweep ------------------------------------------------------
    # A synthesised cartesian of plausible site records. For each one, the
    # trigger channel alone must produce a usable pack: enough chunks, and among
    # them something that states a rule and something that states a limit. A
    # hole here is a site state the tool can reach and cannot explain.
    grid = {
        'inAoi': [True],
        'ruleId': ['state', 'ngt'],
        'verdict': ['REJECT', 'REFER', 'CONDITIONS', 'NO_OBJECTION'],
        'distPresent': [0, 12, 40, 90, 255],
        'distHistoric': [0, 12, 40, 90, 255],
        'distDrain': [0, 20, 120, 255],
        'handM': [0, 1, 3, 12],
        'occurrence': [5, 60],
        'encroached': [0.0, 0.9],
        'hasBuildings': [True, False],
        'plotM': [30, 120],
        'intent': ['flood', 'feasibility', 'consequence', 'procedure', 'evidence'],
    }
    keys = list(grid)
    worst, bad = None, []
    for combo in itertools.product(*(grid[k] for k in keys)):
        rec = dict(zip(keys, combo))
        rec['retreatM'] = max(0, rec['distPresent'] - rec['distHistoric'])
        rec['lastWaterYear'] = 2010 if rec['distHistoric'] == 0 else None
        rec['handClass'] = ('AT_DRAINAGE_LEVEL' if rec['handM'] == 0 else
                            'DEEP_IN_A_WATER_PATH' if rec['handM'] <= 1 else
                            'LOW_GROUND' if rec['handM'] <= 2 else
                            'MARGINAL' if rec['handM'] <= 5 else 'ELEVATED')
        rec['flowClass'] = ('ON_FLOW_PATH' if rec['distDrain'] == 0 else
                            'ADJACENT' if rec['distDrain'] <= 10 else
                            'NEAR' if rec['distDrain'] <= 70 else
                            'UNRESOLVED' if rec['distDrain'] >= 255 else 'OFF')
        rec['upaKm2'] = None
        rec['runoffDisplacedM3'] = 30
        rec['codes'] = []
        hits = triggered(chunks, rec)
        kinds = set(h['kind'] for h in hits)
        if worst is None or len(hits) < worst[0]:
            worst = (len(hits), rec)
        if len(hits) < 3:
            bad.append('only %d chunks for %s' % (len(hits), rec))
        elif 'rule' not in kinds:
            bad.append('no rule chunk for %s' % rec)
        elif not (kinds & {'error', 'limit'}):
            bad.append('no error or limit chunk for %s' % rec)
        if rec['intent'] == 'flood' and \
           'refusal.not-a-flood-predictor' not in [h['id'] for h in hits]:
            bad.append('flood question with no flood refusal: %s' % rec)
        if len(bad) > 5:
            break
    if bad:
        ok = fail('the trigger channel has a hole — a reachable site state with '
                  'nothing to say about it:', bad[:6])
    elif verbose:
        print('coverage: worst cell retrieves %d chunks' % worst[0])

    # 7. the parameter store -------------------------------------------------
    try:
        prm, dup = bc.params(chunks)
    except bc.Bad as e:
        return 0 if fail('asserts are malformed:', [str(e)]) else 1
    if dup:
        ok = fail('a threshold is declared twice — two copies is how a tool '
                  'quietly lies:', dup)
    missing = [p for p in REQUIRED_PARAMS if p not in prm]
    if missing:
        ok = fail('the code computes with these and no chunk declares them:',
                  missing)

    # index.html keeps a bootstrap copy of these so the plot check runs before
    # corpus.json lands. A bootstrap copy is still a second copy, so it is
    # compared against the corpus here rather than trusted. This is the same
    # move verify_encoding.py makes between two rasters that must agree.
    src = read('index.html')
    boot = {}
    m = re.search(r'//\s*@params\s*\n(.*?)//\s*@end-params', src, re.S)
    if m:
        for k, v in re.findall(r'(\w+)\s*:\s*(-?[\d.]+)', m.group(1)):
            boot[k] = float(v)
    m = re.search(r'var UNCERTAINTY_M\s*=\s*([\d.]+)', src)
    if m:
        boot['uncertaintyM'] = float(m.group(1))
    for rid, keys in (('state', ('lakeM_state', 'drainM_state')),
                      ('ngt', ('lakeM_ngt', 'drainM_ngt'))):
        m = re.search(r"%s:\s*\{id:'%s'.*?lakeM:(\d+),\s*drainM:(\d+)" % (rid, rid),
                      src, re.S)
        if m:
            boot[keys[0]] = float(m.group(1))
            boot[keys[1]] = float(m.group(2))
    # a few bootstrap names read an uncertainty rather than a value, and one
    # was shortened; the alias table keeps that explicit instead of implicit.
    ALIAS = {'P_pm': ('P_mm', 'pm'), 'dC_pm': ('dC', 'pm'),
             'upaCeilKm2': ('upaCeilingKm2', 'v')}
    for boot_key, (pk, field) in ALIAS.items():
        if boot_key in boot and pk in prm and field in prm[pk]:
            prm[boot_key] = {'v': prm[pk][field], 'chunk': prm[pk]['chunk']}

    drift = ['%s: index.html says %g, the corpus says %g (%s)'
             % (k, v, prm[k]['v'], prm[k]['chunk'])
             for k, v in sorted(boot.items())
             if k in prm and float(prm[k]['v']) != v]
    if drift:
        ok = fail('index.html and the corpus disagree about a threshold — one '
                  'of them is what the tool actually used:', drift)
    unchecked = [k for k in boot if k not in prm]
    if unchecked:
        ok = fail('index.html computes with a value no chunk declares:', unchecked)

    # 8. precision ------------------------------------------------------------
    bad = []
    for c in chunks:
        for k, spec in c['asserts'].items():
            pm = spec.get('pm')
            v = spec.get('v')
            if pm is None or not isinstance(v, (int, float)) or not pm:
                continue
            # the last significant digit of the value must not be finer than the
            # uncertainty: quoting 29.7 +/- 15 claims precision that is not there
            import math
            if v and abs(v) > 0 and (abs(v) * 1e-3 > abs(pm)):
                continue
            dec = len(('%g' % v).split('.')[1]) if '.' in ('%g' % v) else 0
            pmdec = len(('%g' % pm).split('.')[1]) if '.' in ('%g' % pm) else 0
            if dec > pmdec + 1:
                bad.append('%s: %s = %g +/- %g claims more digits than its '
                           'uncertainty supports' % (c['file'], k, v, pm))
            del math
    if bad:
        ok = fail('a value is quoted more precisely than it is known:', bad)

    # 9. budget ---------------------------------------------------------------
    bad = []
    lens = []
    for c in chunks:
        n = len(WORDS.findall(c['body']))
        lens.append((n, c))
        if n > MAX_WORDS:
            bad.append('%s is %d words, over the %d-word cap'
                       % (c['file'], n, MAX_WORDS))
    if bad:
        ok = fail('a chunk is too long to sit in an evidence pack:', bad)
    lens.sort(reverse=True, key=lambda x: x[0])
    worst_pack = sum(n for n, _ in lens[:MAX_PACK_CHUNKS])
    approx_tokens = int(worst_pack * 1.4) + 400
    if approx_tokens > TOKEN_BUDGET:
        ok = fail('the worst-case pack is too big:',
                  ['%d chunks would be about %d tokens, over %d'
                   % (MAX_PACK_CHUNKS, approx_tokens, TOKEN_BUDGET)])

    # 10. the two tokenisers agree -------------------------------------------
    # build_corpus.py builds the postings and index.html scores against them.
    # If their stopword lists drift, the client scores a query against a
    # vocabulary that was never built and no error is raised anywhere.
    m = re.search(r"\('([^']*?)'\s*\n?\+?\s*'([^']*?)'\)\.split\(' '\)", src)
    if not m:
        m = re.search(r"\(\s*'((?:[^']|'\s*\n\s*\+\s*')*)'\s*\)\.split", src)
    js_stop = set()
    block = re.search(r"var STOP = \{\};\s*\n(.*?)\.split\(' '\)", src, re.S)
    if block:
        js_stop = set(' '.join(re.findall(r"'([^']*)'", block.group(1))).split())
    if js_stop != bc.STOP:
        ok = fail('the two tokenisers disagree — the client would score against '
                  'postings built for a different vocabulary:',
                  ['only in build_corpus.py: %s' % sorted(bc.STOP - js_stop),
                   'only in index.html: %s' % sorted(js_stop - bc.STOP)])

    # 11. no key anywhere in the repo -----------------------------------------
    leaked = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', '__pycache__')]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if fn.endswith(('.png', '.json')) and fn != 'corpus.json':
                continue
            try:
                if 'sk-ant-api' in open(p, encoding='utf-8', errors='ignore').read():
                    if os.path.abspath(p) != os.path.abspath(__file__):
                        leaked.append(os.path.relpath(p, ROOT))
            except OSError:
                pass
    if leaked:
        ok = fail('an API key is committed to the repository:', leaked)

    if not ok:
        return 1

    unverified = [c['file'] for c in chunks if c['verify']]
    print('%d chunks, %d parameters, worst-case pack about %d tokens — all checks pass'
          % (len(chunks), len(prm), approx_tokens))
    if unverified:
        print('%d chunks are drafted and not yet checked against the original '
              'source (verify: true):' % len(unverified))
        for f in sorted(unverified):
            print('    %s' % f)
    return 0


if __name__ == '__main__':
    sys.exit(main())
