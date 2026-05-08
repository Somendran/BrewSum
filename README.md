# BrewSum

![Python](https://img.shields.io/badge/python-3.11-blue)
![Airflow](https://img.shields.io/badge/airflow-2.8-017CEE)
![dbt](https://img.shields.io/badge/dbt-core-FF694B)
![BigQuery](https://img.shields.io/badge/warehouse-BigQuery-4285F4)
![Great Expectations](https://img.shields.io/badge/data%20quality-Great%20Expectations-FF6319)

A production-style ELT batch pipeline using Python, GCS, BigQuery, dbt Core, Great Expectations, and Apache Airflow for orchestration.

## Architecture

```text
Open Brewery DB API
        |
        v
Python extract job
        |
        v
GCS data lake: raw/breweries/YYYY-MM-DD/breweries.json
        |
        v
Python load job
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
Great Expectations validation report

Apache Airflow will orchestrate this flow in Phase 2.
```

## Roadmap

- Phase 1: Run the pipeline manually using Python, dbt, and Great Expectations.
- Phase 2: Add local Apache Airflow orchestration without additional runtime packaging.
- Phase 3: Polish portfolio documentation, screenshots, and resume bullets.

## Prerequisites

- Python 3.11.
- A Google Cloud project with BigQuery enabled.
- A GCS bucket created ahead of time.
- A service account JSON key with permissions to read/write the bucket and create/load BigQuery tables.

Recommended IAM permissions for the service account:

- `roles/storage.objectAdmin` on the bucket.
- `roles/bigquery.dataEditor` on the target datasets.
- `roles/bigquery.jobUser` on the project.

## Setup

Create and activate a virtual environment from PowerShell:

```powershell
cd D:\BrewSum
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Copy the sample environment file and edit `.env` with your values:

```powershell
Copy-Item .env.example .env
```

Required `.env` variables:

```text
GCP_PROJECT_ID=brewsum
GCS_BUCKET_NAME=brewsum-raw
BIGQUERY_DATASET=raw
DBT_DATASET=dbt_brewery
BIGQUERY_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
AIRFLOW_UID=50000
AIRFLOW_FAILURE_EMAIL=<your-email>
```

Place your service account key at the path referenced by `GOOGLE_APPLICATION_CREDENTIALS`.

## Manual Local Run

Run extraction:

```powershell
python ingestion/extract.py --run-date 2026-05-08
```

Load raw data into BigQuery:

```powershell
python ingestion/load.py --run-date 2026-05-08
```

Run dbt models and tests:

```powershell
cd dbt_project
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..
```

Run Great Expectations validation:

```powershell
python great_expectations/validate.py
```

## Make Targets

These targets are thin wrappers around the same local commands:

```powershell
make install
make extract RUN_DATE=2026-05-08
make load RUN_DATE=2026-05-08
make dbt-run
make dbt-test
make validate
make run-all RUN_DATE=2026-05-08
```

If Make is not available on Windows, use the manual PowerShell commands above.

## Expected Output

- Raw brewery data extracted from Open Brewery DB API.
- Raw files uploaded to GCS.
- Raw BigQuery tables created and populated.
- dbt models created in the `dbt_brewery` dataset family.
- dbt tests pass.
- Great Expectations validation passes.

## dbt Models

- `stg_breweries`: casts raw API fields, renames identifiers to analytics-friendly names, filters null brewery names, and adds `loaded_at`.
- `int_breweries_cleaned`: keeps one row per brewery ID, standardizes `brewery_type`, filters to United States breweries, and adds `has_coordinates`.
- `mart_brewery_stats`: aggregates brewery counts by state, including brewery type counts and website/coordinate coverage percentages.

dbt creates layer-specific datasets using the configured `DBT_DATASET` prefix. With `DBT_DATASET=dbt_brewery`, objects are created in datasets such as `dbt_brewery_staging`, `dbt_brewery_intermediate`, and `dbt_brewery_marts`.

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

## Airflow

The DAG file is kept at `dags/brewery_pipeline_dag.py` and represents this flow:

```text
extract -> load -> dbt_run -> dbt_test -> great_expectations_validate
```

Phase 2 uses local Apache Airflow from WSL2 Ubuntu. The recommended WSL project path is:

```bash
/mnt/d/BrewSum
```

Create an Airflow virtual environment in WSL:

```bash
cd /mnt/d/BrewSum
python3 -m venv airflow_venv
source airflow_venv/bin/activate
pip install -r requirements.txt
```

Configure Airflow for local execution:

```bash
export AIRFLOW_HOME=/mnt/d/BrewSum/airflow_home
export BREWSUM_PROJECT_DIR=/mnt/d/BrewSum
export GCP_PROJECT_ID=brewsum
export GCS_BUCKET_NAME=brewsum-raw
export BIGQUERY_DATASET=raw
export DBT_DATASET=dbt_brewery
export BIGQUERY_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/mnt/d/BrewSum/gcp-credentials.json
```

Initialize Airflow and create an admin user:

```bash
airflow db migrate
airflow users create \
  --username admin \
  --firstname BrewSum \
  --lastname Admin \
  --role Admin \
  --email your-email@example.com \
  --password admin
```

Point Airflow at the project DAGs folder. One simple local option is to symlink the project DAG into `AIRFLOW_HOME`:

```bash
mkdir -p "$AIRFLOW_HOME/dags"
ln -sf /mnt/d/BrewSum/dags/brewery_pipeline_dag.py "$AIRFLOW_HOME/dags/brewery_pipeline_dag.py"
```

Start the scheduler and webserver in separate WSL terminals with the same environment variables loaded:

```bash
airflow scheduler
```

```bash
airflow webserver --port 8080
```

Open `http://localhost:8080`, enable `brewery_elt_pipeline`, and trigger a DAG run. No additional runtime packaging is used.

## CI/CD

GitHub Actions performs lightweight checks:

- Check out the repository.
- Set up Python 3.11.
- Install pinned dependencies.
- Compile Python files.
- Parse the dbt project with a temporary fake service account file, without calling GCP.

Full `dbt test` and Great Expectations validation require real GCP credentials and should be run locally after `.env` is configured.

## Known Limitations

- The GCS bucket must already exist.
- Airflow email alerts require SMTP settings in addition to `AIRFLOW_FAILURE_EMAIL`.
- This project uses full-refresh loads only.
- CI intentionally avoids live cloud calls.

## Future Improvements

- Add infrastructure-as-code for GCS, service account, and BigQuery dataset provisioning.
- Add ingestion-date history to the raw BigQuery table.
- Add screenshots of BigQuery tables, dbt lineage, and validation reports.
- Add portfolio-ready summary bullets and operational runbook notes.
