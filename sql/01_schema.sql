--this files creates three tables with their indexes and runs once when the Postgres container starts
--the main table one row per violation data from Chicago open data CSV
CREATE TABLE IF NOT EXISTS violations (
    id                   BIGINT PRIMARY KEY,         -- taken from source CSV "ID" column
    address_normalized   TEXT NOT NULL,
    address_raw          TEXT NOT NULL,
    violation_date       DATE NOT NULL,
    violation_code       TEXT,
    violation_status     TEXT,
    violation_description TEXT,
    inspector_comments   TEXT
);

--looks for violation by any address and joins with scofflaws table
CREATE INDEX IF NOT EXISTS idx_violations_address
    ON violations (address_normalized);

--looks for violations by date and joins with scofflaws table
CREATE INDEX IF NOT EXISTS idx_violations_date
    ON violations (violation_date);


CREATE TABLE IF NOT EXISTS scofflaws (
    id                   BIGSERIAL PRIMARY KEY,
    address_normalized   TEXT NOT NULL UNIQUE,       -- source duplicates collapsed at ingest
    address_raw          TEXT NOT NULL               
);


CREATE TABLE IF NOT EXISTS comments (
    id                   BIGSERIAL PRIMARY KEY,
    address_normalized   TEXT NOT NULL,
    author               TEXT NOT NULL,
    comment_text         TEXT NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- no FK to (violations or scofflaws)any addresss can have comments
);

--index for fetching all comments at once for selecred address
CREATE INDEX IF NOT EXISTS idx_comments_address
    ON comments (address_normalized);
