-- =====================================================================
-- BlueTrace - every SQL query the app uses (CP3)
-- Team T0015 (Bluetrace), Section E
--
-- Today BlueTrace keeps its data in JavaScript objects, JSON files and
-- localStorage (dbms/01_normalization.md, section 1). This file is the same
-- app expressed against the tables of dbms/03_schema.sql: one query for every
-- place the app reads or writes data. Each query names the code it replaces
-- (blue-grid/index.html line numbers unless said otherwise).
--
--   16 READ queries   R1 - R16
--   11 WRITE queries  W1 - W11
--
-- The "-- @R1" marker lines follow the format of the DE project's
-- run_benchmark.sh, so the same script can time this file in CP4. Parameters
-- are written as literal example values so every query runs as it is, against
-- the data loaded by dbms/load_app_data.py:
--     screening 1 = the Kasavanahalli plot (shoreline disagreement, certificate 0001)
--     screening 6 = a plot with three findings (certificate 0004)
-- The whole file runs inside BEGIN ... ROLLBACK, so the writes change nothing.
--
--     psql -d bluetrace -f dbms/04_queries.sql
-- =====================================================================
SET search_path TO bluetrace;
BEGIN;

-- =====================================================================
-- Opening a city (loadCity, line 1951)
-- =====================================================================

-- @R1
-- READ R1: open a city - its configuration, headline statistics and named hotspots in one round trip
-- Replaces: CITIES (line 1173) + fetch('data/<city>/stats.json') (line 2051)
SELECT c.city_key, c.city_label, c.catchment, c.zones,
       c.lon_min, c.lat_min, c.lon_max, c.lat_max,
       c.historic_ha, c.present_ha, c.lost_ha, c.encroached_ha, c.floodprone_ha, c.buildings_in_floodprone,
       coalesce(json_agg(json_build_object('name', h.name, 'lon', h.lon, 'lat', h.lat, 'px', h.px)
                         ORDER BY h.px DESC) FILTER (WHERE h.name IS NOT NULL), '[]') AS hotspots
FROM city c
LEFT JOIN hotspot h ON h.city_key = c.city_key
WHERE c.city_key = 'bengaluru'
GROUP BY c.city_key;

-- @R2
-- READ R2: the buffer regimes offered in the rule selector, widest lake buffer first
-- Replaces: RULESETS (line 1372)
SELECT r.rule_id, r.rule_label, r.lake_m, r.drain_m
FROM buffer_rule r
ORDER BY r.lake_m DESC;

-- @R3
-- READ R3: the flagged-structures list - a city's flagged buildings, highest risk first
-- Replaces: fetch('data/<city>/flagged_buildings.geojson') and the ranked list built from it (lines 2055, 2076)
SELECT b.building_id, b.verdict, round(b.risk_score::numeric, 2) AS risk_score,
       round(b.upstream_km2::numeric, 2) AS upstream_km2, round(b.hand_m::numeric, 1) AS hand_m,
       round(b.area_m2::numeric) AS area_m2, round(b.confidence::numeric, 3) AS confidence,
       round(b.centroid_lon::numeric, 6) AS lon, round(b.centroid_lat::numeric, 6) AS lat,
       c.city_label
FROM building b
JOIN city c ON c.city_key = b.city_key
WHERE b.city_key = 'bengaluru'
ORDER BY b.risk_score DESC
LIMIT 25;

-- @R4
-- READ R4: up to three flagged buildings within 300 m of a clicked point, nearest first
-- Replaces: neighboursOf() (line 2478) with metresBetween() (line 1556). The
-- bounding box (300 m is about 0.0027 degrees of latitude and 0.0028 of
-- longitude here) lets ix_building_centroid discard most rows before the
-- exact equirectangular distance - the same formula as the app - is computed.
-- Example click: the HSR Layout / Parangipalya hotspot (14 flagged buildings within 300 m).
SELECT b.building_id, b.verdict, round(d.metres) AS metres,
       round(b.risk_score::numeric, 2) AS risk_score
FROM building b
CROSS JOIN LATERAL (
    SELECT sqrt(power((b.centroid_lon - 77.6403) * 111320 * cos(radians(12.9114)), 2)
              + power((b.centroid_lat - 12.9114) * 110574, 2)) AS metres
) d
WHERE b.city_key = 'bengaluru'
  AND b.centroid_lat BETWEEN 12.9114 - 0.0028 AND 12.9114 + 0.0028
  AND b.centroid_lon BETWEEN 77.6403 - 0.0029 AND 77.6403 + 0.0029
  AND d.metres <= 300
