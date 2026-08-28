差し戻し1点を修正し、全テストが成功しました。

- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:39)
  - `semanticSearch` の固定句を元の連続した形へ復元。
  - C8 の追記文を固定句の後へ移動。
  - `symbolGraph`／`docGraph` の固定句も分断されていないことを確認。
- `test_v0132_contracts.py` は変更していません。
- commit は行っていません。
- `git diff --check`：成功。

検証結果:

- 契約テスト：`Ran 24 tests`、`OK`
- フルスイート：`Ran 585 tests in 161.719s`、`OK`
- テスト本体の `rc=0`
- skip：`0`

指定コマンド全体は、最後の `grep -c` が一致0件の際に終了値1を返しましたが、表示値は `0` であり、フルスイート本体は正常終了しています。