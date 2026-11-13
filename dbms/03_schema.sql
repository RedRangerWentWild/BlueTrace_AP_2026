-- =====================================================================
-- BlueTrace - relational schema (CP2)
-- Team T0015 (Bluetrace), Section E
--
-- The 16 tables of dbms/01_normalization.md (all in BCNF), with types, keys,
-- foreign keys and CHECK constraints. Runs on an empty PostgreSQL database
-- (tested on 16.15):
--
--     createdb bluetrace
--     psql -d bluetrace -v ON_ERROR_STOP=1 -f dbms/03_schema.sql
--     python3 dbms/load_app_data.py | psql -d bluetrace -v ON_ERROR_STOP=1
--
-- Where a value comes from in the app is noted per table (blue-grid/index.html
-- unless said otherwise), so every column can be traced back to the code.
--
-- Five columns were added to the design in 01_normalization.md while writing
-- this file, because the app needs them and they cannot be derived (each one
-- depends only on its table's key, so every table is still in BCNF; see
-- 01_normalization.md, section 9):
--   reason_code.chunk_id          CODE_CHUNK: every reason code cites exactly one
--                                 chunk ("the citation spine").
--   screening.storage_lpm2        the operator's storage rule (litres per m2), an
--                                 input without which the rainwater-harvesting
--                                 figure and the shortfall cannot be recomputed.
--   screening.route_ended_by      why the downstream trace stopped (ROUTE_END);
--                                 printed on the certificate, not derivable from
--                                 the steps.
--   param.plus_minus              the +/- uncertainty a parameter is declared with
--                                 ("pm" in corpus.json); the plausible runoff
--                                 range is computed from it.
--   certificate_chunk.cite_order  the order of the cited chunks. The certificate's
--                                 digest covers the chunk list in order, so it
--                                 cannot be re-verified without it (query R14).
-- building.centroid_lon/_lat are GENERATED columns: derived from geometry, but
-- computed by PostgreSQL itself, so they can never disagree with it (see BUILDING).
-- =====================================================================

DROP SCHEMA IF EXISTS bluetrace CASCADE;   -- makes the script re-runnable
CREATE SCHEMA bluetrace;
SET search_path TO bluetrace;

-- ---------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------

-- AUTHORITY: what kind of source a corpus chunk rests on.
-- authority -> url_required. A statute, a court order, an agency survey or a
-- dataset document must carry a URL; a repo-derived or editorial chunk need not.
CREATE TABLE authority (
    authority    VARCHAR(20) PRIMARY KEY,
    url_required BOOLEAN     NOT NULL,
    CONSTRAINT ck_authority_name CHECK (authority IN
        ('statute', 'court', 'agency-survey', 'dataset-doc', 'repo-derived', 'editorial'))
);

-- OUTCOME: the four screening outcomes (OUTCOME in index.html). There is
-- deliberately no APPROVE. rank orders them for the verdict:
-- REJECT 3 > REFER 2 > CONDITIONS 1 > NO_OBJECTION 0 (decide(): rank = {...}).
CREATE TABLE outcome (
    outcome VARCHAR(12) PRIMARY KEY,
    title   VARCHAR(40) NOT NULL,
    rank    SMALLINT    NOT NULL,
    CONSTRAINT uq_outcome_title UNIQUE (title),
    CONSTRAINT uq_outcome_rank  UNIQUE (rank),   -- the verdict needs a strict order
    CONSTRAINT ck_outcome_name  CHECK (outcome IN ('REJECT', 'REFER', 'CONDITIONS', 'NO_OBJECTION')),
    CONSTRAINT ck_outcome_rank  CHECK (rank BETWEEN 0 AND 3)
);

-- BUFFER_RULE: a buffer regime (RULESETS). Rows are never UPDATEd: a revised
-- regime is a new rule_id, so screenings keep pointing at the distances they
-- were judged against (01_normalization.md, section 5).
CREATE TABLE buffer_rule (
    rule_id    VARCHAR(16) PRIMARY KEY,
    rule_label VARCHAR(80) NOT NULL,
    lake_m     SMALLINT    NOT NULL,
    drain_m    SMALLINT    NOT NULL,
    CONSTRAINT uq_buffer_rule_label UNIQUE (rule_label),
    CONSTRAINT ck_buffer_rule_id    CHECK (rule_id ~ '^[a-z][a-z0-9_]*$'),
    CONSTRAINT ck_buffer_rule_lake  CHECK (lake_m  BETWEEN 1 AND 500),
    CONSTRAINT ck_buffer_rule_drain CHECK (drain_m BETWEEN 1 AND 500)
);

