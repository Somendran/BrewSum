"""Load raw brewery JSON from GCS into a BigQuery raw table."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery, storage

RAW_COLUMNS = [
    "id",
    "name",
    "brewery_type",
    "address_1",
    "address_2",
    "address_3",
    "city",
    "state_province",
    "postal_code",
    "country",
    "longitude",
    "latitude",
    "phone",
    "website_url",
    "state",
    "street",
]

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the load job."""
    parser = argparse.ArgumentParser(description="Load raw brewery JSON from GCS to BigQuery.")
    parser.add_argument(
        "--run-date",
        required=True,
        help="Partition date for the raw GCS object in YYYY-MM-DD format.",
    )
    return parser.parse_args()


def read_raw_breweries(bucket_name: str, run_date: str) -> list[dict[str, Any]]:
    """Read raw brewery JSON records from GCS."""
    object_name = f"raw/breweries/{run_date}/breweries.json"
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)

    if not blob.exists():
        raise FileNotFoundError(f"Raw object not found: gs://{bucket_name}/{object_name}")

    payload = blob.download_as_bytes()
    records = json.loads(payload)
    if not isinstance(records, list):
        raise TypeError("Raw brewery JSON must contain an array of records")

    LOGGER.info("Read %s records from gs://%s/%s", len(records), bucket_name, object_name)
    return records


def normalize_record(record: dict[str, Any], ingestion_timestamp: str) -> dict[str, Any]:
    """Normalize a raw API record into the BigQuery raw table shape."""
    normalized = {
        column: None if record.get(column) is None else str(record.get(column))
        for column in RAW_COLUMNS
    }
    normalized["ingestion_timestamp"] = ingestion_timestamp
    return normalized


def ensure_dataset(client: bigquery.Client, dataset_id: str, location: str) -> None:
    """Create the BigQuery dataset if it does not already exist."""
    dataset_ref = bigquery.Dataset(dataset_id)
    dataset_ref.location = location

    try:
        client.get_dataset(dataset_id)
        LOGGER.info("BigQuery dataset already exists: %s", dataset_id)
    except NotFound:
        client.create_dataset(dataset_ref)
        LOGGER.info("Created BigQuery dataset: %s", dataset_id)


def load_breweries_to_bigquery(
    records: list[dict[str, Any]],
    project_id: str,
    dataset_name: str,
    location: str,
) -> None:
    """Load normalized brewery records into BigQuery with WRITE_TRUNCATE."""
    client = bigquery.Client(project=project_id, location=location)
    dataset_id = f"{project_id}.{dataset_name}"
    table_id = f"{dataset_id}.breweries"
    ensure_dataset(client, dataset_id, location)

    ingestion_timestamp = datetime.now(UTC).isoformat()
    rows = [normalize_record(record, ingestion_timestamp) for record in records]
    schema = [bigquery.SchemaField(column, "STRING", mode="NULLABLE") for column in RAW_COLUMNS]
    schema.append(bigquery.SchemaField("ingestion_timestamp", "TIMESTAMP", mode="REQUIRED"))
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()
    destination = client.get_table(table_id)
    LOGGER.info("Loaded %s rows into %s", destination.num_rows, table_id)


def main() -> None:
    """Run the BigQuery raw load job."""
    load_dotenv()
    args = parse_args()

    try:
        project_id = require_env("GCP_PROJECT_ID")
        bucket_name = require_env("GCS_BUCKET_NAME")
        dataset_name = os.getenv("BIGQUERY_DATASET", "raw")
        location = os.getenv("BIGQUERY_LOCATION", "US")
        records = read_raw_breweries(bucket_name, args.run_date)
        load_breweries_to_bigquery(records, project_id, dataset_name, location)
    except Exception:
        LOGGER.exception("Brewery BigQuery load failed")
        raise


if __name__ == "__main__":
    main()