ORDER BY d.metres
LIMIT 3;

-- @R5
-- READ R5: the building-layer legend - how many flagged buildings, and how much floor area, per verdict class
-- Replaces: the per-class summary drawn from the GeoJSON features (line 2076)
SELECT b.verdict, count(*) AS buildings, round(sum(b.area_m2)::numeric) AS total_area_m2,
       round(avg(b.risk_score)::numeric, 2) AS avg_risk,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct_of_flagged
FROM building b
JOIN city c ON c.city_key = b.city_key
WHERE c.city_key = 'bengaluru'
GROUP BY b.verdict
ORDER BY buildings DESC;

-- =====================================================================
-- Checking a plot (checkPlot, line 3288 -> siteContext, decide, traceDownstream)
-- =====================================================================

-- @R6
-- READ R6: the verdict panel - a screening with its city, rule and verdict
-- Replaces: decide()'s "top" (line 2920). The verdict is not stored
-- (01_normalization.md): it is the highest-ranked outcome among the
-- screening's reasons, found through reason_code -> outcome.
SELECT s.screening_id, s.checked_at, c.city_label, r.rule_label, r.lake_m, r.drain_m,
       s.lat, s.lon, s.plot_m, v.outcome AS verdict, v.title AS verdict_title, v.findings
FROM screening s
JOIN city c        ON c.city_key = s.city_key
JOIN buffer_rule r ON r.rule_id = s.rule_id
CROSS JOIN LATERAL (
    SELECT o.outcome, o.title, count(*) OVER () AS findings
    FROM screening_reason sr
    JOIN reason_code rc ON rc.reason_code = sr.reason_code
    JOIN outcome o      ON o.outcome = rc.outcome
    WHERE sr.screening_id = s.screening_id
    ORDER BY o.rank DESC
    LIMIT 1
) v
WHERE s.screening_id = 6;

-- @R7
-- READ R7: the reasons listed under the verdict, worst first, with the chunk each one cites
-- Replaces: out.why / out.codes (line 2925) and CODE_CHUNK (line 2934)
SELECT o.outcome, o.title AS outcome_title, sr.reason_code, sr.reason_text,
       rc.chunk_id AS cites, ch.title AS cited_title, ch.authority
FROM screening_reason sr
JOIN reason_code rc ON rc.reason_code = sr.reason_code
JOIN outcome o      ON o.outcome = rc.outcome
JOIN chunk ch       ON ch.chunk_id = rc.chunk_id
WHERE sr.screening_id = 6
ORDER BY o.rank DESC, sr.reason_code;

