# BlueTrace

Reconstructs a city's lost water bodies from the satellite record, then flags the
buildings sitting on them and the low ground that floods as a result.

Not a flood predictor. An evidence tool: it says which structures are on former
water, ranks them by how much catchment they block, checks any plot before it
gets built on, and answers questions about that plot from a corpus where every
number carries the source it came from.

Full operating detail is below. For what the project is and why it is built
this way, see the [front page](../README.md).

---

## Run order

**1. Extract (Earth Engine, browser, ~2 min)**

Paste `gee_blue_grid.js` into <https://code.earthengine.google.com> and Run.
The console prints ten `PNG <name>: https://...` lines and six figures.

**2. Pull the layers down**

Copy every `PNG ...` line into `urls/bengaluru.txt`, then:

```
./fetch_layers.sh bengaluru
```

Earth Engine thumbnail URLs expire. If a download reports `BAD`, re-Run the
script and copy fresh links.

**3. Pull the buildings**

In Earth Engine, open the **Tasks** tab and run `blue_grid_flagged_buildings`.
It lands in Drive as `blue_grid_flagged_buildings.geojson`. Download it and
move it to:

```
data/bengaluru/flagged_buildings.geojson
```

This unlocks the ranked list, the per-building evidence panel, CSV export and
the structure count on the downstream panel. Everything else works without it.

The script also holds a direct `getDownloadURL` path behind
`TRY_DIRECT_DOWNLOAD`, **off by default**. It returns a link you paste into
`urls/<city>.txt` like any raster, and `fetch_layers.sh` understands a
`GEOJSON` line — but it is synchronous, and on a catchment this dense it hangs
the editor tab before it returns. The `risk_score > 1` filter shrinks the
output, not the work: the scoring is a `reduceRegions` over every Open
Buildings polygon in the study area against four rasters. Turn it on for a
sparse AOI; leave it off here.

**4. Update the numbers**

Put the printed hectare figures into `data/bengaluru/stats.json`.

**5. Build the corpus**

```
./build_corpus.py && ./check_corpus.py
```

The first compiles `corpus/**/*.md` into `data/corpus.json`. The second checks
it against the code it describes and refuses to pass if the two have drifted.
`data/corpus.json` is committed, so this is only needed after editing a chunk.

**6. Serve**

```
python3 server.py                          # answers stay local
ANTHROPIC_API_KEY=... python3 server.py    # answers get a model
GEMINI_API_KEY=... python3 server.py       # or Gemini
GROQ_API_KEY=... python3 server.py         # or Groq
```

`file://` will not work — the browser blocks local image sources over CORS.
`python3 -m http.server 8000` still serves everything except `/ask`, in which
case answers are composed locally and say so.

**7. Second city**

In `gee_blue_grid.js` set `var CITY = CITIES.chennai`, Run, repeat steps 2–4
with `chennai`, then:

```
./hotspots.py chennai
```

Paste the printed block into the `CITIES` table in `index.html`.

---

## The three modes

| Mode | Question it answers | Ground it draws on |
|---|---|---|
| **Timeline** | What was here, and what happened to it? Scrub the 2003–07 composite to the 2023–25 one. Space bar plays it. | Satellite, always — the imagery *is* the evidence |
| **Plot check** | May this plot be built on? Click anywhere for a screening decision against a selectable buffer regime. | Pale basemap by default |
| **Downstream** | Who pays? Low ground receiving the runoff the lost tanks used to hold, and the route from a checked plot to it. | Pale basemap by default |

The **Map / Satellite** switch in the bottom-right corner overrides that
default. Satellite imagery is the right ground when the question is *what
changed here* — you can see the lakebed and the rooftops standing on it. It is
the wrong ground when the question is *what constrains this plot*, because
canopy, shadow and rooftop all carry the same visual weight as a flagged
footprint. Timeline mode does not offer the switch.

Any plot or flagged structure can then be asked about in plain language —
*what happens if a construction occurs here*, *should this be allowed*, *will it
affect the flooding level*. See **Asking** below.

### What the plot check decides

Four outcomes, and deliberately none of them is *approve* — this screens, it
does not grant permission.

