id: limit.no-drain-capacity-modelled
title: Nothing here models what the drains can carry
kind: limit
tags: ["capacity", "drain", "hydraulic", "carry", "overflow", "network", "not modelled", "flood"]
authority: repo-derived
source: index.html, the scope of the downstream mode
repo_ref: README.md#L67-L73
when: [["intent", "eq", "flood"]]
intents: ["flood", "consequence"]
---
Whether a given storm overwhelms the drains depends on the geometry, gradient,
condition and current blockage of the network carrying the water away. None of
that is in this tool, and none of it is derivable from the satellite record.

So the tool can say how much additional runoff a plot generates and where the
land slopes, and cannot say whether that additional runoff exceeds what the
channel downhill can take. Those are different questions and only the first one
is answerable here.
