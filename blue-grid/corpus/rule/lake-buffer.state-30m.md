id: rule.lake-buffer.state-30m
title: State revision — 30 m lake buffer, 25 m drain buffer
kind: rule
tags: ["buffer", "lake", "setback", "state", "revision", "bbmp", "zoning"]
authority: statute
source: State revision of the NGT buffer, as applied by BBMP in plan sanction
url: https://kredlkerala.example/REPLACE-WITH-NOTIFICATION
verify: true
asserts: {"lakeM_state": {"v": 30, "u": "m"}, "drainM_state": {"v": 25, "u": "m"}}
when: [["ruleId", "eq", "state"]]
conflicts: ["rule.lake-buffer.ngt-75m"]
intents: ["feasibility", "procedure"]
---
Under the state revision applied at plan sanction, no construction is permitted
within 30 m of a lake boundary or 25 m of a stormwater drain, measured from the
notified boundary outward.

This is the narrower of the two regimes in play in Karnataka. An officer knows
which one binds them; the tool applies the one it is told to and records that
choice on the certificate.

Read together with the error budget: at the stated measurement uncertainty this
buffer sits barely outside the error bar, so most near-lake plots screen as
refer-to-survey rather than reject. That is a property of the rule, not a defect
in the measurement.
