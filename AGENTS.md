# AGENTS.md

## Project Guidance

- This repository is a public GitHub CI verification project for Python AWS Lambda backends.
- Keep each application and internal library as an independent Poetry project.
- Put Lambda applications under `src/applications/<name>`.
- Put internal libraries under `src/libs/<name>`.
- Use Poetry path dependencies for internal libraries.
- Keep local AWS verification resources under `local-env/infra`.
- Keep PostgreSQL initialization DDL under `local-env/database/init`.

## Quality Checks

Run checks from the repository root when changing Python projects:

```bash
make ci-all
```

For narrower work, run the same commands inside the affected Poetry project:

```bash
poetry install
poetry run isort --check-only .
poetry run black --check .
poetry run flake8 .
poetry run mypy .
poetry run pytest --cov --cov-report=term --cov-report=xml
```

## CI Strategy

- The GitHub Actions workflow targets the `develop` branch for both pull requests and pushes.
- Poetry projects are discovered from `src/applications/**/pyproject.toml` and `src/libs/**/pyproject.toml`.
- Pull request CI validates only changed Poetry projects. Changes to CI, the root `Makefile`, or the root `pyproject.toml` force validation of all projects.
- Pull request validation runs `poetry install`, `isort --check-only`, `black --check`, `flake8`, `mypy`, and pytest through `coverage`.
- Push CI on `develop` runs unit tests for all Poetry projects, then regenerates the combined coverage report with `make coverage-all`.
- The `update-coverage-badge` job updates the README unit test coverage badge on `develop` when the combined coverage changes.
- Keep CI commands reproducible through Makefile targets where practical; avoid adding one-off workflow logic that cannot be run locally.

## Implementation Notes

- Prefer small, explicit Lambda handler modules over shared framework abstractions.
- Add shared code to `src/libs` only when more than one Lambda application needs it or it belongs in a Lambda Layer.
- Avoid committing generated coverage output.
