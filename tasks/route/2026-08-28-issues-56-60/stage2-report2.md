修正は完了し、フルスイートを含む全指定テストが通過しました。

## 変更差分

- `test_g_refresh_paragraph_versions` に `0.13.2` を追加。他のassertは変更なし。
- 日本語§7を以下の意味に修正。
  - `enabled` はJSON真偽値必須
  - 絶対パスはリポジトリルート配下
- `test_v014_behavior_changes_paragraph` の日本語6項目も同じ文言へ更新。
- commitは実施していません。

## テスト結果

- 個別テスト: `Ran 65 tests in 11.129s` — `OK`
- フルスイート: `Ran 580 tests in 154.727s` — `OK`
- skip: `0`
- 失敗: なし

## 修正後の日本語§7段落

> **v0.14.0 の挙動変更:** `indexing`、`contextMode`、`webExtract`、`codexReview` のキーでは、`enabled` は JSON の真偽値でなければなりません。`enabled:false` 以外の場合、`enabled` が真偽値でない、キーがオブジェクトでない（`null` を含む）、または `indexing`・`webExtract`・`codexReview` の `bin` が文字列でない、空、NUL を含むときは `invalid-config` を報告し、ツールを起動しません（キーが無い場合は従来どおり有効で、`bin` の非文字列値は変換されず、読めない設定は従来どおり Phase 0 より前に監査を停止します）。`indexing` キーが不正な場合は、未インストール時と同じく Phase 0 の mdq 確認ゲートが起動します。`codexReview.required:true` と不正な `codexReview` キーを組み合わせた場合は、codex を黙って実行せず `REFUSED` になります。Phase 0 の probe 結果は `$RUN_DIR/phase0-probes.json` に保存されます（表示専用で、verdict の入力にはなりません）。Phase 5 の状態行は初回実行でも再開実行でもその記録から描画され、記録が無いか読めない場合は「state unknown after resume」と表示されます。codex probe は呼び出し元の `CODEX_HOME` と、そこに `auth.json` があるかどうかを報告します（表示専用で、wrapper 自身の環境は観測されません）。`import-audit-scope.py` はリポジトリルート配下の絶対パスの `--config`／`--scope` を受け付けます（POSIX パスのみ）。

PLANとの乖離: 無し。