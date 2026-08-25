# 段階 B 実装記録

## 計画

- [x] 段階 A の差し戻し 2 件を修正し、回帰テストを通す
- [x] 段階 B 対象スクリプトと既存テストの契約を確認する
- [x] レポート判定を change-set-sha / decide-verdict / sibling-scan に統一する
- [x] corpus 除外を resolve-impact / impact-supplement / start-run に適用する
- [x] SKILL.md の impact-supplement 呼び出しと PLAN §5.6 のテストを更新する
- [x] 対象テスト、全体テスト、差分、変更範囲を検証する

## レビュー

- 対象 134 件: 成功。
- 全体: 294 件中 5 failures / 5 errors。すべて `check-docs-engine` の照合値未更新による scaffold 失敗。
- 既存期待値の意図的変更:
  - `test_machinery_paths_are_separate_from_diffglob_filter`: suffix レポートを追加し
    `machineryExcludedCount` を 8→9。PLAN §5.6 の #35 suffix 除外に対応。
  - 同テストの `changed` に `doc_audit_policy.md` を追加。PLAN §5.6 の過剰除外解消に対応。
  - `test_report_is_excluded_and_run_dir_matches_stdin`: glob 入力と `doc_audit_x.md` を regex 入力と
    日付 suffix レポートへ変更。PLAN §5.6 の sibling-scan マッチャ統一に対応。
- `compute-baseline.sh` は変更していない。
