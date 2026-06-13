SHELL := /bin/bash

ROOT_DIR := $(CURDIR)
POETRY := POETRY_VIRTUALENVS_IN_PROJECT=true poetry
POETRY_PROJECTS := $(shell find src/applications src/libs -name pyproject.toml -not -path '*/.venv/*' -exec dirname {} \; | sort)
COVERAGE_PROJECT := $(firstword $(POETRY_PROJECTS))

.PHONY: local-up local-down ci-all coverage-all format-all test-all install-all lint-all typecheck-all list-projects

list-projects:
	@printf '%s\n' $(POETRY_PROJECTS)

local-up:
	docker compose -f local-env/docker-compose.yml up -d

local-down:
	docker compose -f local-env/docker-compose.yml down

install-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> poetry install: $$project"; \
		(cd "$$project" && $(POETRY) install); \
	done

format-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> format: $$project"; \
		(cd "$$project" && $(POETRY) run isort . && $(POETRY) run black .); \
	done

lint-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> lint: $$project"; \
		(cd "$$project" && $(POETRY) run isort --check-only . && $(POETRY) run black --check . && $(POETRY) run flake8 .); \
	done

typecheck-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> mypy: $$project"; \
		(cd "$$project" && $(POETRY) run mypy .); \
	done

test-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> pytest: $$project"; \
		(cd "$$project" && $(POETRY) run pytest --cov --cov-report=term --cov-report=xml); \
	done

coverage-all:
	@set -euo pipefail; \
	rm -rf coverage-reports .coverage .coverage.* coverage.xml htmlcov; \
	mkdir -p coverage-reports; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> coverage: $$project"; \
		(cd "$$project" && rm -f .coverage .coverage.* coverage.xml && $(POETRY) install && $(POETRY) run coverage run --parallel-mode --source="$(ROOT_DIR)/src" -m pytest); \
		find "$$project" -maxdepth 1 -name '.coverage.*' -exec cp {} coverage-reports/ \; ; \
	done; \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage combine --data-file="$(ROOT_DIR)/.coverage" "$(ROOT_DIR)/coverage-reports"); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage report --data-file="$(ROOT_DIR)/.coverage" --include="$(ROOT_DIR)/src/*" --omit="*/tests/*,*/.venv/*"); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage xml --data-file="$(ROOT_DIR)/.coverage" -o "$(ROOT_DIR)/coverage.xml" --include="$(ROOT_DIR)/src/*" --omit="*/tests/*,*/.venv/*"); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage html --data-file="$(ROOT_DIR)/.coverage" -d "$(ROOT_DIR)/htmlcov" --include="$(ROOT_DIR)/src/*" --omit="*/tests/*,*/.venv/*")

ci-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> ci: $$project"; \
		(cd "$$project" && $(POETRY) install && $(POETRY) run isort --check-only . && $(POETRY) run black --check . && $(POETRY) run flake8 . && $(POETRY) run mypy . && $(POETRY) run pytest --cov --cov-report=term --cov-report=xml); \
	done