| | Meaning |
|---|---|
| **REJECT** | Inside live water, on a former water body with ≥ 50% occurrence, on a former bed that already carries construction, or confidently inside a buffer. |
| **REFER TO GROUND SURVEY** | The measurement cannot resolve the question at ±20 m, or the two shorelines disagree. |
| **CONDITIONS REQUIRED** | Low ground: retention and a plinth condition. |
| **NO RECORDED OBJECTION** | Nothing found — which at 30 m is not the same as nothing there. |

Occurrence deliberately does not carry that branch on its own. JRC occurrence
is the share of observations that were water across 1984–2021, so a tank drained
and built over part-way through the window scores *low* precisely because it was
destroyed — the more completely a bed was encroached, the weaker the only signal
that would have rejected it. A bed lost in 2017 came back at 16% and screened as
an unresolved wet season. Two corroborating signals now settle it: construction
already standing on the mapped bed, which is a rejection, and a bed still at the
level of the channel it drained into, which is a referral naming the reason.

The finding worth demonstrating is the shoreline disagreement. An applicant
measures their buffer from the water's edge *as it stands today*. Where the
lake has already shrunk, that edge is one encroachment produced, so the buffer
measured from the 1984–99 edge lands somewhere else entirely. When the two
distances differ by more than one JRC pixel the tool says so.

Buffer distances are **operator configuration**, not a legal determination:

| Ruleset | Lake | Drain |
|---|---|---|
| State revision | 30 m | 25 m |
| NGT, upheld by the Supreme Court | 75 m | 50 m |

A consequence worth knowing before anyone asks: at ±20 m measurement
uncertainty, the 30 m buffer is barely outside the error bar, so under that
ruleset most near-lake plots return REFER rather than REJECT. The 75 m buffer
is confidently testable. That is a fact about the rule, not a defect in the
tool.

### Layer channels

Four exports carry measurements rather than colour and are never drawn:

- `buffers.png` — R: metres to today's water edge · G: metres to the 1984–99
  edge · B: metres to the nearest drainage line. 255 means "beyond the ceiling".
- `history.png` — R: last year water was recorded, as `year − 1983`, 0 = never
  · G: JRC occurrence percent · B: height above nearest drainage, metres.
- `hydro.png` — R: upstream drainage area, **log-packed** as
  `255·log10(1+km²)/log10(1001)`, ceiling 1000 km² · G: metres to the nearest
  trunk channel (> 10 km²) · B: metres above the lowest ground in the study
  area. The only layer not read as a straight byte, so the decode law is
  printed on the certificate. Optional: without it every answer says upstream
  catchment is unavailable rather than guessing at it.
- `routing.png` — R: MERIT Hydro flow direction, remapped off its native powers
  of two into `0` nodata · `1` E · `2` SE · `3` S · `4` SW · `5` W · `6` NW ·
  `7` N · `8` NE · `9` mouth · `10` depression. G and B reserved. Optional:
  without it the downstream panel says so rather than tracing nothing and
  calling it a route.

The direction channel is **categorical**, and that changes what can be checked.
The graded-field rule that catches a collapsed distance field — more than thirty
distinct codes or it is a mask — would fail a perfectly good direction layer,
which legally holds eleven. Worse, passing it would prove nothing: a flow field
can be entirely plausible and entirely wrong. `verify_encoding.py` tests three
other things instead, and the third is the one that matters — upstream area must
be **non-decreasing downstream**. A transposed, flipped or bilinearly averaged
direction field breaks that immediately while still producing routes that look
like routes.

The distance transform runs at **10 m**, which must stay coarser than the
6.36 m/px export or the thumbnail downsamples and averages adjacent byte codes
into distances that never existed. Do not "optimise" it finer.

The plot check reads the same PNGs the map draws, pixel by pixel, in an
offscreen canvas. No server, no API, no network. It cannot fail on stage.

---

## Downstream — where the displaced water goes

The plot check can say a development displaces roughly N cubic metres per design
storm. Until now it could not say where those cubic metres went, which left
*who pays* a rhetorical question: a volume with no destination.

