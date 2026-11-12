id: error.budget.combined-20m
title: Every distance in this tool carries about twenty metres of uncertainty
kind: error
tags: ["error", "uncertainty", "accuracy", "plus minus", "budget", "tolerance", "how precise", "20"]
authority: repo-derived
source: index.html, ERROR_BUDGET
repo_ref: index.html#L355-L362
asserts: {"uncertaintyM": {"v": 20, "u": "m"}, "errShorelineM": {"v": 15, "u": "m"}, "errQuantumM": {"v": 7, "u": "m"}, "errGeorefM": {"v": 6, "u": "m"}}
always: true
when: []
intents: ["evidence", "feasibility"]
---
Four terms make up the budget. The position of a shoreline within a source pixel
contributes about 15 m. The quantisation of the distance transform contributes
about 7 m. One pixel of georeferencing slack contributes about 6 m. The
thumbnail resample and the byte decode contribute nothing, being nearest
neighbour and exact.

Combined in quadrature that is about 20 m, and it attaches to every distance
this tool reports. A distance should never be stated as exact, and two distances
differing by less than the budget should never be described as different.
