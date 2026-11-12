id: method.hand-merit-90m
title: Terrain comes from MERIT Hydro, precomputed, at 90 m
kind: method
tags: ["merit", "hydro", "terrain", "hand", "height above drainage", "dem", "elevation", "90"]
authority: dataset-doc
source: MERIT Hydro v1.0.1, upstream drainage area and height above nearest drainage
url: https://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Hydro/
asserts: {"meritScaleM": {"v": 90, "u": "m"}}
when: []
intents: ["evidence", "consequence"]
---
Height above nearest drainage and upstream drainage area are both taken
precomputed from MERIT Hydro at 90 m. There is no flow accumulation calculated
here and no digital elevation model processed here.

Height above nearest drainage is the vertical drop from a point to the channel
it drains into. It is an exposure ordinal, not a flood depth: low ground near a
channel floods first and drains last, which is a different statement from
saying how deep the water gets. At 90 m the model resolves catchment drainage
and not the individual drain outside a particular plot.
