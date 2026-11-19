"""Load every scraped snapshot into DuckDB.

Each scrape is saved as data/history/raw_listings_<YYYY-MM-DD>.json. This script
loads all of them into one `raw_listings` table with a `snapshot_date` column,
so dbt can build both "latest" tables and price-over-time tables.
"""

import glob
import json
import os
import re
import sys

import duckdb

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
DB_FILE = os.environ.get("DUCKDB_PATH", os.path.join(DATA_DIR, "realestate.duckdb"))

SNAPSHOT_RE = re.compile(r"raw_listings_(\d{4}-\d{2}-\d{2})\.json$")

COLUMNS = ("title", "price_raw", "location", "area_sqm", "bedrooms",
           "bathrooms", "url", "scraped_at", "page")


def read_snapshots():
    """Yield (snapshot_date, records) for each history file, oldest first."""
    for path in sorted(glob.glob(os.path.join(HISTORY_DIR, "raw_listings_*.json"))):
        match = SNAPSHOT_RE.search(os.path.basename(path))
        if not match:
            continue
        with open(path, "r", encoding="utf-8") as f:
            yield match.group(1), json.load(f)


def load():
    snapshots = list(read_snapshots())
    if not snapshots:
        # Fail loudly so Airflow marks the task as failed instead of "success".
        sys.exit(f"No snapshot files found in {HISTORY_DIR}")

    rows = []
    for snapshot_date, records in snapshots:
        seen = set()
        for r in records:
            # One row per listing per snapshot, even if the scrape saw it twice.
            if not r.get("url") or r["url"] in seen:
                continue
            seen.add(r["url"])
            rows.append([snapshot_date] + [r.get(c) for c in COLUMNS])

    if not rows:
        sys.exit("Snapshot files contain no listings.")

    # The database only holds derived data (the JSON files are the source of
    # truth), so start from a fresh file each run. This also avoids "unsupported
    # version" errors when the file was written by a different DuckDB version.
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    con = duckdb.connect(DB_FILE)

    con.execute("""
        CREATE TABLE raw_listings (
            snapshot_date DATE,
            title         VARCHAR,
            price_raw     VARCHAR,
            location      VARCHAR,
            area_sqm      VARCHAR,
            bedrooms      INTEGER,
            bathrooms     INTEGER,
            url           VARCHAR,
            scraped_at    TIMESTAMP,
            page          INTEGER
        )
    """)
    con.executemany("INSERT INTO raw_listings VALUES (?,?,?,?,?,?,?,?,?,?)", rows)

    summary = con.execute("""
        SELECT snapshot_date, COUNT(*) FROM raw_listings
        GROUP BY 1 ORDER BY 1
    """).fetchall()
    print(f"Loaded {len(rows)} rows from {len(summary)} snapshot(s) into {DB_FILE}")
    for snapshot_date, count in summary:
        print(f"  {snapshot_date}: {count} listings")

    con.close()


if __name__ == "__main__":
    load()
