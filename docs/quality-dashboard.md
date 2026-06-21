# Quality Dashboard Feasibility

## Conclusion

GitHub Pages に最新の品質ダッシュボードを公開する構成は実現可能です。

推奨は、テスト結果のダッシュボードに Allure Report、カバレッジ詳細に coverage.py の HTML report を使い、CI が生成した静的ファイルを GitHub Pages に配置する構成です。独自の画面実装は最小限に抑えられ、現在の Python/pytest/coverage.py/GitHub Actions 構成との相性も良いです。

## Current State

- `develop` push で全 Poetry project の unit test を実行している。
- 各 project の `coverage.xml` を artifact として保存し、`update-readme-badges` job で集約して README badge を更新している。
- integration test は `src/applications/**/integration_tests` を検出し、変更内容に応じて対象アプリケーションだけを `integration-test` job で実行している。
- integration test の結果は、現状 GitHub Actions の job 成否とログで確認する必要がある。
- GitHub Pages 向けの静的レポート公開 job はまだない。

## Demo Branch Policy

検証中は `github-page-demo` branch への push で品質ダッシュボードを GitHub Pages に deploy します。

本運用では `develop` push に切り替える想定ですが、検証段階では README badge 更新と分離します。`update-readme-badges` job は `develop` push のみで動かし、`github-page-demo` push から `develop` を更新しないようにします。

GitHub repository settings の Pages source は `GitHub Actions` にしておく必要があります。`github-pages` environment に「default branch のみ deploy 可」の保護ルールがある場合、`github-page-demo` からの検証 deploy はブロックされます。

## Requirements Fit

| Requirement | Feasibility | Proposed implementation |
| --- | --- | --- |
| 最新CI状態を画面で確認したい | High | `develop` push CI の最後に Pages を更新する |
| カバレッジ率を見たい | High | coverage.py HTML report と `coverage.xml` summary を Pages に配置する |
| integration test の ok/ng 件数を見たい | High | pytest に Allure result を出力させ、Allure Report の overview / suites で確認する |
| どのテストが失敗したか見たい | High | Allure Report の failed/broken test detail、stack trace、fixture/step 情報を使う |
| ダッシュボード画面はOSS等を使いたい | High | Allure Report を採用する |

## Recommended Architecture

```text
GitHub Actions on develop
  unit-test-all
    pytest + coverage
    upload coverage.xml artifacts

  integration-test
    pytest integration_tests --alluredir allure-results/<project>
    upload allure result artifacts

  publish-quality-dashboard
    download coverage artifacts
    download allure result artifacts
    generate coverage HTML
    generate Allure HTML report
    compose static site directory
    deploy to GitHub Pages
```

Pages の想定構成:

```text
/
  index.html                  # 軽量な入口。リンクと最新サマリーのみ
  allure/                     # Allure Report
  coverage/                   # coverage.py HTML report
  coverage.xml                # 機械処理用
  quality-summary.json        # README badge や将来の簡易トップ画面用
```

## OSS Choice

### Primary: Allure Report

Allure Report を第一候補にします。

Reasons:

- pytest 用の adapter があり、`pytest --alluredir allure-results` で結果を出力できる。
- `allure generate` で静的 HTML report を生成でき、GitHub Pages に置きやすい。
- passed/failed/broken/skipped の件数、失敗テスト、stack trace、fixture、step、添付ファイル、履歴を表示できる。
- Allure の history を引き継げば、直近だけでなくトレンドも表示できる。
- integration test のような「どのケースが落ちたか」を見る用途に合う。

Limitations:

- coverage.py の HTML report を Allure の画面内に自然に統合するものではないため、カバレッジ詳細は別ページにするのが現実的。
- Allure CLI 実行のため Java が必要。
- Allure history を Pages 上で維持するには、前回公開済みレポートの `history` を次回生成時に取り込む処理が必要。

### Alternative: ReportPortal

ReportPortal は強力ですが、このリポジトリの最初のダッシュボードには重いです。

Reasons to avoid for first phase:

- GitHub Pages に静的ファイルを置くだけではなく、ReportPortal サーバー、DB、永続ストレージを運用する必要がある。
- real-time analytics、機械学習による失敗分類、共同分析などは魅力的だが、現在の要件より運用コストが大きい。
- public GitHub CI verification project では、まず static report 方式の方が再現性と保守性が高い。

