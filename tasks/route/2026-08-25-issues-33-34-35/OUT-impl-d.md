P2 を修正し、全298テストが成功しました。

- 5つの `report_pattern()` で、`docGlobs` 省略時に既定値 `["docs/**/*.md", "*.md"]` を使用するよう統一。
- [契約テスト](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_report_matcher_contract.py:69)に、`docGlobs` 省略時も5実装が同じ matcher を導出するケースを追加。
- [generic-layers テスト](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_generic_layers.py:620)に、既定の列挙でもレポートだけが除外されるケースを追加。
- 配布 engine の変更に伴い、[engine-shas.json](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/engine-shas.json:15)を `scaffold.py` の計算結果へ更新。
  - `check-docs-engine`: `d0e64dd5c436a04ec1b28e75a73964b324da9de47ff81e7541f7ec223dba5a82`
- 対象31テスト成功、`git diff --check` 成功。
- 既存テストの期待値変更はありません。

全体検証:

```text
----------------------------------------------------------------------
Ran 298 tests in 58.421s

OK
```

既存テスト由来の `ResourceWarning` は表示されましたが、失敗・エラーはありません。