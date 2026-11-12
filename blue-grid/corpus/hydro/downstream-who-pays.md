id: hydro.downstream-who-pays
title: The cost of a blocked flow path is paid downstream
kind: hydro
tags: ["downstream", "who pays", "impact", "consequence", "neighbour", "harm", "elsewhere"]
authority: repo-derived
source: README, the three modes
repo_ref: README.md#L67-L73
when: [["flowClass", "in", ["ON_FLOW_PATH", "ADJACENT"]]]
intents: ["consequence", "flood"]
---
Water that a tank used to hold, or that a flow path used to carry, does not stop
falling when the tank is filled or the path is built over. It finds another
route, and that route runs across land belonging to someone else.

This is the asymmetry the tool is built to make visible. The benefit of building
on low ground accrues to the plot. The cost accrues downstream, to people with
no part in the application and usually no notice of it. Ranking by how much
catchment a structure blocks is a way of ordering enforcement by that cost
rather than by complaint volume.