-- @R8
-- READ R8: the derived facts of a screening, computed from the stored measurements and PARAM
-- Replaces: retreatM, flowClass, handClass (lines 2457-2475, 2757) and the runoff /
-- retention arithmetic (lines 2682-2721). None of these is stored (01_normalization.md,
-- section 5); the constants come from PARAM, which is where the corpus declares them.
WITH p AS (
    SELECT max(value)      FILTER (WHERE param_name = 'P_mm')          AS p_mm,
           max(plus_minus) FILTER (WHERE param_name = 'P_mm')          AS p_pm,
           max(value)      FILTER (WHERE param_name = 'P_annualMm')    AS p_annual_mm,
           max(value)      FILTER (WHERE param_name = 'dC')            AS dc,
           max(plus_minus) FILTER (WHERE param_name = 'dC')            AS dc_pm,
           max(value)      FILTER (WHERE param_name = 'tankerL')       AS tanker_l,
           max(value)      FILTER (WHERE param_name = 'uncertaintyM')  AS uncertainty_m,
           max(value)      FILTER (WHERE param_name = 'handDeepM')     AS hand_deep_m,
           max(value)      FILTER (WHERE param_name = 'handLowM')      AS hand_low_m,
           max(value)      FILTER (WHERE param_name = 'handMarginalM') AS hand_marginal_m
    FROM param
    WHERE param_name IN ('P_mm', 'P_annualMm', 'dC', 'tankerL', 'uncertaintyM',
                         'handDeepM', 'handLowM', 'handMarginalM')
)
SELECT s.screening_id,
       s.plot_m * s.plot_m AS plot_area_m2,
       CASE WHEN s.dist_present IS NOT NULL AND s.dist_historic > 0
            THEN greatest(0, s.dist_present - s.dist_historic) END AS retreat_m,
       CASE WHEN s.dist_drain IS NULL THEN NULL
            WHEN s.dist_drain >= 255 THEN 'UNRESOLVED'
            WHEN s.dist_drain = 0 THEN 'ON_FLOW_PATH'
            WHEN s.dist_drain <= 10 THEN 'ADJACENT'
            WHEN s.dist_drain <= r.drain_m + p.uncertainty_m THEN 'NEAR'
            ELSE 'OFF' END AS flow_class,
       CASE WHEN s.hand_m IS NULL THEN NULL
            WHEN s.hand_m >= 255 THEN 'UNKNOWN'
            WHEN s.hand_m = 0 THEN 'AT_DRAINAGE_LEVEL'
            WHEN s.hand_m <= p.hand_deep_m THEN 'DEEP_IN_A_WATER_PATH'
            WHEN s.hand_m <= p.hand_low_m THEN 'LOW_GROUND'
            WHEN s.hand_m <= p.hand_marginal_m THEN 'MARGINAL'
            ELSE 'ELEVATED' END AS hand_class,
       x.runoff_m3 AS runoff_displaced_m3,
       sig2(x.raw_m3 * (1 - x.rel)) AS runoff_low_m3,
       sig2(x.raw_m3 * (1 + x.rel)) AS runoff_high_m3,
       CASE WHEN x.raw_m3 IS NOT NULL THEN sig2(s.plot_m * s.plot_m * p.p_annual_mm / 1000 * p.dc) END AS runoff_per_year_m3,
       -- GREATEST(1, NULL) would be 1, so outside the study area this must be guarded too
       CASE WHEN x.raw_m3 IS NOT NULL THEN greatest(1, round(x.raw_m3 / (p.tanker_l / 1000))) END AS tanker_loads,
       x.runoff_m3 AS retention_required_m3,
       CASE WHEN x.runoff_m3 IS NOT NULL THEN sig2(s.plot_m * s.plot_m * s.storage_lpm2 / 1000) END AS rwh_required_m3,
       -- blank, not zero, when the officer gave no storage rule (GREATEST would skip the NULL)
       CASE WHEN s.storage_lpm2 IS NOT NULL AND x.runoff_m3 IS NOT NULL
            THEN sig2(greatest(0, x.runoff_m3 - sig2(s.plot_m * s.plot_m * s.storage_lpm2 / 1000))) END AS shortfall_m3
FROM screening s
JOIN buffer_rule r ON r.rule_id = s.rule_id
CROSS JOIN p
CROSS JOIN LATERAL (
    -- not computed outside the study area: "a volume derived entirely from
    -- assumptions looks identical to a measurement and is not one"
    SELECT CASE WHEN s.dist_present IS NOT NULL THEN s.plot_m * s.plot_m * p.p_mm / 1000 * p.dc END AS raw_m3,
           CASE WHEN s.dist_present IS NOT NULL THEN sig2(s.plot_m * s.plot_m * p.p_mm / 1000 * p.dc) END AS runoff_m3,
           sqrt(power(p.p_pm / p.p_mm, 2) + power(p.dc_pm / p.dc, 2)) AS rel
) x
WHERE s.screening_id = 6;

-- @R9
-- READ R9: the downstream panel - the traced route, step by step, with running totals
-- Replaces: traceDownstream() (line 2541). Each segment is attributed to the
-- ground it LEAVES (the cell read before the step): LAG() gives that cell, and
-- the plot itself for the first step.
SELECT x.step_no, x.direction, x.step_length_m,
       sum(x.step_length_m) OVER w AS metres_from_plot,
       x.step_upa_km2, max(x.step_upa_km2) OVER w AS largest_catchment_so_far,
       x.step_hand_m,
       sum(CASE WHEN x.hand_left <= x.hand_low_m THEN x.step_length_m ELSE 0 END) OVER w AS low_ground_m_so_far,
       x.route_ended_by
