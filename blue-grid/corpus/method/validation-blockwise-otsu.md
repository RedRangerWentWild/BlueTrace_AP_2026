id: method.validation-blockwise-otsu
title: The reference is checked against an independent spectral method
kind: method
tags: ["validation", "accuracy", "mndwi", "otsu", "held out", "blocks", "check", "reproducible"]
authority: repo-derived
source: validate.py, blockwise Landsat 5 MNDWI against the JRC yearly reference
repo_ref: validate.py#L1-L20
asserts: {"valFrom": {"v": 2003}, "valTo": {"v": 2007}, "valCols": {"v": 6}, "valRows": {"v": 4}, "valHoldout": {"v": 8}}
when: []
intents: ["evidence"]
---
What can be tested is whether the reference this pipeline leans on is
reproducible by a different method over the same pixels in the same years. A
water index computed from Landsat 5 is scored against the JRC per-year
classification for 2003 to 2007, on a 6 by 4 grid with 8 blocks held out.

Blocks are contiguous tiles, not random pixels. Neighbouring pixels of one lake
are not independent samples and a pixel-wise split would inflate every score.
The threshold is fitted on training blocks only, and per-block scores are
reported alongside the pooled one.