ReportPortal は、複数リポジトリ・大量テスト・長期履歴・失敗分類の運用が必要になった段階で再評価します。

## Coverage Handling

カバレッジ詳細は coverage.py HTML report を使います。

現在の CI は各 project の `coverage.xml` を集約して全体率を出しています。一方で、詳細なファイル別・行別表示には HTML report が必要です。

推奨する次の改善:

- `unit-test-all` で `.coverage` data も artifact 化する。
- 集約 job で `coverage combine` 相当の処理を行い、`coverage html` を生成する。
- 生成した `htmlcov/` を Pages の `coverage/` に配置する。

当面は簡易版として、既存の `coverage.xml` 集約結果から summary を作り、詳細はローカル `make coverage-all` と同等の再生成で `htmlcov/` を作ることも可能です。ただし unit test の二重実行を避けるなら `.coverage` artifact 集約へ寄せる方が良いです。

## Integration Test Handling

integration test job を次のように変更します。

```bash
poetry run pytest integration_tests --alluredir allure-results
```

CI job が失敗しても結果を見られるように、Allure result artifact の upload は `if: always()` にします。

matrix project ごとに artifact を分けます。

```text
allure-results-<project-hash>/
  *.json
  *.txt
  attachments/
  project.txt
```

`publish-quality-dashboard` job で全 artifact をダウンロードし、1つの `allure-results/` に集約して `allure generate` を実行します。

## GitHub Pages Deployment

GitHub Pages は Actions の custom workflow で公開できます。

必要な変更:

- workflow permissions に `pages: write` と `id-token: write` を追加する。
- repository settings で Pages source を GitHub Actions にする。
- `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages` を使う。

この publish job は `if: always()` で動かすのが望ましいです。unit test または integration test が失敗したときこそ、失敗内容をダッシュボードに出したいためです。

## Failure Behavior

品質ダッシュボード公開は、CI 成否と独立して扱います。

- unit test が成功した場合: coverage summary と coverage detail を更新する。
- unit test が失敗した場合: 前回 coverage detail へのリンクを残し、最新の unit test failure を Allure 側に出す構成を検討する。
- integration test が失敗した場合: job は失敗させるが、Allure result は `if: always()` で publish job に渡す。
- publish job 自体が失敗した場合: CI の補助情報が壊れているため失敗として扱う。

## Phased Plan

### Phase 1: Integration Test Dashboard

- 各 application project に `allure-pytest` を dev dependency として追加する。
- `integration-test` job の pytest 実行に `--alluredir` を追加する。
- Allure result artifact を `if: always()` で upload する。
- `publish-quality-dashboard` job で Allure HTML report を生成して Pages に deploy する。

### Phase 2: Coverage Detail Publishing

- unit test の coverage artifact に `.coverage` data または HTML report 生成に必要な情報を追加する。
- Pages に `coverage/` を追加する。
- `index.html` または `quality-summary.json` に coverage rate を表示する。

### Phase 3: History and Trend

- 前回 Pages の Allure `history` を次回 `allure-results/history` にコピーする。
- Allure の trend chart を有効化する。
- `quality-summary.json` に commit SHA、workflow run URL、実行日時、unit/integration 件数を出す。

## Recommendation

このリポジトリでは Phase 1 から進めるのが妥当です。

最初に integration test の可視化を Allure Report で実装すると、現在もっとも見えづらい「どの integration test が落ちたか」を GitHub Pages で確認できるようになります。coverage は既に README badge と artifact 集約があるため、次の段階で HTML report 公開へ広げるのがリスクの低い順序です。

## References

- Allure Report pytest adapter: https://allurereport.org/docs/pytest/
- Allure history files: https://allurereport.org/docs/how-it-works-history-files/
- Coverage.py HTML report: https://coverage.readthedocs.io/en/latest/commands/cmd_html.html
- Coverage.py XML report: https://coverage.readthedocs.io/en/latest/commands/cmd_xml.html
- GitHub Pages custom workflows: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- ReportPortal overview: https://reportportal.io/docs/
