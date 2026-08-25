段階 C を実装し、全296テストが成功しました。v0.11.0 への更新と scaffold の照合値不整合も解消済みです。

- 版数と移行説明を 0.11.0 に更新。
- [engine-shas.json](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/engine-shas.json:12) に、`scaffold.py` で算出した3つの照合値を追加。
  - `check-docs`: `a5c1ef…f1ab8`
  - `doc-lint`: `ebc594…66727`
  - `check-docs-engine`: `091e21…4c29`
- [test_scaffold.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_scaffold.py:200) に、0.10.1 engine の更新・利用者変更時の保存・0.11.0生成物照合テストを追加。scaffold 18件は全成功。
- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:12) に新設定、重大度変更、互換性、既知の限界、レポート判定規則を記載。
- [audit/SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:516) に `_02`～`_100`、挿入位置、上書き禁止の契約を追加。
- ADOPTION 英日版の existence 層説明を新しい重大度に更新。
- 指定3ファイルに「リンクのみ」「existence は WARN のみ」という旧前提は該当なしでした。
- 既存テストの期待結果変更はありません。`test_decide_verdict.py:422` は PLAN §5.5 指定どおり入力版だけを0.11.0へ更新し、期待する終了値は0のままです。
- `git diff --check` 成功。

全体検証結果:

```text
----------------------------------------------------------------------
Ran 296 tests in 58.649s

OK
```

0.10.1 の残置は、許可された次の3行だけです。

```text
skills/audit/references/engine-shas.json:7:  "0.10.1": {
docs/ADOPTION.md:254:Existing unmodified stamped 0.10.1 templates can be updated to 0.11.0 with
docs/ADOPTION.ja.md:237:変更されていない stamp 付きの 0.10.1 テンプレートは、`/docaudit:init --harness --refresh`
```

補足が1点あります。[歴史的 fixture](/Users/akiratakahashi/Projects/doc-audit-harness/tests/data/generic-layers-v0.10.1.py) はタグ本文と同一でテストにも使用済みですが、既存の `data/` 無視規則で `git status` に表示されません。環境側で `.git` が読み取り専用だったため登録できず、コミット時に次だけ必要です。

```bash
git add -f tests/data/generic-layers-v0.10.1.py
```

また、`skill-creator` の専用形式検査は環境に PyYAML がなく起動できませんでした。依存不要の同等確認では、既存の `argument-hint` を許容した全条件に合格しています。作業記録は [IMPLEMENTATION-C.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/IMPLEMENTATION-C.md) に残しました。