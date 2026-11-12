id: hydro.design-rainfall.bengaluru
title: The design storm used for runoff arithmetic
kind: hydro
tags: ["rainfall", "storm", "design", "mm", "intensity", "idf", "return period", "how much rain"]
authority: dataset-doc
source: PLACEHOLDER pending IMD Bengaluru intensity-duration-frequency curve or the BBMP stormwater design storm
url: https://mausam.imd.gov.in/REPLACE-WITH-IDF
verify: true
asserts: {"P_mm": {"v": 60, "u": "mm", "pm": 24, "note": "one-hour design depth, placeholder"}, "P_durationMin": {"v": 60, "u": "min"}, "P_annualMm": {"v": 970, "u": "mm"}}
when: []
intents: ["flood", "consequence"]
---
Runoff arithmetic here uses a design depth of 60 mm falling in 60 minutes, and
an annual total of 970 mm for the yearly figure.

This value is a placeholder and carries the widest uncertainty of anything in
the tool, roughly plus or minus 24 mm, dominated by the choice of return period
rather than by any measurement. It must be replaced with the published
intensity-duration-frequency figure for this city before any output is relied
on. Every volume the tool reports scales linearly with it, so replacing it
rescales every runoff number at once and changes nothing else.
