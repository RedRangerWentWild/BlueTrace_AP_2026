id: refusal.not-a-flood-predictor
title: This tool does not predict flooding
kind: refusal
tags: ["flood", "predict", "forecast", "will it flood", "risk", "chance", "probability", "level"]
authority: repo-derived
source: README, the opening statement of scope
repo_ref: README.md#L5-L8
always: true
when: [["intent", "eq", "flood"]]
intents: ["flood", "consequence"]
---
This is an evidence tool, not a flood predictor. It reports what the satellite
record shows was water, what the terrain says about where water runs, and how
much additional runoff a development generates.

It does not say whether a place will flood, when, how often, or how deep. Those
are outputs of a hydraulic model with inputs this tool does not hold. Asked a
flooding question, the answerable part is the displaced volume and the
topographic exposure, and the unanswerable part should be named rather than
approximated.
