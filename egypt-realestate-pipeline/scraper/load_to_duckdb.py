import duckdb
import json
import os

RAW_FILE = "data/raw_listings.json"
DB_FILE = "data/realestate.duckdb"

def load():
    if not os.path.exists(RAW_FILE):
        print(f"Raw file not found: {RAW_FILE}")
        return

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        listings = json.load(f)

    if not listings:
        print("No listings to load.")
        return

    con = duckdb.connect(DB_FILE)

    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_listings (
            title       VARCHAR,
            price_raw   VARCHAR,
            location    VARCHAR,
            area_sqm    VARCHAR,
            url         VARCHAR,
            scraped_at  TIMESTAMP,
            page        INTEGER
        )
    """)

    con.execute("DELETE FROM raw_listings")

    for row in listings:
        con.execute("""
            INSERT INTO raw_listings VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            row.get("title"),
            row.get("price_raw"),
            row.get("location"),
            row.get("area_sqm"),
            row.get("url"),
            row.get("scraped_at"),
            row.get("page"),
        ])

    count = con.execute("SELECT COUNT(*) FROM raw_listings").fetchone()[0]
    print(f"Loaded {count} rows into DuckDB → {DB_FILE}")
    con.close()

if __name__ == "__main__":
    load()