id: rule.outcome.none-is-approve
title: None of the outcomes is an approval
kind: rule
tags: ["approve", "approval", "permission", "sanction", "outcome", "allowed", "screening"]
authority: repo-derived
source: index.html, the OUTCOME table and the comment above decide()
repo_ref: index.html#L746-L748
asserts: {"n_outcomes": {"v": 4}}
always: true
when: []
intents: ["feasibility", "procedure"]
---
There are 4 outcomes and deliberately none of them is approve. This screens; it
does not grant permission.

The best available outcome is that nothing was found — no recorded water body,
no buffer breach, no drainage line within the measurement uncertainty of the
plot. That is a statement about the satellite record, not a licence.

Asked whether a construction should be allowed, the honest answer is what the
record shows and what it cannot show, followed by who decides. The deciding
authority is the sanctioning authority. It is never this tool, and it is never
the model reading this.
