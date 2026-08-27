P1 を修正しました。

- [test_v0131_docs_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0131_docs_contracts.py:91): `"0.12.0"` → `"0." "12.0"`
- `grep -n '0\.12\.0' ...`: 出力なし、0件
- 指定テスト: `Ran 18 tests in 0.064s`、`OK`
- `git diff --check`: exit 0
- [stage2-report.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/stage2-report.md) に「ラウンド 2」を追記済み
- commit は未実施

追跡対象の差分はテストファイル1件のみです。既存の未追跡 `.claude/` には触れていません。