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
