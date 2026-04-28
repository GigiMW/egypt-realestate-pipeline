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

## Quick Start

```bash
# Setup
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt

# Run pipeline manually
python scraper/dubizzle_scraper.py   # Scrape live Dubizzle listings
python scraper/load_to_duckdb.py     # Load to DuckDB
cd dbt_project && dbt run && dbt test
```

**Or via Docker Compose** (includes Airflow orchestration):
```bash
docker-compose up
# Access Airflow at http://localhost:8080
# Runs daily at 8am UTC
```

## How to run locally

### Setup & Installation
```bash
git clone https://github.com/YOUR_USERNAME/egypt-realestate-pipeline.git
cd egypt-realestate-pipeline
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### Manual Run (Development)
```bash
# Scrape → Load → Transform
python scraper/dubizzle_scraper.py
python scraper/load_to_duckdb.py
cd dbt_project
dbt run    # Build models
dbt test   # Run data quality tests
```

### Production Run (Airflow)
```bash
# Start Airflow + DuckDB stack
docker-compose up
# Trigger DAG: egypt_realestate_pipeline
# View results in Airflow > Data > DuckDB
```

## Sample Analytics

**Current dataset: 36 live listings from Dubizzle Egypt**

| Metric | Value |
|--------|-------|
| Price Range | 3.3M - 15M EGP |
| Average Price | 6.97M EGP |
| Hottest Location | Mountain View iCity (6 listings, 38K EGP/sqm) |
| Most Common Bucket | 5M-10M EGP (21 listings, 58%) |
| Price/sqm Range | 33K - 114K EGP |

**Top Locations by Average Price:**
1. Villette Compound (5th Settlement) — 15M EGP
2. Galleria Moon Valley (5th Settlement) — 10.6M EGP  
3. O West Compound (6th October) — 7.8M EGP

**Price Distribution:**
- Under 3M: 6 listings (17%)
- 3M-5M: 0 listings (0%)
- 5M-10M: 21 listings (58%)
- 10M+: 9 listings (25%)

## dbt Lineage

raw_listings → stg_listings → mart_listings

## Key metrics produced
- Price per sqm by Cairo district
- Listings bucketed by price range (under 1M, 1M–3M, 3M–5M, 5M–10M, above 10M)
- Value listings flagged (price/sqm below market average)