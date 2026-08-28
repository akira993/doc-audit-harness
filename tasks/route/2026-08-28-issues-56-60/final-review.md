580件の自動確認は成功しましたが、再開時に Codex の実行先を復元できず、不正設定が状態表示から隠れる経路があります。どちらも新しい保存・再表示機能の利用場面で実際の動作を誤らせます。

Full review comments:

- [P2] 再開用の Codex 実行先も保持する — /Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:283-286
  `codexReview.bin` で実行用ラッパーを指定した監査が Phase 4 前に再開される場合、SKILL は欠けた `CODEX_REVIEW_BIN` を `rebind` から復元するとしていますが、この辞書は元の `codexReviewBin` を捨てています。そのため設定済みラッパーを呼べず、誤った CLI の実行や required 監査の REFUSED につながるので、unknown/complete の両形に bin を保持してください。

- [P2] invalid-config を未実行表示より先に警告する — /Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:751-751
  `codexReview` が不正でも影響文書などがなく `SEALED_PHASE4_REQUIRED=false` になる場合、保存済みの `reason:"invalid-config"` よりこの分岐が優先され、報告は `phase 4 not required` とだけ表示して設定不正を隠します。`config-schema.md` が約束する警告を出せるよう、`invalid-config` をこの分岐より先に判定してください。