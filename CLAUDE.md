# CLAUDE.md

このリポジトリでは AI 駆動開発を前提に、変更範囲を小さく保ち、各 Poetry プロジェクト単位で検証してください。

基本方針:

- Lambda アプリは `src/applications` に追加する
- 内部ライブラリは `src/libs` に追加する
- 内部参照は Poetry path dependency を使う
- CI と同じ検証は `make ci-all` で実行する
- ローカル AWS/PostgreSQL 検証は `local-env` 配下に閉じる

CI 戦略:

- GitHub Actions は `develop` への pull request と push で動作する
- Poetry プロジェクトは `src/applications/**/pyproject.toml` と `src/libs/**/pyproject.toml` から自動検出する
- pull request では変更された Poetry プロジェクトだけを matrix で検証する
- CI workflow、ルート `Makefile`、ルート `pyproject.toml` の変更時は全 Poetry プロジェクトを検証する
- pull request 検証では `poetry install`, `isort`, `black`, `flake8`, `mypy`, pytest/coverage を実行する
- `develop` push では全 Poetry プロジェクトの unit test を実行し、`make coverage-all` で統合 coverage を作成する
- 統合 coverage の結果は README の unit test coverage badge に反映される
- CI で使う処理は、可能な限り Makefile からローカルでも再現できる形に保つ