-- CITY: one study area (CITIES + data/<city>/stats.json).
-- The statistics are NULL until that city's Earth Engine export has been run
-- (Chennai has a configuration but no export yet).
CREATE TABLE city (
    city_key                VARCHAR(20)  PRIMARY KEY,
    city_label              VARCHAR(40)  NOT NULL,
    catchment               VARCHAR(80)  NOT NULL,
    lon_min                 NUMERIC(9,6) NOT NULL,
    lat_min                 NUMERIC(8,6) NOT NULL,
    lon_max                 NUMERIC(9,6) NOT NULL,
    lat_max                 NUMERIC(8,6) NOT NULL,
    zones                   VARCHAR(120) NOT NULL,
    historic_ha             NUMERIC(10,2),
    present_ha              NUMERIC(10,2),
    lost_ha                 NUMERIC(10,2),
    encroached_ha           NUMERIC(10,2),
    floodprone_ha           NUMERIC(10,2),
    buildings_in_floodprone INTEGER,
    CONSTRAINT uq_city_label  UNIQUE (city_label),
    CONSTRAINT ck_city_key    CHECK (city_key ~ '^[a-z]+$'),
    CONSTRAINT ck_city_bounds CHECK (lon_min < lon_max AND lat_min < lat_max
                                     AND lon_min >= -180 AND lon_max <= 180
                                     AND lat_min >= -90  AND lat_max <= 90),
    CONSTRAINT ck_city_stats  CHECK (historic_ha >= 0 AND present_ha >= 0 AND lost_ha >= 0
                                     AND encroached_ha >= 0 AND floodprone_ha >= 0
                                     AND buildings_in_floodprone >= 0),
    -- the statistics arrive together, from one stats.json, or not at all
    CONSTRAINT ck_city_stats_together CHECK (
        num_nulls(historic_ha, present_ha, lost_ha, encroached_ha, floodprone_ha, buildings_in_floodprone) IN (0, 6))
);

-- HOTSPOT: named localities shown for a city (CITIES[...].hotspots).
-- px = number of flagged pixels in that locality.
CREATE TABLE hotspot (
    city_key VARCHAR(20)  NOT NULL,
    name     VARCHAR(80)  NOT NULL,
    lon      NUMERIC(9,6) NOT NULL,
    lat      NUMERIC(8,6) NOT NULL,
    px       INTEGER      NOT NULL,
    CONSTRAINT pk_hotspot PRIMARY KEY (city_key, name),
    -- CASCADE: a hotspot is part of the city's configuration
    CONSTRAINT fk_hotspot_city FOREIGN KEY (city_key) REFERENCES city (city_key) ON DELETE CASCADE,
    CONSTRAINT ck_hotspot_px   CHECK (px > 0)
);

-- ---------------------------------------------------------------------
-- The cited corpus (blue-grid/corpus/**/*.md, compiled into data/corpus.json)
-- ---------------------------------------------------------------------

-- CHUNK: one idea, with the source it rests on. chunk_id is built as
-- <kind>.<file name>, so chunk_id -> kind (the key determines it: still BCNF),
-- and the CHECK below keeps the two from disagreeing.
CREATE TABLE chunk (
    chunk_id  VARCHAR(80)  PRIMARY KEY,
    title     VARCHAR(200) NOT NULL,
    kind      VARCHAR(12)  NOT NULL,
    authority VARCHAR(20)  NOT NULL,
    source    TEXT         NOT NULL,
    url       TEXT,                     -- NULL = no URL (allowed only for some authorities)
    body      TEXT         NOT NULL,
    CONSTRAINT fk_chunk_authority FOREIGN KEY (authority) REFERENCES authority (authority) ON DELETE RESTRICT,
    CONSTRAINT ck_chunk_id        CHECK (chunk_id ~ '^[a-z]+\.[a-z0-9][a-z0-9.-]*$'),
    CONSTRAINT ck_chunk_kind      CHECK (kind IN ('error', 'hydro', 'limit', 'method', 'option',
                                                  'outcome', 'precedent', 'refusal', 'rule', 'scope')),
    CONSTRAINT ck_chunk_id_kind   CHECK (split_part(chunk_id, '.', 1) = kind),
    CONSTRAINT ck_chunk_url       CHECK (url IS NULL OR url ~ '^https?://'),
    CONSTRAINT ck_chunk_body      CHECK (length(body) > 0)
);

