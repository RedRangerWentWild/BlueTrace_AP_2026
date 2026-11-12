id: error.probe-radius-changes-the-answer
title: The assumed plot size changes the result, and is an input
kind: error
tags: ["plot size", "frontage", "radius", "assumed", "changes", "sensitivity", "input"]
authority: repo-derived
source: index.html, the plot frontage control and readSite()
repo_ref: index.html#L726-L730
when: [["plotM", "gt", 60]]
intents: ["feasibility", "evidence"]
---
Distances are the nearest approach over the assumed footprint, so a larger
assumed plot reaches closer to everything and can turn a clear result into a
referral, or a referral into a rejection.

The frontage is operator input, not a measurement of the actual plot. Where it
has been set well above a typical residential footprint, the result describes a
large site and should be read that way. The value used is printed on the
certificate next to the distances it produced, precisely so that a reader can
tell whether it was the right one.
