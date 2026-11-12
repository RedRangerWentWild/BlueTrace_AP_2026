id: method.water.one-source-jrc-transition
title: Both eras of water come from one source and one method
kind: method
tags: ["jrc", "global surface water", "transition", "source", "how", "water", "classification"]
authority: dataset-doc
source: JRC Global Surface Water v1.4, transition and occurrence bands, Landsat archive 1984 to 2021
url: https://global-surface-water.appspot.com/
asserts: {"jrcScaleM": {"v": 30, "u": "m"}}
always: true
when: []
intents: ["evidence", "feasibility"]
---
Water then and water now are read from the same band of the same dataset: the
JRC transition classification, which compares the 1984 to 1999 record against
the 2000 to 2021 record across the whole Landsat archive using one method, at
30 m.

Using one source for both epochs is the point. A change detected inside a single
consistent classification is a change on the ground. A change detected between
two different classifications is partly a change of method, and there is no way
afterwards to say how much of it was which.
