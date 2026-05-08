"""Airflow DAG for the BrewSum brewery ELT batch pipeline.

This DAG is intended for local non-Docker Airflow execution, preferably from WSL2.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_HOME = Path(os.getenv("BREWSUM_PROJECT_DIR", "/mnt/d/BrewSum")).as_posix()
DBT_PROJECT_DIR = f"{PROJECT_HOME}/dbt_project"
PYTHON_BIN = "python"
DBT_BIN = "dbt"

TASK_ENV = {
    name: os.getenv(name, "")
    for name in [
        "GCP_PROJECT_ID",
        "GCS_BUCKET_NAME",
        "BIGQUERY_DATASET",
        "DBT_DATASET",
        "BIGQUERY_LOCATION",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]
}

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email": [os.getenv("AIRFLOW_FAILURE_EMAIL", "alerts@example.com")],
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="brewery_elt_pipeline",
    description="Extract, load, transform, and validate Open Brewery DB data.",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["elt", "breweries", "bigquery"],
) as dag:
    extract_task = BashOperator(
        task_id="extract_task",
        bash_command=(
            f"{PYTHON_BIN} ingestion/extract.py "
            '--run-date "{{ ds }}"'
        ),
        cwd=PROJECT_HOME,
        env=TASK_ENV,
        append_env=True,
    )

    load_task = BashOperator(
        task_id="load_task",
        bash_command=(
            f"{PYTHON_BIN} ingestion/load.py "
            '--run-date "{{ ds }}"'
        ),
        cwd=PROJECT_HOME,
        env=TASK_ENV,
        append_env=True,
    )

    dbt_run_task = BashOperator(
        task_id="dbt_run_task",
        bash_command=f"{DBT_BIN} run --profiles-dir .",
        cwd=DBT_PROJECT_DIR,
        env=TASK_ENV,
        append_env=True,
    )

    dbt_test_task = BashOperator(
        task_id="dbt_test_task",
        bash_command=f"{DBT_BIN} test --profiles-dir .",
        cwd=DBT_PROJECT_DIR,
        env=TASK_ENV,
        append_env=True,
    )

    ge_validation_task = BashOperator(
        task_id="ge_validation_task",
        bash_command=f"{PYTHON_BIN} great_expectations/validate.py",
        cwd=PROJECT_HOME,
        env=TASK_ENV,
        append_env=True,
    )

    extract_task >> load_task >> dbt_run_task >> dbt_test_task >> ge_validation_task
