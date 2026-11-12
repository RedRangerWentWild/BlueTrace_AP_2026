id: method.byte-packing.history
title: history.png carries when water was last seen, how often, and height above drainage
kind: method
tags: ["history", "channel", "packing", "occurrence", "last year", "hand", "raster", "how stored"]
authority: repo-derived
source: gee_blue_grid.js, the history export
repo_ref: gee_blue_grid.js#L361-L375
asserts: {"yearEpoch": {"v": 1983, "note": "codes are year minus this"}}
when: []
intents: ["evidence"]
---
The second measurement export packs the last year water was recorded at that
pixel, offset from 1983 so it fits a byte and zero means never; the JRC
occurrence percentage, which is the share of all observations in which the pixel
was water; and the height of the ground above the nearest drainage line, in
metres.

Occurrence is the field that separates a tank from a wet season. A pixel that
was water in most observations was a water body. A pixel that was water in a
small minority of them may have been a flooded field, and at this resolution the
two cannot be told apart.
