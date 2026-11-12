# The corpus

Every chunk is one file. One file is one idea, at most 120 words.

The corpus is also the **parameter store**. Design rainfall, runoff coefficients,
buffer distances, the error budget, the HAND class boundaries — none of them are
literals in `index.html`. They are declared in `asserts:` here, compiled into
`data/corpus.json`, and read at load. A number therefore cannot reach an answer
without a chunk id attached to it, because there is nowhere else for it to have
come from.

## Format

A file is a block of `key: value` lines, then `---`, then the body.

```
id: rule.lake-buffer.ngt-75m
title: NGT 75 m lake buffer, upheld by the Supreme Court
kind: rule
tags: ["buffer", "lake", "ngt", "setback"]
authority: court
source: NGT O.A. 222/2014, Forward Foundation v. State of Karnataka
url: https://...
verify: true
asserts: {"lakeM": {"v": 75, "u": "m"}}
when: [["ruleId", "eq", "ngt"]]
intents: ["feasibility"]
---
Body prose.
```

`tags`, `asserts`, `when`, `intents`, `conflicts` are JSON. Everything else is a
plain string, except `always`, `never_alone` and `verify`, which are `true`/`false`.

`id` must equal `<kind>.<filename without .md>`, and the file must sit in
`corpus/<kind>/`.

## Fields

| field | meaning |
|---|---|
| `kind` | rule, method, limit, error, outcome, hydro, precedent, refusal, scope, option |
| `authority` | statute, court, agency-survey, dataset-doc, repo-derived, editorial |
| `source` | the thing a reader would go and check |
| `url` | required for statute, court, agency-survey, dataset-doc |
| `repo_ref` | required for repo-derived — `index.html#L349-L353`. The range is opened and confirmed to exist. |
| `verify` | `true` means drafted from public knowledge and **not yet checked against the original**. Say so in the UI. |
| `asserts` | every number this chunk is allowed to state |
| `when` | OR of ANDs of `[field, op, value]` over the live site record. `[]` = never fires by trigger. |
| `always` | floor score, for chunks that belong in almost every answer |
| `never_alone` | an answer citing only chunks like this is rejected. Precedent sets it. |
| `conflicts` | ids that must not appear in the same pack |
| `intents` | flood, feasibility, consequence, procedure, evidence |

Ops for `when`: `lt lte gt gte eq ne between in isnull notnull`. It is a
declarative list, never `eval`. A clause on a null field fails unless the op is
`isnull`.

## Rules that `check_corpus.py` enforces

1. Ids unique, well formed, and matching the file path.
2. Every `when` field exists in the manifest scraped out of `siteContext` in
   `index.html`. Rename a field and the corpus breaks loudly.
3. **Every number in a body is declared.** Whitelisted: 1984, 1999, 2000, 2021,
   and any number already in that chunk's own `source` or `url`.
4. External authorities carry a URL. `repo-derived` carries a `repo_ref` whose
   line range exists.
5. Every `decide()` code has a chunk.
6. A synthesised sweep of site records retrieves at least three chunks for every
   cell, including a rule and an error or limit.
7. Each shared parameter is asserted exactly once across the whole corpus.
8. No value carries more significant figures than its uncertainty supports.
9. Worst-case pack fits the token budget; no body over 120 words.
10. No `sk-ant` anywhere in the repo.

Run it before every commit. It exits 1 and says which file.
