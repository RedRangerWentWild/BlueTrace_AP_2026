id: method.routing.d8-trace
title: How the downstream route is traced
kind: method
tags: ["route", "trace", "downstream", "where does it go", "path", "d8", "step", "receiving", "who pays"]
authority: repo-derived
source: index.html, traceDownstream
repo_ref: index.html#L2050-L2152
asserts: {"routeStepM": {"v": 90, "u": "m"}, "routeMaxSteps": {"v": 200}, "routeCorridorM": {"v": 150, "u": "m"}}
when: [["routeTraced", "eq", true]]
intents: ["consequence", "evidence"]
---
The trace follows the terrain model's own flow-direction field one cell at a
time, stepping 90 m because that is the cell size. Stepping one export pixel
instead would read the same cell over and over and invent precision the source
does not have.

It stops at an outlet, a closed depression, a trunk channel, the edge of the
study area, a cell already visited, or 200 steps. Diagonal steps cross more
ground than orthogonal ones and are counted that way. Structures are counted
where they fall within 150 m of the line.
