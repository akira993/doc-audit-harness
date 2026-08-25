ローカルの296件のテストは通過しますが、必要なfixtureが変更セットに含まれていないため、クリーンな環境ではテストが失敗します。また、省略可能な設定を省いた場合に新しいレポート除外機能が働きません。

Full review comments:

- [P1] 履歴用エンジンを変更セットに含める — /Users/akiratakahashi/Projects/doc-audit-harness/tests/test_scaffold.py:7-7
  この参照先 `tests/data/generic-layers-v0.10.1.py` は `.gitignore` の `data/` に一致し、現在 Git に追跡されていません。ローカルではファイルが残っているため成功しますが、クリーンな取得環境では refresh テストが `FileNotFoundError` になり、CI が必ず失敗するため、fixture を強制追加する必要があります。

- [P2] docGlobs 省略時にも既定値でレポートを除外する — /Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:64-65
  `docGlobs` は省略可能で既定値が定義されています（`skills/audit/references/config-schema.md:10`）が、ここでは省略時に空配列となるため `report_pattern()` が常に `None` を返します。その結果、`reportPath` だけを指定した有効な設定では、後段の文書列挙が既定の `docs/**/*.md` を使う一方、過去の監査レポートは除外されず再び監査対象になります。同じ複製を持つ各処理でも既定の `docGlobs` を使う必要があります。