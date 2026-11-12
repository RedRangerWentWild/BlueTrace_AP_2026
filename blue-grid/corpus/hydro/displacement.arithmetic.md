id: hydro.displacement.arithmetic
title: How the displaced volume is computed
kind: hydro
tags: ["displaced", "volume", "cubic metres", "extra water", "how calculated", "runoff", "arithmetic"]
authority: repo-derived
source: index.html, the derived quantities in siteContext()
repo_ref: index.html#L726-L744
when: [["runoffDisplacedM3", "notnull"]]
intents: ["flood", "consequence"]
---
Displaced volume is the plot area in square metres, times the design storm depth
in metres, times the change in runoff coefficient. Each of the three inputs is
declared with its own source and its own uncertainty, and the result is reported
to two significant figures with a plausible range rather than as a point value.

The uncertainty is dominated by the design storm and the coefficient change, not
by the plot area. Combined it is large enough that a reader should treat the
figure as an order of magnitude with a direction, and small enough that the
direction is unambiguous: development on open ground sends more water downhill.
