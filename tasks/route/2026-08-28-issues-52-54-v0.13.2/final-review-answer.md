549件のテストと文法確認は成功しましたが、未記載の外部コマンドがない環境で `.gitignore` の変更を見逃します。報告専用という重要な契約に関わるため、修正が必要です。

Review comment:

- [P2] Python標準機能でファイル内容の指紋を計算する — /Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:85-85
  `shasum` がない最小構成のLinux環境では、この処理が失敗しても実行が継続し、変更前後の値が両方とも空になります。その状態で既存の `.gitignore` が書き換わると差分を検出できず、誤って `reason:"ok"` を返します。必要条件はPython 3のみなので（`README.md:23`）、`hashlib`を使うか、計算失敗時は利用不可として扱ってください。