Click a plot and the tool now walks MERIT Hydro's own flow-direction field
downhill from it, one 90 m cell at a time, and draws the line. The panel names
the ground the route reaches, ranked by how much catchment concentrates there.

**It reports receiving, never inundation.** The route says water runs downhill
across this ground. It does not say the ground floods, and the tool still
refuses depth, level, extent and probability exactly as before — the four
refusal chunks are unchanged and a flooding question still forces them into
every answer.

### Why the direction field had to be exported

Nothing already on disk could substitute. `upa` says how much land drains
*through* a point and `hnd` says how deep it sits; neither says which way water
*leaves*. The obvious shortcut — descend `hydro.png`'s blue channel — does not
work: that channel is elevation above the study-area minimum, quantised to 1 m
over about 60 m of local relief, while a 90 m step across this catchment falls
roughly 0.05–0.2 m. Descending it would be descending the quantisation, and it
produces long flats, arbitrary jumps and closed loops that look exactly like
routes.

### Why the trace steps cells and not pixels

MERIT's cell is 90 m; the export is 6.36 m/px. Stepping one pixel at a time
would read the same cell about fourteen times and invent precision the source
does not have. Diagonal steps cross a factor of √2 more ground than orthogonal
ones and are counted that way — calling every step 90 m understates a diagonal
route by forty per cent.

The walk stops at an outlet, a closed depression, a trunk channel, the edge of
the study area, a cell already visited, or 200 steps. **Which of those ended it
is reported**, because a route that ran out of study area and a route that
reached a trunk channel are different findings and only one of them is complete.

### What is checked, and what is not claimed

`./verify_encoding.py` asserts three things about the direction field: every
code is legal, every trace terminates, and upstream area is non-decreasing
downstream. The third is the real guard. A flipped or averaged direction field
produces confident, plausible, wrong routes, and that invariant is what catches
it — it was written before any trace was trusted, and it caught the first test
fixture that tried to fake a flow field by descending distance-to-trunk.

`./validate.py <city> --routing` scores how often traced cells land on the
flow-path mask, which is built by a different code path from the same two bands.
It prints the baseline beside the figure, because agreement means nothing until
you know what agreement a random walk would score.

It is **not an accuracy**, and the output says so. Both readings come from MERIT
Hydro, so this is cross-method agreement inside one source rather than
independent corroboration. There is no surveyed drain network for this
catchment; anyone reporting how often these routes are right has invented it.
That is the same position `validate.py` already takes on lakes.

### The honest limit

The trace follows terrain, not pipes. MERIT resolves catchment drainage at a
scale far coarser than a single storm drain, so a route crossing a built-up
block says water runs downhill across it, not that a channel exists there. A
downstream finding is a lead for verification, in the same way a drainage
finding is — `limit/routing-is-not-a-drain-network.md` states this and rides
into every answer the route appears in.

---

## Retention — what it would take, and what could discharge it

A tool that only blocks gets overridden. Layer 3 says where the water goes;
this says what the site could be instead, so that refusing is not the only
thing on offer.

**The requirement is the displaced volume, read as an obligation.** Hold back
what sealing the plot added and the catchment below is no worse off than before
the permit. That needs no new parameter — it is the same figure the runoff
arithmetic already produced, which is why it stays checkable on paper.

### The storage rule is the officer's number, not the tool's

Bengaluru already requires rainwater harvesting storage on new plots, and part
of what a development displaces is therefore already meant to be held on site.
Comparing the two is the single most useful thing an officer can do with these
figures.

**This tool does not hold that rule.** No chunk states the figure, deliberately,
because nobody here has read it. So it is entered in the inspector beside the
buffer regime, and left blank it stays blank — a shortfall measured against a
number the tool guessed at would look exactly like a shortfall measured against
the rule in force. Same posture as the buffer distances: operator
configuration, not a legal determination.

That choice also keeps the corpus honest. `check_corpus.py` fails if anything
in the `@params` block lacks a declaring chunk, so putting the figure in
`PARAMS` would have forced this repo to invent a statute to satisfy its own
checker.

### It states a requirement and lists options. It never recommends

