id: method.why-not-hand-differencing
title: Why a Landsat composite is not differenced against a Sentinel-2 one
kind: method
tags: ["sentinel", "landsat", "difference", "asymmetric", "sensor", "why not", "comparison"]
authority: repo-derived
source: README, Method and where it is weak, on differencing Landsat against Sentinel-2
repo_ref: README.md#L126-L130
when: []
intents: ["evidence"]
---
The obvious approach is to classify water in an old composite, classify it in a
new one, and subtract. It cannot be made symmetric. The finer sensor finds more
water whatever is on the ground — narrow channels, pond margins, wet field
edges — so the subtraction reports water appearing wherever the newer sensor
simply looks harder.

Since the whole claim of this tool is water disappearing, a method with a known
bias toward finding water in the later epoch would undercut the one direction
that matters. The newer imagery is therefore shown, and used for land cover, but
never differenced for the water finding itself.
