RUN_DATE ?= 2026-05-08

.PHONY: install extract load dbt-run dbt-test validate run-all

install:
	pip install -r requirements.txt

extract:
	python ingestion/extract.py --run-date $(RUN_DATE)

load:
	python ingestion/load.py --run-date $(RUN_DATE)

dbt-run:
	cd dbt_project && dbt run --profiles-dir .

dbt-test:
	cd dbt_project && dbt test --profiles-dir .

validate:
	python great_expectations/validate.py

run-all: extract load dbt-run dbt-test validate
