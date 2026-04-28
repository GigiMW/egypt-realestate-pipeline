import duckdb
import json
import os

RAW_FILE = "data/raw_indicators.json"
DB_FILE  = "data/realestate.duckdb"

def load():
    if not os.path.exists(RAW_FILE):
        print(f"File not found: {RAW_FILE}")
        return

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        print("No records to load.")
        return

    con = duckdb.connect(DB_FILE)

    con.execute("DROP TABLE IF EXISTS raw_indicators")
    con.execute("""
        CREATE TABLE raw_indicators (
            indicator_key   VARCHAR,
            indicator_code  VARCHAR,
            indicator_name  VARCHAR,
            country         VARCHAR,
            country_code    VARCHAR,
            year            INTEGER,
            value           DOUBLE,
            unit            VARCHAR,
            scraped_at      TIMESTAMP
        )
    """)

    for r in records:
        con.execute("""
            INSERT INTO raw_indicators VALUES (?,?,?,?,?,?,?,?,?)
        """, [
            r["indicator_key"],
            r["indicator_code"],
            r["indicator_name"],
            r["country"],
            r["country_code"],
            r["year"],
            r["value"],
            r["unit"],
            r["scraped_at"],
        ])

    count = con.execute("SELECT COUNT(*) FROM raw_indicators").fetchone()[0]
    print(f"Loaded {count} rows into DuckDB → {DB_FILE}")

    print("\nSample data:")
    rows = con.execute("""
        SELECT indicator_key, year, round(value, 2) as value
        FROM raw_indicators
        ORDER BY indicator_key, year DESC
        LIMIT 10
    """).fetchall()
    for row in rows:
        print(f"  {row[0]:25} {row[1]}  {row[2]}")

    con.close()

if __name__ == "__main__":
    load()