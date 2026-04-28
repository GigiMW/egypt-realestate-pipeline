from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBT_PROJECT_DIR = os.path.join(PROJECT_ROOT, "dbt_project")

default_args = {
    "owner": "engy",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

def run_scraper():
    scraper_path = os.path.join(PROJECT_ROOT, "scraper", "dubizzle_scraper.py")
    result = subprocess.run(
        [sys.executable, scraper_path],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Scraper failed:\n{result.stderr}")

def run_loader():
    loader_path = os.path.join(PROJECT_ROOT, "scraper", "load_to_duckdb.py")
    result = subprocess.run(
        [sys.executable, loader_path],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"Loader failed:\n{result.stderr}")

with DAG(
    dag_id="egypt_realestate_pipeline",
    description="Scrape Dubizzle property listings → load to DuckDB → transform with dbt",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 8 * * *",  # runs every day at 8am
    catchup=False,
    tags=["egypt", "realestate", "portfolio"],
) as dag:

    scrape_task = PythonOperator(
        task_id="scrape_listings",
        python_callable=run_scraper,
    )

    load_task = PythonOperator(
        task_id="load_to_duckdb",
        python_callable=run_loader,
    )

    dbt_run = BashOperator(
    task_id="dbt_run",
    bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --profiles-dir {DBT_PROJECT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --profiles-dir {DBT_PROJECT_DIR}",
    )

    scrape_task >> load_task >> dbt_run >> dbt_test