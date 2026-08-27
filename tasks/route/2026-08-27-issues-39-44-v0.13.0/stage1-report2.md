S1 の実装内容は完了しましたが、既存 S5 試験の版残存と `.git` の書き込み制限により、全テスト成功・ブランチ作成・コミットは未達です。

実装済み:

- #43 の3修正
  - list 継続段落の過剰マスクを修正
  - 複数行 link 後の行番号を保持
  - 未使用 `_token_base` を削除
- 14件のインデント対テスト、複数行 link、死コード試験を追加
- 0.12.0 fixture を保存し、登録済み指紋 `d0e64d…` と一致
- 版5面を 0.13.0 に更新
- 新エンジン指紋 `04117a…` を登録
- 0.12.0 stamp → 0.13.0 更新試験を追加
- 契約テスト骨格を追加。(a)〜(h) は明示的保留、(i) は成功、(j) は下記理由で失敗

差し戻し検証では、0.12.0 fixture が以下の旧挙動を再現しました。

- list 継続段落の bare path を検出できない
- 3行 link 後の4行目を2行目と誤判定

修正版はそれぞれ正しく2行目・4行目を返しました。

検証結果:

- 変更前: `368 tests`、全成功
- 変更後: `396 tests`、`1 failure / 8 skipped`
- `test_generic_layers`: 76件、全成功
- fixture hash・更新試験・現行 engine hash・版5面契約: 4件、全成功
- `git diff --check`、JSON形式検査: 成功
- 最終失敗:

```text
FAIL: test_j_only_allowlisted_0_12_0_references_remain
First list contains 14 additional elements.
First extra element:
tests/test_release_handoff.py:1: """Branch and archive-boundary tests for the v0.12.0 release handoff."""
Ran 396 tests in 111.306s
FAILED (failures=1, skipped=8)
```

[tests/test_release_handoff.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:1) の14行は指定許容リスト外ですが、S1 の変更許可外でS5の更新対象です。不正な例外追加はしていません。

Git操作も環境側で失敗しました。

```text
fatal: cannot lock ref ... Operation not permitted
fatal: Unable to create '.git/index.lock': Operation not permitted
```

現在も `main` 上で、コミットは0件、pushは未実行です。fixture は `data/` の除外規則に該当するため、書き込み可能な環境では `git add -f tests/data/engine-0.12.0.py` が必要です。

変更ファイル一覧（`git diff --stat main`）:

```text
 .claude-plugin/plugin.json               |  2 +-
 docs/ADOPTION.ja.md                      |  6 +--
 docs/ADOPTION.md                         |  4 +-
 skills/audit/references/engine-shas.json |  5 +++
 skills/audit/scripts/generic-layers.py   | 75 ++++++++++++++++++++++++++-----
 tests/test_generic_layers.py             | 76 ++++++++++++++++++++++++++++++++
 tests/test_scaffold.py                   | 37 ++++++++++++++--
 7 files changed, 183 insertions(+), 22 deletions(-)
```

未追加の新規ファイル:

- [tests/test_v013_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py)
- [tests/data/engine-0.12.0.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/data/engine-0.12.0.py)

テスト件数（前後）: **368成功 → 396実行、1失敗・8保留**

許可外変更の必要有無: **あり**。契約 (j) を成功させるには、S5対象の `tests/test_release_handoff.py` 更新が必要です。S1では変更していません。