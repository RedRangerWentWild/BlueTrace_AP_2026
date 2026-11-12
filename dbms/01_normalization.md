# BlueTrace - Normalization (1NF → 2NF → 3NF → BCNF)

**Team T0015 (Bluetrace), Section E**

## 1. Where the data comes from

BlueTrace does not use a relational database today. Its data lives in these places in the app:

| Data | Where the app keeps it now | Size |
|------|----------------------------|------|
| A plot screening and the certificate issued for it | A JavaScript object built in `index.html` (`rec`, `decide()`, `renderCertificate()`); only the certificate counter is saved, in `localStorage` | one per plot check |
| The cited corpus (rules, methods, limits, refusals...) | One Markdown file per chunk in `corpus/`, compiled into `data/corpus.json` | 86 chunks, 53 parameters |
| Flagged buildings | `data/bengaluru/flagged_buildings.geojson` | 3,169 buildings |
| City configuration and headline statistics | The `CITIES` and rule tables in `index.html`, and `data/bengaluru/stats.json` | 2 cities, 2 buffer rules |

This document takes that data and designs the relational tables for it. We start from the two
records a user actually sees, exactly as the app holds them, and remove one kind of problem at a time.

Notation: `X → Y` means "X determines Y". Primary keys are **bold**. `{ ... }` is a repeating group.

## 2. Unnormalized form (UNF)

### U1. Screening certificate

Everything printed on one certificate, as one record:

```
CERTIFICATE(
  cert_ref, issued_at, application_no, survey_no, applicant,
  city_key, city_label, catchment, lon_min, lat_min, lon_max, lat_max, zones,
  historic_ha, present_ha, lost_ha, encroached_ha, floodprone_ha, buildings_in_floodprone,
  lat, lon, plot_m, plot_area_m2,
  rule_id, rule_label, lake_m, drain_m,
  dist_present, dist_historic, dist_drain, retreat_m,
  last_water_year, occurrence, hand_m, hand_class, encroached, upa_km2,
  runoff_displaced_m3, retention_required_m3,
  verdict, verdict_title,
  { reason_code, reason_outcome, reason_text },
  route_length_m, route_steps,
  { step_no, direction, step_length_m, step_upa_km2, step_hand_m },
  corpus_version, generator,
  { chunk_id, title, kind, authority, url_required, source, url, body,
    tags[], intents[],
    { param_name, value, unit } }
)
```

Example (shortened):

| cert_ref | city_label | lat, lon | rule_id | lake_m | verdict | reasons | route steps | cited chunks |
|----------|-----------|----------|---------|-------:|---------|---------|-------------|--------------|
| BT/BLR/20261112/0001-9A3F01C2 | Bengaluru | 12.9324, 77.6759 | ngt | 75 | REFER | refer.shoreline-disagreement, conditions.low-ground | (1, NE, 128 m, 0.06 km², 7 m), (2, NE, 128 m, 0.15 km², 1 m), (3, N, 92 m, 218 km², 0 m) | rule.lake-buffer.ngt-75m [buffer, lake, ngt] {lakeM_ngt = 75 m, drainM_ngt = 50 m}, outcome.refer.meaning [...] |

### U2. Flagged building

One GeoJSON feature. It is already flat, but has no identifier.

```
BUILDING(city_key, geometry, verdict, risk_score, lost_frac, flow_frac,
         upstream_km2, hand_m, area_m2, confidence)
```

### Problems in UNF

- **Repeating groups**: reasons, route steps and cited chunks; inside a chunk, tags, intents and parameters. One cell holds a list.
- **Redundancy**: the text of chunk `rule.lake-buffer.ngt-75m` is copied into every certificate that cites it; the city's name and bounds are copied into every certificate.
- **Update anomaly**: correcting a chunk's source means editing every certificate that cites it.
- **Insert anomaly**: a new buffer rule or a new chunk cannot be stored until some certificate uses it.
- **Delete anomaly**: deleting the only certificate that used the `state` rule loses the fact that its lake buffer is 30 m.

