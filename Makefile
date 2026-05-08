DOCKER_COMPOSE ?= docker compose
AIRFLOW_SERVICE ?= airflow-worker
DBT_DIR ?= /opt/airflow/dbt_project

.PHONY: up down logs dbt-run dbt-test validate

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

dbt-run:
	$(DOCKER_COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(DBT_DIR) && dbt run --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)"

dbt-test:
	$(DOCKER_COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(DBT_DIR) && dbt test --project-dir $(DBT_DIR) --profiles-dir $(DBT_DIR)"

validate:
	$(DOCKER_COMPOSE) exec $(AIRFLOW_SERVICE) python /opt/airflow/great_expectations/validate.py
