"""Validate raw brewery records in BigQuery with Great Expectations."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import great_expectations as ge
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from great_expectations.core import ExpectationSuiteValidationResult
from great_expectations.render.renderer import ValidationResultsPageRenderer
from great_expectations.render.view import DefaultJinjaPageView

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)

SUITE_PATH = Path(__file__).parent / "expectations" / "breweries_suite.json"
REPORT_DIR = Path(__file__).parent / "uncommitted" / "data_docs" / "local_site" / "validations"


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_expectation_suite(path: Path = SUITE_PATH) -> dict[str, Any]:
    """Load the configured Great Expectations suite JSON."""
    with path.open("r", encoding="utf-8") as suite_file:
        suite = json.load(suite_file)

    expectations = suite.get("expectations")
    if not isinstance(expectations, list) or not expectations:
        raise ValueError(f"Expectation suite has no expectations: {path}")

    return suite


def fetch_raw_breweries(project_id: str, dataset_name: str, location: str) -> pd.DataFrame:
    """Fetch the raw brewery table from BigQuery into a pandas DataFrame."""
    client = bigquery.Client(project=project_id, location=location)
    table_id = f"`{project_id}.{dataset_name}.breweries`"
    query = f"select * from {table_id}"
    rows = client.query(query).result()
    records = [dict(row.items()) for row in rows]
    LOGGER.info("Fetched %s rows from %s", len(records), table_id)
    return pd.DataFrame.from_records(records)


def run_expectations(dataframe: pd.DataFrame, suite: dict[str, Any]) -> ExpectationSuiteValidationResult:
    """Run supported expectations from the suite against a DataFrame."""
    dataset = ge.dataset.PandasDataset(dataframe)
    results = []

    for expectation in suite["expectations"]:
        expectation_type = expectation["expectation_type"]
        kwargs = expectation.get("kwargs", {})
        expectation_method = getattr(dataset, expectation_type)
        result = expectation_method(**kwargs)
        results.append(result)
        LOGGER.info("Expectation %s success=%s", expectation_type, result.success)

    success = all(result.success for result in results)
    statistics = {
        "evaluated_expectations": len(results),
        "successful_expectations": sum(1 for result in results if result.success),
        "unsuccessful_expectations": sum(1 for result in results if not result.success),
        "success_percent": 100.0 * sum(1 for result in results if result.success) / len(results),
    }

    return ExpectationSuiteValidationResult(
        success=success,
        results=results,
        statistics=statistics,
        meta={
            "expectation_suite_name": suite.get("expectation_suite_name", "breweries_suite"),
            "run_id": datetime.now(timezone.utc).isoformat(),
            "validation_target": "raw.breweries",
        },
    )


def write_html_report(validation_result: ExpectationSuiteValidationResult) -> Path:
    """Render and write a local HTML validation report."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"breweries_suite_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.html"
    rendered_document = ValidationResultsPageRenderer().render(validation_result)
    html = DefaultJinjaPageView().render(rendered_document)
    report_path.write_text(html, encoding="utf-8")
    LOGGER.info("Wrote Great Expectations HTML report to %s", report_path)
    return report_path


def main() -> None:
    """Run the raw brewery Great Expectations validation suite."""
    load_dotenv()

    try:
        project_id = require_env("GCP_PROJECT_ID")
        dataset_name = os.getenv("BIGQUERY_DATASET", "raw")
        location = os.getenv("BIGQUERY_LOCATION", "US")
        suite = load_expectation_suite()
        dataframe = fetch_raw_breweries(project_id, dataset_name, location)
        validation_result = run_expectations(dataframe, suite)
        write_html_report(validation_result)

        if not validation_result.success:
            raise RuntimeError("Great Expectations validation failed")

        LOGGER.info("Great Expectations validation succeeded")
    except Exception:
        LOGGER.exception("Great Expectations validation failed")
        raise


if __name__ == "__main__":
    main()
