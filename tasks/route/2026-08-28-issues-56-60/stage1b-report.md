S1b の実装は完了しましたが、全体テストは既存のファイル一覧契約が新スクリプトを未登録として数えるため、1件失敗しています。

## 変更ファイルと要点

- [probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py)
  - 10 seam の検査、実行フォルダの安全な読取・原子的保存、`--read` と7行の再束縛値を実装。
- [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md)
  - Phase 0/3/4 の記録、Phase 5 の再読込・unknown 表示・fail-open 規約を追加。
- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md)
  - `phase0-probes.json` を表示専用・gate 非読込として記載。
- [test_probe_record.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py)
  - 固定32 ID、保存・検査・欠損・リンク拒否・表示境界を確認。
- [test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py)
  - Phase 0/3/4/5、再開、unknown、EVIDENCE、Guardrails の契約を追加。

## DoD テスト

- (10) `tests.test_probe_record`: 7 テスト、固定32 ID、成功。
- (11) `tests.test_v014_contracts`: 8 テスト、成功。
- 指定の関連テスト一式: `Ran 72 tests`、成功。
- `py_compile`: 成功。
- gate の `phase0-probes` 非参照・表示用式非存在: ともに成功。
- 禁止スクリプトと `docs/` の差分確認: 成功。

## 検証結果

- 全体: `Ran 578 tests in 150.607s`、skip 0、1件失敗。

```text
FAIL: test_c_appendix_file_map_matches_files
AssertionError: 43 != 42 : implementation paths=43
```

新規 `probe-record.py` により、`test_v0131_docs_contracts.py` が固定している実装ファイル数が 42 から 43 になったことが原因です。

## PLAN との乖離・未実施

無しではありません。全体テストを green にするには、許可外の以下を変更する必要があります。

- `tests/test_v0131_docs_contracts.py` の固定件数更新
- `docs/ADOPTION.md` と `docs/ADOPTION.ja.md` の付録ファイル一覧への `probe-record.py` 追加

これらは S1b の許可範囲外のため変更していません。`git commit` も行っていません。

なお、開始時から存在した `tasks/.../REVIEW.md` の変更と `.claude/` 未追跡項目には触れていません。