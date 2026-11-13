#!/usr/bin/env python3
"""Generate a realistic volume of plot checks for timing the queries (CP4).

    python3 dbms/generate_workload.py --screenings 100000 --seed 2026 | psql -d bluetrace -v ON_ERROR_STOP=1

Run it after dbms/load_app_data.py. It appends; it does not replace anything.

Why: BlueTrace keeps a plot check only in the browser, so there is no history to
export, and timing queries on a handful of rows measures nothing (PostgreSQL
reads a table that small sequentially whatever indexes exist). This script
produces the history a screening desk would build up, using the app's own
logic for every value:

  where       a seeded random mix: 60% uniform over the study rectangle, 40%
              within about 100 m of a flagged building (officers check plots
              where the map shows a problem)
  settings    plot frontage weighted towards small residential plots; buffer
              rule state or NGT; storage rule left blank 60% of the time
  measured    Layers.read_site() - readSite() over the same PNG layers
  judged      decide_() - decide()
  traced      Layers.trace() - traceDownstream(), inside the study area only
  certified   25% of checks, a few minutes later; the reference carries the
              real FNV-1a digest of the canonical record, so query R14 must
              verify every one of them

Screening ids, certificate numbers and the identity / sequence counters are
assigned by the database, so the output can be appended to any database built
from dbms/03_schema.sql.
"""
import argparse
import csv
import datetime
import io
import json
import random
import sys

from bluetrace_logic import (APP, CODE_CHUNK, CORPUS, RULESETS, Layers, canonical, decide_, fnv1a)

CITY = 'bengaluru'
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
PLOT_M = [(9, 15), (12, 20), (15, 15), (18, 10), (24, 10), (30, 20), (40, 6), (60, 4)]   # (metres, weight)
STORAGE = [None] * 12 + [10, 20, 30, 40, 60] * 1 + [20, 30, 30]                       # mostly blank
GENERATORS = [('none', 30), ('offline', 50), ('model', 20)]
RULE_CHUNK = {'ngt': 'rule.lake-buffer.ngt-75m', 'state': 'rule.lake-buffer.state-30m'}


def weighted(rng, pairs):
    total = sum(w for _, w in pairs)
    x = rng.uniform(0, total)
    for v, w in pairs:
        x -= w
        if x <= 0:
            return v
    return pairs[-1][0]


def centroids():
    """centroidOf() for every flagged building of the city (vertex average, closing vertex included)."""
    feats = json.loads((APP / 'data' / CITY / 'flagged_buildings.geojson').read_text())['features']
    out = []
    for f in feats:
        ring = f['geometry']['coordinates'][0]
        out.append((sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)))
    return out


