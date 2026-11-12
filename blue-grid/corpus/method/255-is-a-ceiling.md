id: method.255-is-a-ceiling
title: 255 is a ceiling, not a measurement
kind: method
tags: ["255", "ceiling", "saturated", "beyond", "far", "no value", "clamp"]
authority: repo-derived
source: index.html, the metres() formatter
repo_ref: index.html#L823
asserts: {"byteCeiling": {"v": 255}}
when: []
intents: ["evidence"]
---
Distances are packed into a single byte, so the largest value they can carry is
255. A pixel reading 255 is not 255 m from the feature; it is somewhere beyond
the range the search covered.

The tool prints such a reading as beyond the ceiling rather than as a number,
and any answer that quotes it as a distance is wrong. In practice this only
happens well away from water and drainage, where the exact distance carries no
decision weight anyway — which is why the ceiling was set where it was.