`BANNED` rejects *we recommend*, and the tool's whole posture is that it
screens rather than decides. So the panel names the uses that can hold the
volume and says which one applies is the authority's decision.

Options are corpus chunks of kind `option`, selected by the same trigger
channel retrieval uses — a chunk that fires in the panel is one the evidence
pack can also carry. They are ordered by the **specificity of the trigger that
fired**: an option that fired on *on the former bed and water most of the time*
precedes one that fired on *low ground*, which precedes the one available
anywhere. Ties fall back to a declared rank, because sorting them on chunk id
is deterministic and meaningless — it put the option available on any site
ahead of restoring a bed the plot is demonstrably sitting on.

| option | fires when |
|---|---|
| Restoration with the development value moved elsewhere | on the 1984–99 bed |
| A sunken park that holds the storm and looks like an amenity | low ground or at drainage level |
| Build around the channel rather than over it | on or beside a flow path |
| Return the water to the aquifer instead of to the drain | any site with a requirement |

All four are marked **drafted** in the panel and carry `verify: true`. They
describe policy mechanisms whose sources have not been read, and a panel that
looked equally confident about all of them would be claiming more than the
corpus does.

### When the panel does not appear

`recharge-structure` fires on *a requirement exists*, so it applies to every
plot in the study area. It is a real supplement and never a finding, and the
panel is suppressed when it is the only thing that fired.

That matters more than it sounds. Measured over twelve sites, seven came back
with no recorded objection and were still being handed a "requirement" of the
same thirty cubic metres and one option available anywhere — a demand the
screening had found no basis for, phrased as though it had, identically every
time. The panel now hangs on whether a **site-specific** option fired, and
shows on six of those twelve.

The gate is on the ground, not on the verdict. A plot on low ground that
screened as NO RECORDED OBJECTION still gets the sunken park, because the
alternative exists for the terrain the plot sits on rather than for the ruling
the screening reached.

### The volume is not a measurement of the site

It is plot area × design storm × the change in runoff coefficient, so it is the
same figure for any plot of that frontage anywhere in the study area — 30 m³ at
a 30 m frontage on a lakebed and on high ground a kilometre away alike. The
panel says so in as many words. What is specific to a location is **which uses
can hold it**, and that is what the list below the figure is for.

---

## The interface

Everything below is a legibility argument, not a style preference.

### Two eras, two hue families

The first version of this drew 1984–99 water in `#1f6feb` and 2000–21 water in
`#58a6ff`, over satellite imagery, and expected a viewer to tell two decades
apart by saturation. Nobody could, including the people who built it.

Water that survived is now **cyan**. Water that was lost is **amber**, which is
a different hue family, not a different shade of the same one. Built-on-former-
water stays **crimson**. Read together on one frame: cyan is the remnant, amber
is what used to surround it, red is what is standing on the difference.

Amber alone is not enough, because dry-season Landsat over Bengaluru is very
nearly the colour of amber. So the lost water carries two more signals:

- **It is hatched.** Diagonal stripes read as annotation in every mapping
  tradition there is, and the ground shows through between them at full
  chroma, so the amber stays amber instead of averaging into olive over
  vegetation. The hatch only appears at close zoom; across the whole catchment
  a 4 px period in a 2048 px raster downsamples below the point where stripes
  exist, so `update()` crossfades to a solid wash on zoom-out.
- **Its 1984–99 shoreline is drawn as a line.** `traceEdge()` walks the mask
  in the browser and marks every pixel on the inner boundary. That contour
  over today's ground, with red construction inside it, is the whole finding
  in one frame.

### The palette lives in the client, not in Earth Engine

`gee_blue_grid.js` still stamps a colour into every visual export, but each of
those layers is a **single flat colour behind an alpha mask** — the colour is
decoration, the alpha is the data. `tint()` repaints them on load. So the map
palette can change in `index.html` alone, without a two-minute Earth Engine run
and ten fresh thumbnail URLs, and the legend cannot drift out of step with the
map because both read `PALETTE`.

`DATA_LAYERS` never goes through `tint()`. Re-tinting a byte-packed distance
field would destroy the measurement.

### Chrome is monochrome

