# BlueTrace - Query timings (CP4)

**Team T0015 (Bluetrace), Section E**

Every query of [`04_queries.sql`](04_queries.sql) (16 READ, 11 WRITE), timed with `EXPLAIN (ANALYZE, BUFFERS)`, three runs each, average of the three `Execution Time` values; writes inside `BEGIN ... ROLLBACK`. The plan of every run is in [`plans/`](plans/) (one file per query), and every number below comes from those files, [`plans/summary.csv`](plans/summary.csv) and [`plans/diagnostics/`](plans/diagnostics/).

## 1. What was measured, and on what data

| Item | Value |
|------|-------|
| Command | `./dbms/time_queries.sh bluetrace_big` ([`time_queries.sh`](time_queries.sh): the method of `CHECKPOINTS.md`, the same as the DE project's `run_benchmark.sh`; a new connection for every run) |
| Procedure | One full warm-up pass discarded, then `VACUUM (ANALYZE)`, then the measured pass. No measured run read a page from disk (`shared read` never appears in the plans). |
| Server | PostgreSQL 16.15, default configuration, `timezone` Asia/Kolkata; Linux VM, Intel Xeon 2.10 GHz, 4 vCPU, 16 GB RAM (the machine used for the DE project) |
| Data | `03_schema.sql` + `load_app_data.py` (the app's own data: 86 chunks, 53 parameters, 3,169 flagged buildings, 9 example checks) + `generate_workload.py --screenings 100000 --seed 2026` |

**Why we generated plot checks.** BlueTrace keeps a plot check only in the browser, so the app has no history to load, and timing queries against 9 checks measures nothing: PostgreSQL reads a table that small sequentially whatever indexes exist, and every plan looks the same. [`generate_workload.py`](generate_workload.py) produces the history a screening desk would build up, using the app's own logic for every value (ports in [`bluetrace_logic.py`](bluetrace_logic.py)):

- 100,000 plot checks at seeded random plots: 60% anywhere in the Bellandur-Varthur study area, 40% within about 100 m of a flagged building;
- each one **measured from the app's own raster layers** (`readSite()`: distances, water history, height above drainage, upstream area), **judged by `decide()`** and **traced downhill with `traceDownstream()`** over the MERIT flow directions;
- a quarter of them certified, with the real FNV-1a digest of the canonical record.

The 100,000 generated checks are 56.1% REFER, 37.0% NO_OBJECTION, 4.4% REJECT and 2.5% CONDITIONS (518 fall outside the study area), and all 11 reason codes occur. With the app's 9 examples the database holds 100,009 screenings, 145,007 reasons, 876,867 route steps (8.9 per traced route on average, at most 38; 94,958 routes end at a trunk channel), 25,296 certificates and 59,942 citations. All 25,296 certificates pass the verification of query R14. The database grew from 11 MB to 171 MB, about 1.6 kB per plot check (route steps 77 MB, reasons 41 MB, screenings 20 MB, citations 17 MB, certificates 4.5 MB, each with its indexes).

## 2. Timing table

| Query | Type | What it does | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Average (ms) | Scan type |
|-------|------|--------------|-----------:|-----------:|-----------:|-------------:|-----------|
| R1 | READ | Open a city: configuration, statistics, hotspots | 0.129 | 0.144 | 0.775 | 0.349 | Seq Scan (city, hotspot: 2 and 4 rows) |
| R2 | READ | Buffer regimes for the rule selector | 0.062 | 0.067 | 0.078 | 0.069 | Seq Scan (buffer_rule: 2 rows) |
| R3 | READ | Flagged buildings of a city, highest risk first (top 25) | 0.377 | 0.320 | 0.320 | 0.339 | Index Scan (ix_building_city_risk) |
| R4 | READ | Flagged buildings within 300 m of a click (top 3) | 0.222 | 0.158 | 0.208 | 0.196 | Bitmap Index Scan (ix_building_centroid) |
| R5 | READ | Building-layer legend: count and area per verdict class | 1.802 | 1.835 | 2.630 | 2.089 | Seq Scan (building: all 3,169) |
| R6 | READ | Verdict panel: screening, rule, city, derived verdict | 0.292 | 0.304 | 0.340 | 0.312 | Index Scan (screening_pkey) + Index Only Scan (pk_screening_reason) |
| R7 | READ | Reasons under the verdict, worst first, with the chunk each cites | 0.205 | 0.300 | 0.241 | 0.249 | Index Scan (pk_screening_reason, chunk_pkey) |
| R8 | READ | Derived facts: retreat, flow and hand class, runoff, retention | 0.551 | 0.698 | 0.612 | 0.620 | Index Scan (screening_pkey); Seq Scan (param: 53 rows) |
| R9 | READ | Downstream route with running length and low-ground length | 0.226 | 0.275 | 0.239 | 0.247 | Index Scan (pk_route_step, screening_pkey) |
| R10 | READ | Evidence-pack candidates for an intent and question words | 0.363 | 0.359 | 0.346 | 0.356 | Index Only Scan (pk_chunk_tag); Seq Scan (chunk, chunk_intent) |
| R11 | READ | Citation spine: chunks forced into the pack for a screening | 0.199 | 0.194 | 0.245 | 0.213 | Index Only Scan (pk_screening_reason) + Index Scan (chunk_pkey) |
| R12 | READ | Parameters with the source of each value | 0.217 | 0.296 | 0.242 | 0.252 | Seq Scan (chunk, param, authority) |
| R13 | READ | Refusal chunks with their routing tags | 0.584 | 0.586 | 0.593 | 0.588 | Seq Scan (chunk_tag, chunk_intent, chunk) |
| R14 | READ | Verify a certificate: rebuild the canonical record, recompute the digest | 1.582 | 1.565 | 2.353 | 1.833 | Index Scan (certificate_pkey, screening_pkey, uq_cc_order) |
| R15 | READ | Render a certificate: everything printed on it | 0.503 | 0.704 | 0.561 | 0.589 | Index Scan (certificate_pkey, screening_pkey, uq_cc_order) |
| R16 | READ | Corpus check: chunks that break a corpus rule | 0.509 | 0.398 | 0.448 | 0.452 | Seq Scan (corpus tables, anti-joins) |
| W1 | WRITE | Record a plot check: screening, reasons and route in one statement | 1.540 | 1.485 | 1.539 | 1.521 | Insert into 3 tables (no scan) + FK checks |
| W2 | WRITE | Issue a certificate and record its cited sources | 0.949 | 0.914 | 0.927 | 0.930 | Index Only Scan (screening_pkey, chunk_pkey) + Insert |
| W3 | WRITE | Fill in the application fields of a certificate | 0.387 | 0.535 | 0.478 | 0.467 | Index Scan (certificate_pkey) |
| W4 | WRITE | Load a rebuilt corpus chunk (insert or update) | 0.552 | 0.491 | 0.392 | 0.478 | Insert ... ON CONFLICT (chunk_pkey) |
| W5 | WRITE | Add the tags a chunk now declares | 0.795 | 1.062 | 1.213 | 1.023 | Insert ... ON CONFLICT (pk_chunk_tag) |
| W6 | WRITE | Remove the tags a chunk no longer declares | 0.171 | 0.105 | 0.162 | 0.146 | Bitmap Index Scan (pk_chunk_tag) |
| W7 | WRITE | Reconcile a parameter with the corpus (only a real change is written) | 0.069 | 0.099 | 0.066 | 0.078 | Seq Scan (param: 53 rows) |
| W8 | WRITE | Load a city's statistics from a new export | 0.431 | 0.448 | 0.334 | 0.404 | Seq Scan (city: 2 rows) |
| W9 | WRITE | Retire a city's previous building export (3,169 rows) | 2.029 | 2.932 | 2.085 | 2.349 | Seq Scan (building: 3,169) |
| W10 | WRITE | Load one flagged building (centroid generated by the database) | 1.613 | 1.695 | 1.299 | 1.536 | Insert (no scan) + FK check |
| W11 | WRITE | Add a revised buffer regime | 0.278 | 0.233 | 0.254 | 0.255 | Insert (no scan) |
| **Total** | | | **16.637** | **18.202** | **18.980** | **17.940** | |

Every query averages under 2.4 ms. The slowest are W9 (deletes all 3,169 buildings of a city), R5 (reads all of them) and R14 (runs the digest function); none of them depends on how many plot checks exist.

**Jitter.** Sub-millisecond timings on a virtual machine are noisy: in this pass five queries had one run more than 1.3 times their median (R1: 0.775 ms against 0.129 and 0.144; R5: 2.630; R14: 2.353; W7: 0.099; W9: 2.932). The required method averages three runs, so a single spike moves the average; we report the averages as measured and use medians where two measurements are compared (section 3).

## 3. Nine checks or a hundred thousand: the times do not grow

The same pass on the app's data alone ([`plans/app_data_only/`](plans/app_data_only/)) against the 100,009-check database:

| Query | 9 checks: average | 100,009 checks: average | 9 checks: median | 100,009 checks: median | Ratio of medians |
|-------|------:|------:|------:|------:|------:|
| R1 | 0.174 | 0.349 | 0.185 | 0.144 | 0.78 |
| R2 | 0.061 | 0.069 | 0.060 | 0.067 | 1.12 |
| R3 | 0.229 | 0.339 | 0.219 | 0.320 | 1.46 |
| R4 | 0.150 | 0.196 | 0.154 | 0.208 | 1.35 |
| R5 | 1.571 | 2.089 | 1.579 | 1.835 | 1.16 |
| R6 | 0.221 | 0.312 | 0.226 | 0.304 | 1.35 |
| R7 | 0.168 | 0.249 | 0.171 | 0.241 | 1.41 |
| R8 | 0.612 | 0.620 | 0.606 | 0.612 | 1.01 |
| R9 | 0.165 | 0.247 | 0.166 | 0.239 | 1.44 |
| R10 | 0.359 | 0.356 | 0.364 | 0.359 | 0.99 |
| R11 | 0.161 | 0.213 | 0.164 | 0.199 | 1.21 |
| R12 | 0.176 | 0.252 | 0.172 | 0.242 | 1.41 |
| R13 | 0.413 | 0.588 | 0.398 | 0.586 | 1.47 |
| R14 | 1.578 | 1.833 | 1.520 | 1.582 | 1.04 |
| R15 | 0.411 | 0.589 | 0.399 | 0.561 | 1.41 |
| R16 | 0.494 | 0.452 | 0.441 | 0.448 | 1.02 |
| W1 | 1.810 | 1.521 | 1.899 | 1.539 | 0.81 |
| W2 | 0.922 | 0.930 | 0.921 | 0.927 | 1.01 |
| W3 | 0.321 | 0.467 | 0.314 | 0.478 | 1.52 |
| W4 | 0.429 | 0.478 | 0.412 | 0.491 | 1.19 |
| W5 | 0.785 | 1.023 | 0.792 | 1.062 | 1.34 |
| W6 | 0.114 | 0.146 | 0.107 | 0.162 | 1.51 |
| W7 | 0.095 | 0.078 | 0.067 | 0.069 | 1.03 |
| W8 | 0.342 | 0.404 | 0.316 | 0.431 | 1.36 |
| W9 | 2.261 | 2.349 | 2.362 | 2.085 | 0.88 |
| W10 | 1.139 | 1.536 | 1.172 | 1.613 | 1.38 |
| W11 | 0.335 | 0.255 | 0.325 | 0.254 | 0.78 |
| **Total** | **15.496** | **17.940** | **15.511** | **17.058** | **1.10** |

With 11,000 times more plot-check data, the sum of the medians rose by 10%, and the per-query ratios go both ways (0.78 to 1.52). The same spread appears in queries that never read a plot-check table, such as R3 (buildings, 1.46), R13 (corpus, 1.47) and W6 (tags, 1.51), so it is run-to-run variation between the two passes, not growth. A design that scanned the plot checks would have grown in proportion to them.

**Why.** The app never asks a question about *all* plot checks; it asks about *one* (the plot on screen, the certificate in hand). Every such query reaches its rows through a primary or unique key:

| Index | Entries | Pages | Height | A lookup reads |
|-------|--------:|------:|-------:|---------------:|
| `screening_pkey` | 100,009 | 276 | root + leaves | 2 index pages |
| `certificate_pkey` | 25,296 | 155 | root + leaves | 2 index pages |
| `pk_screening_reason` | 145,007 | 935 | root + 1 level + leaves | 3 index pages |
| `pk_route_step` | 876,867 | 3,376 | root + 1 level + leaves | 3 index pages |

(Heights from `bt_metap()`.) Each extra level of a B-tree multiplies what it can hold by a few hundred, so the cost of "this screening, these reasons, this route" grows with the logarithm of the history, not with its size. The verdict panel (R6) touches 17 shared buffers, the route (R9) 11 and the full certificate (R15) 41, in a 171 MB database.

The queries that do read whole tables read tables that do **not** grow with use: the corpus (86 chunks, 662 tags, 170 intents, 53 parameters), the rules, outcomes and cities (2 to 11 rows, one page each) and one city's flagged buildings (3,169). For those a sequential scan is the right plan; an index on a one-page table costs more than it saves.

## 4. What the plans show

**Plot check (R6-R9, R11).** R6 derives the verdict instead of storing it: an Index Only Scan of `pk_screening_reason` finds the screening's reasons (Heap Fetches: 0), the 4-row `outcome` table gives their ranks, and `LIMIT 1` after sorting by rank keeps the worst, which is `decide()`'s `top`. R9 reads the route through `pk_route_step`, which returns the steps in `step_no` order, the order its window functions need (running length, largest catchment, low-ground length via `LAG()`). R8 pivots the 53-row `param` table once and computes the facts with the `sig2()` SQL function; its 0.6 ms is arithmetic, not access.

**Certificate (R14, R15, W2, W3).** Both read paths fetch the cited chunks through `uq_cc_order`, the `UNIQUE (cert_ref, cite_order)` constraint added in CP2 so that a certificate's digest can be re-verified: the same index returns the sources in citation order, which is the order `string_agg(... ORDER BY cite_order)` needs. R14 spends most of its time in `fnv1a()`, a PL/pgSQL loop over the 257-character canonical record (section 5).

**Map (R3, R4, R5).** R3 reads `ix_building_city_risk (city_key, risk_score DESC)` from the top and stops after 25 entries: no sort of 3,169 rows. R4 uses `ix_building_centroid` as a bounding box (Bitmap Index Scan) and computes the exact equirectangular distance only for the buildings inside it. R5 has to read every building of the city (199 buffers) because it summarises all of them; it is the one read whose cost grows with the size of a city's export.

**Corpus (R10, R12, R13, R16, W4-W7).** Small tables, read whole. R10 joins the 662 tags through `pk_chunk_tag` as an Index Only Scan. R16 returns no rows: the loaded corpus passes all three checks. W7 updates 0 rows, by design: the database already agrees with the corpus, and `IS DISTINCT FROM` makes the reconciliation write only a real change.

**Writes (W1, W2, W9, W10).** W1 stores a whole plot check (one screening, its reasons and 3 route steps) in one statement, so a screening can never be saved without its findings; most of its time is the five foreign-key checks (section 5). W9 deletes all 3,169 buildings of a city (3,364 buffers) and is the most expensive statement measured, which is fine for a bulk reload when a new export arrives. W10 includes PostgreSQL computing the generated centroid columns from the GeoJSON (`ring_centroid()`, twice).

## 5. Where the time actually goes: the first use of a statement in a connection

`time_queries.sh` opens a new connection for every run, as the method requires, so every measured run pays costs that a running application pays once per connection.

**Planning.** For 14 of the 16 reads, planning took longer than execution: over all reads, **17.057 ms of planning against 8.752 ms of execution** (the `Planning Time` lines of the same plan files). R15 is planned in 2.457 ms and executed in 0.589 ms. The reported times (execution only, as `CHECKPOINTS.md` asks) therefore understate what a user waits for.

**First use.** [`plans/diagnostics/first_use_in_a_connection.txt`](plans/diagnostics/first_use_in_a_connection.txt) runs the same statement three times inside one session:

| Statement | 1st run | 2nd run | 3rd run | What the 1st run pays for |
|-----------|--------:|--------:|--------:|---------------------------|
| `fnv1a()` on 257 characters | 1.253 ms | 0.283 ms | 0.456 ms | compiling the PL/pgSQL function |
| W1, record a plot check | 2.236 ms | 0.482 ms | 0.419 ms | preparing the foreign-key check queries (`fk_screening_city`: 0.672 ms, then 0.066 ms) |
| R15, render a certificate (planning + execution) | 2.747 + 0.640 ms | 0.776 + 0.252 ms | 0.640 + 0.205 ms | catalog caches filling up |

So in a deployed app, with a connection pool and prepared statements, these queries would run three to five times faster than the table in section 2 shows. The table is the honest worst case: a statement on a brand-new connection.

**R14, improved during this checkpoint.** R14 first called `fnv1a()` twice (once to show the digest, once to compare it), so the loop over the record ran twice. It now computes the digest once in a `MATERIALIZED` CTE. Three back-to-back runs per version ([`plans/diagnostics/r14_digest_computed_once.txt`](plans/diagnostics/r14_digest_computed_once.txt)): 1.851, 1.920 and 1.700 ms before; 1.518, 1.505 and 1.441 ms after, same result row. The saving (about 0.3 ms) matches the cost of a second call measured above. A first, noisier comparison had suggested no gain, which is why the saved three-run comparison was made. In the full pass of section 2, R14 averages 1.833 ms because one of its runs took 2.353 ms; the other two (1.582 and 1.565 ms) are below all three "before" runs of the back-to-back comparison.

## 6. Problems found while measuring

| Found | Effect | Fixed |
|-------|--------|-------|
| W2 numbered certificates with `lpad(n::text, 4, '0')`, and PostgreSQL's `lpad` **cuts** longer strings: certificate 12345 became `1234`. | A wrong reference that still passes the format CHECK and can collide with a real one. In the generated history, 15,297 of the 25,296 certificates have five-digit numbers. | Yes: padded to `greatest(4, length(...))` digits, like `padStart(4, '0')` in the app. |
| R14 computed the digest twice. | About 0.3 ms per verification. | Yes (section 5). |
| A sequence is not rolled back: every W2 run of our timing passes used up a certificate number although its transaction was rolled back. | After all passes, `certificate_seq` stands at 25,309 for 25,296 certificates: 13 numbers that will never appear on paper. The app's `localStorage` counter has the same property. | Documented. If the desk needs numbers without gaps, the counter has to become a row updated in the issuing transaction, which serialises certificate issue. |
| Planning outweighs execution for most reads. | End-to-end latency on a fresh connection is about three times the reported execution time for reads. | Recommendation: prepared statements and a connection pool (section 5). |

## 7. Reproduce

```bash
createdb bluetrace_big
psql -d bluetrace_big -c "ALTER DATABASE bluetrace_big SET timezone TO 'Asia/Kolkata'"
psql -d bluetrace_big -v ON_ERROR_STOP=1 -f dbms/03_schema.sql
python3 dbms/load_app_data.py | psql -d bluetrace_big -v ON_ERROR_STOP=1
python3 dbms/generate_workload.py --screenings 100000 --seed 2026 | psql -d bluetrace_big -v ON_ERROR_STOP=1
./dbms/time_queries.sh bluetrace_big 3 dbms/04_queries.sql /tmp/warmup    # warm-up, discard
psql -d bluetrace_big -c "VACUUM (ANALYZE)"
./dbms/time_queries.sh bluetrace_big                                        # -> dbms/plans/
```

The generator is seeded, so the same command produces the same 100,000 plot checks. Times on another machine will differ in absolute terms; the shape (flat with the number of plot checks, planning-heavy reads) should not.
