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
mkdir -p "$OUT"
SUMMARY="$OUT/summary.csv"
header="query_id,type"
for ((i = 1; i <= RUNS; i++)); do header="$header,run${i}_ms"; done
echo "$header,avg_ms,scan_nodes" > "$SUMMARY"

TMP="$(mktemp -d)"
awk -v dir="$TMP" '
  /^-- @/ { id = ""; if ($2 ~ /^@[RW][0-9]+$/) { id = substr($2, 2); file = dir "/" id ".sql"; printf "" > file }; next }
  id != "" && !/^--/ { print >> file }
' "$QUERIES"

for f in $(ls "$TMP"/*.sql | sort -V); do
  id="$(basename "$f" .sql)"
  type="READ"; [[ "$id" == W* ]] && type="WRITE"
  query="$(cat "$f")"
  times=()
  : > "$OUT/$id.txt"
  for ((i = 1; i <= RUNS; i++)); do
    if [[ "$type" == "WRITE" ]]; then
      sql="SET search_path TO bluetrace; BEGIN; EXPLAIN (ANALYZE, BUFFERS) $query ROLLBACK;"
    else
      sql="SET search_path TO bluetrace; EXPLAIN (ANALYZE, BUFFERS) $query"
    fi
    plan="$(printf '%s\n' "$sql" | psql -d "$DB" -X -q -A -t -v ON_ERROR_STOP=1)"
    echo "=== $id run $i ===" >> "$OUT/$id.txt"
    echo "$plan" >> "$OUT/$id.txt"
    times+=("$(echo "$plan" | grep -oE 'Execution Time: [0-9.]+' | awk '{print $3}')")
  done
  avg="$(printf '%s\n' "${times[@]}" | awk '{ s += $1 } END { printf "%.3f", s / NR }')"
  # every scan node of the last run, e.g. "Index Scan using screening_pkey on screening"
  node="$(echo "$plan" | grep -oE '(Parallel )?(Seq Scan|Index Scan|Index Only Scan|Bitmap Heap Scan|Bitmap Index Scan|CTE Scan|Function Scan|Values Scan)( Backward)?( using [a-z0-9_]+)?( on [a-z0-9_]+)?' | sed -E 's/Parallel //; s/ Backward//' | awk '!seen[$0]++' | paste -sd'|' - | sed 's/|/ | /g' || true)"
  node="${node:-(no scan)}"
  echo "$id,$type,$(IFS=,; echo "${times[*]}"),$avg,\"$node\"" >> "$SUMMARY"
  printf '%-4s %-5s avg %9s ms   %s\n' "$id" "$type" "$avg" "$node"
done
rm -rf "$TMP"
echo "Queries: $QUERIES"
echo "Saved the plans of every run and the summary to $OUT"
