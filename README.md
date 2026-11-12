# BlueTrace (AP project, 2026)

**Team T0015 (Bluetrace), Section E** · Aadi Kalra, Tushar Khemka, Rudransh Singh, Abhishek Panigrahi

BlueTrace reconstructs a city's lost water bodies from the satellite record, flags the buildings standing on them, and screens any plot before it is built on. For a clicked plot it measures the distance to today's and to the 1984-99 water edge, applies a lake-buffer rule, returns a screening outcome (reject, refer, conditions, no objection), traces where the plot's runoff goes downhill, and can issue a screening certificate. Every number in an answer comes from a cited corpus of short source notes.

- Live demo: https://bluetrace-1oys.onrender.com

## DBMS deliverables (`dbms/`)

| File | Content |
|------|---------|
| `dbms/01_normalization.md` | The app's data taken through 1NF, 2NF, 3NF and BCNF |
| `dbms/02_er_diagram.png` | ER diagram (CP2) |
| `dbms/03_schema.sql` | CREATE TABLE statements for PostgreSQL (CP2) |
| `dbms/04_queries.sql` | Every query the app uses, marked READ / WRITE (CP3) |
| `dbms/05_query_timings.md` | Three runs and the average for every query (CP4) |
