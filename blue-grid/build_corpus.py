#!/usr/bin/env python3
"""Compile corpus/**/*.md into data/corpus.json.

The app has no build step at runtime: it fetches one JSON. So the tokenising,
the BM25 postings and the parameter store are all resolved here, once, and the
result is committed alongside the rasters it describes.

Usage:  ./build_corpus.py [--check-only]
"""
import hashlib
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(ROOT, 'corpus')
OUT = os.path.join(ROOT, 'data', 'corpus.json')

KINDS = ['rule', 'method', 'limit', 'error', 'outcome', 'hydro',
         'precedent', 'refusal', 'scope', 'option']
AUTHORITIES = ['statute', 'court', 'agency-survey', 'dataset-doc',
               'repo-derived', 'editorial']
INTENTS = ['flood', 'feasibility', 'consequence', 'procedure', 'evidence']
OPS = ['lt', 'lte', 'gt', 'gte', 'eq', 'ne', 'between', 'in', 'isnull', 'notnull']

JSON_FIELDS = ['tags', 'asserts', 'when', 'intents', 'conflicts']
BOOL_FIELDS = ['always', 'never_alone', 'verify']
STR_FIELDS = ['id', 'title', 'kind', 'authority', 'source', 'url', 'repo_ref']

# Tokenisation must be byte-identical to tok() in index.html. If these two ever
# disagree the client scores against postings that were built for a different
# vocabulary, and nothing anywhere reports an error.
STOP = set(
    # articles, conjunctions, copulas
    'a an the and or of to in on at is are was were be been it its this '
    'that these those for from with as by if then than so such not no '
    # interrogatives and auxiliaries. Without these, "what is this tool and
    # what does it do" tokenises to "what tool what does do" and BM25 ranks
    # every chunk whose title happens to start "What a ...", which is most of
    # the outcome group. The one content word gets buried under the noise.
    'what which who whom whose when where why how '
    'do does did done doing can could will would shall should may might must '
    'have has had having am being '
    'i me my we us our you your he she him her they them their '
    'about into onto over under above below out up down '
    'again more most other some any all both each few own same too very just now '
    'here there thing things okay ok please tell say'.split())


def tok(s):
    return [t for t in re.split(r'[^a-z0-9]+', s.lower())
            if t and t not in STOP and (len(t) > 1 or t.isdigit())]


class Bad(Exception):
    pass


