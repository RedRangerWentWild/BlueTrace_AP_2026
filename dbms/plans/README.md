# Query plans (CP4)

The raw output behind [`../05_query_timings.md`](../05_query_timings.md): every timing in that document can be checked against a file here. [`../time_queries.sh`](../time_queries.sh) writes the files, and section 7 of the timings document has the commands.

| Path | Content |
|------|---------|
| `R1.txt` ... `R16.txt`, `W1.txt` ... `W11.txt` | The full `EXPLAIN (ANALYZE, BUFFERS)` output of every run of one query on the 100,009-check database, each run headed `=== R14 run 1 ===` |
| `summary.csv` | One row per query, taken from those files (columns below) |
| `app_data_only/` | The same files for a database holding only the app's own data and its 9 example checks: the comparison in section 3 |
| `diagnostics/first_use_in_a_connection.txt` | One statement run three times inside one session: what the first use in a connection costs (section 5) |
| `diagnostics/r14_digest_computed_once.txt` | R14 with the digest computed twice, as first written, against the committed version that computes it once; three runs each (section 5) |

`summary.csv` has one column per run, so its header depends on how many runs were asked for:

| Column | Meaning |
|--------|---------|
| `query_id`, `type` | The marker in `04_queries.sql` (`R1` ... `W11`) and READ or WRITE |
| `run1_ms`, `run2_ms`, `run3_ms` | The `Execution Time` of each run, in milliseconds |
| `avg_ms` | Their mean, the figure in the timing table |
| `scan_nodes` | Every distinct scan in the plan of the last run, such as `Index Scan using screening_pkey on screening`; `(no scan)` when the plan has none (W4, W10 and W11 insert directly) |

Each run is a new `psql` connection. The writes ran inside `BEGIN ... ROLLBACK`: their plans show the work a write does, and the data was left as it was, apart from sequence numbers, which a rollback does not return (section 6).

## Reading a plan

One node of `R14.txt`:

```
Index Scan using screening_pkey on screening s  (cost=0.29..8.31 rows=1 width=53) (actual time=0.014..0.014 rows=1 loops=1)
  Index Cond: (screening_id = ce.screening_id)
  Buffers: shared hit=3
```

| Part | Meaning |
|------|---------|
| `cost=0.29..8.31` | The planner's estimate, made before running, in its own units (reading one page sequentially costs 1.0): to the first row .. to the last. The planner compares plans by it; it is not a time. |
| `rows=1 width=53` | The estimated number of rows, and their average size in bytes |
| `actual time=0.014..0.014` | Measured milliseconds to the first row .. to the last, per loop |
| `rows=1 loops=1` | Rows actually returned per loop, and how many times the node ran. The inner side of a nested loop runs once per outer row, so its totals are these figures times `loops`. |
| `Index Cond` | The condition used to search the index. A `Filter` is applied to each row after it is read, and `Rows Removed by Filter` counts the rows read for nothing. |
| `Buffers: shared hit=3` | 8 kB pages found in PostgreSQL's own cache. Pages fetched from the operating system would show as `read=`; none of the measured runs has one. |
| `Planning Time` (end of each run) | Choosing the plan. It is not in the timing table, and for 14 of the 16 reads it is longer than the execution (section 5). |
| `Execution Time` (end of each run) | Running the plan, including the foreign-key checks of a write (the `Trigger for constraint` lines), but not parsing, planning or sending rows to the client. This is the timed figure. |

The scan nodes that appear in these files:

| Node | What PostgreSQL does | Here |
|------|----------------------|------|
| `Seq Scan` | Reads every page of the table: the cheapest way to read a small table, or most of a large one | `city`, `param`, `outcome` and the corpus tables; all 3,169 buildings in R5 and W9 |
| `Index Scan` | Walks the B-tree to the matching entries, then fetches each row from the table, in index order | R3 (`ix_building_city_risk` returns the buildings already ordered by risk, so the plan has no sort), R6-R9, R14, R15 |
| `Index Only Scan` | Answers from the index alone when it holds every column the query needs. `Heap Fetches: 0` means VACUUM had marked every page all-visible, so the table itself was not read. | R6, R10, R11, R14, R15, W2 |
| `Bitmap Index Scan` + `Bitmap Heap Scan` | Collects the addresses of all matching rows from the index first, then reads each table page once, in physical order. `Recheck Cond` is the condition applied again if the bitmap ran short of memory and kept only pages, not rows. | R4 (`ix_building_centroid`), W6 |
| `CTE Scan` | Reads the result of a `WITH` query, computed once | R14 (`checked`, so the digest is computed once), W1, W2 |
| `Values Scan`, `Function Scan` | Rows from a `VALUES` list, or from a function such as `unnest()` | W1, W2, W5 |
