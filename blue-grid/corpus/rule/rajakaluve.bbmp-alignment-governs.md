id: rule.rajakaluve.bbmp-alignment-governs
title: The BBMP rajakaluve alignment governs, not the terrain model
kind: rule
tags: ["rajakaluve", "drain", "storm water", "alignment", "survey number", "bbmp", "kaluve"]
authority: agency-survey
source: BBMP stormwater drain survey and the notified rajakaluve alignment
url: https://bbmp.gov.in/REPLACE-WITH-SWD-ALIGNMENT
verify: true
when: [["flowClass", "in", ["ON_FLOW_PATH", "ADJACENT", "NEAR"]]]
intents: ["feasibility", "procedure"]
---
What this tool calls a drainage line is a channel derived from a terrain model.
It is where water runs downhill. A rajakaluve is a drain with a notified
alignment, a width and a survey record, and the two are related but not the
same object.

Where the terrain says water flows and the record shows no drain, that is worth
checking and nothing more. Where the record shows a drain, the record governs.
The tool therefore never rejects a plot on drainage evidence alone; it refers it
to the alignment held against that survey number.
