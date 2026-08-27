S3 差し戻し1は完了しました。コード欠陥5点、故障注入4種、§1.6 (i)〜(viii)、実物検査、退行検出、フルスイートをすべて確認済みです。

主な修正:

- inode が違う他者の lock は削除しない
- config 不在＋base config なしを exit 1・無変更で拒否
- report 判定を既存5実装と完全一致させ、共通契約に追加
- UTC表現を `datetime.timezone.utc` に統一
- 複数文を詰めた記述を整理し、glob変換を一度だけ実行
- `DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT` の4経路を実装
- lock 内で config・scope を再読込し、その内容から再生成
- `auditScope:null`、入れ子の重複key、初回draft固有の`docGlobs`も正しく処理
- scopeの構文・値エラーをgit列挙前に早期終了

テスト結果:

```text
Ran 441 tests in 116.316s

OK (skipped=3)
```

- 着手前（boss提示）: 414件、skip 6
- 完了後: 441件、skip 3
- 重点テスト: 41件成功、skip 3
- dir-framework実物検査: 24規則、46ファイル、errorsなし、`not-imported`
- `git diff --check`: 成功
- 既存の `test_generic_layers.py` から `ResourceWarning` が出ていますが、失敗ではなく今回の変更範囲外です。

退行検出確認:

- A-1: lock削除を旧来の無条件動作へ差し替えると、置換後lockが消えて `FileNotFoundError`
- A-2: 一時複製からconfig不在拒否を除くと、期待exit 1に対してexit 0となり失敗
- hold-lock: 一時複製から待機処理を除くと、`importer exited before holding lock` で失敗

作業ツリー本体は戻さず、実行時差し替えと一時ディレクトリの複製で確認しました。

テスト名⇔検査内容:

| 項目 | テスト |
|---|---|
| (i) glob変換 | `test_i_glob_translation_positive_and_negative_examples`、`test_i_allowed_fnmatch_and_docaudit_dialects_match_on_composite_paths` |
| (ii) 検査順序・git列挙 | `test_ii_absent_skips_git_even_with_crlf_filename`、`test_ii_tracked_and_untracked_crlf_names_are_rejected_and_count_is_reported`、`test_ii_zero_git_paths_is_an_error` |
| (iii) scope拒否条件 | `test_iii_rejects_duplicate_empty_missing_nonstring_invalid_and_outside_values`、`test_iii_report_exclusion_respects_audit_reports_in_corpus`、`test_iii_crlf_in_rule_and_impact_are_rejected`、`test_iii_each_unsupported_rule_error_is_reported_once` |
| (iv) impact:none | `test_iv_impact_none_is_skipped_and_reported` |
| (v) write・lock・SHA・原子更新 | `test_v_fresh_run_base_mode_state_symlink_and_existing_lock`、`test_v_lock_inode_mismatch_does_not_remove_replacement_lock`、`test_v_hold_lock_blocks_break_lock_in_real_process`、`test_v_faults_before_and_after_replace_cleanup_and_atomic_state`、`test_v_unlink_before_flock_stops_without_change`、`test_v_expect_sha_mismatches_exit_four_without_change`、`test_v_replaces_only_source_entries_and_preserves_other_items`、`test_v_base_config_rejects_existing_bad_sha_and_missing_base`、`test_v_base_config_success_publishes_only_complete_config` |
| (vi) check状態・metadata | `test_vi_check_absent_not_imported_in_sync_and_four_drift_paths`、`test_vi_multiset_detects_one_deleted_duplicate`、`test_vi_metadata_type_contract_rejects_invalid_forms`、`test_vi_repeated_doc_glob_and_comma_is_one_literal_glob` |
| (vii) パス安全・custom scope | `test_vii_config_and_scope_containment_missing_and_symlink_contract`、`test_vii_custom_scope_path_is_saved_in_metadata` |
| (viii) source互換 | `test_viii_generated_source_is_accepted_by_resolve_impact` |
| 実物検査 | `test_real_dir_framework_scope_has_24_rules_and_46_equivalence_paths` |

変更ファイル一覧:

- [import-audit-scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py)
- [test_import_audit_scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py)
- [test_report_matcher_contract.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_report_matcher_contract.py)
- [test_v013_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py)
- [audit SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md)
- [init SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md)
- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md)
- [ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md)
- [ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md)

許可外変更の必要はありませんでした。既存の未追跡 `.claude/` には触れておらず、git操作も行っていません。