## 3. First normal form (1NF)

Rule: every cell holds one value, and every table has a key. Each repeating group becomes its own
table whose key is the parent's key plus what identifies one member of the group. `BUILDING` gets a
surrogate key `building_id`.

```
CERTIFICATE(cert_ref, issued_at, application_no, survey_no, applicant,
            city_key, city_label, catchment, lon_min, lat_min, lon_max, lat_max, zones,
            historic_ha, present_ha, lost_ha, encroached_ha, floodprone_ha, buildings_in_floodprone,
            lat, lon, plot_m, plot_area_m2, rule_id, rule_label, lake_m, drain_m,
            dist_present, dist_historic, dist_drain, retreat_m, last_water_year, occurrence,
            hand_m, hand_class, encroached, upa_km2, runoff_displaced_m3, retention_required_m3,
            verdict, verdict_title, route_length_m, route_steps, corpus_version, generator)

CERT_REASON(cert_ref, reason_code, reason_outcome, reason_text)

CERT_ROUTE_STEP(cert_ref, step_no, direction, step_length_m, step_upa_km2, step_hand_m)

CERT_CHUNK(cert_ref, chunk_id, title, kind, authority, url_required, source, url, body)

CERT_CHUNK_TAG(cert_ref, chunk_id, tag)

CERT_CHUNK_INTENT(cert_ref, chunk_id, intent)

CERT_CHUNK_PARAM(cert_ref, chunk_id, param_name, value, unit)

BUILDING(building_id, city_key, geometry, verdict, risk_score, lost_frac, flow_frac,
         upstream_km2, hand_m, area_m2, confidence)
```

Keys: **cert_ref**; (**cert_ref, reason_code**); (**cert_ref, step_no**); (**cert_ref, chunk_id**);
(**cert_ref, chunk_id, tag**); (**cert_ref, chunk_id, intent**); (**cert_ref, chunk_id, param_name**);
**building_id**.

All tables are now in 1NF. The redundancy is still there: chunk text is still stored once per certificate.

## 4. Second normal form (2NF)

Rule: 1NF, and no non-key column depends on only *part* of a composite key. Tables with a
single-column key (`CERTIFICATE`, `BUILDING`) are already in 2NF.

Functional dependencies on the composite-key tables:

| Table | Key | Dependency | Kind |
|-------|-----|------------|------|
| CERT_REASON | (cert_ref, reason_code) | reason_code → reason_outcome | **partial** (needs only reason_code) |
| CERT_REASON | | (cert_ref, reason_code) → reason_text | full: the sentence contains this plot's own distances |
| CERT_ROUTE_STEP | (cert_ref, step_no) | (cert_ref, step_no) → direction, step_length_m, step_upa_km2, step_hand_m | full |
| CERT_CHUNK | (cert_ref, chunk_id) | chunk_id → title, kind, authority, url_required, source, url, body | **partial** (every non-key column) |
| CERT_CHUNK_TAG | (cert_ref, chunk_id, tag) | chunk_id → the set of tags; cert_ref plays no part | **partial** (the fact "chunk has tag" does not depend on the certificate) |
| CERT_CHUNK_INTENT | (cert_ref, chunk_id, intent) | same as tags | **partial** |
| CERT_CHUNK_PARAM | (cert_ref, chunk_id, param_name) | param_name → chunk_id, value, unit | **partial** |

Two of these were checked in the app rather than assumed:

- `reason_code → reason_outcome`: `decide()` has 10 reason codes and each is always returned with the same outcome (`reject.inside-buffer` is always REJECT, `refer.near-drainage` always REFER, `conditions.low-ground` always CONDITIONS).
- `param_name → chunk_id`: the 86 chunks declare 53 parameters and the compiled store has 53 distinct names, so a parameter name is unique across the whole corpus and belongs to exactly one chunk.

Removing the partial dependencies:

