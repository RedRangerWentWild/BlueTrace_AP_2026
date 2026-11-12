id: method.no-learned-model
title: There is no learned model in the pipeline
kind: method
tags: ["model", "machine learning", "trained", "confidence score", "black box", "reason", "why flagged"]
authority: repo-derived
source: README, Accuracy
repo_ref: README.md#L173-L175
always: true
when: []
intents: ["evidence", "feasibility"]
---
Nothing in this pipeline is trained. Every flag traces to a published dataset
and a stated threshold, which means the reason for any individual flag can be
handed over in full rather than reported as a confidence score.

That is a deliberate trade. A learned model would very likely detect more, and
would be unable to say why it detected any particular thing. For an output whose
purpose is to survive being questioned by the person it is used against, the
reason is worth more than the recall.

The language model reading this explains those reasons. It does not produce them.
