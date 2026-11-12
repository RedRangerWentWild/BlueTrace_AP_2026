id: scope.building-layer-absent
title: The ranked building layer is not loaded
kind: scope
tags: ["buildings", "missing", "not loaded", "ranked", "list", "absent", "no footprints"]
authority: repo-derived
source: index.html, the optional building layer in loadCity()
repo_ref: index.html#L544-L609
when: [["hasBuildings", "eq", false]]
intents: ["evidence", "consequence"]
---
The building footprint layer for this city has not been exported, so no ranked
structures, per-building evidence or neighbourhood context is available. Every
other layer works without it.

That means an answer here can describe the ground under the plot and cannot say
what is already standing on or near it, and it should say so rather than leaving
the omission to be inferred. Producing the layer is one export task in the
extraction step; until it runs, statements about nearby flagged structures are
unavailable rather than negative.
