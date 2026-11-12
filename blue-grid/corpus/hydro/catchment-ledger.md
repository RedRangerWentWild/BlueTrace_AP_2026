id: hydro.catchment-ledger
title: The catchment totals are read at runtime, not stated here
kind: hydro
tags: ["total", "hectares", "how much lost", "ledger", "summary", "city wide", "statistics"]
authority: repo-derived
source: data/<city>/stats.json, printed by the Earth Engine extraction
repo_ref: README.md#L42-L44
when: []
intents: ["evidence", "consequence"]
---
The catchment-wide figures — water lost, water surviving, built area on former
water, structures intersecting it — are computed by the extraction step and
loaded from the statistics file for the active city.

They are deliberately not written into this corpus. A total that is copied into
prose goes stale the first time the extraction is re-run over a different date
range, and then two numbers exist for one quantity with nothing to say which is
current. Any catchment total quoted in an answer must come from the loaded
statistics, not from here.
