id: limit.merit-90m-drain-order
title: Drain order and drain position are not resolved
kind: limit
tags: ["drain", "resolution", "limit", "order", "primary", "secondary", "position", "uncertain"]
authority: repo-derived
source: README, Known limits
repo_ref: README.md#L142
when: [["flowClass", "in", ["ON_FLOW_PATH", "ADJACENT", "NEAR"]]]
intents: ["feasibility", "consequence"]
---
The terrain model resolves catchment-scale drainage. It does not resolve which
order a drain is, how wide it is, or exactly where its alignment runs, and the
buffer that applies depends on all three.

A drainage finding from this tool is therefore always a referral and never a
rejection. It says a channel appears to pass close to this plot and the
alignment record should be checked. If the record shows no drain there, the
record governs and the finding was a false lead, which is an acceptable cost for
a screening step.
