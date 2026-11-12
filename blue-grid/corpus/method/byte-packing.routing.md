id: method.byte-packing.routing
title: How the flow-direction layer is packed
kind: method
tags: ["routing", "direction", "d8", "flow direction", "encoding", "packing", "remap", "merit", "downstream"]
authority: repo-derived
source: gee_blue_grid.js, section 14
repo_ref: gee_blue_grid.js#L470-L515
when: [["routeTraced", "eq", true]]
intents: ["evidence", "consequence"]
---
The routing layer carries one measurement and two reserved channels. Red holds
the flow direction, remapped off the terrain model's native powers of two into a
compact index: eight compass directions, then one code for an outlet and one for
a closed depression, with zero reserved for nodata.

The remap runs before reprojection, so no resampling step ever sees a power of
two and every legal value sits in a contiguous run. That is what lets the
encoding check assert legality directly, because an averaged direction lands
between the codes rather than on one.
