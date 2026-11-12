id: hydro.hand.exposure-classes
title: Height above drainage, as an ordinal exposure class
kind: hydro
tags: ["hand", "height", "above drainage", "class", "exposure", "low", "elevated", "metres above"]
authority: repo-derived
source: index.html, the exposure classes in siteContext()
repo_ref: index.html#L726-L744
asserts: {"handAtM": {"v": 0, "u": "m"}, "handDeepM": {"v": 1, "u": "m"}, "handLowM": {"v": 2, "u": "m"}, "handMarginalM": {"v": 5, "u": "m"}}
when: [["handM", "notnull"]]
intents: ["flood", "consequence", "feasibility"]
---
Height above the nearest drainage line is banded rather than read as a depth. At
0 m the plot is at channel level. Up to 1 m it sits inside a water path, which
is the band that triggers a retention and plinth condition. Up to 2 m it is low
ground and counts as flood-prone. Up to 5 m it is marginal. Above that it is
elevated relative to its own drainage.

The bands are ordinal. A plot in a lower band is exposed sooner and longer than
one in a higher band. Nothing in the banding says how much water, or how often.
