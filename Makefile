SHELL := /bin/bash

POETRY := POETRY_VIRTUALENVS_IN_PROJECT=true poetry
POETRY_PROJECTS := $(shell find src/applications src/libs -name pyproject.toml -not -path '*/.venv/*' -exec dirname {} \; | sort)

.PHONY: local-up local-down ci-all format-all test-all install-all lint-all typecheck-all list-projects

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

ci-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> ci: $$project"; \
		(cd "$$project" && $(POETRY) install && $(POETRY) run isort --check-only . && $(POETRY) run black --check . && $(POETRY) run flake8 . && $(POETRY) run mypy . && $(POETRY) run pytest --cov --cov-report=term --cov-report=xml); \
	done
