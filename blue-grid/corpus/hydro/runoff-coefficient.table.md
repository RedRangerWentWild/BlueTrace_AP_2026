id: hydro.runoff-coefficient.table
title: Runoff coefficients before and after development
kind: hydro
tags: ["runoff", "coefficient", "impervious", "paving", "roof", "absorb", "soak", "before after"]
authority: dataset-doc
source: PLACEHOLDER pending CPHEEO Manual on Sewerage and Sewage Treatment, storm water drainage chapter, or IRC SP:50
url: https://cpheeo.gov.in/REPLACE-WITH-MANUAL
verify: true
asserts: {"C_pre": {"v": 0.30}, "C_post": {"v": 0.85}, "dC": {"v": 0.55, "pm": 0.15}}
when: []
intents: ["flood", "consequence"]
---
A runoff coefficient is the fraction of rain falling on a surface that leaves it
as surface flow rather than soaking in or evaporating.

Open, unbuilt urban land is taken at 0.3, the middle of the usual pervious band.
A developed plot of roof and paving is taken at 0.85, the middle of the built-up
band. The change is therefore 0.55, with an uncertainty of about 0.15 covering
how much of the plot is actually sealed and what the soil beneath was like.

Both figures are stated defaults pending the published tables, and both are
operator-editable.
