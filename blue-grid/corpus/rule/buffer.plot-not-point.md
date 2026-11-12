id: rule.buffer.plot-not-point
title: A buffer applies to the footprint, so the nearest corner governs
kind: rule
tags: ["plot", "footprint", "frontage", "corner", "nearest", "radius", "size"]
authority: repo-derived
source: index.html, the minimum reduction in readSite()
repo_ref: index.html#L726-L744
when: [["plotM", "gte", 5]]
intents: ["feasibility", "evidence"]
---
A buffer is breached if any part of the plot falls inside it, so every distance
here is the nearest approach over the assumed footprint, not the distance from
its centre. Taking the centre, or the maximum, would pass every corner plot that
clips a lake edge.

The footprint is an assumption, not a measurement. The tool assumes a square
plot of the stated frontage centred on the click, and the frontage is operator
input. Enlarging it moves every distance closer and can change the outcome,
which is why the assumed frontage is printed on the certificate beside the
distances it produced.
