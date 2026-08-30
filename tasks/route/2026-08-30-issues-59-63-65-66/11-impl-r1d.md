完了しました。方式1を含む実装・文書・契約テスト更新と、指定された全検証が完了しています。

## (1) 完了条件 1〜8

1. 全体テスト

   - 変更前基線: `Ran 655 tests in 237.338s` / `OK`
   - 最終結果（verbatim）:

     ```text
     Ran 697 tests in 283.236s

     OK
     ```

   - 途中実行では旧テスト更新漏れにより、以下の失敗がありました。修正後に上記最終結果を確認しています。

     ```text
     Ran 697 tests in 280.249s

     FAILED (failures=9)
     ```

   - skip なし。既存 `test_generic_layers.py` の非致命的な `ResourceWarning` は残っています。

2. CT-1

   ```text
   call sites 22／exempt 3／getters 13／scripts 21／observers 19
   ```

   期待値 `22／3／13／21／19` と一致しました。

3. CT-2

   ```text
   対象 21 本を検査
   ```

   全21本の一致／不一致対、単独コピー、全対象の読取回数、親子間SHA引継ぎを実測しました。

   契約テスト全体:

   ```text
   Ran 14 tests in 11.035s

   OK
   ```

   CT-1〜CT-7および枝番はすべて `ok` です。

4. `json.load(open` 残存

   shell script: 0件。残存は封印前の `ANCHOR_PATH` 1件のみです。

   ```text
   skills/audit/SKILL.md:14:Also bind `ANCHOR_PATH="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("anchorPath",""))' "$CFG")"` for the run lifecycle and Phase 5.
   ```

5. `"$CFG"` exemption

   指定どおり3件のみです。

   ```text
   14:Also bind `ANCHOR_PATH="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("anchorPath",""))' "$CFG")"` for the run lifecycle and Phase 5.
   25:Before acquiring a run lock, run `AUDIT_SCOPE_CHECK="$(python3 "$SD/scripts/import-audit-scope.py" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --check --json)"`.
   717:`python3 "$SD/scripts/decide-verdict.py" --run-dir "$RUN_DIR" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --anchor-path "$ANCHOR_PATH" --runid "$RUNID" --expect-json "$EVIDENCE"`.
   ```

6. 構文検査

   - `python3 -m py_compile skills/audit/scripts/*.py`: exit 0
   - `bash -n skills/audit/scripts/*.sh`: exit 0
   - `git diff --check`: exit 0
   - `tests.test_sealed_config`: `Ran 9 tests` / `OK`

7. 版・SHA

   `0.15.1` のソース上の残存は次の履歴・過去版参照のみです。

   - `tests/test_v015_contracts.py`: v0.15.1 挙動履歴（英・日）
   - `tests/test_release_handoff.py`: 過去のhandoff、tag、title
   - `docs/ADOPTION.md` / `docs/ADOPTION.ja.md`: v0.15.1挙動履歴と更新元一覧
   - `skills/audit/references/engine-shas.json`: 過去版entry
   - `.mdq/*.sqlite`、`tests/__pycache__/*.pyc`: 生成済みbinaryの一致

   0.16.0 engine SHA:

   ```text
   registry:                   3ba2bc34da259ebdefba32b431bc6267595fe2f75d47b530313455411682abd1
   scaffold-normalized actual: 3ba2bc34da259ebdefba32b431bc6267595fe2f75d47b530313455411682abd1
   match: True
   ```

   `tests.test_scaffold`: `Ran 21 tests` / `OK`

8. branch・差分

   - branch: `fix/v0.16.0-issues-63-59`
   - git書込み操作: 未実施
   - 許可外差分: なし
   - `git status --short`: tracked変更52件、新規4件

## (2) PLANとの食い違い・PLAN外の判断

なし。boss裁定どおり、`generic-layers.py` は `sealed_config` をimportせず、単独複製可能な最小封印読取を内包しています。

## (3) 許可外ファイルの変更が必要な箇所

なし。

## (4) `git diff --stat`

新規未追跡4ファイルはこの統計には含まれません。

```text
 .claude-plugin/plugin.json                 |   2 +-
 README.md                                  |   4 +-
 docs/ADOPTION.ja.md                        |  13 +-
 docs/ADOPTION.md                           |  11 +-
 skills/audit/SKILL.md                      | 111 +++++----
 skills/audit/references/config-schema.md   |   5 +-
 skills/audit/references/engine-shas.json   |   5 +
 skills/audit/scripts/ax-probe.sh           |  13 +-
 skills/audit/scripts/change-set-sha.py     |   8 +-
 skills/audit/scripts/classify-run.py       |  15 +-
 skills/audit/scripts/cocoindex-probe.sh    |  13 +-
 skills/audit/scripts/codegraph-probe.sh    |  13 +-
 skills/audit/scripts/codex-probe.sh        |  13 +-
 skills/audit/scripts/codex-review-plan.py  |  94 ++++++-
 skills/audit/scripts/compute-baseline.sh   |  15 +-
 skills/audit/scripts/decide-verdict.py     | 386 ++++++++++++++++++++++++++---
 skills/audit/scripts/docaudit_cache.py     |  93 +++++++
 skills/audit/scripts/docaudit_paths.py     |  28 +++
 skills/audit/scripts/fix-scope.py          |  10 +-
 skills/audit/scripts/generic-layers.py     |  38 ++-
 skills/audit/scripts/graphify-probe.sh     |  13 +-
 skills/audit/scripts/impact-supplement.py  |  30 ++-
 skills/audit/scripts/import-audit-scope.py |  37 ++-
 skills/audit/scripts/mdq-index.sh          |  42 ++--
 skills/audit/scripts/open-run.py           | 203 ++++++++++++---
 skills/audit/scripts/plan-dispatch.py      |  46 ++--
 skills/audit/scripts/resolve-impact.py     |  17 +-
 skills/audit/scripts/seal-run.py           |   7 +-
 skills/audit/scripts/set-config-key.py     |  13 +-
 skills/audit/scripts/start-run.py          |  13 +-
 tests/test_ax_probe.py                     |  22 +-
 tests/test_check_verdicts.py               |   8 +-
 tests/test_cocoindex_probe.py              |  60 +++--
 tests/test_codegraph_probe.py              |  67 +++--
 tests/test_codex_probe.py                  |  31 ++-
 tests/test_codex_review_plan.py            |  43 +++-
 tests/test_compute_baseline.py             |  11 +-
 tests/test_decide_verdict.py               |  53 ++--
 tests/test_graphify_probe.py               |  57 +++--
 tests/test_impact_supplement.py            |   9 +-
 tests/test_import_audit_scope.py           |   7 +-
 tests/test_mdq_index.py                    |  22 +-
 tests/test_plan_dispatch.py                |  19 +-
 tests/test_resolve_impact.py               |  16 +-
 tests/test_scaffold.py                     |  25 +-
 tests/test_start_run.py                    |  12 +-
 tests/test_v0131_docs_contracts.py         |   4 +-
 tests/test_v0132_contracts.py              |   5 +-
 tests/test_v013_contracts.py               |  17 +-
 tests/test_v014_contracts.py               |  76 +++---
 tests/test_wp12_contracts.py               | 206 ++++++++++++++-
 tests/wp12_helpers.py                      |  16 +-
 52 files changed, 1679 insertions(+), 418 deletions(-)
```