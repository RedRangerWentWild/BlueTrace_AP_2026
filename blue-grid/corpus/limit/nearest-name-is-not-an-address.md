id: limit.nearest-name-is-not-an-address
title: The locality shown against a structure is the nearest name, not an address
kind: limit
tags: ["label", "address", "locality", "structure", "building", "name", "which", "belongs"]
authority: repo-derived
source: index.html, nearestSettlement() used to label flagged footprints
repo_ref: index.html#L1279-L1295
when: []
intents: ["evidence", "consequence"]
---
Flagged footprints are listed against the nearest settlement or road name so
that one row can be told from another. That label is computed from distance
alone and is chosen only from settlements and roads, never from a water body,
because naming a building after a lake would assert the finding the screening
exists to make.

It is not an address and not a jurisdiction. It does not identify an owner, an
occupant, a khata or a survey number, and it does not establish which ward or
panchayat the footprint falls in. Two structures on opposite sides of a boundary
can carry the same label.
