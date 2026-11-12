id: refusal.no-approval-prediction
title: Whether the authority will approve is not predicted here
kind: refusal
tags: ["will it be approved", "chances", "likely", "predict", "sanction", "outcome", "get permission"]
authority: repo-derived
source: index.html, the comment above decide()
repo_ref: index.html#L746-L748
always: true
when: []
intents: ["feasibility", "procedure"]
---
Asked whether an application will be approved, this tool has nothing to say. It
does not know the sanction record, the applicant, the local practice or which
buffer regime the deciding officer applies.

What it can say is what a screening check against a stated ruleset finds, and
what the deciding authority would have to resolve before deciding. Converting
that into a likelihood of approval would mean modelling the authority rather
than the ground, which is a different exercise and not one this evidence
supports.
