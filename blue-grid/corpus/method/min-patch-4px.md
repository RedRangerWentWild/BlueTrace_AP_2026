id: method.min-patch-4px
title: Isolated pixels are dropped before anything is called lost water
kind: method
tags: ["patch", "speckle", "noise", "isolated", "connected", "filter", "minimum size"]
authority: repo-derived
source: gee_blue_grid.js, the connected-pixel filter on lost water
repo_ref: gee_blue_grid.js#L128-L134
asserts: {"minPatchPx": {"v": 4, "u": "px"}}
when: []
intents: ["evidence"]
---
A single pixel that changes class between two epochs is usually noise: a shadow,
a misregistration, a wet patch after rain. The loss layer keeps only patches of
at least 4 connected pixels.

This costs the tool genuinely small losses, and that cost is one-directional and
known. It buys a map where every visible patch is large enough to go and look
at, which is what the output is for. A speckled map that is technically more
complete would be less usable and no more true.
