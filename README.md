# Egypt Real Estate Pipeline

[![CI](https://github.com/GigiMW/egypt-realestate-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/GigiMW/egypt-realestate-pipeline/actions/workflows/ci.yml)

An end-to-end data engineering pipeline that scrapes apartment-for-sale listings
from **Dubizzle Egypt**, loads them into **DuckDB**, models them with **dbt**, and
runs daily on **Apache Airflow** inside **Docker**. The output is a small set of
analytics tables on Cairo property prices: price per square meter, price buckets,
average price by area, and how prices change between scrapes.

## Architecture

```mermaid
flowchart LR
    A[Dubizzle Egypt<br/>results pages] -->|JSON-LD, 3 requests| B[data/history/<br/>one JSON per day]
    B -->|load_to_duckdb.py| C[(DuckDB<br/>raw_listings)]
    C --> D[stg_listings]
    S[/location_areas seed/] --> I
    D --> I[int_listings_with_area]
    I --> E[mart_listings]
    I --> F[avg_price_by_location]
    D --> G[price_distribution]
    I --> T[price_trends]
    I --> P[listing_price_changes]
    E & F & G & T & P -->|convert_to_csv.py| H[CSV exports]
```

The Airflow DAG `egypt_realestate_pipeline` runs every day at 08:00:

```
scrape_listings → load_to_duckdb → dbt_run → dbt_test → convert_to_csv
```

Each task fails loudly, so a broken step stops the run instead of passing
empty data downstream. Every task retries once after 5 minutes.

### How the scraper works

Every Dubizzle results page embeds a [schema.org](https://schema.org/ItemList)
`ItemList` in a JSON-LD `<script>` tag. It holds the title, price, size, bedrooms,
bathrooms, compound and locality of every ad on the page. The scraper reads that
instead of opening each ad, so a run is **3 requests** (about 140 listings), not
one request per ad. It is also polite:

- it waits 3–5 seconds between requests
- it retries `429`/`503` responses after 10 s and then 30 s
- it **stops** if Dubizzle asks it to wait longer than a minute (`Retry-After`)
  or shows its "Security check" page, instead of retrying forever

## Tech stack

| Layer            | Tool                        | Role                                        |
|------------------|-----------------------------|---------------------------------------------|
| Ingestion        | Python, requests, BeautifulSoup | Read listings from the structured data on results pages |
| Storage          | DuckDB                      | Embedded analytical database                |
| Transformation   | dbt Core 1.7 + dbt-duckdb   | Staging and mart models, data tests         |
| Orchestration    | Apache Airflow 2.9          | Daily schedule, retries, task dependencies  |
| Packaging        | Docker Compose              | One-command local Airflow setup             |

## Data models

| Model                   | Layer   | Type  | Description |
|-------------------------|---------|-------|-------------|
| `stg_listings`          | staging | view  | Parses the raw price and area strings into numbers, computes EGP per sqm and drops implausible bedroom counts |
| `int_listings_with_area`| intermediate | view | Maps each listing to a clean `area` (New Cairo, 6th of October, New Capital…) using the `location_areas` seed |
| `mart_listings`         | mart    | table | Latest scrape: one row per listing with its `area` and a `price_bucket` (`under_3m`, `3m_to_5m`, `5m_to_10m`, `10m_plus`) |
| `avg_price_by_location` | mart    | table | Latest scrape: listing count, average and median price per sqm, and min/max price per area |
| `price_distribution`    | mart    | table | Latest scrape: listing count and average price per price bucket |
| `price_trends`          | mart    | table | **History:** listing count and median price per sqm for each scrape date and area (plus an `All areas` row), with the change since the previous scrape |
| `listing_price_changes` | mart    | table | **History:** first vs. latest asking price for every ad seen in more than one scrape (price drops and rises) |

### Data quality tests

`dbt test` runs **30 tests**:

- `not_null` on the key fields: snapshot date, title, URL, raw and parsed price, area and timestamp
- one row per listing per snapshot (a custom test), so the same ad can't be counted twice
- `unique` on listing URLs in the latest-snapshot and price-change tables
- `unique` on the aggregation keys (`area`, `price_bucket`)
- `accepted_values` on `price_bucket` in both mart tables
- `not_null` and `unique` on the seed's keywords

### How areas are cleaned

Ads don't have a structured location field, so the scraped `location` is often
noise ("the", "very", "Ready Duplex"). Instead, `int_listings_with_area` searches the
**title and location** for keywords from
[`seeds/location_areas.csv`](egypt-realestate-pipeline/dbt_project/seeds/location_areas.csv).
The keywords cover areas, compounds and landmarks, for example `fifth settlement`,
`taj city`, `r7` and `mall of egypt`. When several keywords match, the **longest
one wins**, so `mountain view icity october` (6th of October) beats
`mountain view`. Listings with no match are labeled `Unknown`.

To support a new area or compound, add a row to the CSV. No SQL changes are needed.

## Project structure

```
egypt-realestate-pipeline/
├── dags/
│   └── realestate_pipeline.py      # Airflow DAG (5 tasks)
├── scraper/
│   ├── dubizzle_scraper.py         # Results pages → data/history/raw_listings_<date>.json
│   └── load_to_duckdb.py           # Loads the JSON into DuckDB
├── conversion/
│   └── convert_to_csv.py           # Exports the mart tables to CSV
├── dbt_project/
│   ├── models/
│   │   ├── staging/                # stg_listings + sources and tests (schema.yml)
│   │   ├── intermediate/           # int_listings_with_area (area mapping)
│   │   └── marts/                  # mart_listings, avg_price_by_location, price_distribution
│   ├── seeds/
│   │   └── location_areas.csv      # keyword → area lookup
│   ├── dbt_project.yml
│   └── profiles.yml                # DuckDB path from DUCKDB_PATH (default ../data)
├── tests/
│   ├── test_scraper.py             # Offline unit tests for the parser (pytest)
│   └── fixtures/results_page.html  # Trimmed real results page
├── data/
│   ├── history/                    # One raw_listings_<YYYY-MM-DD>.json per scrape (source of truth)
│   ├── raw_listings.json           # Copy of the latest scrape
│   └── *.csv                       # Exported marts (the .duckdb file is git-ignored)
├── docker-compose.yml              # Reads secrets from .env
├── .github/workflows/ci.yml        # (repo root) CI: full pipeline on every push
├── .env.example                    # Template for your local .env (never commit .env)
└── requirements.txt
```

## Getting started

```bash
git clone https://github.com/GigiMW/egypt-realestate-pipeline.git
cd egypt-realestate-pipeline/egypt-realestate-pipeline
```

### Option 1: Docker + Airflow (recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**1. Create your `.env` file.** It holds your Airflow keys and admin password.
Git ignores it, so it is never committed.

```bash
cp .env.example .env              # Windows: copy .env.example .env
```

Open `.env` and fill in the values. The two keys can be generated with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_hex(32))"
```

(The first command needs `pip install cryptography`.) Docker Compose refuses
to start until all the required values are set.

**2. Start Airflow:**

```bash
docker compose up
```

The first start takes a few minutes while the container installs dbt and
DuckDB. Then:

1. Open <http://localhost:8080> and sign in with the username and password from your `.env`.
2. Unpause the **`egypt_realestate_pipeline`** DAG and click **Trigger DAG**.
3. When all five tasks are green, the fresh CSVs are in `data/`.

Stop everything with `docker compose down`.

### Option 2: Run the steps manually

Requires **Python 3.11 or 3.12** (dbt 1.7 does not support 3.13).

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python scraper/dubizzle_scraper.py       # 1. scrape → data/history/raw_listings_<today>.json
python scraper/load_to_duckdb.py         # 2. load all snapshots → data/realestate.duckdb

cd dbt_project
dbt build --profiles-dir .               # 3. load the seed, build 7 models, run 30 tests
cd ..

python conversion/convert_to_csv.py      # 5. export marts → data/*.csv
```

To explore the models and the lineage graph:

```bash
cd dbt_project
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8081
```

## Sample output

From the snapshot in `data/` (18 listings, mostly New Cairo):

| Price bucket | Listings | Avg price (EGP) | Avg EGP / sqm |
|--------------|---------:|----------------:|--------------:|
| 10M+         | 9        | 14,277,111      | 81,450        |
| 5M – 10M     | 8        | 6,652,125       | 40,650        |
| 3M – 5M      | 1        | 4,700,000       | 42,727        |

| Area           | Listings | Avg EGP / sqm | Median EGP / sqm |
|----------------|---------:|--------------:|-----------------:|
| New Cairo      | 10       | 71,168        | 73,316           |
| 6th of October | 3        | 36,575        | 34,595           |
| New Giza       | 1        | 91,837        | 91,837           |
| Suez           | 1        | 61,111        | 61,111           |
| El Rehab       | 1        | 54,000        | 54,000           |
| Mostakbal City | 1        | 42,727        | 42,727           |
| New Capital    | 1        | 29,900        | 29,900           |

With 18 listings these numbers are illustrative only. Most areas have a single ad.

## Price history

Every scrape is saved as `data/history/raw_listings_<YYYY-MM-DD>.json`. If you scrape
twice on the same day, the second run replaces that day's file. The loader rebuilds
DuckDB from **all** of these files, so the JSON snapshots are the source of truth
and the database can be deleted at any time.

From the snapshots, dbt builds:

- **`price_trends`**: median EGP/sqm per area for each scrape date, and how much it
  moved since the previous scrape
- **`listing_price_changes`**: every ad seen more than once, with its first and
  latest asking price, so price cuts are easy to spot

The latest-only tables (`mart_listings`, `avg_price_by_location` and
`price_distribution`) automatically use the newest snapshot. The repo currently
holds one snapshot (2026-04-30), so the history tables fill in as soon as the
DAG runs on new days. Commit the new files in `data/history/` to keep them.

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull
request:

1. Installs the pinned dependencies on Python 3.12
2. Checks that all Python files compile
3. Runs the scraper's unit tests against a saved results page (no network)
4. Loads the committed snapshots in `data/history/` into DuckDB (CI doesn't scrape
   live, so builds don't depend on Dubizzle)
5. Runs `dbt build`: the seed, all 7 models and all 30 tests
6. Exports the CSVs
7. Validates `docker-compose.yml`

## Configuration

| Setting      | Where                            | Default |
|--------------|----------------------------------|---------|
| `DUCKDB_PATH`| environment variable             | `data/realestate.duckdb` (`/opt/airflow/data/...` in Docker) |
| Pages scraped| `MAX_PAGES` in `dubizzle_scraper.py` | 3 |
| Ads per page | `ADS_PER_PAGE` in `dubizzle_scraper.py` | 12 |
| Schedule     | `schedule_interval` in the DAG   | `0 8 * * *` (daily, 08:00) |
| Airflow keys and login | `.env` (see `.env.example`) | none: required |

## Limitations and next steps

- **The scraper depends on Dubizzle's HTML.** If the site changes its layout or
  blocks the request, the scrape task fails and the run stops.
- **Area mapping is keyword-based.** Ads that name a compound missing from the
  seed end up as `Unknown`. Add the compound to `location_areas.csv` to fix them.
- **The sample is modest.** The scraper reads 3 results pages (about 140 ads).
  Raising `MAX_PAGES` gives more reliable averages. Keep the delay between
  requests if you do.
- **History grows one file per day.** That's about 10 KB per scrape, which is fine
  for years of daily runs. At a larger scale, Parquet files or a proper warehouse
  would be a better fit.
- **Dubizzle blocks cloud IPs.** The scraper stops with a clear "Security check"
  error when that happens. Run it from a home or office connection.
- **The scraper relies on Dubizzle's structured data.** If Dubizzle removes the
  JSON-LD from its results pages, the scraper says so and stops.
- **Docker installs packages on every start.** The Compose file uses
  `_PIP_ADDITIONAL_REQUIREMENTS`, which is fine locally. A production setup would
  build a custom image with the packages already installed.

## Disclaimer

This is a portfolio and learning project. Listing data belongs to Dubizzle and its
advertisers. Scrape responsibly and respect the site's terms of use.
