"""Extract brewery data from Open Brewery DB and land raw JSON in GCS."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date
from typing import Any

import requests
from dotenv import load_dotenv
from google.cloud import storage

API_URL = "https://api.openbrewerydb.org/v1/breweries"
PER_PAGE = 200
REQUEST_TIMEOUT_SECONDS = 30

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


def fetch_breweries(session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Fetch all breweries from the paginated Open Brewery DB API."""
    http = session or requests.Session()
    breweries: list[dict[str, Any]] = []
    page = 1

    while True:
        params = {"page": page, "per_page": PER_PAGE}
        LOGGER.info("Fetching breweries page=%s per_page=%s", page, PER_PAGE)
        response = http.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        page_records = response.json()

        if not isinstance(page_records, list):
            raise TypeError("Open Brewery DB response must be a JSON array")

        if not page_records:
            LOGGER.info("No records returned for page=%s; pagination complete", page)
            break

        breweries.extend(page_records)
        LOGGER.info("Fetched %s records from page=%s", len(page_records), page)
        page += 1

    return breweries


def upload_raw_breweries(
    breweries: list[dict[str, Any]],
    bucket_name: str,
    run_date: str,
) -> str:
    """Upload raw brewery records to the expected GCS object path."""
    object_name = f"raw/breweries/{run_date}/breweries.json"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    payload = json.dumps(breweries, ensure_ascii=False, indent=2).encode("utf-8")

    blob.upload_from_string(payload, content_type="application/json")
    LOGGER.info("Uploaded %s records to gs://%s/%s", len(breweries), bucket_name, object_name)
    return object_name


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the extract job."""
    parser = argparse.ArgumentParser(description="Extract Open Brewery DB records to GCS.")
    parser.add_argument(
        "--run-date",
        default=date.today().isoformat(),
        help="Partition date for the raw GCS object in YYYY-MM-DD format.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the brewery extraction job."""
    load_dotenv()
    args = parse_args()

    try:
        bucket_name = require_env("GCS_BUCKET_NAME")
        breweries = fetch_breweries()
        upload_raw_breweries(breweries, bucket_name, args.run_date)
        LOGGER.info("Extraction complete; total_records=%s run_date=%s", len(breweries), args.run_date)
    except Exception:
        LOGGER.exception("Brewery extraction failed")
        raise


if __name__ == "__main__":
    main()
