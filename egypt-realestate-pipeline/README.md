# Egypt Real Estate Pipeline

An end-to-end data engineering pipeline that ingests live property listings
from Dubizzle Egypt, transforms them with dbt, and serves analytics via DuckDB.

## Architecture

Dubizzle Egypt → Python Scraper → DuckDB (raw) → dbt (staging + marts) → Analytics

Orchestrated by Apache Airflow — runs daily at 8am.

## Stack

| Layer | Tool |
|-------|------|
| Ingestion | Python, BeautifulSoup |
| Storage | DuckDB |
| Transformation | dbt Core |
| Orchestration | Apache Airflow |
| Containerisation | Docker |

## Data Models

- `raw_listings` — raw scraped data, loaded as-is
- `stg_listings` — cleaned: prices parsed to EGP integers, area extracted
- `mart_listings` — analytics table: price per sqm, price buckets, value flags

## How to run locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/egypt-realestate-pipeline.git
cd egypt-realestate-pipeline
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 3. Run the scraper
```bash
python scraper/aqarmap_scraper.py
python scraper/load_to_duckdb.py
```

### 4. Run dbt transformations
```bash
cd dbt_project
dbt run
dbt test
dbt docs serve
```

## dbt Lineage

raw_listings → stg_listings → mart_listings

## Key metrics produced
- Price per sqm by Cairo district
- Listings bucketed by price range (under 1M, 1M–3M, 3M–5M, 5M–10M, above 10M)
- Value listings flagged (price/sqm below market average)