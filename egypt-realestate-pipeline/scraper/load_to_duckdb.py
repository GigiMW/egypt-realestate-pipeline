import duckdb
import json
import os

RAW_FILE = "data/raw_listings.json"
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

    con.execute("DROP TABLE IF EXISTS raw_listings")
    con.execute("""
        CREATE TABLE raw_listings (
            title        VARCHAR,
            price_raw    VARCHAR,
            location     VARCHAR,
            area_sqm     VARCHAR,
            bedrooms     INTEGER,
            bathrooms    INTEGER,
            url          VARCHAR,
            scraped_at   TIMESTAMP,
            page         INTEGER
        )
    """)

    for r in records:
        con.execute("""
            INSERT INTO raw_listings VALUES (?,?,?,?,?,?,?,?,?)
        """, [
            r.get("title"),
            r.get("price_raw"),
            r.get("location"),
            r.get("area_sqm"),
            r.get("bedrooms"),
            r.get("bathrooms"),
            r.get("url"),
            r["scraped_at"],
            r.get("page"),
        ])

    count = con.execute("SELECT COUNT(*) FROM raw_listings").fetchone()[0]
    print(f"Loaded {count} rows into DuckDB → {DB_FILE}")

    print("\nSample data:")
    rows = con.execute("""
        SELECT title, location, price_raw
        FROM raw_listings
        ORDER BY scraped_at DESC
        LIMIT 10
    """).fetchall()
    for row in rows:
        print(f"  {row[0][:55]:55} | {row[1]} | {row[2]}")

    con.close()

if __name__ == "__main__":
    load()