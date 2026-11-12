id: limit.dynamic-world-built-understates
title: Built-up area under tree canopy is undercounted
kind: limit
tags: ["canopy", "trees", "built", "understate", "dynamic world", "land cover", "conservative"]
authority: repo-derived
source: README, Known limits
repo_ref: README.md#L143-L145
when: []
intents: ["evidence"]
---
The land cover classification is conservative about calling a pixel built when
tree canopy covers part of it. Across a green, low-rise catchment that biases
the built-on-former-water area downward.

The hectare figure for construction on former water is therefore a floor rather
than an estimate. The count of individual building footprints intersecting
former water is the stronger number, because it rests on footprint geometry
rather than on a per-pixel land cover call, and it should be preferred whenever
both are available.