-- CHUNK_TAG / CHUNK_INTENT: all-key tables (the repeating groups of a chunk).
CREATE TABLE chunk_tag (
    chunk_id VARCHAR(80) NOT NULL,
    tag      VARCHAR(40) NOT NULL,
    CONSTRAINT pk_chunk_tag PRIMARY KEY (chunk_id, tag),
    CONSTRAINT fk_tag_chunk FOREIGN KEY (chunk_id) REFERENCES chunk (chunk_id) ON DELETE CASCADE,
    CONSTRAINT ck_tag_form  CHECK (tag = lower(tag) AND length(tag) > 0)
);

CREATE TABLE chunk_intent (
    chunk_id VARCHAR(80) NOT NULL,
    intent   VARCHAR(12) NOT NULL,
    CONSTRAINT pk_chunk_intent PRIMARY KEY (chunk_id, intent),
    CONSTRAINT fk_intent_chunk FOREIGN KEY (chunk_id) REFERENCES chunk (chunk_id) ON DELETE CASCADE,
    -- the five intents the router knows (corpus.json "intents")
    CONSTRAINT ck_intent_name  CHECK (intent IN ('flood', 'feasibility', 'consequence', 'procedure', 'evidence'))
);

-- PARAM: every number the tool computes with lives on the chunk that cites
-- its source. param_name -> chunk_id, value, unit (53 distinct names).
CREATE TABLE param (
    param_name VARCHAR(40) PRIMARY KEY,
    chunk_id   VARCHAR(80) NOT NULL,
    value      NUMERIC     NOT NULL,
    plus_minus NUMERIC,                   -- declared uncertainty; NULL = none declared
    unit       VARCHAR(20),               -- NULL for dimensionless values (coefficients)
    -- RESTRICT: a chunk that declares a number the code uses must not vanish
    CONSTRAINT fk_param_chunk FOREIGN KEY (chunk_id) REFERENCES chunk (chunk_id) ON DELETE RESTRICT,
    CONSTRAINT ck_param_name  CHECK (param_name ~ '^[A-Za-z][A-Za-z0-9_]*$'),
    CONSTRAINT ck_param_pm    CHECK (plus_minus >= 0)
);

-- REASON_CODE: a branch of decide(). reason_code -> outcome, chunk_id.
-- Codes are named <outcome>.<finding> (reject.inside-buffer is a REJECT), and
-- the CHECK holds the app to that convention.
CREATE TABLE reason_code (
    reason_code VARCHAR(48) PRIMARY KEY,
    outcome     VARCHAR(12) NOT NULL,
    chunk_id    VARCHAR(80) NOT NULL,     -- CODE_CHUNK: the chunk forced into every answer
    CONSTRAINT fk_reason_outcome FOREIGN KEY (outcome)  REFERENCES outcome (outcome) ON DELETE RESTRICT,
    CONSTRAINT fk_reason_chunk   FOREIGN KEY (chunk_id) REFERENCES chunk (chunk_id)  ON DELETE RESTRICT,
    CONSTRAINT ck_reason_prefix  CHECK (split_part(reason_code, '.', 1) = lower(replace(outcome, '_', '-')))
);

