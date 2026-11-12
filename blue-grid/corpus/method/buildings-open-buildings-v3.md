id: method.buildings-open-buildings-v3
title: Building footprints are filtered before they are ranked
kind: method
tags: ["buildings", "footprint", "open buildings", "confidence", "filter", "structure", "ranked"]
authority: dataset-doc
source: Google Open Buildings v3 polygons
url: https://sites.research.google/open-buildings/
asserts: {"obConfidence": {"v": 0.70}, "obMinAreaM2": {"v": 40, "u": "m2"}}
when: [["hasBuildings", "eq", true]]
intents: ["evidence", "consequence"]
---
Footprints come from Google Open Buildings, kept only where the model's
confidence is at least 0.70 and the footprint is at least 40 square metres. The
filter removes the two failure modes that would otherwise dominate a ranked
list: low-confidence artefacts on bare ground, and sheds.

Each surviving footprint is scored by how much of it sits on former water, how
much sits in a flow path, how much catchment drains through it and how low it
stands. The score orders a queue for verification. It is not a probability that
the structure is unlawful.
