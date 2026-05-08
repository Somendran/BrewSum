"""Airflow DAG for the BrewSum brewery ELT batch pipeline."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_HOME = "/opt/airflow"
DBT_PROJECT_DIR = f"{PROJECT_HOME}/dbt_project"

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
            "python /opt/airflow/ingestion/extract.py "
            '--run-date "{{ ds }}"'
        ),
    )

    load_task = BashOperator(
        task_id="load_task",
        bash_command=(
            "python /opt/airflow/ingestion/load.py "
            '--run-date "{{ ds }}"'
        ),
    )

    dbt_run_task = BashOperator(
        task_id="dbt_run_task",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt run --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}"
        ),
    )

    dbt_test_task = BashOperator(
        task_id="dbt_test_task",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt test --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}"
        ),
    )

    ge_validation_task = BashOperator(
        task_id="ge_validation_task",
        bash_command="python /opt/airflow/great_expectations/validate.py",
    )

    extract_task >> load_task >> dbt_run_task >> dbt_test_task >> ge_validation_task
