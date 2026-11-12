id: hydro.displacement.is-not-a-flood-depth
title: A displaced volume is not a flood depth
kind: hydro
tags: ["depth", "level", "how deep", "water level", "volume", "not the same", "flood", "rise"]
authority: repo-derived
source: index.html, the scope of the runoff arithmetic
repo_ref: README.md#L5-L8
always: true
when: [["intent", "eq", "flood"]]
intents: ["flood", "consequence"]
---
The volume a plot displaces is a quantity of water. How deep that water stands
somewhere downhill depends on where it goes, what carries it, what is already in
the channel and how fast it drains, none of which this tool holds.

So the volume can be stated and the depth cannot. The volume is still the useful
number, because it is additive: it is what the plot contributes to a total that
a drainage authority holding the network model can convert into a level. This
tool supplies the term. It does not solve the equation.
