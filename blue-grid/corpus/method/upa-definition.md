id: method.upa-definition
title: Upstream drainage area is how much land drains through a point
kind: method
tags: ["upstream", "catchment", "drainage area", "upa", "how much land", "flow", "contributing"]
authority: dataset-doc
source: MERIT Hydro v1.0.1, upstream drainage area band
url: https://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Hydro/
when: [["upaKm2", "notnull"]]
intents: ["consequence", "flood"]
---
Upstream drainage area at a point is the total area of land uphill of it whose
runoff passes through that point on its way downhill. It is measured in square
kilometres and it grows monotonically downstream.

It is the number that separates a plot on a minor slope from a plot astride a
channel that the surrounding neighbourhoods drain through. Blocking the first
displaces the rain that falls on the plot. Blocking the second displaces that,
plus whatever the upstream area delivers during the same storm, which is the
larger quantity by orders of magnitude.