```
CERT_REASON(cert_ref, reason_code, reason_text)
REASON_CODE(reason_code, outcome)

CERT_ROUTE_STEP(cert_ref, step_no, direction, step_length_m, step_upa_km2, step_hand_m)

CERT_CHUNK(cert_ref, chunk_id)                       -- "this certificate cited this chunk"
CHUNK(chunk_id, title, kind, authority, url_required, source, url, body)
CHUNK_TAG(chunk_id, tag)
CHUNK_INTENT(chunk_id, intent)
PARAM(param_name, chunk_id, value, unit)

CERTIFICATE(...unchanged...)
BUILDING(...unchanged...)
```

A chunk is now stored once, however many certificates cite it. A new chunk or a new reason code
can be inserted before any certificate uses it.

## 5. Third normal form (3NF)

Rule: 2NF, and no non-key column depends on another non-key column (no transitive dependency).

Transitive dependencies found:

| Table | Dependency chain | Fix |
|-------|------------------|-----|
| CERTIFICATE | cert_ref → city_key → city_label, catchment, bounds, zones, historic_ha ... buildings_in_floodprone | new table `CITY` |
| CERTIFICATE | cert_ref → rule_id → rule_label, lake_m, drain_m | new table `BUFFER_RULE` |
| CERTIFICATE | cert_ref → verdict → verdict_title | new table `OUTCOME` |
| CERTIFICATE | cert_ref → (the screening) → application_no, survey_no, applicant, issued_at | split: a plot can be checked without a certificate being issued, so the measurements belong to a `SCREENING` and the paperwork to a `CERTIFICATE` |
| CHUNK | chunk_id → authority → url_required | new table `AUTHORITY` (a url is required for statute, court, agency-survey and dataset-doc; not for repo-derived or editorial) |

Columns that are **computed from other stored columns** are a transitive dependency too, so they
are removed and calculated when needed:

| Removed column | Computed from |
|----------------|---------------|
| `verdict` | the highest-ranked outcome among the screening's reason codes (REJECT > REFER > CONDITIONS > NO_OBJECTION). This is exactly what `decide()` does. Every screening has at least one reason code, so the verdict is always defined. |
| `retreat_m` | `dist_present - dist_historic` |
| `hand_class` | `hand_m` compared with the class boundaries stored in `PARAM` |
| `route_length_m`, `route_steps` | sum and count over `ROUTE_STEP` |
| `plot_area_m2`, `runoff_displaced_m3`, `retention_required_m3` | `plot_m` and the rainfall and runoff coefficients stored in `PARAM` |

Because `verdict` is gone from the screening, the reasons and route steps now hang off the
screening, not the certificate (a plot check has reasons whether or not a certificate is printed).

One dependency needs a rule to stay true: `rule_id → lake_m, drain_m` only holds if a rule's
distances never change after certificates have been issued under it. So `BUFFER_RULE` rows are
never updated; a revised regime is inserted as a new `rule_id`. Old screenings then keep pointing
at the distances they were actually judged against.

### Final tables (3NF)

