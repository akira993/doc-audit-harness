差し戻し2点を修正し、フルスイートは green になりました。

- `_strip_container_markers` を元の `[ \t]*` に復元
- 新設 `_strip_blockquote_markers` は `[ \t]?` のまま維持
- 契約テスト (j) を指定文言で S5 まで保留
- 追随して 0.13.0 engine hash を `fbef5b46…` に再計算
- コミット・Git操作は未実施

検証結果:

- 新規テスト: 16件成功
- `test_generic_layers`: 76件成功
- 引用内 list 3ケース: すべて成功、正規表現復元による影響なし
- フルスイート: **成功387／失敗0／skip 9**
- 合計: `Ran 396 tests ... OK (skipped=9)`

`git status --short`:

```text
 M .claude-plugin/plugin.json
 M docs/ADOPTION.ja.md
 M docs/ADOPTION.md
 M skills/audit/references/engine-shas.json
 M skills/audit/scripts/generic-layers.py
 M tests/test_generic_layers.py
 M tests/test_scaffold.py
?? .claude/
?? tests/test_v013_contracts.py
```

`tests/data/engine-0.12.0.py` は既存の `data/` 除外規則により、この表示には出ていません。