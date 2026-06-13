# microservice-ci

<!-- unit-test-coverage:start -->
![Unit Test Coverage](https://img.shields.io/badge/unit_test_coverage-79%25-yellow)
<!-- unit-test-coverage:end -->

Python/AWS Lambda 向けバックエンドプロジェクトの最小構成です。
各 Lambda アプリケーションと内部ライブラリは、個別の Poetry プロジェクトとして `src/applications` と `src/libs` に配置します。

## Layout

```text
src/
  applications/
    sample-eventbridge-handler-app/
  libs/
    infra-core/
local-env/
  infra/
  database/
  docker-compose.yml
```

## Local Environment

floci と PostgreSQL を起動します。

```bash
make local-up
make local-down
```

`local-env/docker-compose.yml` の floci イメージは `FLOCI_IMAGE` で差し替えできます。

```bash
FLOCI_IMAGE=your-floci-image:tag make local-up
```

## Poetry Projects

配下の Poetry プロジェクトは Makefile が自動検出します。

```bash
make list-projects
make ci-all
make format-all
make test-all
make coverage-all
```

サンプルアプリケーションは内部ライブラリ `infra-core` を Poetry path dependency として参照しています。

## CI

GitHub Actions は `src/applications/**/pyproject.toml` と `src/libs/**/pyproject.toml` を検出し、matrix で各 Poetry プロジェクトに対して以下を実行します。

```bash
poetry install
poetry run isort --check-only .
poetry run black --check .
poetry run flake8 .
poetry run mypy .
poetry run pytest --cov --cov-report=term --cov-report=xml
```