```
CITY(city_key, city_label, catchment, lon_min, lat_min, lon_max, lat_max, zones,
     historic_ha, present_ha, lost_ha, encroached_ha, floodprone_ha, buildings_in_floodprone)

HOTSPOT(city_key, name, lon, lat, px)                         FK city_key → CITY

BUILDING(building_id, city_key, geometry, verdict, risk_score, lost_frac, flow_frac,
         upstream_km2, hand_m, area_m2, confidence)           FK city_key → CITY

BUFFER_RULE(rule_id, rule_label, lake_m, drain_m)

OUTCOME(outcome, title, rank)

REASON_CODE(reason_code, outcome)                             FK outcome → OUTCOME

SCREENING(screening_id, checked_at, city_key, rule_id, lat, lon, plot_m,
          dist_present, dist_historic, dist_drain, last_water_year, occurrence,
          hand_m, encroached, upa_km2)                        FK city_key → CITY, rule_id → BUFFER_RULE

SCREENING_REASON(screening_id, reason_code, reason_text)      FK → SCREENING, REASON_CODE

ROUTE_STEP(screening_id, step_no, direction, step_length_m, step_upa_km2, step_hand_m)
                                                              FK screening_id → SCREENING

CERTIFICATE(cert_ref, screening_id, issued_at, application_no, survey_no, applicant,
            corpus_version, generator)                        FK screening_id → SCREENING (UNIQUE)

CERTIFICATE_CHUNK(cert_ref, chunk_id)                         FK → CERTIFICATE, CHUNK

AUTHORITY(authority, url_required)

CHUNK(chunk_id, title, kind, authority, source, url, body)    FK authority → AUTHORITY

CHUNK_TAG(chunk_id, tag)                                      FK chunk_id → CHUNK

CHUNK_INTENT(chunk_id, intent)                                FK chunk_id → CHUNK

PARAM(param_name, chunk_id, value, unit)                      FK chunk_id → CHUNK
```

`HOTSPOT` is new here: it is the list of named localities inside each city's `CITIES` entry, a
repeating group of `CITY` that only became visible once `CITY` was its own table.

Functional dependencies in the final tables (every one has a key on its left side):

| Table | Functional dependencies |
|-------|-------------------------|
| CITY | city_key → all other columns |
| HOTSPOT | (city_key, name) → lon, lat, px |
| BUILDING | building_id → all other columns |
| BUFFER_RULE | rule_id → rule_label, lake_m, drain_m |
| OUTCOME | outcome → title, rank |
| REASON_CODE | reason_code → outcome |
| SCREENING | screening_id → all other columns |
| SCREENING_REASON | (screening_id, reason_code) → reason_text |
| ROUTE_STEP | (screening_id, step_no) → direction, step_length_m, step_upa_km2, step_hand_m |
| CERTIFICATE | cert_ref → all other columns; screening_id → cert_ref |
| CERTIFICATE_CHUNK | none besides the key (all-key table) |
| AUTHORITY | authority → url_required |
| CHUNK | chunk_id → all other columns |
| CHUNK_TAG, CHUNK_INTENT | none besides the key (all-key tables) |
| PARAM | param_name → chunk_id, value, unit |

## 6. BCNF

Rule: for every dependency `X → Y` in a table, `X` must be a candidate key. 3NF allows one
exception (when `Y` is part of some key); BCNF does not. So the only tables that can be in 3NF but
not BCNF are those with more than one candidate key or overlapping keys.

| Table | Candidate keys | BCNF? |
|-------|----------------|-------|
| CERTIFICATE | {cert_ref}, {screening_id} | Yes. Both determinants are candidate keys (one certificate per screening). |
| OUTCOME | {outcome}, {title}, {rank} | Yes. Each of the three is unique, so each is a candidate key. |
| CITY | {city_key}, {city_label} | Yes. |
| BUFFER_RULE | {rule_id}, {rule_label} | Yes. `(lake_m, drain_m)` is deliberately **not** a key: a revised regime may reuse the same distances under a new id. |
| CHUNK | {chunk_id} | Yes. `chunk_id` is built as `<kind>.<file name>`, so `chunk_id → kind`; the determinant is the key, which BCNF allows. `title` is not declared unique. |
| PARAM | {param_name} | Yes. |
| HOTSPOT, SCREENING_REASON, ROUTE_STEP | the composite key shown | Yes. No dependency inside the key and no non-key determinant. |
| CERTIFICATE_CHUNK, CHUNK_TAG, CHUNK_INTENT | the whole row | Yes. An all-key table has no non-trivial dependency. |
| BUILDING, SCREENING, REASON_CODE, AUTHORITY | the single key shown | Yes. |

All 16 tables are in BCNF.

Two things we looked at and decided were **not** dependencies:

