id: limit.routing-is-not-a-drain-network
title: The traced route follows terrain, not pipes
kind: limit
tags: ["route", "trace", "limit", "drain", "network", "pipes", "downstream", "not a flood", "receiving"]
authority: repo-derived
source: index.html, traceDownstream and the downstream panel
repo_ref: index.html#L2000-L2152
when: [["routeTraced", "eq", true]]
intents: ["consequence", "evidence", "flood"]
---
The terrain model resolves catchment drainage at a scale far coarser than a
single storm drain, so a route crossing a built-up block says water runs
downhill across it, not that a channel exists there.

What the trace is good for is naming the ground that receives what a plot sheds,
and ranking it by how much catchment concentrates there. What it cannot say is
that the water arrives, because arrival depends on a drain network this tool
does not hold. A downstream finding is a lead for verification, the same way a
drainage finding is.
