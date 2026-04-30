# Egypt Real Estate Pipeline

An end-to-end data engineering pipeline that scrapes live apartment listings
from Dubizzle Egypt, transforms them with dbt, and produces Cairo market analytics.

![dbt run](docs/dbt_run.png)

## Architecture
Dubizzle Egypt
│
▼
Python Scraper (BeautifulSoup)
│
▼
DuckDB  ──►  raw_listings
│
▼
dbt Core
├──► stg_listings       (cleaned prices, areas, timestamps)
├──► mart_listings       (price buckets, price per sqm)
├──► avg_price_by_location (aggregated by Cairo district)
└──► price_distribution  (listing count by price range)
│
▼
Apache Airflow DAG (daily @ 8am)
## Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Ingestion | Python, BeautifulSoup | Scrape live Dubizzle listings |
| Storage | DuckDB | Local analytical database |
| Transformation | dbt Core 1.11 | Staging + mart models |
| Orchestration | Apache Airflow 2.9 | Daily scheduling + retries |
| Containerisation | Docker Compose | One-command local setup |

## Data Models

### Staging
- `stg_listings` — raw listings cleaned: prices parsed to EGP float,
  areas extracted to sqm integers, price-per-sqm calculated

### Marts
- `mart_listings` — all listings enriched with price bucket classification
- `avg_price_by_location` — average price and price/sqm by Cairo district
- `price_distribution` — listing count and avg price per price range bucket

## dbt Lineage

![Lineage Graph](docs/lineage.png)

## Key Metrics Produced

| Metric | Description |
|--------|-------------|
| Price per sqm | EGP per square meter per listing |
| Price bucket | under_3M / 3M_to_5M / 5M_to_10M / 10M_plus |
| Avg price by district | Aggregated by Cairo location |
| Distribution | Count and avg price per price range |

## Sample Data (Latest Run)

| Price Bucket | Listings | Avg Price EGP | Avg EGP/sqm |
|-------------|----------|---------------|-------------|
| 10M+ | 7 | 17,394,325 | 104,729 |
| 5M–10M | 6 | 8,171,667 | 55,649 |
| 3M–5M | 5 | 4,010,000 | 30,814 |

## How to Run Locally

### Option 1 — Manual (Development)

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/egypt-realestate-pipeline.git
cd egypt-realestate-pipeline
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt

# Run pipeline
python scraper/dubizzle_scraper.py   # Scrape live listings
python scraper/load_to_duckdb.py     # Load to DuckDB

# Transform with dbt
cd dbt_project
dbt run      # Build all 4 models
dbt test     # Run 13 data quality tests
dbt docs serve  # View lineage + docs at localhost:8080
```

### Option 2 — Docker (Airflow orchestration)

```bash
docker-compose up
# Airflow UI at http://localhost:8080
# Username: admin  Password: admin
# Trigger DAG: egypt_realestate_pipeline
```

## Data Quality Tests (13 total)

- `not_null` on all critical fields (title, price, area, url, scraped_at)
- `unique` on location and price_bucket aggregation keys
- `accepted_values` on price_bucket enum

## Project Structure
egypt-realestate-pipeline/
├── dags/
│   └── realestate_pipeline.py   # Airflow DAG — 4 tasks
├── scraper/
│   ├── dubizzle_scraper.py      # Live listing scraper
│   └── load_to_duckdb.py        # JSON → DuckDB loader
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_listings.sql
│   │   │   └── schema.yml       # Tests + source definitions
│   │   └── marts/
│   │       ├── mart_listings.sql
│   │       ├── avg_price_by_location.sql
│   │       └── price_distribution.sql
│   └── dbt_project.yml
├── docker-compose.yml
├── requirements.txt
└── docs/