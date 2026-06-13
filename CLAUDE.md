# CLAUDE.md

このリポジトリでは AI 駆動開発を前提に、変更範囲を小さく保ち、各 Poetry プロジェクト単位で検証してください。

基本方針:

- Lambda アプリは `src/applications` に追加する
- 内部ライブラリは `src/libs` に追加する
- 内部参照は Poetry path dependency を使う
- CI と同じ検証は `make ci-all` で実行する
- ローカル AWS/PostgreSQL 検証は `local-env` 配下に閉じる
