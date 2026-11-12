id: rule.lake-buffer.ngt-75m
title: NGT 75 m lake buffer, upheld by the Supreme Court
kind: rule
tags: ["buffer", "lake", "setback", "ngt", "supreme court", "tribunal", "forward foundation"]
authority: court
source: NGT O.A. 222/2014, Forward Foundation v. State of Karnataka, upheld by the Supreme Court
url: https://greentribunal.gov.in/REPLACE-WITH-ORDER
verify: true
asserts: {"lakeM_ngt": {"v": 75, "u": "m"}, "drainM_ngt": {"v": 50, "u": "m"}}
when: [["ruleId", "eq", "ngt"]]
conflicts: ["rule.lake-buffer.state-30m"]
intents: ["feasibility", "procedure"]
---
The National Green Tribunal fixed a 75 m no-construction buffer around lakes and
50 m around primary stormwater drains, measured from the boundary outward. The
Supreme Court upheld it.

This is the wider of the two regimes. It is also the one this tool can test
confidently: 75 m is comfortably outside the measurement uncertainty, so a plot
inside it can be called inside it rather than referred.

The buffer is a prohibition on construction, not a taking of title. A plot may
be lawfully owned and still be unbuildable.