FROM (
    SELECT st.step_no, st.direction, st.step_length_m, st.step_upa_km2, st.step_hand_m,
           coalesce(lag(st.step_hand_m) OVER (ORDER BY st.step_no), s.hand_m) AS hand_left,
           p.value AS hand_low_m, s.route_ended_by
    FROM route_step st
    JOIN screening s ON s.screening_id = st.screening_id
    JOIN param p     ON p.param_name = 'handLowM'
    WHERE st.screening_id = 1
) x
WINDOW w AS (ORDER BY x.step_no)
ORDER BY x.step_no;

-- =====================================================================
-- Answering a question about the plot (ask box: retrieve, routeIntent, compose)
-- =====================================================================

-- @R10
-- READ R10: evidence-pack candidates - chunks for the question's intent that carry the question's words as tags
-- Replaces: the candidate step of routeIntent() (line 3936) and retrieve()
-- (line 4013). BM25 scoring stays in the browser; the database narrows 86 chunks
-- to the ones worth scoring. Example: "Will it affect the flooding level here
-- and downstream?" -> intent flood, matched against the corpus's own tags.
SELECT ch.chunk_id, ch.title, ch.kind, ch.authority, a.url_required,
       count(*) AS matching_tags,
       array_agg(t.tag ORDER BY t.tag) AS matched_tags
FROM chunk ch
JOIN chunk_intent ci ON ci.chunk_id = ch.chunk_id AND ci.intent = 'flood'
JOIN chunk_tag t     ON t.chunk_id = ch.chunk_id
JOIN authority a     ON a.authority = ch.authority
WHERE t.tag = ANY (ARRAY['flood', 'will it flood', 'water level', 'level', 'downstream', 'runoff', 'drain', 'depth'])
GROUP BY ch.chunk_id, ch.title, ch.kind, ch.authority, a.url_required
ORDER BY matching_tags DESC, ch.chunk_id
LIMIT 8;

-- @R11
-- READ R11: the citation spine - chunks forced into the evidence pack at rank zero for a screening's findings
-- Replaces: CODE_CHUNK lookup for every code in rec.codes (line 2934)
SELECT DISTINCT ON (ch.chunk_id)
       ch.chunk_id, ch.title, ch.kind, ch.authority, ch.source, ch.url, sr.reason_code
FROM screening_reason sr
JOIN reason_code rc ON rc.reason_code = sr.reason_code
JOIN chunk ch       ON ch.chunk_id = rc.chunk_id
WHERE sr.screening_id = 6
ORDER BY ch.chunk_id, sr.reason_code;

-- @R12
-- READ R12: facts with their sources - the parameters a fact is computed from, and where each value comes from
-- Replaces: fact(..., {chunk: ...}) in the evidence pack (lines 4160-4200) and the
-- PARAMS bootstrap copy (line 1394)
SELECT p.param_name, p.value, p.plus_minus, p.unit,
       ch.chunk_id, ch.title, ch.source, ch.url, a.url_required
FROM param p
JOIN chunk ch    ON ch.chunk_id = p.chunk_id
JOIN authority a ON a.authority = ch.authority
WHERE p.param_name IN ('P_mm', 'dC', 'C_pre', 'C_post', 'P_annualMm', 'tankerL', 'uncertaintyM')
ORDER BY ch.chunk_id, p.param_name;

-- @R13
-- READ R13: the refusal router - the refusal chunks, with the tags that route a question to each
-- Replaces: REFUSAL_RULES / routeRefusals() (lines 3884-3935)
SELECT ch.chunk_id, ch.title, ch.authority,
       string_agg(t.tag, ', ' ORDER BY t.tag) AS tags,
       count(DISTINCT ci.intent) AS intents
FROM chunk ch
JOIN chunk_tag t          ON t.chunk_id = ch.chunk_id
LEFT JOIN chunk_intent ci ON ci.chunk_id = ch.chunk_id
WHERE ch.kind = 'refusal'
GROUP BY ch.chunk_id, ch.title, ch.authority
ORDER BY ch.chunk_id;

-- =====================================================================
-- The certificate (issueCertificate / renderCertificate, lines 3626-3800)
-- =====================================================================

