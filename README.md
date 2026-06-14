# microservice-ci

<!-- unit-test-status:start -->
![Unit Tests](https://img.shields.io/badge/unit_tests-passing-brightgreen)
<!-- unit-test-status:end -->

<!-- unit-test-coverage:start -->
![Unit Test Coverage](https://img.shields.io/badge/unit_test_coverage-49%25-orange)
<!-- unit-test-coverage:end -->

Python/AWS Lambda 向けバックエンドプロジェクトの最小構成です。
各 Lambda アプリケーションと内部ライブラリは、個別の Poetry プロジェクトとして `src/applications` と `src/libs` に配置します。

## Layout

```text
src/
  applications/
    sample-eventbridge-handler-app/
    sample-sqs-handler-app/
  libs/
    infra-core/
  test-libs/
    integration-test-utils/
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
make integration-test PROJECT=src/applications/sample-sqs-handler-app
```

サンプルアプリケーションは内部ライブラリ `infra-core` を Poetry path dependency として参照しています。
Integration test はアプリケーション配下の `integration_tests` に配置し、共通のテスト補助コードは `src/test-libs/integration-test-utils` から Poetry path dependency として参照します。

## CI

GitHub Actions は `develop` ブランチへの pull request と push で動作します。
`src/applications/**/pyproject.toml` と `src/libs/**/pyproject.toml` を検出し、各ディレクトリを独立した Poetry プロジェクトとして扱います。

Pull request では変更された Poetry プロジェクトだけを matrix で検証します。
ただし、`.github/workflows/ci.yml` またはルート `pyproject.toml` が変更された場合は、全 Poetry プロジェクトを検証します。
個別 Poetry プロジェクトの `pyproject.toml` 変更は、そのプロジェクトだけを検証対象にします。

Pull request の各プロジェクト検証では以下を実行します。

```bash
poetry install
poetry run isort --check-only .
poetry run black --check .
poetry run flake8 .
poetry run mypy .
poetry run pytest --cov --cov-report=term --cov-report=xml
```

`develop` への push では全 Poetry プロジェクトの unit test を実行し、各 project の coverage report を artifact として保存します。
その後、`update-readme-badges` job が coverage artifact を集約して README の coverage badge を更新します。
また、変更されたアプリケーション、内部ライブラリ、テスト用ライブラリ、またはローカル環境定義に応じて、対象アプリケーションの Integration test を Floci と PostgreSQL を起動したローカル環境で実行します。
ローカルでは `make coverage-all` で統合 coverage を `coverage.xml` と `htmlcov/index.html` に出力できます。

```bash
make coverage-all
```

CI の `update-readme-badges` job は、unit test の成功/失敗と集約した coverage から README 冒頭の badges を更新します。
