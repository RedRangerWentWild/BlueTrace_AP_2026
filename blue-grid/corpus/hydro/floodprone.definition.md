id: hydro.floodprone.definition
title: What this tool calls flood-prone
kind: hydro
tags: ["flood prone", "low ground", "definition", "floodprone", "purple", "layer", "at risk"]
authority: repo-derived
source: gee_blue_grid.js, the floodProne definition
repo_ref: gee_blue_grid.js#L143-L152
when: [["handClass", "in", ["AT_DRAINAGE_LEVEL", "DEEP_IN_A_WATER_PATH", "LOW_GROUND"]]]
intents: ["flood", "consequence"]
---
Flood-prone here means ground standing below the low-ground threshold above the
channel it drains into. It is a topographic statement and nothing more: this
ground is near the level of the water that passes it.

It is not a flood zone, not a return-period map and not a statement that water
has reached this point or will. Ground this low fills first when a channel
exceeds its section and empties last, which is enough to justify a plinth and
retention condition, and not enough to justify a depth, a frequency or a
probability.
