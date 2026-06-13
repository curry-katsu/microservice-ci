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

## Implementation Notes

- Prefer small, explicit Lambda handler modules over shared framework abstractions.
- Add shared code to `src/libs` only when more than one Lambda application needs it or it belongs in a Lambda Layer.
- Avoid committing generated coverage output.
