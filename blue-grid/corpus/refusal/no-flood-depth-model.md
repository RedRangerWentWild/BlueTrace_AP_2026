id: refusal.no-flood-depth-model
title: What a real flood-depth answer would require
kind: refusal
tags: ["depth", "how deep", "water level", "metres of water", "inundation", "model", "simulate", "rise"]
authority: repo-derived
source: index.html, the stated scope of the terrain layers
repo_ref: README.md#L124-L150
always: true
when: [["intent", "eq", "flood"]]
intents: ["flood"]
---
Producing a defensible flood depth for a plot needs four things this tool does
not have: the geometry and condition of the drain network carrying water away, a
fine-resolution elevation model rather than a coarse global one, a local
intensity-duration-frequency curve, and a hydraulic solver routing water over
that surface with stated boundary conditions.

Without them a depth would be a guess wearing a unit. Naming the four missing
inputs is more useful than producing one, because it tells whoever needs the
answer what to go and commission.
