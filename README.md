# BrewSum

![Python](https://img.shields.io/badge/python-3.11-blue)
![Airflow](https://img.shields.io/badge/airflow-2.8-017CEE)
![dbt](https://img.shields.io/badge/dbt-core-FF694B)
![BigQuery](https://img.shields.io/badge/warehouse-BigQuery-4285F4)
![Great Expectations](https://img.shields.io/badge/data%20quality-Great%20Expectations-FF6319)
![Docker](https://img.shields.io/badge/runtime-Docker-2496ED)

A production-style local ELT batch pipeline for Open Brewery DB data using GCS, BigQuery, dbt, Great Expectations, and Airflow.

## Architecture

```text
Open Brewery DB API
        |
        v
ingestion/extract.py
        |
        v
GCS data lake: raw/breweries/YYYY-MM-DD/breweries.json
        |
        v
ingestion/load.py
        |
        v
BigQuery raw.breweries
        |
        v
dbt staging -> dbt intermediate -> dbt marts
        |
        v
BigQuery mart_brewery_stats
        |
        v
Great Expectations HTML validation report

Airflow DAG brewery_elt_pipeline orchestrates the full path daily.
```

## Prerequisites

- Docker and Docker Compose.
- GNU Make, or run the Docker Compose commands directly.
- A Google Cloud project with BigQuery enabled.
- A GCS bucket created ahead of time.
- A service account JSON key with permissions to read/write the bucket and create/load BigQuery tables.
- Python 3.11 for local syntax checks outside Docker.

Recommended IAM permissions for the service account:

- `roles/storage.objectAdmin` on the bucket.
- `roles/bigquery.dataEditor` on the target datasets.
- `roles/bigquery.jobUser` on the project.

## Setup

1. Copy the environment file.

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your GCP values.

   ```bash
   GCP_PROJECT_ID=your-project-id
   GCS_BUCKET_NAME=your-bucket-name
   BIGQUERY_DATASET=raw
   DBT_DATASET=dbt_brewery
   BIGQUERY_LOCATION=US
   GOOGLE_APPLICATION_CREDENTIALS=./gcp-key.json
   AIRFLOW_UID=50000
   AIRFLOW_FAILURE_EMAIL=alerts@example.com
   ```

3. Place the service account key at the path referenced by `GOOGLE_APPLICATION_CREDENTIALS`.

4. Build and start Airflow.

   ```bash
   make up
   ```

5. Open Airflow at `http://localhost:8080`.

   Default local credentials:

   - Username: `admin`
   - Password: `admin`

## Run Locally

Run the whole pipeline from Airflow by triggering the `brewery_elt_pipeline` DAG.

The DAG runs these tasks in order:

1. `extract_task`
2. `load_task`
3. `dbt_run_task`
4. `dbt_test_task`
5. `ge_validation_task`

## Run Components Individually

Run extraction for a specific partition date:

```bash
docker compose exec airflow-worker python /opt/airflow/ingestion/extract.py --run-date 2026-05-08
```

Run the raw BigQuery load:

```bash
docker compose exec airflow-worker python /opt/airflow/ingestion/load.py --run-date 2026-05-08
```

Run dbt models:

```bash
make dbt-run
```

Run dbt tests:

```bash
make dbt-test
```

Run Great Expectations validation:

```bash
make validate
```

Follow Airflow logs:

```bash
make logs
```

Stop the stack:

```bash
make down
```

## dbt Models

- `stg_breweries`: casts raw API fields, renames identifiers to analytics-friendly names, filters null brewery names, and adds `loaded_at`.
- `int_breweries_cleaned`: keeps one row per brewery ID, standardizes `brewery_type`, filters to United States breweries, and adds `has_coordinates`.
- `mart_brewery_stats`: aggregates brewery counts by state, including brewery type counts and website/coordinate coverage percentages.

dbt creates layer-specific datasets using the configured `DBT_DATASET` prefix. For example, with `DBT_DATASET=dbt_brewery`, BigQuery objects are created in datasets such as `dbt_brewery_staging`, `dbt_brewery_intermediate`, and `dbt_brewery_marts`.

## Data Quality

Great Expectations validates `raw.breweries` with these checks:

- `id` must not be null.
- `name` must not be null.
- Row count must be between 7,000 and 15,000.
- `brewery_type` must be one of the accepted Open Brewery DB brewery types.

HTML reports are written under:

```text
great_expectations/uncommitted/data_docs/local_site/validations/
```

## CI/CD

The GitHub Actions workflow installs pinned dependencies, compiles Python files, and runs `dbt compile` with an offline dummy BigQuery service account key. It does not touch BigQuery or GCS.

Full `dbt test` execution requires a real BigQuery connection and should be run locally or in credentialed CI after adding secure GitHub secrets.

## Known Limitations

- The GCS bucket must already exist.
- Airflow email alerts require SMTP settings in addition to `AIRFLOW_FAILURE_EMAIL`.
- This project uses full refresh loads only; it does not implement incremental source capture.
- CI is syntax-oriented and intentionally avoids live cloud calls.

## Future Improvements

- Add Terraform for GCS bucket, service account, and BigQuery dataset provisioning.
- Add partitioning or ingestion-date history to the raw BigQuery table.
- Add observability metrics for record counts, API latency, and task duration.
- Add a credentialed CI environment for live dbt tests and Great Expectations validation.