Graphite, paper, hairlines. Every colour on screen belongs to a layer or to a
verdict. A screening tool that paints its own buttons blue is telling the
reader that blue means *clickable* at the same moment the map is telling them
blue means *water*.

The interface is light because the artifact that leaves it is a printed,
signed certificate. What you sign is now what you saw.

### Type is self-hosted

Geist and Geist Mono, `assets/fonts/*.woff2`, about 84 KB. A demo that loses
the network must not also lose its typography, and a typeface swapping in two
seconds after the map is the most obvious tell there is that a page was thrown
together. `server.py` declares the `font/woff2` type because `mimetypes` does
not know it on every Python build and Chrome refuses a font served as
`application/octet-stream`.

Numbers are monospaced and tabular everywhere, prose is not. A column of
distances that does not align on the decimal cannot be scanned.

---

## Asking

The ask box is docked at the bottom of the window, in the same slot the
timeline occupies in timeline mode — one place to look for the control you drive
the tool with, and one that never moves as the answer grows. The answer opens
upward from it, so the input stays under the cursor.

Click a plot or a flagged structure, then ask. Three chips cover the questions
this was built for; the box takes anything.

The answer is **retrieved, not recalled**. Two channels feed it:

- **The site record.** Everything `readSite` already measured, plus what can be
  derived from it: runoff displacement, the exposure class, the shoreline
  retreat, the catchment draining through the point.
- **The corpus.** About seventy short chunks under `corpus/`, one idea each,
  every one carrying its source. Chunks declare numeric *triggers* over the
  site record — `distHistoric == 0`, `ruleId == ngt`, `handM <= 1` — and those
  triggers are the dominant retrieval signal. Wording similarity is the other
  35%, scored with BM25 over postings built at compile time.

### Why the corpus holds the numbers

Design rainfall, runoff coefficients, buffer distances, the ±20 m budget and
the exposure bands are all declared in `asserts:` on the chunk that cites their
source. `index.html` keeps a bootstrap copy so the plot check runs before
`corpus.json` lands, and `check_corpus.py` fails if the two ever disagree.

A figure therefore cannot appear in an answer without a chunk id attached,
because there is nowhere else in the system for it to have come from.

### Why the model never types a digit

It emits `{{fact.distPresent}}` placeholders and the client substitutes. Any
bare digit left in the narrative — after placeholders and bracketed citations
are stripped — is a validation failure. So is echoing a verdict other than the
one screening reached, citing a chunk that is not in the pack, or answering a
flooding question without refusing the part that cannot be answered.

A rejected answer is reported on screen, not hidden. The officer is entitled to
know the machine said something the tool would not stand behind.

### Three tiers

| | |
|---|---|
| **0** | A deterministic composer renders **first, always**, before any network call. |
| **1** | If `/ask` reaches a model, it replaces the narrative paragraph only. The verdict, the numbers table and the source list are never regenerated. |
| **2** | A validation failure reverts to tier 0 and says why. |

Pull the network cable and the page behaves identically, minus one paragraph.
Three providers are wired, and the provider follows `BLUETRACE_PROVIDER` or
whichever key is present; `BLUETRACE_MODEL` overrides the default model. Anthropic
gets the answer through a forced tool call, Gemini and Groq through a response
schema — the same contract and the same validated shape either way, because
the client validates what comes back rather than trusting how it was asked
for. On Groq the default is `openai/gpt-oss-120b`: `json_schema` output is
only honoured by some of the models Groq serves, and one that ignores it
answers in prose that the client then rejects.

Starting `server.py` with no key at all is a supported way to run it:
`/ask` answers 503 and the page stays on the answer it has already rendered.

### What it refuses

Flood depth, level, extent or probability. Damage cost. Legality. The identity
of an owner. Anything at all outside the mapped rectangle, including the runoff
arithmetic — a volume computed from assumptions alone looks exactly like a
measurement and is not one.

`refusal.no-flood-depth-model` names the four things a real depth answer would
need: the drain network, a fine elevation model, a local rainfall curve and a
hydraulic solver. Naming them is more useful than producing a number, because
it says what to go and commission.

### The corpus is not finished

