id: limit.jrc-30m-small-tanks-invisible
title: Small tanks do not appear in this record at all
kind: limit
tags: ["small", "tank", "invisible", "missing", "resolution", "limit", "not found", "kunte"]
authority: repo-derived
source: README, Known limits
repo_ref: README.md#L139-L141
asserts: {"minTankHa": {"v": 0.5, "u": "ha"}}
always: true
when: []
intents: ["feasibility", "evidence"]
---
At the source resolution a water body under roughly 0.5 ha is not reliably
detected. The small neighbourhood tanks that a dense settlement swallows first
are exactly the ones below that floor.

So a clear screening result means no recorded water body was found near the
plot. It does not mean there was never a tank there. Where local knowledge, a
place name or a revenue entry says otherwise, the local knowledge is the better
evidence and this tool has nothing to contribute against it.
