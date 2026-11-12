id: method.byte-packing.hydro
title: hydro.png packs upstream area on a log scale
kind: method
tags: ["hydro", "packing", "log", "upstream", "trunk", "elevation", "channel", "how stored"]
authority: repo-derived
source: gee_blue_grid.js, the hydro export
repo_ref: gee_blue_grid.js#L394-L449
asserts: {"upaCeilingKm2": {"v": 1000, "u": "km2"}, "trunkUpaKm2": {"v": 10, "u": "km2"}}
when: [["upaKm2", "notnull"]]
intents: ["evidence", "consequence"]
---
Upstream drainage area spans several orders of magnitude across one catchment,
so packing it linearly into a byte would spend almost the whole range on the
trunk channel and leave the tributaries indistinguishable. It is packed
logarithmically instead, with a ceiling of 1000 square kilometres, which holds
the relative resolution roughly constant across the range.

This is the one place the tool scales a byte on decode rather than reading it
straight, so the log law is printed on the certificate. The same file also
carries metres to the nearest trunk channel, defined as one draining more than
10 square kilometres, and metres above the lowest point in the study area.