-- @R14
-- READ R14: verify a certificate - rebuild the canonical record from the database and recompute its digest
-- Replaces: the canonical string and fnv1a() (lines 3603, 3650). "The canonical
-- string is printed on the certificate so anyone can recompute the digest and
-- detect an altered copy." valid = the digest in the reference matches.
WITH ce AS (SELECT * FROM certificate WHERE cert_ref = 'BT/BLR/20261112/0001-DF9684FA'),
v AS (
    SELECT o.outcome
    FROM ce
    JOIN screening_reason sr ON sr.screening_id = ce.screening_id
    JOIN reason_code rc      ON rc.reason_code = sr.reason_code
    JOIN outcome o           ON o.outcome = rc.outcome
    ORDER BY o.rank DESC
    LIMIT 1
),
canon AS (
    SELECT ce.cert_ref,
           concat_ws('|', s.city_key, s.lat::text, s.lon::text, s.plot_m::text, r.rule_id,
                     r.lake_m::text, r.drain_m::text,
                     coalesce(s.dist_present::text, ''), coalesce(s.dist_historic::text, ''),
                     coalesce(s.dist_drain::text, ''), coalesce(s.last_water_year::text, ''),
                     coalesce(s.occurrence::text, ''), coalesce(s.hand_m::text, ''),
                     v.outcome,
                     to_char(ce.issued_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
                     ce.corpus_version, ce.generator,
                     coalesce((SELECT string_agg(cc.chunk_id, ',' ORDER BY cc.cite_order)
                               FROM certificate_chunk cc WHERE cc.cert_ref = ce.cert_ref), '')) AS canonical
    FROM ce
    JOIN screening s   ON s.screening_id = ce.screening_id
    JOIN buffer_rule r ON r.rule_id = s.rule_id
    CROSS JOIN v
)
SELECT cert_ref, canonical, fnv1a(canonical) AS recomputed_digest,
       fnv1a(canonical) = right(cert_ref, 8) AS valid
FROM canon;

-- @R15
-- READ R15: render a certificate - everything printed on it, in one query
-- Replaces: renderCertificate() (line 3639): heading, decision, reasons,
-- application fields, measurements, rule applied, cited sources
SELECT ce.cert_ref, ce.issued_at, c.city_label, c.catchment,
       o.title AS decision,
       (SELECT string_agg(sr.reason_text, E'\n' ORDER BY o2.rank DESC, sr.reason_code)
        FROM screening_reason sr
        JOIN reason_code rc ON rc.reason_code = sr.reason_code
        JOIN outcome o2     ON o2.outcome = rc.outcome
        WHERE sr.screening_id = s.screening_id) AS reasons,
       ce.application_no, ce.survey_no, ce.applicant,
       s.lat, s.lon, s.plot_m, s.dist_present, s.dist_historic, s.dist_drain,
       s.last_water_year, s.occurrence, s.hand_m, s.upa_km2,
       r.rule_label, r.lake_m, r.drain_m,
       ce.corpus_version, ce.generator,
       (SELECT string_agg(ch.title || ' (' || ch.authority || ')', '; ' ORDER BY cc.cite_order)
        FROM certificate_chunk cc
        JOIN chunk ch ON ch.chunk_id = cc.chunk_id
        WHERE cc.cert_ref = ce.cert_ref) AS sources
FROM certificate ce
JOIN screening s   ON s.screening_id = ce.screening_id
JOIN city c        ON c.city_key = s.city_key
JOIN buffer_rule r ON r.rule_id = s.rule_id
CROSS JOIN LATERAL (
    SELECT o.title
    FROM screening_reason sr
    JOIN reason_code rc ON rc.reason_code = sr.reason_code
    JOIN outcome o      ON o.outcome = rc.outcome
    WHERE sr.screening_id = s.screening_id
    ORDER BY o.rank DESC
    LIMIT 1
) o
WHERE ce.cert_ref = 'BT/BLR/20261112/0004-F1A66EF4';

-- =====================================================================
-- Keeping the corpus honest (blue-grid/check_corpus.py)
-- =====================================================================

-- @R16
-- READ R16: corpus check - chunks that break a rule the corpus must keep
-- Replaces: the checks in check_corpus.py (lines 185-215): an external authority
-- needs a url; a chunk declaring parameters or cited by a reason code must exist
-- and have an intent the router can reach. Returns no rows when the corpus is clean.
SELECT ch.chunk_id, 'external source without a url' AS problem
FROM chunk ch
JOIN authority a ON a.authority = ch.authority
WHERE a.url_required AND ch.url IS NULL
UNION ALL
SELECT rc.chunk_id, 'cited by reason code ' || rc.reason_code || ' but reachable by no intent'
FROM reason_code rc
LEFT JOIN chunk_intent ci ON ci.chunk_id = rc.chunk_id
WHERE ci.chunk_id IS NULL
UNION ALL
SELECT p.chunk_id, 'declares ' || p.param_name || ' but has no tags'
FROM param p
LEFT JOIN chunk_tag t ON t.chunk_id = p.chunk_id
WHERE t.chunk_id IS NULL
ORDER BY 1, 2;

-- =====================================================================
-- WRITES
-- =====================================================================

-- @W1
-- WRITE W1: record a plot check - the screening, decide()'s findings and the downstream trace, in one statement
-- Replaces: state.lastCheck = {...} after checkPlot() (line 3288), which today
-- lives only in the browser. One statement, so a screening is never stored
-- without its reasons or its route. (Example: the Kasavanahalli plot checked
-- again under the state rule.)
WITH s AS (
    INSERT INTO screening (city_key, rule_id, lat, lon, plot_m, dist_present, dist_historic, dist_drain,
                           last_water_year, occurrence, hand_m, encroached, upa_km2, storage_lpm2, route_ended_by)
    VALUES ('bengaluru', 'state', 12.932400, 77.675900, 15, 118, 42, 140, 1999, 22, 11, 0.050, 0.03, 30, 'trunk')
    RETURNING screening_id
),
reasons AS (
    INSERT INTO screening_reason (screening_id, reason_code, reason_text)
    SELECT s.screening_id, v.code, v.reason_text
    FROM s, (VALUES ('refer.shoreline-disagreement',
                     'Measured from today’s water edge the plot is 118 m away and clears the 30 m buffer. '
                     'Measured from the 1984–99 edge it is 42 m away, inside it. The shoreline has retreated '
                     '76 m here, so the buffer measured today is drawn from a boundary that encroachment '
                     'created. Verify against the notified lake boundary.')) AS v(code, reason_text)
    RETURNING 1
),
steps AS (
    INSERT INTO route_step (screening_id, step_no, direction, step_length_m, step_upa_km2, step_hand_m)
    SELECT s.screening_id, v.step_no, v.direction, v.len, v.upa, v.hand
    FROM s, (VALUES (1, 'NE', 129.1, 0.06, 7), (2, 'NE', 129.1, 0.15, 1), (3, 'N', 92.1, 218.0, 0))
            AS v(step_no, direction, len, upa, hand)
    RETURNING 1
)
SELECT s.screening_id, (SELECT count(*) FROM reasons) AS reasons, (SELECT count(*) FROM steps) AS steps
FROM s;

-- @W2
-- WRITE W2: issue a certificate for a screening and record the sources it cites, in order
-- Replaces: nextSeq() (line 3612), whose counter lived in localStorage and so
-- restarted on every new browser, and issueCertificate() (line 3626). The
-- number now comes from a sequence; the digest is computed by the app over the
-- canonical record (line 3650) and passed in.
WITH c AS (
    INSERT INTO certificate (cert_ref, screening_id, issued_at, corpus_version, generator)
    -- 5B0E9F21 stands for the digest the app computes over the canonical record.
    -- The number is padded to at least 4 digits like padStart(4, '0'): lpad(x, 4)
    -- alone would cut certificate 12345 down to 1234.
    SELECT 'BT/BLR/20261112/' || lpad(n::text, greatest(4, length(n::text)), '0') || '-5B0E9F21',
           s.screening_id, TIMESTAMPTZ '2026-11-12 12:06:00+05:30', '2026-09-20.94e12680', 'offline'
    FROM screening s
    CROSS JOIN LATERAL (SELECT nextval('certificate_seq') AS n) seq
    WHERE s.screening_id = 7
    RETURNING cert_ref
)
INSERT INTO certificate_chunk (cert_ref, chunk_id, cite_order)
SELECT c.cert_ref, ch.chunk_id, v.cite_order
FROM c
CROSS JOIN (VALUES ('error.budget.combined-20m', 1), ('outcome.refer.meaning', 2), ('rule.lake-buffer.ngt-75m', 3))
           AS v(chunk_id, cite_order)
JOIN chunk ch ON ch.chunk_id = v.chunk_id;

-- @W3
-- WRITE W3: fill in the application fields typed onto a certificate
-- Replaces: the three input boxes on the certificate (line 3684), which today
-- are lost when the page is closed. Not part of the digest, so filling them in
-- does not invalidate the reference.
UPDATE certificate
SET application_no = 'APP-2026-0001', survey_no = 'SURVEY-112/3', applicant = 'Applicant name as typed'
WHERE cert_ref = 'BT/BLR/20261112/0001-DF9684FA';

-- @W4
-- WRITE W4: load a rebuilt corpus chunk (after build_corpus.py) - insert it, or update it if it exists
-- Replaces: fetch('data/corpus.json') (line 2092). Upsert, never delete: a chunk
-- cited on a certificate must stay (fk_cc_chunk is RESTRICT).
INSERT INTO chunk (chunk_id, title, kind, authority, source, url, body)
VALUES ('error.budget.combined-20m', 'Every distance in this tool carries about twenty metres of uncertainty', 'error', 'repo-derived',
        'index.html, UNCERTAINTY_M and the error budget comment', NULL,
        'Four terms make up the budget: shoreline position in a source pixel (15 m), the distance-transform '
        'quantum (7 m), georeferencing slack (6 m) and the resample (nil). In quadrature, about 20 m.')
ON CONFLICT (chunk_id) DO UPDATE
SET title = EXCLUDED.title, kind = EXCLUDED.kind, authority = EXCLUDED.authority,
    source = EXCLUDED.source, url = EXCLUDED.url, body = EXCLUDED.body;

-- @W5
-- WRITE W5: add the tags a rebuilt chunk now declares (the ones it already has are kept)
-- Replaces: the tags array of a chunk in corpus.json
INSERT INTO chunk_tag (chunk_id, tag)
SELECT 'error.budget.combined-20m', t
FROM unnest(ARRAY['uncertainty', 'error budget', 'plus or minus', 'accuracy', 'twenty metres']) AS t
ON CONFLICT (chunk_id, tag) DO NOTHING;

-- @W6
-- WRITE W6: remove the tags a rebuilt chunk no longer declares
DELETE FROM chunk_tag
WHERE chunk_id = 'error.budget.combined-20m'
  AND NOT (tag = ANY (ARRAY['uncertainty', 'error budget', 'plus or minus', 'accuracy', 'twenty metres']));

-- @W7
-- WRITE W7: reconcile a parameter with the corpus - the corpus wins, and only a real change is written
-- Replaces: reconcileParams() (line 2784), which overrides the PARAMS bootstrap copy
UPDATE param
SET value = 60, plus_minus = 24, unit = 'mm'
WHERE param_name = 'P_mm'
  AND (value, plus_minus, unit) IS DISTINCT FROM (60, 24, 'mm');

-- @W8
-- WRITE W8: load a city's headline statistics from a new Earth Engine export
-- Replaces: data/<city>/stats.json
UPDATE city
SET historic_ha = 198.66, present_ha = 127.35, lost_ha = 57.72, encroached_ha = 3.05,
    floodprone_ha = 2212.44, buildings_in_floodprone = 13818
WHERE city_key = 'bengaluru';

-- @W9
-- WRITE W9: retire a city's previous building export before loading a new one
-- Replaces: overwriting data/<city>/flagged_buildings.geojson
DELETE FROM building
WHERE city_key = 'bengaluru';

-- @W10
-- WRITE W10: load one flagged building from the new export (run once per GeoJSON feature)
-- centroid_lon / centroid_lat are computed by the database from the geometry.
INSERT INTO building (city_key, geometry, verdict, risk_score, lost_frac, flow_frac,
                      upstream_km2, hand_m, area_m2, confidence)
VALUES ('bengaluru',
        '{"type":"Polygon","coordinates":[[[77.74477330289042,12.96123752323092],[77.74487817034483,12.961259753624766],[77.74484717289776,12.961400692701922],[77.74474230541405,12.961378548481552],[77.74477330289042,12.96123752323092]]]}',
        'RED_BLOCKS_DRAINAGE', 1.7746577356938864, 0, 1.0, 7.036657220667058, 50, 186.51280212402344, 0.8125)
RETURNING building_id, centroid_lon, centroid_lat;

-- @W11
-- WRITE W11: add a revised buffer regime. Rules are never updated: a new regime
-- gets a new rule_id, so old screenings keep the distances they were judged
-- against (01_normalization.md, section 5).
-- Replaces: editing RULESETS (line 1372)
INSERT INTO buffer_rule (rule_id, rule_label, lake_m, drain_m)
VALUES ('state_2027', 'State revision 2027 · 50 m lake', 50, 35);

-- @END
ROLLBACK;
