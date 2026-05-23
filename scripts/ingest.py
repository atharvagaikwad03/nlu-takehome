## Reads both CSVs into Postgres clears tables first so there are no duplicates
#!/usr/bin/env python3
import csv
import logging
import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

rootPath = Path(__file__).resolve().parent.parent #path to the project root
sys.path.insert(0, str(rootPath)) #import app.normalize 

from app.normalize import normalizeAddress  

load_dotenv(rootPath / ".env")
#set up logging to console for ingest process
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

#find the most recent CSV file matching the pattern
def findCsv(pattern: str) -> Path:
    matches = sorted((rootPath / "data").glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching data/{pattern}")
    if len(matches) > 1:
        log.warning("Multiple files match %s, using %s", pattern, matches[-1].name)
    return matches[-1]

#set the CSV files to ingest
violationsCsv = findCsv("Building_Violations*.csv")
scofflawCsv = findCsv("Building_Code_Scofflaw_List*.csv")
batchSize = 1000 #batch size for inserting rows



def normKey(k: str) -> str:
   
    return re.sub(r"\s+", "_", k.strip().upper())

#convert empty strings to None
def coerceNone(value: str) -> str | None:
    # empty CSV cells become NULL in Postgres not empty strings
    v = value.strip() if value else ""
    return v if v else None

#find the column in the CSV file
def findCol(rowNorm: dict, *candidates: str) -> str | None:
    # try each candidate key in order first match wins
    for c in candidates:
        key = normKey(c)
        if key in rowNorm:
            return rowNorm[key]
    return None

#normalize
def normalizeRow(raw: dict) -> dict:
    return {normKey(k): v for k, v in raw.items()}

#ingest the violations CSV file to the violations table
def ingestViolations(cur):
    log.info("Truncating violations table …")
    cur.execute("TRUNCATE TABLE violations")
#log the loading of the violations CSV file
    log.info("Loading %s …", violationsCsv)
    rows = [] 
    skipped = 0
    seenIds: set[int] = set() # export has duplicate IDs keep first row only

    with open(violationsCsv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            nr = normalizeRow(raw)

            idStr = (findCol(nr, "ID") or "").strip()
            if not idStr:
                skipped += 1
                continue
            try:
                rowId = int(idStr)
            except ValueError:
                skipped += 1
                continue
            if rowId in seenIds:
                # CSV export contains duplicate IDs skip, count them
                skipped += 1
                continue
            seenIds.add(rowId)

            addressRaw = (findCol(nr, "ADDRESS") or "").strip()
            # both column name formats appear depending on the export vintage
            violationDateStr = (findCol(nr, "VIOLATION DATE", "VIOLATION_DATE") or "").strip()

            if not addressRaw or not violationDateStr:
                skipped += 1
                continue

            rows.append((
                rowId,
                normalizeAddress(addressRaw),
                addressRaw,
                violationDateStr,
                coerceNone(findCol(nr, "VIOLATION CODE", "VIOLATION_CODE") or ""),
                coerceNone(findCol(nr, "VIOLATION STATUS", "VIOLATION_STATUS") or ""),
                coerceNone(findCol(nr, "VIOLATION DESCRIPTION", "VIOLATION_DESCRIPTION") or ""),
                coerceNone(findCol(
                    nr,
                    "VIOLATION INSPECTOR COMMENTS", "VIOLATION_INSPECTOR_COMMENTS",
                    "INSPECTOR COMMENTS", "INSPECTOR_COMMENTS",
                ) or ""),
            ))

            if len(rows) >= batchSize:
                flushViolations(cur, rows) # don't buffer all 77k rows in memory
                rows = []

    if rows:
        flushViolations(cur, rows)

    log.info("Violations inserted: %d  |  skipped (dup ID / missing data): %d", len(seenIds), skipped)


def flushViolations(cur, rows):
    
    execute_values(
        cur,
        """
        INSERT INTO violations
            (id, address_normalized, address_raw, violation_date,
             violation_code, violation_status, violation_description,
             inspector_comments)
        VALUES %s
        """,
        rows,
    )


def ingestScofflaws(cur):
    log.info("Truncating scofflaws table …")
    cur.execute("TRUNCATE TABLE scofflaws")

    log.info("Loading %s …", scofflawCsv)
    # collapse duplicate addresses same property can appear under multiple court cases
    seen: dict[str, str] = {}  # normalized -> first-seen raw

    with open(scofflawCsv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            nr = normalizeRow(raw)
            addressRaw = (findCol(nr, "ADDRESS") or "").strip()
            if not addressRaw:
                continue
            norm = normalizeAddress(addressRaw)
            if norm not in seen:
                seen[norm] = addressRaw

    if seen:
        execute_values(
            cur,
            "INSERT INTO scofflaws (address_normalized, address_raw) VALUES %s",
            list(seen.items()),
        )

    log.info("Scofflaw unique addresses: %d", len(seen))


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        log.error("DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            ingestViolations(cur)
            ingestScofflaws(cur)
        conn.commit()
        log.info("Ingest complete.")
    except Exception:
        conn.rollback()
        log.exception("Ingest failed — transaction rolled back")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
