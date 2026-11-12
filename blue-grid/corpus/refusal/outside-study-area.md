id: refusal.outside-study-area
title: Outside the mapped rectangle there is no evidence at all
kind: refusal
tags: ["outside", "not covered", "no data", "study area", "boundary", "elsewhere", "other city"]
authority: repo-derived
source: index.html, the first branch of decide()
repo_ref: index.html#L750-L751
when: [["inAoi", "eq", false]]
intents: ["feasibility", "procedure", "evidence"]
---
The layers cover one rectangle. A point outside it has no measurement, and the
tool returns a referral saying so rather than a value.

Nothing is reported for such a point: no distance, no exposure class and no
displaced volume. A volume computed for a plot the tool holds no evidence about
would be arithmetic on assumptions alone, which is indistinguishable in
appearance from a measurement and is not one. Extending coverage is a matter of
re-running the extraction over a different rectangle.
