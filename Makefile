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
		(cd "$$project" && $(POETRY) run coverage erase && set +e; $(POETRY) run coverage run --source=src -m pytest; rc=$$?; set -e; if [[ $$rc -ne 0 && $$rc -ne 5 ]]; then exit $$rc; fi; $(POETRY) run coverage report -i --include='src/*' --omit='*/tests/*'; $(POETRY) run coverage xml -i -o coverage.xml --include='src/*' --omit='*/tests/*'); \
	done

coverage-all:
	@set -euo pipefail; \
	rm -rf coverage-reports .coverage .coverage.* coverage.xml htmlcov; \
	mkdir -p coverage-reports; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> poetry install: $$project"; \
		(cd "$$project" && $(POETRY) install); \
	done; \
	source_dirs="$$(find "$(ROOT_DIR)/src/applications" "$(ROOT_DIR)/src/libs" -path '*/.venv/*' -prune -o -path '*/src' -type d -print | sort)"; \
	coverage_source="$$(printf '%s\n' "$$source_dirs" | paste -sd, -)"; \
	pythonpath="$$(printf '%s\n' "$$source_dirs" | paste -sd: -)"; \
	test_dirs="$$(find "$(ROOT_DIR)/src/applications" "$(ROOT_DIR)/src/libs" -path '*/.venv/*' -prune -o -path '*/tests' -type d -print | sort | tr '\n' ' ')"; \
	echo "==> coverage: all projects"; \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage erase && PYTHONPATH="$$pythonpath" $(POETRY) run coverage run --data-file="$(ROOT_DIR)/.coverage" --source="$$coverage_source" -m pytest $$test_dirs); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage report --data-file="$(ROOT_DIR)/.coverage" --omit="*/tests/*,*/.venv/*"); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage xml --data-file="$(ROOT_DIR)/.coverage" -o "$(ROOT_DIR)/coverage.xml" --omit="*/tests/*,*/.venv/*"); \
	(cd "$(COVERAGE_PROJECT)" && $(POETRY) run coverage html --data-file="$(ROOT_DIR)/.coverage" -d "$(ROOT_DIR)/htmlcov" --omit="*/tests/*,*/.venv/*")

ci-all:
	@set -euo pipefail; \
	for project in $(POETRY_PROJECTS); do \
		echo "==> ci: $$project"; \
		(cd "$$project" && $(POETRY) install && $(POETRY) run isort --check-only . && $(POETRY) run black --check . && $(POETRY) run flake8 . && $(POETRY) run mypy . && $(POETRY) run coverage erase && set +e; $(POETRY) run coverage run --source=src -m pytest; rc=$$?; set -e; if [[ $$rc -ne 0 && $$rc -ne 5 ]]; then exit $$rc; fi; $(POETRY) run coverage report -i --include='src/*' --omit='*/tests/*'; $(POETRY) run coverage xml -i -o coverage.xml --include='src/*' --omit='*/tests/*'); \
	done
