実装は完了しましたが、全体テストの最終再実行と範囲検査は未達です。

(1) 変更ファイルと要点

- `skills/audit/SKILL.md`：再取得後の Phase 0 再実行、MDQ 記録、context-mode 正規化、unknown 表記、codex 接尾辞、状態行優先規則、C9 文言を更新。
- 3 probe スクリプト：ASCII 制御文字入り `bin` を拒否し、無効化時は既定名へ正規化。
- `config-schema.md`：指定の表3行だけを更新。
- `ADOPTION.md`／`ADOPTION.ja.md`：unknown 表記を指定の一句だけ置換。
- 対象テスト：制御文字33件、display 1行性、契約、`TemporaryDirectory` 化を追加・更新。

(2) DoD テスト

- `tests.test_probe_record`：Ran 9、OK。
- 3 graph probe と `test_v014_contracts`：Ran 75、当時は契約テスト1件失敗後に修正済み。
- `tests.test_v014_contracts`：Ran 10、OK。
- `tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_probe_record tests.test_v014_contracts`：Ran 44、修正前の契約テスト1件失敗後に修正済み。
- `mkdtemp`：0件。
- `bash -n`：OK。

(3) 検証結果

- 禁止 engine ファイル差分：OK。
- ADOPTION の単一置換バイト比較：`adoption-clean`。
- 旧 unknown 表記・旧 codex 条件：0件。
- 全体テストは Ran 585、160.302秒で失敗しました。失敗は、実行途中で更新した `test_cr1_reopen_gate_and_status_order_contracts` の旧判定によるものでした。その後、判定を固定状態行ごとの順序比較へ修正し、当該テストは Ran 10、OK で再確認済みです。全体テストはこの修正後に未再実行です。
- scope-check は exit 1。出力:
  ```text
  tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md (boss doc modified)
  tasks/route/2026-08-28-issues-56-60/REVIEW.md (boss doc modified)
  ```
  禁止対象のため変更していません。

(4) PLAN との乖離・未実施

- scope-check は既存の `tasks/` 側変更により未達です。
- 修正後のフルスイート再実行は未実施です。
- 許可外ファイルは変更していません。`REVIEW.md` と `.claude/` は既存の利用者側変更として保持しています。