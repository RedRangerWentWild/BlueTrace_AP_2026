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
