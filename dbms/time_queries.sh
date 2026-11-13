#!/usr/bin/env bash
# Times every query of dbms/04_queries.sql the way CHECKPOINTS.md asks:
# EXPLAIN (ANALYZE, BUFFERS), RUNS times (default 3), average of the
# "Execution Time" lines; WRITE queries inside BEGIN ... ROLLBACK so the data
# never changes. Same method as benchmarks/run_benchmark.sh in the DE project.
#
# Usage:   ./dbms/time_queries.sh <database> [runs] [queries.sql] [output dir]
# Example: ./dbms/time_queries.sh bluetrace
#          -> dbms/plans/R1.txt ... W11.txt   (the plan of every run)
#          -> dbms/plans/summary.csv          (each run, the average, scan types)
#
# Each run is a fresh psql connection. Queries are split on "-- @R1" / "-- @W1"
# marker lines; "-- @END" stops collection. Lines starting with "--" are dropped.
# Connection settings come from the usual libpq variables (PGHOST, PGPORT, PGUSER).
set -euo pipefail

DB="${1:?database name required}"
RUNS="${2:-3}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUERIES="${3:-$ROOT/dbms/04_queries.sql}"
OUT="${4:-$ROOT/dbms/plans}"

# Check everything before the first write: a mistyped database name must not
# leave the committed summary.csv and plan files truncated.
die() { echo "time_queries.sh: $*" >&2; exit 2; }
[[ "$RUNS" =~ ^[1-9][0-9]*$ ]] || die "runs must be a whole number of at least 1, not '$RUNS'"
[[ -r "$QUERIES" ]] || die "cannot read $QUERIES"
grep -qE '^-- @[RW][0-9]+([[:space:]]|$)' "$QUERIES" || die "no '-- @R1' / '-- @W1' markers in $QUERIES"
schema="$(psql -d "$DB" -X -q -A -t -c "SELECT to_regclass('bluetrace.screening') IS NOT NULL" 2>&1)" \
  || die "cannot connect to database '$DB': $schema"
[[ "$schema" == t ]] || die "database '$DB' has no bluetrace schema: load dbms/03_schema.sql first (see README)"
[[ "$(psql -d "$DB" -X -q -A -t -c "SELECT EXISTS (SELECT 1 FROM bluetrace.screening)")" == t ]] \
  || die "database '$DB' has the schema but no plot checks: load the data with dbms/load_app_data.py first"

# Results are written to a temporary folder and copied over the previous ones
# only when every query has run, so a failure never leaves old and new mixed.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/sql" "$TMP/out"
SUMMARY="$TMP/out/summary.csv"
header="query_id,type"
for ((i = 1; i <= RUNS; i++)); do header="$header,run${i}_ms"; done
echo "$header,avg_ms,scan_nodes" > "$SUMMARY"

awk -v dir="$TMP/sql" '
  /^-- @/ { id = ""; if ($2 ~ /^@[RW][0-9]+$/) { id = substr($2, 2); file = dir "/" id ".sql"; printf "" > file }; next }
  id != "" && !/^--/ { print >> file }
' "$QUERIES"

for f in $(ls "$TMP"/sql/*.sql | sort -V); do
  id="$(basename "$f" .sql)"
  type="READ"; [[ "$id" == W* ]] && type="WRITE"
  query="$(cat "$f")"
  times=()
  for ((i = 1; i <= RUNS; i++)); do
    if [[ "$type" == "WRITE" ]]; then
      sql="SET search_path TO bluetrace; BEGIN; EXPLAIN (ANALYZE, BUFFERS) $query ROLLBACK;"
    else
      sql="SET search_path TO bluetrace; EXPLAIN (ANALYZE, BUFFERS) $query"
    fi
    plan="$(printf '%s\n' "$sql" | psql -d "$DB" -X -q -A -t -v ON_ERROR_STOP=1)" \
      || die "$id failed on run $i; the results in $OUT were left as they were"
    echo "=== $id run $i ===" >> "$TMP/out/$id.txt"
    echo "$plan" >> "$TMP/out/$id.txt"
    times+=("$(echo "$plan" | grep -oE 'Execution Time: [0-9.]+' | awk '{print $3}')")
  done
  avg="$(printf '%s\n' "${times[@]}" | awk '{ s += $1 } END { printf "%.3f", s / NR }')"
  # every scan node of the last run, e.g. "Index Scan using screening_pkey on screening"
  node="$(echo "$plan" | grep -oE '(Parallel )?(Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|CTE Scan|Function Scan|Values Scan)( Backward)?( using [a-z0-9_]+)?( on [a-z0-9_]+)?' | sed -E 's/Parallel //; s/ Backward//' | awk '!seen[$0]++' | paste -sd'|' - | sed 's/|/ | /g' || true)"
  node="${node:-(no scan)}"
  echo "$id,$type,$(IFS=,; echo "${times[*]}"),$avg,\"$node\"" >> "$SUMMARY"
  printf '%-4s %-5s avg %9s ms   %s\n' "$id" "$type" "$avg" "$node"
done
mkdir -p "$OUT"
cp "$TMP"/out/* "$OUT"/
echo "Queries: $QUERIES"
echo "Saved the plans of every run and the summary to $OUT"