def copy_block(table, columns, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    for r in rows:
        w.writerow(['' if v is None else v for v in r])
    return ('COPY %s (%s) FROM STDIN WITH (FORMAT csv, NULL \'\');\n' % (table, ', '.join(columns))
            + buf.getvalue() + '\\.\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--screenings', type=int, default=100000)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--certified', type=float, default=0.25, help='share of checks that get a certificate')
    args = ap.parse_args()
    if args.screenings < 1:
        ap.error('--screenings must be at least 1')
    if not 0 <= args.certified <= 1:
        ap.error('--certified is a share of the checks, between 0 and 1')

    rng = random.Random(args.seed)
    layers = Layers(CITY)
    missing = [n for n in ('buffers', 'history', 'hydro', 'routing', 'encroached') if n not in layers.s]
    if missing:
        sys.exit('missing raster layers for %s in blue-grid/data/%s: %s (run blue-grid/fetch_layers.sh)'
                 % (CITY, CITY, ', '.join(missing)))
    b = layers.b
    near = centroids()
    start = datetime.datetime(2025, 1, 1, tzinfo=IST)
    days = (datetime.datetime(2026, 11, 12, tzinfo=IST) - start).days

    # when each check happened: working days, office hours, in time order
    times = []
    while len(times) < args.screenings:
        d = start + datetime.timedelta(days=rng.randrange(days))
        if d.weekday() == 6:      # no Sunday desk
            continue
        times.append(d + datetime.timedelta(seconds=rng.randrange(int(9.5 * 3600), 18 * 3600)))
    times.sort()

    screenings, reasons, steps, certs, cited = [], [], [], [], []
    for rel, checked in enumerate(times, start=1):
        if rng.random() < 0.6:
            lon, lat = rng.uniform(b[0], b[2]), rng.uniform(b[1], b[3])
        else:
            clon, clat = near[rng.randrange(len(near))]
            lon, lat = clon + rng.uniform(-0.0009, 0.0009), clat + rng.uniform(-0.0009, 0.0009)
        lon, lat = round(lon, 6), round(lat, 6)       # the certificate prints 6 decimals
        plot_m = weighted(rng, PLOT_M)
        rule = RULESETS['state' if rng.random() < 0.55 else 'ngt']
        storage = rng.choice(STORAGE)

        m = layers.read_site(lon, lat, plot_m)
        verdict, found = decide_(m, rule)
        in_aoi = m['distPresent'] is not None and m['distHistoric'] is not None
        route, ended = layers.trace(lon, lat) if in_aoi else ([], None)

        screenings.append((rel, checked.isoformat(), CITY, rule['id'], '%.6f' % lat, '%.6f' % lon, plot_m,
                           m['distPresent'], m['distHistoric'], m['distDrain'], m['lastWaterYear'],
                           m['occurrence'], m['handM'], round(m['encroached'], 3), m['upaKm2'], storage, ended))
        for code, text in found:
            reasons.append((rel, code, text))
        for k, (direction, length, upa, hand) in enumerate(route, start=1):
            steps.append((rel, k, direction, length, upa, hand))

        if rng.random() < args.certified:
            issued = checked + datetime.timedelta(seconds=rng.randrange(60, 1200), milliseconds=rng.randrange(1000))
            iso = issued.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') \
                + '%03dZ' % (issued.microsecond // 1000)
            generator = weighted(rng, GENERATORS)
            chunks = []
            if generator != 'none':
                for c in [CODE_CHUNK[code] for code, _ in found] + [RULE_CHUNK[rule['id']], 'error.budget.combined-20m']:
                    if c not in chunks:
                        chunks.append(c)
            canon = canonical(CITY, lat, lon, plot_m, rule, m, verdict, iso, CORPUS['corpus_version'],
                              generator, chunks)
            digest = fnv1a(canon)
            certs.append((rel, issued.isoformat(timespec='milliseconds'), iso[:10].replace('-', ''),
                          CORPUS['corpus_version'], generator, digest))
            for k, c in enumerate(chunks, start=1):
                cited.append((rel, c, k))

    w = sys.stdout.write
    w('-- generated by dbms/generate_workload.py --screenings %d --seed %d --certified %s\n'
      % (args.screenings, args.seed, args.certified))
    w('SET search_path TO bluetrace;\nBEGIN;\n')
    w('CREATE TEMP TABLE stg_screening (rel BIGINT, checked_at TIMESTAMPTZ, city_key TEXT, rule_id TEXT, lat NUMERIC, '
      'lon NUMERIC, plot_m SMALLINT, dist_present SMALLINT, dist_historic SMALLINT, dist_drain SMALLINT, '
      'last_water_year SMALLINT, occurrence SMALLINT, hand_m SMALLINT, encroached NUMERIC, upa_km2 NUMERIC, '
      'storage_lpm2 NUMERIC, route_ended_by TEXT) ON COMMIT DROP;\n')
    w('CREATE TEMP TABLE stg_reason (rel BIGINT, reason_code TEXT, reason_text TEXT) ON COMMIT DROP;\n')
    w('CREATE TEMP TABLE stg_step (rel BIGINT, step_no SMALLINT, direction TEXT, step_length_m NUMERIC, '
      'step_upa_km2 NUMERIC, step_hand_m SMALLINT) ON COMMIT DROP;\n')
    w('CREATE TEMP TABLE stg_cert (rel BIGINT, issued_at TIMESTAMPTZ, ymd TEXT, corpus_version TEXT, generator TEXT, '
      'digest TEXT) ON COMMIT DROP;\n')
    w('CREATE TEMP TABLE stg_cited (rel BIGINT, chunk_id TEXT, cite_order SMALLINT) ON COMMIT DROP;\n')
    w(copy_block('stg_screening', ['rel', 'checked_at', 'city_key', 'rule_id', 'lat', 'lon', 'plot_m', 'dist_present',
                                   'dist_historic', 'dist_drain', 'last_water_year', 'occurrence', 'hand_m',
                                   'encroached', 'upa_km2', 'storage_lpm2', 'route_ended_by'], screenings))
    w(copy_block('stg_reason', ['rel', 'reason_code', 'reason_text'], reasons))
    w(copy_block('stg_step', ['rel', 'step_no', 'direction', 'step_length_m', 'step_upa_km2', 'step_hand_m'], steps))
    w(copy_block('stg_cert', ['rel', 'issued_at', 'ymd', 'corpus_version', 'generator', 'digest'], certs))
    w(copy_block('stg_cited', ['rel', 'chunk_id', 'cite_order'], cited))
    w("""
-- the database assigns the ids: new screening id = current maximum + rel
CREATE TEMP TABLE base ON COMMIT DROP AS SELECT coalesce(max(screening_id), 0) AS id FROM screening;
INSERT INTO screening (screening_id, checked_at, city_key, rule_id, lat, lon, plot_m, dist_present, dist_historic,
                       dist_drain, last_water_year, occurrence, hand_m, encroached, upa_km2, storage_lpm2,
                       route_ended_by)
OVERRIDING SYSTEM VALUE
SELECT base.id + rel, checked_at, city_key, rule_id, lat, lon, plot_m, dist_present, dist_historic, dist_drain,
       last_water_year, occurrence, hand_m, encroached, upa_km2, storage_lpm2, route_ended_by
FROM stg_screening, base ORDER BY rel;
SELECT setval(pg_get_serial_sequence('bluetrace.screening', 'screening_id'), (SELECT max(screening_id) FROM screening));
INSERT INTO screening_reason SELECT base.id + rel, reason_code, reason_text FROM stg_reason, base;
INSERT INTO route_step SELECT base.id + rel, step_no, direction, step_length_m, step_upa_km2, step_hand_m
FROM stg_step, base;
-- certificate numbers continue the sequence, in the order the certificates were issued
CREATE TEMP TABLE numbered ON COMMIT DROP AS
SELECT s.*, base.id + s.rel AS screening_id,
       (SELECT last_value FROM certificate_seq) + row_number() OVER (ORDER BY s.issued_at, s.rel) AS n
FROM stg_cert s, base;
INSERT INTO certificate (cert_ref, screening_id, issued_at, corpus_version, generator)
-- padStart(4, '0'): at least 4 digits; lpad() alone would cut 12345 down to 1234
SELECT 'BT/BLR/' || ymd || '/' || lpad(n::text, greatest(4, length(n::text)), '0') || '-' || digest,
       screening_id, issued_at, corpus_version,
       generator
FROM numbered ORDER BY n;
SELECT setval('certificate_seq', (SELECT max(n) FROM numbered));
INSERT INTO certificate_chunk (cert_ref, chunk_id, cite_order)
SELECT c.cert_ref, s.chunk_id, s.cite_order
FROM stg_cited s
JOIN base ON true
JOIN certificate c ON c.screening_id = base.id + s.rel;
COMMIT;
VACUUM (ANALYZE) screening;
VACUUM (ANALYZE) screening_reason;
VACUUM (ANALYZE) route_step;
VACUUM (ANALYZE) certificate;
VACUUM (ANALYZE) certificate_chunk;
""")
    print('generated %d screenings, %d reasons, %d route steps, %d certificates, %d citations'
          % (len(screenings), len(reasons), len(steps), len(certs), len(cited)), file=sys.stderr)


if __name__ == '__main__':
    main()
