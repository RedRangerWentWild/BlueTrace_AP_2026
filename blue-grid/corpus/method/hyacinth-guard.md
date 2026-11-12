id: method.hyacinth-guard
title: Hyacinth-covered water is protected from being read as destroyed
kind: method
tags: ["hyacinth", "vegetation", "bellandur", "varthur", "weed", "green", "false positive"]
authority: repo-derived
source: gee_blue_grid.js, the still-wet guard
repo_ref: gee_blue_grid.js#L113-L134
when: []
intents: ["evidence"]
---
A lake under a mat of water hyacinth reflects like vegetation, and every water
index reads it as land. Left alone, the pipeline would report the largest lakes
in this catchment as destroyed, which would be both wrong and the most visible
thing on the map.

Land cover classified as water or as flooded vegetation in the recent record is
therefore treated as surviving water and excluded from the loss finding. The
guard is deliberately generous: it trades some real loss going unreported
against the alternative of headline false positives on the two lakes everyone
checks first.
