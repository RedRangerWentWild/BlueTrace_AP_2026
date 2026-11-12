id: method.probe-disc-min-reduction
title: Each reading is reduced over a disc, not taken at a point
kind: method
tags: ["sample", "probe", "disc", "minimum", "maximum", "reduction", "how read", "pixel"]
authority: repo-derived
source: index.html, readSite() and sampleCh()
repo_ref: index.html#L508-L542
when: []
intents: ["evidence"]
---
A click is not a point measurement. The tool reads every pixel within a disc the
size of the assumed plot and reduces them.

Distances take the minimum, because a buffer is breached by the nearest corner.
The last year water was recorded and the occurrence take the maximum, because
the strongest evidence of water anywhere under the footprint is the evidence
that matters. Height above drainage takes the minimum, because the lowest ground
under the footprint is what floods.

Each reduction is chosen to be the conservative one for the decision it feeds.
Together they make the screening err toward referral.
