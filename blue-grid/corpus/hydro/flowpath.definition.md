id: hydro.flowpath.definition
title: What this tool calls a flow path
kind: hydro
tags: ["flow path", "channel", "definition", "flowpath", "stream", "where water runs"]
authority: repo-derived
source: gee_blue_grid.js, the flowPath definition
repo_ref: gee_blue_grid.js#L143-L152
asserts: {"flowUpaKm2": {"v": 2, "u": "km2"}}
when: [["flowClass", "in", ["ON_FLOW_PATH", "ADJACENT"]]]
intents: ["consequence", "flood", "evidence"]
---
A flow path here is ground that is both low relative to the nearest channel and
carrying the drainage of more than 2 square kilometres of upstream land. Both
conditions have to hold: low ground away from any catchment is a hollow, and a
large catchment on high ground is a ridge above a valley.

Where both hold, water concentrates and runs. Building across such ground does
not merely add runoff, it obstructs runoff that was already passing through, and
the second effect is typically much the larger of the two.
