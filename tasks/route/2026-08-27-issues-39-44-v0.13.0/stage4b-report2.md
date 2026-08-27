差し戻し1点を修正し、全477件が成功しました。

- `codexReview` が辞書形式でなければ `{}` に変換し、`required:false` 相当として処理。
- `[]`／`"x"` × incremental／full の4組合せを回帰テストで固定。
  - incremental、対象文書0件 → `phase4Required:false`
  - full → 従来どおり `phase4Required:true`

検証結果:

- 指定重点テスト: 105件成功
- フルスイート: 477件成功、対象外1件
- `git diff --check`: 成功
- 既存テスト由来の `ResourceWarning` は出ましたが、失敗はありません。
- git操作は行っていません。

変更ファイル:

- [start-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py)
- [test_start_run.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_start_run.py)