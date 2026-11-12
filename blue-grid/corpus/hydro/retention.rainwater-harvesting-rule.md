id: hydro.retention.rainwater-harvesting-rule
title: Some of the displaced volume is already required to be stored on site
kind: hydro
tags: ["retention", "rainwater", "harvesting", "storage", "sump", "rwh", "mitigation", "required"]
authority: statute
source: PLACEHOLDER pending the BWSSB rainwater harvesting storage requirement for Bengaluru
url: https://bwssb.karnataka.gov.in/REPLACE-WITH-RWH-RULE
verify: true
when: [["runoffDisplacedM3", "notnull"]]
intents: ["flood", "procedure", "consequence"]
---
Bengaluru already requires rainwater harvesting storage on new plots above a
size threshold. Where that storage is actually built and kept clear, part of the
volume a development displaces is held on site rather than sent downhill.

This matters for how a conditions result should be read. The mitigation being
asked for is usually not a new obligation but the existing one, sized against
the displacement this tool has computed and actually enforced. Comparing the
displaced volume against the required storage is the most useful single
comparison an officer can make with these numbers.
