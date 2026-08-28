Stage S1a の実装は完了し、全569テストが成功、skip 0、禁止ファイルの差分もありません。

## 1. 変更ファイル

- [import-audit-scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py)
  - リポジトリ内のPOSIX絶対パスを受理。
  - `..`、空成分、リンク経由、リポジトリ外は拒否。

- [mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh)
  - 20ケースの設定判定、`invalid-config`、明示空設定を実装。

- [ax-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh)
  - 同じ20ケースの設定判定と安全なJSON出力を実装。

- [codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh)
  - 設定判定と全分岐のJSON生成を刷新。
  - `callerCodexHome`、`callerCodexHomeSource`、`callerAuthFile` を追加。

- [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md)
  - context-mode三値判定、理由の束縛、不正設定の状態行を追加。
  - Codex呼び出し元情報、認証診断、Phase 4環境注記を追加。
  - #59の収束運用注記を追加。

- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md)
  - 4設定項目の`invalid-config`規約、POSIX限定、Codex wrapperの限界を記載。

- [ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md)、[ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md)
  - Codex呼び出し元表示の限界と#59運用注記を追加。

- [test_import_audit_scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py)
  - 絶対パス20ケースと明示的なリンク構成を追加。

- [test_mdq_index.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py)、[test_ax_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_ax_probe.py)、[test_codex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py)
  - 各20ケース、全出力分岐、不正時の未起動確認を追加。
  - Codexには呼び出し元7ケースと特殊文字往復確認も追加。

- [test_codex_review_plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py)、[test_decide_verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py)
  - `invalid-config`の完全一致伝播と、必須レビュー未稼働時の拒否を固定。

- [test_v0132_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py)
  - ax・codexの理由集合を更新。

- [test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py)
  - S1aの文言、順序、出現回数、13ケース三値判定、資料記載を固定。

## 2. DoD

- (1) `test_absolute_path_cases_v014`：成功、20 ID。
- (2) `docaudit_paths.py`差分なし。
- (3) 3ファイルの`test_config_decision_table_v014`、`test_output_key_sets_per_branch`：成功。
- (4) `test_invalid_config_reason_passes_through`、`test_required_with_not_active_state_is_refused`：成功。
- (5) `test_reason_enumerations_and_gate_include_invalid_config`、`test_invalid_config_status_lines_and_phase0_bindings`、`test_cm_enabled_expression_decision_table`、`test_probe_reason_enumerations_match_fixed_sets`：成功。
- (6) `test_config_schema_four_seams_invalid_config`：成功。
- (7) `test_codex_review_convergence_note`：成功。
- (8) `test_caller_codex_home_and_auth_file`、`test_caller_keys_present_in_every_branch`、`test_json_escaping_of_bin_and_home`：成功。
- (9) `test_codex_caller_status_and_documentation_contracts`：成功。
- (15) フルスイート：`Ran 569 tests in 152.492s`、OK、skip 0。
- (16) 3スクリプトの構文確認、変更Pythonの構文確認：成功。
- (18) 禁止ファイル比較：`forbidden-clean`。

対象一式は `Ran 147 tests in 84.350s`、既存契約は `Ran 43 tests in 6.104s` で、いずれも成功しました。

## 3. 検証結果

すべて終了番号0です。

- フルスイート：569件成功、skip 0。
- S1a対象一式：147件成功。
- 既存契約一式：43件成功。
- `bash -n`：成功。
- `py_compile`：成功。
- 表示用Python式の禁止確認：該当0件。
- `git diff --check`：問題なし。
- 禁止ファイル：差分なし。
- `docaudit_paths.py`：差分なし。
- `git status --short`：許可された16ファイルのみ変更・新規作成。開始前からの未追跡`.claude/`は未変更。

## 4. PLANとの差異・未実施事項

S1a実装の乖離、許可外変更、未実施項目はありません。

作業中にbossがPLANをrev.7からrev.8へ更新しましたが、追加裁定はS1bのみでした。現在のPLAN等6文書はHEADと完全一致し、こちらでは変更していません。git commitも行っていません。