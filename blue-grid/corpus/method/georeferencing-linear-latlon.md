id: method.georeferencing-linear-latlon
title: Every layer is a linear stretch over one rectangle
kind: method
tags: ["georeference", "projection", "grid", "pixel", "alignment", "resolution", "raster", "coordinates"]
authority: repo-derived
source: index.html, the sampler, and the AOI bounds comment
repo_ref: index.html#L298-L303
asserts: {"exportW": {"v": 2048, "u": "px"}, "exportH": {"v": 1195, "u": "px"}, "mppM": {"v": 6.36, "u": "m/px"}}
when: []
intents: ["evidence"]
---
There is no affine transform stored anywhere. Each exported layer is 2048 by
1195 pixels stretched linearly across the study rectangle, which works out at
about 6.36 m of ground per pixel, and a lookup is arithmetic on the corner
coordinates.

The consequence is that every layer must share those dimensions exactly. If one
did not, its lookups would land on the wrong ground and the tool would return
confident measurements of the wrong place with nothing visibly amiss. An
encoding check gates on matching dimensions before it tests anything else.
