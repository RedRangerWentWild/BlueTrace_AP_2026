id: hydro.rational-method.volumetric-form
title: Volume displaced, not peak flow
kind: hydro
tags: ["rational method", "volume", "peak", "flow", "discharge", "calculation", "formula", "method"]
authority: dataset-doc
source: PLACEHOLDER pending CPHEEO Manual, storm water drainage chapter
url: https://cpheeo.gov.in/REPLACE-WITH-MANUAL
verify: true
when: []
intents: ["flood", "consequence", "evidence"]
---
The usual drainage calculation estimates a peak rate of flow, which requires a
time of concentration and is used to size a pipe. This tool does not size pipes
and does not have a defensible time of concentration for a single plot.

It uses the volumetric form instead: the depth of the design storm, multiplied
by the plot area, multiplied by the change in runoff coefficient. That yields
the extra volume of water the development sends downhill during one such storm.
It is arithmetic on three stated numbers and can be checked by hand, which is
the reason for preferring it.