def parse(path):
    raw = open(path, encoding='utf-8').read()
    if '\n---\n' not in raw:
        raise Bad('no --- separating frontmatter from body')
    head, body = raw.split('\n---\n', 1)

    c = {'tags': [], 'asserts': {}, 'when': [], 'intents': [], 'conflicts': [],
         'always': False, 'never_alone': False, 'verify': False,
         'url': '', 'source': '', 'repo_ref': ''}

    for n, line in enumerate(head.split('\n'), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if ':' not in line:
            raise Bad('line %d is not "key: value": %s' % (n, line))
        k, v = line.split(':', 1)
        k, v = k.strip(), v.strip()
        if k in JSON_FIELDS:
            try:
                c[k] = json.loads(v)
            except ValueError as e:
                raise Bad('%s is not valid JSON: %s' % (k, e))
        elif k in BOOL_FIELDS:
            if v not in ('true', 'false'):
                raise Bad('%s must be true or false, got %r' % (k, v))
            c[k] = (v == 'true')
        elif k in STR_FIELDS:
            c[k] = v
        else:
            raise Bad('unknown field %r' % k)

    c['body'] = body.strip()
    c['weight'] = 1.0
    return c


def norm_when(w, cid):
    """OR of ANDs. A group of one condition may be written as a bare triple."""
    out = []
    for group in w:
        if not isinstance(group, list) or not group:
            raise Bad('%s: empty or non-list when group' % cid)
        conds = [group] if isinstance(group[0], str) else group
        g = []
        for t in conds:
            if not isinstance(t, list) or len(t) not in (2, 3):
                raise Bad('%s: condition must be [field, op] or [field, op, value]' % cid)
            f, op = t[0], t[1]
            if op not in OPS:
                raise Bad('%s: unknown op %r' % (cid, op))
            if op in ('isnull', 'notnull'):
                g.append([f, op, None])
            else:
                if len(t) != 3:
                    raise Bad('%s: op %s needs a value' % (cid, op))
                g.append([f, op, t[2]])
        out.append(g)
    return out


def load_all():
    chunks, errs = [], []
    for kind in sorted(os.listdir(CORPUS)):
        d = os.path.join(CORPUS, kind)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.md'):
                continue
            path = os.path.join(d, fn)
            rel = os.path.relpath(path, ROOT)
            try:
                c = parse(path)
                want = '%s.%s' % (kind, fn[:-3])
                if c.get('id') != want:
                    raise Bad('id is %r but the path says it should be %r'
                              % (c.get('id'), want))
                if c.get('kind') != kind:
                    raise Bad('kind is %r but the file sits in corpus/%s/'
                              % (c.get('kind'), kind))
                if c['kind'] not in KINDS:
                    raise Bad('unknown kind %r' % c['kind'])
                if c.get('authority') not in AUTHORITIES:
                    raise Bad('unknown authority %r' % c.get('authority'))
                for i in c['intents']:
                    if i not in INTENTS:
                        raise Bad('unknown intent %r' % i)
                if not c.get('title'):
                    raise Bad('no title')
                if not c['body']:
                    raise Bad('empty body')
                c['when'] = norm_when(c['when'], c['id'])
                c['file'] = rel
                chunks.append(c)
            except Bad as e:
                errs.append('%s: %s' % (rel, e))
    return chunks, errs


def synonyms():
    """Hand-authored, in place of a stemmer. Merging drain/drainage is right;
    merging water/waterlogging is not, and a stemmer cannot tell the two apart."""
    p = os.path.join(CORPUS, 'synonyms.txt')
    syn = {}
    if not os.path.exists(p):
        return syn
    for line in open(p, encoding='utf-8'):
        line = line.split('#')[0].strip()
        if not line or '->' not in line:
            continue
        k, v = line.split('->', 1)
        ks = tok(k)
        if len(ks) != 1:
            continue
        syn[ks[0]] = sorted(set(t for t in tok(v) if t != ks[0]))
    return syn


def index(chunks):
    """BM25 postings, precomputed so the client tokenises nothing at load."""
    docs = []
    for c in chunks:
        # tags weigh triple: they are the author's own retrieval hints.
        terms = tok(c['title']) + tok(' '.join(c['tags'])) * 3 + tok(c['body'])
        tf = {}
        for t in terms:
            tf[t] = tf.get(t, 0) + 1
        docs.append((tf, len(terms)))

    postings, df = {}, {}
    for i, (tf, _) in enumerate(docs):
        for t, n in tf.items():
            postings.setdefault(t, []).append([i, n])
            df[t] = df.get(t, 0) + 1
    dl = [d[1] for d in docs]
    return {
        'N': len(docs),
        'avgdl': (sum(dl) / len(dl)) if dl else 0,
        'doclen': dl,
        'df': df,
        'postings': postings,
        'k1': 1.2,
        'b': 0.75,
    }


def params(chunks):
    """The parameter store. Flattened so the client reads one map, but every
    entry keeps the chunk that declared it — that link is what makes a number
    citable rather than merely present."""
    out, dup = {}, []
    for c in chunks:
        for k, spec in c['asserts'].items():
            if not isinstance(spec, dict) or 'v' not in spec:
                raise Bad('%s: asserts.%s must be an object with a "v"' % (c['id'], k))
            if k in out:
                dup.append('%s asserted by both %s and %s' % (k, out[k]['chunk'], c['id']))
                continue
            e = {'v': spec['v'], 'chunk': c['id']}
            for opt in ('u', 'pm', 'rel', 'note'):
                if opt in spec:
                    e[opt] = spec[opt]
            out[k] = e
    return out, dup


def main():
    chunks, errs = load_all()
    if errs:
        sys.stderr.write('corpus does not parse:\n  ' + '\n  '.join(errs) + '\n')
        return 1
    if not chunks:
        sys.stderr.write('no chunks found under %s\n' % CORPUS)
        return 1

    try:
        prm, dup = params(chunks)
    except Bad as e:
        sys.stderr.write('%s\n' % e)
        return 1
    if dup:
        sys.stderr.write('a parameter is declared twice — two copies of a '
                         'threshold is how a tool quietly lies:\n  '
                         + '\n  '.join(dup) + '\n')
        return 1

    body = json.dumps([c['id'] + c['body'] for c in sorted(chunks, key=lambda x: x['id'])],
                      sort_keys=True).encode()
    version = '%s.%s' % (date.today().isoformat(), hashlib.sha256(body).hexdigest()[:8])

    doc = {
        'corpus_version': version,
        'n_chunks': len(chunks),
        'intents': INTENTS,
        'synonyms': synonyms(),
        'params': prm,
        'chunks': [{k: c[k] for k in
                    ('id', 'title', 'kind', 'tags', 'authority', 'source', 'url',
                     'repo_ref', 'verify', 'asserts', 'when', 'always',
                     'never_alone', 'conflicts', 'intents', 'weight', 'body', 'file')}
                   for c in chunks],
        'index': index(chunks),
    }

    if '--check-only' in sys.argv:
        print('%d chunks parse, %d parameters, version %s'
              % (len(chunks), len(prm), version))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    kb = os.path.getsize(OUT) / 1024.0
    print('%s  —  %d chunks, %d parameters, %d terms, %.0f KB, version %s'
          % (os.path.relpath(OUT, ROOT), len(chunks), len(prm),
             len(doc['index']['df']), kb, version))
    return 0


if __name__ == '__main__':
    sys.exit(main())