- `SCREENING`: `(city_key, lat, lon, plot_m, rule_id) → measurements` looks true, because the same point and rule give the same distances today. It stops being true when a newer satellite layer is loaded, and the same plot can be checked twice. So it is not a key, and `screening_id` plus `checked_at` identify a check.
- `BUILDING`: `verdict` looks derivable from `lost_frac` and `flow_frac`. It is computed outside the app, in the Earth Engine export, and the thresholds are not stored with the data, so we treat it as a stored fact, not a derived one.

## 7. What normalization fixed

| Anomaly in UNF | After normalization |
|----------------|---------------------|
| Chunk text copied into every certificate | Stored once in `CHUNK`; a certificate holds only `chunk_id` |
| Correcting a chunk's source means editing many certificates | One row in `CHUNK` |
| A new rule or chunk cannot exist without a certificate | Insert into `BUFFER_RULE` / `CHUNK` directly |
| Deleting the last certificate under a rule loses the rule | The rule stays in `BUFFER_RULE` |
| `verdict` could disagree with the reasons listed under it | `verdict` is not stored; it is computed from the reasons |
| City name and statistics repeated per certificate | One row in `CITY` |

## 8. Left out on purpose

- **The raster layers** (water extent, buffers, hydrology PNGs). They are images read pixel by pixel in the browser, not rows.
- **The search index and synonym list** in `corpus.json`. Both are rebuilt from the chunks by `build_corpus.py`, so they are derived data.
- **Retrieval settings on a chunk** (`when` triggers, `conflicts`, `weight`, `always`). They control which chunk is picked for an answer, not what the app records.

## 9. Changes made while building the schema (CP2)

Writing `dbms/03_schema.sql` and running every query of `dbms/04_queries.sql` against the app's real
data showed five facts the app needs that the tables above could not hold. Each one was added
as a column, and each depends only on the key of its table, so every table is still in BCNF.

| Table | Added column | New dependency | Why it is needed |
|-------|--------------|----------------|------------------|
| REASON_CODE | `chunk_id` → CHUNK | reason_code → chunk_id | `CODE_CHUNK` in `index.html`: every reason code cites exactly one chunk, which is forced into every answer ("the citation spine"). |
| SCREENING | `storage_lpm2` | screening_id → storage_lpm2 | The officer's storage rule (litres per m²). It is an input, not a measurement, and the rainwater-harvesting figure and the retention shortfall cannot be recomputed without it. |
| SCREENING | `route_ended_by` | screening_id → route_ended_by | Why the downstream trace stopped (`ROUTE_END`: trunk, edge, loop, ...). It is printed on the certificate and cannot be derived from the steps: a route that left the study area and one that reached a trunk channel can have the same length. |
| PARAM | `plus_minus` | param_name → plus_minus | The ± uncertainty a parameter is declared with (`pm` in `corpus.json`, e.g. `P_mm` = 60 ± 24 mm). The plausible range of the displaced runoff is computed from it. |
| CERTIFICATE_CHUNK | `cite_order` | (cert_ref, chunk_id) → cite_order | The certificate's digest is computed over the cited chunk ids **in order**, so without the order a stored certificate could not be re-verified. The table now has two candidate keys, {cert_ref, chunk_id} and {cert_ref, cite_order}; both are keys, so it is still in BCNF. |

Two smaller corrections from reading the code again:

- `decide()` has **11** reason codes, not 10: `no-objection.nothing-found` is the eleventh. Each is
  still returned with one outcome only, so `reason_code → outcome` holds (the loader,
  `dbms/load_app_data.py`, checks this against the source of `decide()` and `CODE_CHUNK` before
  loading anything).
- BUILDING also gets `centroid_lon` and `centroid_lat`, computed by PostgreSQL itself from
  `geometry` (generated columns, the same vertex average as `centroidOf()` in the app). They are
  derived, i.e. a deliberate redundancy, but the database computes them, so they can never disagree
  with the geometry; they exist so that "flagged buildings within 300 m" (query R4) can use an
  index instead of decoding 3,169 polygons per click.
