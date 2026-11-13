-- =====================================================================
-- BlueTrace - integrity checks the constraints cannot express
-- Team T0015 (Bluetrace), Section E
--
-- A CHECK constraint sees one row. The rules below span several rows or
-- tables, so they are checked by query instead. Every check returns one row:
-- its id, the rule, and how many rows break it. All counts should be 0.
--
--     psql -d bluetrace -f dbms/integrity_checks.sql
-- =====================================================================
SET search_path TO bluetrace;

-- ---------------------------------------------------------------------
-- Plot checks
-- ---------------------------------------------------------------------

-- IC1: decide() always returns at least one reason, so a screening with none
-- was stored without its findings.
SELECT 'IC1' AS id, 'every screening has at least one reason' AS rule, count(*) AS violations
FROM screening s
WHERE NOT EXISTS (SELECT 1 FROM screening_reason sr WHERE sr.screening_id = s.screening_id);

-- IC2: a plot outside the study area has no measurements, and decide() then
-- returns refer.outside-study-area and nothing else. Both directions.
SELECT 'IC2' AS id, 'outside the study area <=> the only reason is refer.outside-study-area' AS rule,
       count(*) AS violations
FROM screening s
WHERE (s.dist_present IS NULL) <> EXISTS (SELECT 1 FROM screening_reason sr
                                          WHERE sr.screening_id = s.screening_id
                                            AND sr.reason_code = 'refer.outside-study-area')
   OR (s.dist_present IS NULL AND EXISTS (SELECT 1 FROM screening_reason sr
                                          WHERE sr.screening_id = s.screening_id
                                            AND sr.reason_code <> 'refer.outside-study-area'));

-- IC3: a route is a walk, so its steps are numbered 1..n with no gap.
SELECT 'IC3' AS id, 'route steps are numbered 1..n without gaps' AS rule, count(*) AS violations
FROM (SELECT screening_id FROM route_step
      GROUP BY screening_id
      HAVING min(step_no) <> 1 OR max(step_no) <> count(*)) gaps;

-- IC4: traceDownstream() reports why it stopped exactly when it moved at least
-- one cell; with no steps there is nothing to have ended.
SELECT 'IC4' AS id, 'route_ended_by is set exactly when the screening has route steps' AS rule,
       count(*) AS violations
FROM screening s
WHERE (s.route_ended_by IS NOT NULL) <> EXISTS (SELECT 1 FROM route_step st WHERE st.screening_id = s.screening_id);

-- ---------------------------------------------------------------------
-- Certificates
-- ---------------------------------------------------------------------

-- IC5: a certificate is printed from a plot check, so it cannot predate it.
SELECT 'IC5' AS id, 'a certificate is issued after its plot check' AS rule, count(*) AS violations
FROM certificate ce
JOIN screening s ON s.screening_id = ce.screening_id
WHERE ce.issued_at < s.checked_at;

-- IC6: sources are cited only when an answer is carried on the certificate
-- (generator offline or model), and their order is 1..n without gaps, because
-- the digest covers the list in that order.
SELECT 'IC6' AS id, 'sources cited exactly when an answer is carried; cite_order 1..n' AS rule, count(*) AS violations
FROM certificate ce
LEFT JOIN (SELECT cert_ref, count(*) AS n, min(cite_order) AS lo, max(cite_order) AS hi
           FROM certificate_chunk GROUP BY cert_ref) cc ON cc.cert_ref = ce.cert_ref
WHERE (ce.generator = 'none') <> (cc.cert_ref IS NULL)
   OR cc.lo <> 1 OR cc.hi <> cc.n;

-- IC7: every certificate in the register still verifies: the digest in its
-- reference is the FNV-1a digest of the canonical record rebuilt from the
-- database (query R14, for all certificates at once). A failure means the
-- certificate or the plot check behind it was altered after issue.
SELECT 'IC7' AS id, 'every certificate digest verifies against the stored record' AS rule, count(*) AS violations
FROM certificate ce
JOIN screening s   ON s.screening_id = ce.screening_id
JOIN buffer_rule r ON r.rule_id = s.rule_id
CROSS JOIN LATERAL (
    SELECT o.outcome FROM screening_reason sr
    JOIN reason_code rc ON rc.reason_code = sr.reason_code
    JOIN outcome o      ON o.outcome = rc.outcome
    WHERE sr.screening_id = s.screening_id
    ORDER BY o.rank DESC LIMIT 1) v
WHERE fnv1a(concat_ws('|', s.city_key, s.lat::text, s.lon::text, s.plot_m::text, r.rule_id,
                      r.lake_m::text, r.drain_m::text,
                      coalesce(s.dist_present::text, ''), coalesce(s.dist_historic::text, ''),
                      coalesce(s.dist_drain::text, ''), coalesce(s.last_water_year::text, ''),
                      coalesce(s.occurrence::text, ''), coalesce(s.hand_m::text, ''),
                      v.outcome,
                      to_char(ce.issued_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
                      ce.corpus_version, ce.generator,
                      coalesce((SELECT string_agg(cc.chunk_id, ',' ORDER BY cc.cite_order)
                                FROM certificate_chunk cc WHERE cc.cert_ref = ce.cert_ref), '')))
      <> right(ce.cert_ref, 8);

-- ---------------------------------------------------------------------
-- Flagged buildings
-- ---------------------------------------------------------------------
-- verdict and risk_score are derived from the other columns by the Earth Engine
-- export (gee_blue_grid.js, section 6). They are stored because the export is
-- their source, so these checks catch a row that was edited by hand or a new
-- export run with different thresholds.

-- IC8: the verdict follows the export's thresholds.
SELECT 'IC8' AS id, 'building verdict agrees with the export thresholds (0.5 lost, 0.5 flow, 0.15 either)' AS rule,
       count(*) AS violations
FROM building
WHERE verdict <> CASE WHEN lost_frac > 0.5 THEN 'RED_FORMER_WATER_BODY'
                      WHEN flow_frac > 0.5 THEN 'RED_BLOCKS_DRAINAGE'
                      WHEN greatest(lost_frac, flow_frac) > 0.15 THEN 'AMBER_PARTIAL'
                      ELSE 'GREEN_CLEAR' END;

-- IC9: the risk score follows the export's formula (to floating-point precision).
SELECT 'IC9' AS id, 'risk_score = max(lost, flow) * log10(upstream + 1) / (hand + 1) * 100' AS rule,
       count(*) AS violations
FROM building
WHERE abs(risk_score - greatest(lost_frac, flow_frac) * log(upstream_km2 + 1)
                       / (greatest(hand_m, 0) + 1) * 100) > 1e-9;
