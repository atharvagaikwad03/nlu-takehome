# NLU Take-Home: Chicago Building Violations API

A REST API over two City of Chicago building datasets, built with Python 3.12, Flask 3, and PostgreSQL 16.

---

## Quick Start

```bash
# 1. Place CSVs
cp Building_Violations.csv data/
cp Building_Code_Scofflaw_List.csv data/

# 2. Start the database and API server
docker compose up --build -d

# 3. Run ingestion (one-time; idempotent — safe to re-run)
docker compose exec app python scripts/ingest.py

# 4. Verify
curl http://localhost:5000/health
curl "http://localhost:5000/property/7120%20S%20ROCKWELL%20ST/"
curl "http://localhost:5000/property/scofflaws/violations?since=2024-01-01"
```

---

## Design Decisions

### Why no ORM?

This API's data access is entirely defined by the spec's schema and query shapes — fixed at design time. An ORM would:

1. Force an object layer where rows are returned as plain dicts anyway.
2. Make the JOIN in the scofflaws endpoint harder to express (and harder to review in a code walkthrough) than raw SQL.
3. Hide performance characteristics that matter for the 77k-row violation table.

Raw psycopg2 with parameterized queries is the right tool here: direct, auditable, and injection-safe by construction.

### Why Flask over Django?

Django's killer features — the ORM, admin, auth, forms — are all explicitly out of scope. Using Django without its ORM actively fights the framework (its query interface is the ORM; raw SQL is a workaround). Flask lets us wire up three endpoints with a connection pool and a Blueprint in ~150 lines, which is proportionate to the problem.

### Address Normalization as the JOIN Contract

`app/normalize.py` contains a single function, `normalize_address`, used in **both** ingestion and API lookups:

```python
def normalize_address(s: str) -> str:
    s = s.strip().lower()
    return re.sub(r"\s+", " ", s)
```

This function is the contract that makes `violations JOIN scofflaws ON address_normalized` work correctly. If the two code paths (ingest and query) ever diverged, the JOIN would silently return wrong results. Centralizing it in one importable module makes that impossible without editing the module itself.

**Why not expand abbreviations (ST → STREET)?** The source data is internally consistent — the violations and scofflaw CSVs both use the same abbreviations. Expanding them would require a complete mapping table, introduce mismatches on edge cases, and add complexity the spec explicitly warns against. `pg_trgm` (see below) is the right production fallback.

### Index Selection

```sql
CREATE INDEX idx_violations_address ON violations (address_normalized);
CREATE INDEX idx_violations_date    ON violations (violation_date);
```

**Why not a composite index on `(address_normalized, violation_date)`?**

The three query shapes are:
- `WHERE address_normalized = ?` (property lookup)
- `WHERE violation_date >= ?` and `JOIN … ON address_normalized` (scofflaw endpoint)
- `INSERT` (ingestion)

A composite index on `(address_normalized, violation_date)` would help the scofflaw query marginally (the planner would use an index scan instead of a bitmap AND) but would be unused for standalone date-range queries and would add write overhead on every insert. At 77k rows, the planner resolves the JOIN efficiently using a nested loop over the two single-column indexes. The single-column indexes are cleaner, cheaper to maintain, and cover all three query shapes. Composite indexes become worth the trade-off at larger scale or with range-query-heavy workloads; that would be a "what I'd do with more time" item.

### Why `comments` Has No Foreign Key

Comments are allowed on any address, including addresses that don't yet appear in `violations` or `scofflaws`. An FK would reject those inserts. Additionally, the spec explicitly prohibits FKs. The trade-off is that we accept orphaned comments; the trade-up is that the schema doesn't refuse valid user actions.

### Why the Server Controls `created_at` and `address`

- **`created_at`**: Server-side `DEFAULT NOW()` means the timestamp reflects when the record was actually written, not what a client claims. Clients cannot backdate or post-date comments.
- **`address`**: Taken from the URL path, not the request body. A client cannot attribute a comment to a different address than the one they posted to.

---

## What I'd Do With More Time

| Item | Why |
|------|-----|
| Pagination on `GET /property/<address>/` violations | The sample address has only a handful of rows but a busy building could have hundreds. `LIMIT`/`OFFSET` or keyset pagination would make this production-safe. |
| `pg_trgm` fuzzy address matching | Address strings in the real world have typos (`ROCKWEL` vs `ROCKWELL`), missing directionals, or inconsistent abbreviations. A trigram index + similarity threshold would catch these without full-text search complexity. |
| Test suite (pytest + testcontainers) | Unit tests for `normalize_address` and `sanitize_*` helpers; integration tests against a real Postgres container for each endpoint. No mocking — the spec is database-centric. |
| Authentication + rate limiting | Even for an internal API, bearer tokens and per-IP limits prevent accidental data exposure and scraping. |
| Structured logging (structlog or python-json-logger) | JSON logs are trivially queryable in CloudWatch / Datadog. The current `logging.basicConfig` output is for development only. |
| Connection pool health check | The current `ThreadedConnectionPool` doesn't reconnect on stale connections. A health-check wrapper or `psycopg2-pool` replacement would handle database restarts transparently. |
| Alembic for schema evolution | The single `01_schema.sql` approach is fine for a take-home but breaks on production where data exists. Alembic migrations would allow forward evolution without a full re-create. |

---

## AI Use Disclosure

Claude (Anthropic) was used for code assistance and edge-case rubber-ducking during implementation. All architecture decisions, schema design, and the normalization contract are human-authored. The AI did not generate requirements or invent abstractions beyond those in the spec.

---

## Reference

| Dataset | Source |
|---------|--------|
| Building Violations | https://data.cityofchicago.org/Buildings/Building-Violations/22u3-xenr |
| Building Code Scofflaw List | https://data.cityofchicago.org/Buildings/Building-Code-Scofflaw-List/crg5-4zyp |

Expected after full ingest: ~77,492 violation rows, ~256 unique scofflaw addresses.  
`GET /property/scofflaws/violations?since=2024-01-01` → 27 addresses.
