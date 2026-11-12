id: hydro.tanker-equivalent
title: Volumes are also given in tankers, to be legible
kind: hydro
tags: ["tanker", "litres", "equivalent", "how much", "compare", "scale", "intuition"]
authority: editorial
source: Standard water tanker capacity in common use in Bengaluru
asserts: {"tankerL": {"v": 6000, "u": "L"}}
when: [["runoffDisplacedM3", "notnull"]]
intents: ["flood", "consequence"]
---
A volume in cubic metres means little to most readers of a screening note, so
the displaced volume is also expressed as a count of standard 6000 litre water
tankers.

The conversion carries no additional uncertainty of its own and adds no
information. It exists because a number that cannot be pictured is a number that
gets skipped, and the whole purpose of reporting displacement is that someone
weighs it. Where the count is small the honest reading is that a single plot is
a small term in a large sum, which is also worth saying plainly.