Eighteen chunks carry `verify: true` — drafted from public knowledge and the
citations already in this repo, **not yet checked against the original**. They
are listed by `./check_corpus.py` on every run and marked in the source list
under every answer. The design rainfall and the runoff coefficients are stated
placeholders; every runoff figure scales linearly with the first of them.

---

## Method, and where it is weak

Both eras of water come from **one** source: the JRC Global Surface Water
`transition` band, which compares 1984–1999 against 2000–2021 across the whole
Landsat archive with a single method. Hand-differencing a Landsat composite
against a Sentinel-2 one cannot be made symmetric — the finer sensor finds more
water whatever is on the ground, and that shows up as water appearing.

Terrain comes from **MERIT Hydro**: `upa` (upstream drainage area) and `hnd`
(height above nearest drainage), both precomputed, so there is no flow
accumulation to calculate.

Buildings come from **Google Open Buildings v3**, filtered to confidence ≥ 0.70
and area ≥ 40 m².

Known limits, stated up front:

- JRC is 30 m. Tanks under roughly half a hectare are invisible.
- MERIT Hydro is 90 m. It resolves catchment drainage, not individual rajakaluves.
- Dynamic World's `built` class is conservative under tree canopy, so the
  built-on-water hectare figure understates. The building intersection is the
  stronger number.
- Hyacinth-covered lakes read as vegetation in every water index. Dynamic World
  class 3 is treated as surviving water specifically so Bellandur and Varthur
  are not reported as destroyed.

Every flag is a lead for ground verification, not a finding of fact.

---

## Accuracy

There is no surveyed encroachment dataset for this catchment, so there is no
ground truth to score against and no honest "model accuracy" number to report.
What can be measured is whether the reference this pipeline depends on is
reproducible by an independent method.

`validate.py` scores Landsat 5 MNDWI against JRC Global Surface Water's own
per-year classification, over the same pixels in the same years (2003–2007),
on held-out spatial blocks:

```
./validate.py bengaluru --blocks 6x4 --holdout 8 --seeds 6
```

Blocks are contiguous tiles, not random pixels. Neighbouring pixels of one
lake are not independent samples, and a pixel-wise split would inflate every
score. The Otsu threshold is fitted on training blocks only.

**Quote the range, not a run.** With 8 blocks held out of 24, which 8 they are
moves the result more than the choice of threshold does:

| | across six draws |
|---|---|
| pooled IoU | 0.43 – 0.81 |
| per-block median IoU | 0.21 – 0.69 |

`--seeds` exists to make that visible. A single seed reports the draw. The
pooled figure is also the flattering one: one large lake carries it, and the
blocks that score worst are the ones with almost no water in them, where IoU
punishes a handful of misclassified pixels hardest. The defensible summary is
that MNDWI reproduces the JRC reference well where there is water to find and
poorly where there is barely any — which is a statement about the metric and
the terrain as much as about the method.

This pipeline contains no learned model. Every flag traces to a published
dataset and a stated threshold, which is why a judge can be handed the reason
for any individual flag rather than a confidence score.

---

## Files

```
gee_blue_grid.js   extraction — the only thing that touches Earth Engine
index.html         the whole app, single file, no build step
assets/fonts/      Geist and Geist Mono, self-hosted so a demo can go offline
server.py          serves the app and holds the API key; /ask proxies to Claude
fetch_layers.sh    downloads exported PNGs into data/<city>/
hotspots.py        finds where encroachment concentrates, prints coordinates
validate.py        scores MNDWI against the JRC reference on held-out blocks;
                   --routing scores the downstream trace against the flow-path mask
verify_encoding.py proves the byte-packed layers decoded losslessly
build_corpus.py    compiles corpus/**/*.md into data/corpus.json
check_corpus.py    checks the corpus against the code it describes
corpus/            the knowledge, one idea per file — see corpus/README.md
corpus/option/     what a flagged site could be instead, one use per file
data/<city>/       layers, stats.json, flagged_buildings.geojson
data/corpus.json   the compiled corpus, committed
urls/<city>.txt    pasted Earth Engine console links
```

Before committing:

```
./check_corpus.py && ./verify_encoding.py bengaluru
```
