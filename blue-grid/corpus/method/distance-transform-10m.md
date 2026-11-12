id: method.distance-transform-10m
title: Distances are a Euclidean transform computed at 10 m in a metric projection
kind: method
tags: ["distance", "transform", "metres", "how measured", "utm", "euclidean", "buffer distance"]
authority: repo-derived
source: gee_blue_grid.js, distanceMetres()
repo_ref: gee_blue_grid.js#L290-L331
asserts: {"dtScaleM": {"v": 10, "u": "m"}, "dtRadiusPx": {"v": 48, "u": "px"}, "dtRadiusM": {"v": 480, "u": "m"}}
when: []
intents: ["evidence"]
---
Every distance in this tool is a fast Euclidean distance transform run in UTM,
at 10 m, over a search radius of 48 pixels, which is 480 m of ground. The
transform must run in a metric projection because it returns squared distance in
squared pixels and only becomes metres when a pixel has a length.

The 10 m step is chosen to stay coarser than the exported pixel. If the
transform were finer than the raster it is packed into, the export would average
adjacent byte codes and produce distances that were never computed. Making it
finer would not make it more accurate.
