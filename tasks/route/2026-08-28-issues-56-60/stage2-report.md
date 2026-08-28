S2実装は完了しましたが、フルスイートは許可外テスト1件の旧版前提により失敗しました。

(1) 変更ファイルと要点

- 版を `0.14.0` に更新
- ADOPTION英日版に表示行、refresh文、§7の挙動変更6文を追加
- `engine-shas.json` に `0.14.0` を追加
- scaffold・契約テストを再標的
- v0.14.0用release handoffを新規作成
- `test_v014_behavior_changes_paragraph` を追加
- handoffは `.gitignore` の `tasks/` 除外対象のため、実ファイルは存在しますが `git status` には表示されません。boss側で強制追加が必要です。

(2) テスト結果

- S2個別テスト: `Ran 57 tests ... OK`
- `test_v014_behavior_changes_paragraph`: green
- 5面の版確認: `0.14.0`
- handoffテスト、旧定数検査: green
- フルスイート: `Ran 580 tests in 155.275s`
- skip: 0
- 失敗: `tests.test_v0131_docs_contracts.TestV0131DocsContracts.test_g_refresh_paragraph_versions`

失敗理由:

```text
docs/ADOPTION.md: refresh versions=['0.10.1', '0.11.0', '0.12.0', '0.13.0', '0.13.1', '0.13.2', '0.14.0']
```

`tests/test_v0131_docs_contracts.py` はS2許可外のため変更していません。

(3) 検証結果

- bash構文確認: exit 0
- Python構文確認: exit 0
- scaffold stamp確認: `0.14.0`
- 旧handoff定数検査: exit 0
- 残存 `0.13.2` 検査: exit 1（許可された一致のみ）
- verdict guard: exit 0
- 表示式guard: exit 0
- 禁止ファイル差分: exit 0

(4) PLANとの乖離・未実施

- フルスイートgreenのみ未達です。
- `tests/test_v0131_docs_contracts.py` の修正が必要ですが、ユーザー指定のS2許可範囲外のため変更していません。
- 既存の `REVIEW.md` 差分と `.claude/worktrees/` 未追跡ファイルは変更していません。
- commitは実行していません。

日本語 §7 段落全文:

> **v0.14.0 の挙動変更:** `indexing`、`contextMode`、`webExtract`、`codexReview` のキーでは、`enabled` に JSON の真偽値を指定できます。`enabled:false` 以外の場合、`enabled` が真偽値でない、キーがオブジェクトでない（`null` を含む）、または `indexing`・`webExtract`・`codexReview` の `bin` が文字列でない、空、NUL を含むときは `invalid-config` を報告し、ツールを起動しません（キーが無い場合は従来どおり有効で、`bin` の非文字列値は変換されず、読めない設定は従来どおり Phase 0 より前に監査を停止します）。`indexing` キーが不正な場合は、未インストール時と同じく Phase 0 の mdq 確認ゲートが起動します。`codexReview.required:true` と不正な `codexReview` キーを組み合わせた場合は、codex を黙って実行せず `REFUSED` になります。Phase 0 の probe 結果は `$RUN_DIR/phase0-probes.json` に保存されます（表示専用で、verdict の入力にはなりません）。Phase 5 の状態行は初回実行でも再開実行でもその記録から描画され、記録が無いか読めない場合は「state unknown after resume」と表示されます。codex probe は呼び出し元の `CODEX_HOME` と、そこに `auth.json` があるかどうかを報告します（表示専用で、wrapper 自身の環境は観測されません）。`import-audit-scope.py` はリポジトリ直下にある絶対パスの `--config`／`--scope` を受け付けます（POSIX パスのみ）。