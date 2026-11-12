id: rule.jurisdiction.bbmp-zones
title: Study area and which authority holds it
kind: rule
tags: ["zone", "jurisdiction", "bommanahalli", "mahadevapura", "bbmp", "where", "study area", "catchment"]
authority: repo-derived
source: index.html, the CITIES table
repo_ref: index.html#L304-L322
when: [["inAoi", "eq", true]]
intents: ["procedure", "evidence"]
---
The mapped area is the Bellandur and Varthur catchment, falling in the
Bommanahalli and Mahadevapura zones of BBMP. Plan sanction, drain alignment
records and encroachment removal for a plot here sit with that authority.

Outside the mapped rectangle this tool holds no evidence at all. It does not
degrade gracefully beyond the boundary; it stops. A click outside returns a
referral saying so, and no measurement, distance or volume is reported for it,
because a number computed from absent evidence would be a fabrication.