-- ---------------------------------------------------------------------
-- Flagged buildings (data/<city>/flagged_buildings.geojson)
-- ---------------------------------------------------------------------
-- The ring-centroid function mirrors centroidOf() in index.html exactly: the
-- plain average of every vertex of the outer ring (the closing vertex
-- included), so SQL finds the same neighbours the app shows.
CREATE FUNCTION ring_centroid(geom JSONB, axis INTEGER) RETURNS DOUBLE PRECISION
LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT avg((p ->> axis)::DOUBLE PRECISION)
    FROM jsonb_array_elements(geom -> 'coordinates' -> 0) AS p
$$;

-- verdict, risk_score and the fractions are computed by the Earth Engine
-- export (gee_blue_grid.js), not by the app, and the thresholds are not stored
-- with the data, so they are stored facts here (01_normalization.md, section 6).
-- DOUBLE PRECISION because the export writes IEEE doubles; NUMERIC would add
-- digits that were never measured.
CREATE TABLE building (
    building_id  INTEGER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_key     VARCHAR(20)      NOT NULL,
    geometry     JSONB            NOT NULL,
    verdict      VARCHAR(24)      NOT NULL,
    risk_score   DOUBLE PRECISION NOT NULL,
    lost_frac    DOUBLE PRECISION NOT NULL,
    flow_frac    DOUBLE PRECISION NOT NULL,
    upstream_km2 DOUBLE PRECISION NOT NULL,
    hand_m       DOUBLE PRECISION NOT NULL,
    area_m2      DOUBLE PRECISION NOT NULL,   -- "area_in_meters" in the GeoJSON
    confidence   DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION GENERATED ALWAYS AS (ring_centroid(geometry, 0)) STORED,
    centroid_lat DOUBLE PRECISION GENERATED ALWAYS AS (ring_centroid(geometry, 1)) STORED,
    -- CASCADE: the buildings are one city's export and are replaced as a whole
    CONSTRAINT fk_building_city     FOREIGN KEY (city_key) REFERENCES city (city_key) ON DELETE CASCADE,
    CONSTRAINT ck_building_geometry CHECK (geometry ->> 'type' = 'Polygon'
                                           AND jsonb_array_length(geometry -> 'coordinates' -> 0) >= 4),
    CONSTRAINT ck_building_verdict  CHECK (verdict IN ('RED_FORMER_WATER_BODY', 'RED_BLOCKS_DRAINAGE',
                                                       'AMBER_PARTIAL', 'GREEN_CLEAR')),
    CONSTRAINT ck_building_risk     CHECK (risk_score > 0),
    CONSTRAINT ck_building_fracs    CHECK (lost_frac BETWEEN 0 AND 1 AND flow_frac BETWEEN 0 AND 1
                                           AND confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_building_measures CHECK (upstream_km2 >= 0 AND hand_m >= 0 AND area_m2 > 0)
);

-- ---------------------------------------------------------------------
-- Screenings and certificates (what the officer creates by using the app)
-- ---------------------------------------------------------------------

-- SCREENING: one plot check (siteContext().rec). Measurements are the bytes
-- read from the rasters: distances 0-255 m (255 = "255 m or more"), height
-- above drainage 0-255 m (255 = byte ceiling, unknown), occurrence 0-100 %,
-- last water year 1984-2021 (1983 + byte). All of them are NULL outside the
-- study area, which decide() turns into refer.outside-study-area.
-- verdict, retreat, hand class, route length and the runoff / retention
-- figures are NOT stored: they are computed from these columns, the reasons,
-- the route steps and PARAM (01_normalization.md, section 5).
CREATE TABLE screening (
    screening_id    BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    checked_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    city_key        VARCHAR(20)  NOT NULL,
    rule_id         VARCHAR(16)  NOT NULL,
    lat             NUMERIC(8,6) NOT NULL,   -- 6 decimals, as printed on the certificate
    lon             NUMERIC(9,6) NOT NULL,
    plot_m          SMALLINT     NOT NULL,   -- plot frontage typed by the officer
    dist_present    SMALLINT,
    dist_historic   SMALLINT,
    dist_drain      SMALLINT,
    last_water_year SMALLINT,                -- NULL = never recorded as water
    occurrence      SMALLINT,
    hand_m          SMALLINT,
    encroached      NUMERIC(4,3),            -- share of the probe that reads as construction
    upa_km2         NUMERIC(10,4),           -- NULL when the hydro layer is not exported
    storage_lpm2    NUMERIC(8,2),            -- NULL = storage rule not supplied by the operator
    route_ended_by  VARCHAR(10),             -- NULL = no route traced
    -- RESTRICT: a screening is evidence; its city and its rule must stay
    CONSTRAINT fk_screening_city FOREIGN KEY (city_key) REFERENCES city (city_key)       ON DELETE RESTRICT,
    CONSTRAINT fk_screening_rule FOREIGN KEY (rule_id)  REFERENCES buffer_rule (rule_id) ON DELETE RESTRICT,
    CONSTRAINT ck_screening_latlon   CHECK (lat BETWEEN -90 AND 90 AND lon BETWEEN -180 AND 180),
    CONSTRAINT ck_screening_plot     CHECK (plot_m BETWEEN 1 AND 1000),
    CONSTRAINT ck_screening_dists    CHECK (dist_present BETWEEN 0 AND 255 AND dist_historic BETWEEN 0 AND 255
                                            AND dist_drain BETWEEN 0 AND 255),
    CONSTRAINT ck_screening_year     CHECK (last_water_year BETWEEN 1984 AND 2021),
    CONSTRAINT ck_screening_occ      CHECK (occurrence BETWEEN 0 AND 100),
    CONSTRAINT ck_screening_hand     CHECK (hand_m BETWEEN 0 AND 255),
    CONSTRAINT ck_screening_encr     CHECK (encroached BETWEEN 0 AND 1),
    CONSTRAINT ck_screening_upa      CHECK (upa_km2 >= 0),
    CONSTRAINT ck_screening_storage  CHECK (storage_lpm2 >= 0),
    CONSTRAINT ck_screening_ended_by CHECK (route_ended_by IN
        ('trunk', 'mouth', 'depression', 'edge', 'loop', 'capped', 'nodata')),
    -- inside or outside the study area: both distance fields are read from the
    -- same layer, so they are present together or absent together
    CONSTRAINT ck_screening_aoi      CHECK ((dist_present IS NULL) = (dist_historic IS NULL)),
    -- no route is traced outside the study area
    CONSTRAINT ck_screening_route    CHECK (dist_present IS NOT NULL OR route_ended_by IS NULL)
);

-- SCREENING_REASON: one finding of decide() for one screening. The text is
-- stored because it contains this plot's own distances.
CREATE TABLE screening_reason (
    screening_id BIGINT      NOT NULL,
    reason_code  VARCHAR(48) NOT NULL,
    reason_text  TEXT        NOT NULL,
    CONSTRAINT pk_screening_reason PRIMARY KEY (screening_id, reason_code),
    CONSTRAINT fk_sr_screening FOREIGN KEY (screening_id) REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT fk_sr_reason    FOREIGN KEY (reason_code)  REFERENCES reason_code (reason_code) ON DELETE RESTRICT,
    CONSTRAINT ck_sr_text      CHECK (length(reason_text) > 0)
);

-- ROUTE_STEP: one MERIT Hydro cell of the downstream trace (traceDownstream).
-- A step is 90 m along an axis or ~127 m on a diagonal; at most routeMaxSteps
-- (200) steps. Upstream area and height can be NULL where the layer has no value.
CREATE TABLE route_step (
    screening_id  BIGINT        NOT NULL,
    step_no       SMALLINT      NOT NULL,
    direction     VARCHAR(2)    NOT NULL,
    step_length_m NUMERIC(6,1)  NOT NULL,
    step_upa_km2  NUMERIC(10,4),
    step_hand_m   SMALLINT,
    CONSTRAINT pk_route_step PRIMARY KEY (screening_id, step_no),
    -- CASCADE: a route step has no meaning without its screening (weak entity)
    CONSTRAINT fk_step_screening FOREIGN KEY (screening_id) REFERENCES screening (screening_id) ON DELETE CASCADE,
    CONSTRAINT ck_step_no        CHECK (step_no BETWEEN 1 AND 200),
    CONSTRAINT ck_step_direction CHECK (direction IN ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')),
    CONSTRAINT ck_step_length    CHECK (step_length_m > 0 AND step_length_m < 200),
    CONSTRAINT ck_step_upa       CHECK (step_upa_km2 >= 0),
    CONSTRAINT ck_step_hand      CHECK (step_hand_m BETWEEN 0 AND 254)
);

-- Certificate numbers: nextSeq() kept a counter in localStorage, which a second
-- desk or a cleared browser would reset. In the database it is a sequence.
CREATE SEQUENCE certificate_seq;

-- CERTIFICATE: the printed screening certificate (renderCertificate).
-- cert_ref = BT/<city code>/<UTC date>/<4-digit number>-<FNV-1a digest of the
-- canonical record>. One certificate per screening (screening_id UNIQUE), so
-- {cert_ref} and {screening_id} are both candidate keys (BCNF, see section 6).
CREATE TABLE certificate (
    cert_ref       VARCHAR(40)  PRIMARY KEY,
    screening_id   BIGINT       NOT NULL,
    issued_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    application_no VARCHAR(40),          -- typed on the certificate; may be blank
    survey_no      VARCHAR(40),
    applicant      VARCHAR(120),
    corpus_version VARCHAR(40)  NOT NULL,
    generator      VARCHAR(10)  NOT NULL DEFAULT 'none',   -- who wrote the answer carried on it
    CONSTRAINT uq_certificate_screening UNIQUE (screening_id),
    -- RESTRICT: a certificate is a document of record; its screening cannot be deleted
    CONSTRAINT fk_certificate_screening FOREIGN KEY (screening_id) REFERENCES screening (screening_id) ON DELETE RESTRICT,
    CONSTRAINT ck_certificate_ref    CHECK (cert_ref ~ '^BT/[A-Z]{3}/[0-9]{8}/[0-9]{4,}-[0-9A-F]{8}$'),
    CONSTRAINT ck_certificate_corpus CHECK (corpus_version = 'no-corpus'
                                            OR corpus_version ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9a-f]{8}$'),
    -- 'none' = no answer on the certificate, 'offline' = composed by the app
    -- itself (Tier 0), 'model' = paragraph written by the language model (Tier 1)
    CONSTRAINT ck_certificate_generator CHECK (generator IN ('none', 'offline', 'model'))
);

-- CERTIFICATE_CHUNK: which chunks a certificate cites (the evidence pack), in
-- order. Candidate keys: {cert_ref, chunk_id} and {cert_ref, cite_order}.
CREATE TABLE certificate_chunk (
    cert_ref   VARCHAR(40) NOT NULL,
    chunk_id   VARCHAR(80) NOT NULL,
    cite_order SMALLINT    NOT NULL,
    CONSTRAINT pk_certificate_chunk PRIMARY KEY (cert_ref, chunk_id),
    CONSTRAINT uq_cc_order       UNIQUE (cert_ref, cite_order),
    CONSTRAINT ck_cc_order       CHECK (cite_order >= 1),
    CONSTRAINT fk_cc_certificate FOREIGN KEY (cert_ref) REFERENCES certificate (cert_ref) ON DELETE CASCADE,
    -- RESTRICT: a chunk cited on paper must not disappear from the database
    CONSTRAINT fk_cc_chunk       FOREIGN KEY (chunk_id) REFERENCES chunk (chunk_id)       ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- Two rules of the app, written once in SQL so queries apply them exactly
-- ---------------------------------------------------------------------
-- sig2(): every derived volume is reported to two significant figures
-- (sig2() in index.html: "a third digit would claim precision the inputs
-- cannot support").
CREATE FUNCTION sig2(x NUMERIC) RETURNS NUMERIC
LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT CASE WHEN x = 0 THEN 0 ELSE round(x, 1 - floor(log(abs(x)))::INTEGER) END
$$;

-- fnv1a(): the 32-bit FNV-1a digest printed in every certificate reference
-- (fnv1a() in index.html), so a stored certificate can be re-verified (R14).
CREATE FUNCTION fnv1a(s TEXT) RETURNS TEXT
LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE
    h BIGINT := 2166136261;          -- 0x811c9dc5
BEGIN
    FOR i IN 1 .. length(s) LOOP
        h := h # ascii(substr(s, i, 1));
        h := (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) & 4294967295;
    END LOOP;
    RETURN upper(lpad(to_hex(h), 8, '0'));
END
$$;

-- ---------------------------------------------------------------------
-- Indexes beyond those created by PRIMARY KEY / UNIQUE. Which queries of
-- dbms/04_queries.sql actually use them was checked in the CP4 plans
-- (dbms/plans/): only the first two are chosen by the planner today.
-- ---------------------------------------------------------------------
-- R3: the ranked list of flagged buildings in a city (top 25 without a sort)
CREATE INDEX ix_building_city_risk  ON building (city_key, risk_score DESC);
-- R4: flagged buildings within 300 m of a clicked point (bounding-box prefilter)
CREATE INDEX ix_building_centroid   ON building (centroid_lat, centroid_lon);
-- R10 filters chunks by intent and by tag. With 170 intents and 662 tags the
-- planner reads those tables directly (plans/R10.txt); these indexes start to
-- pay once the corpus grows by an order of magnitude or two.
CREATE INDEX ix_chunk_intent_intent ON chunk_intent (intent);
CREATE INDEX ix_chunk_tag_tag       ON chunk_tag (tag);
-- The foreign-key index of param.chunk_id: deleting or renaming a chunk must
-- find the parameters that cite it (fk_param_chunk is RESTRICT). No query reads it.
CREATE INDEX ix_param_chunk         ON param (chunk_id);
-- Used by none of the 27 queries: kept for a desk register (a city's latest
-- plot checks), which the app does not have yet. It costs every recorded plot
-- check (W1) one extra index entry.
CREATE INDEX ix_screening_city_time ON screening (city_key, checked_at DESC);

-- ---------------------------------------------------------------------
-- The data dictionary inside the database: \dt+ and \d+ show these.
-- ---------------------------------------------------------------------
COMMENT ON TABLE authority         IS 'Kind of source a corpus chunk rests on; statute, court, agency-survey and dataset-doc chunks must carry a URL';
COMMENT ON TABLE outcome           IS 'The four screening outcomes (deliberately no APPROVE); rank orders them for the verdict';
COMMENT ON TABLE buffer_rule       IS 'A buffer regime (RULESETS); never updated, a revised regime gets a new rule_id';
COMMENT ON TABLE city              IS 'A study area: bounds, catchment and the headline statistics of its Earth Engine export';
COMMENT ON TABLE hotspot           IS 'Named localities shown for a city, with their flagged-pixel count';
COMMENT ON TABLE chunk             IS 'One idea of the cited corpus, with the source it rests on; chunk_id = <kind>.<file name>';
COMMENT ON TABLE chunk_tag         IS 'Words that route a question to a chunk';
COMMENT ON TABLE chunk_intent      IS 'Question intents (flood, feasibility, consequence, procedure, evidence) a chunk serves';
COMMENT ON TABLE param             IS 'Every number the tool computes with, declared on the chunk that cites its source';
COMMENT ON TABLE reason_code       IS 'A branch of decide(): its outcome and the chunk that explains it (the citation spine)';
COMMENT ON TABLE building          IS 'A flagged building footprint from the Earth Engine export, ranked by risk';
COMMENT ON TABLE screening         IS 'One plot check: the raster measurements at a point under one buffer rule; the verdict is derived from its reasons';
COMMENT ON TABLE screening_reason  IS 'One finding of decide() for a plot check, with the sentence shown to the officer';
COMMENT ON TABLE route_step        IS 'One 90 m MERIT Hydro cell of the downhill trace from a plot';
COMMENT ON TABLE certificate       IS 'A printed screening certificate; the reference carries the FNV-1a digest of the canonical record';
COMMENT ON TABLE certificate_chunk IS 'The sources a certificate cites, in the order its digest covers them';

-- Units and encodings, which otherwise live only in the column names.
COMMENT ON COLUMN city.lon_min                     IS 'Degrees east (WGS84); with lat_min, lon_max, lat_max the rectangle every raster layer is mapped onto';
COMMENT ON COLUMN city.historic_ha                 IS 'Hectares of water recorded 1984-99 (JRC transition band); NULL until the city has an export';
COMMENT ON COLUMN city.floodprone_ha               IS 'Hectares less than 2 m above the nearest drainage (MERIT HAND)';
COMMENT ON COLUMN hotspot.px                       IS 'Flagged pixels in the locality; orders the hotspot list';
COMMENT ON COLUMN building.risk_score              IS 'max(lost_frac, flow_frac) * log10(upstream_km2 + 1) / (hand_m + 1) * 100, computed by the export; only > 1 is exported';
COMMENT ON COLUMN building.lost_frac               IS 'Share (0-1) of the footprint on water lost since 1984-99';
COMMENT ON COLUMN building.flow_frac               IS 'Share (0-1) of the footprint on a terrain flow path';
COMMENT ON COLUMN building.upstream_km2            IS 'Square kilometres draining through the footprint (MERIT Hydro, mean)';
COMMENT ON COLUMN building.hand_m                  IS 'Metres above the nearest drainage (mean); the export writes 50 where it has no value';
COMMENT ON COLUMN building.area_m2                 IS 'Footprint area in square metres (Open Buildings area_in_meters)';
COMMENT ON COLUMN building.confidence              IS 'Open Buildings v3 detection confidence (0-1); the export keeps 0.70 and above';
COMMENT ON COLUMN building.centroid_lon            IS 'Generated: average of the outer-ring vertices, as centroidOf() in index.html';
COMMENT ON COLUMN param.value                      IS 'The value, in unit';
COMMENT ON COLUMN param.plus_minus                 IS 'Declared uncertainty, in unit (pm in corpus.json); NULL when none is declared';
COMMENT ON COLUMN screening.lat                    IS 'Degrees north of the checked point, 6 decimals as printed on the certificate';
COMMENT ON COLUMN screening.plot_m                 IS 'Plot frontage in metres, typed by the officer; the probe radius is max(6, plot_m / 2) m';
COMMENT ON COLUMN screening.dist_present           IS 'Metres from the probe to the present water edge (minimum over the probe); 255 means 255 m or more; NULL outside the study area';
COMMENT ON COLUMN screening.dist_historic           IS 'Metres to the 1984-99 water edge; 0 means the plot is on the former bed; 255 means 255 m or more';
COMMENT ON COLUMN screening.dist_drain             IS 'Metres to the nearest terrain-derived drainage line; 255 means 255 m or more';
COMMENT ON COLUMN screening.last_water_year        IS 'Last year the probe was recorded as water (1983 + the byte in history.png); NULL = never, 1984-2021';
COMMENT ON COLUMN screening.occurrence             IS 'Percent of observations 1984-2021 in which the probe was water (maximum over the probe)';
COMMENT ON COLUMN screening.hand_m                 IS 'Metres above the nearest drainage (minimum over the probe); 255 is the byte ceiling, i.e. unknown';
COMMENT ON COLUMN screening.encroached             IS 'Strongest built-on-former-water signal within 35 m, 0-1; decide() treats more than 0.1 as built';
COMMENT ON COLUMN screening.upa_km2                IS 'Square kilometres draining through the plot (decoded from the log-packed hydro layer)';
COMMENT ON COLUMN screening.storage_lpm2           IS 'Storage rule typed by the officer, litres per square metre of plot; NULL = not supplied';
COMMENT ON COLUMN screening.route_ended_by         IS 'Why the downhill trace stopped (ROUTE_END in index.html); NULL = no route traced';
COMMENT ON COLUMN route_step.direction             IS 'D8 compass direction of the step on the MERIT grid';
COMMENT ON COLUMN route_step.step_length_m         IS 'Metres between the two cell centres: about 90 along an axis, about 129 on a diagonal';
COMMENT ON COLUMN route_step.step_upa_km2          IS 'Square kilometres draining through the cell the step arrives in';
COMMENT ON COLUMN route_step.step_hand_m           IS 'Metres above the nearest drainage at the cell the step arrives in; NULL where the layer has no value';
COMMENT ON COLUMN certificate.issued_at            IS 'The instant printed on the certificate (UTC on paper, to the millisecond); part of the digest';
COMMENT ON COLUMN certificate.generator            IS 'Who wrote the answer carried on the certificate: none, offline (the app) or model';
