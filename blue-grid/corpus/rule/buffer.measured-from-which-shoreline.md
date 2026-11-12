id: rule.buffer.measured-from-which-shoreline
title: A buffer measured from today's shoreline can be a buffer from an encroachment
kind: rule
tags: ["buffer", "shoreline", "retreat", "measured from", "boundary", "shrunk", "disagree"]
authority: repo-derived
source: index.html, the shoreline-disagreement branch of decide()
repo_ref: index.html#L782-L791
when: [["retreatM", "gt", 30]]
intents: ["feasibility", "consequence", "evidence"]
---
An applicant measures their setback from the water's edge as it stands today.
Where the lake has already shrunk, that edge is itself the product of earlier
encroachment, and a buffer drawn from it lands somewhere a buffer drawn from the
original boundary would not.

This tool measures both: from the water edge in the recent record and from the
edge in the earliest record available. When the two disagree by more than one
source pixel it says so and refers the plot, because the question of which
boundary governs is a legal one about the notified boundary, not a question the
satellite record can settle.
