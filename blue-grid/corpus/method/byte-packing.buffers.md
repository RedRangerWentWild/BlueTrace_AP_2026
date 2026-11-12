id: method.byte-packing.buffers
title: buffers.png carries three distances, one per channel
kind: method
tags: ["buffers", "channel", "packing", "red", "green", "blue", "raster", "how stored"]
authority: repo-derived
source: README, Layer channels
repo_ref: README.md#L106-L117
when: []
intents: ["evidence"]
---
One export carries measurement rather than colour and is never drawn. Its red
channel is metres to the water edge in the recent record, its green channel is
metres to the water edge in the earliest record, and its blue channel is metres
to the nearest terrain-derived drainage line.

Reading it is a straight byte lookup: no scaling, no interpolation, no rounding
step that could drift. That is why the exported ranges were chosen to fit a byte
in the first place. The plot check samples this file in an offscreen canvas,
with smoothing disabled, at full resolution.
