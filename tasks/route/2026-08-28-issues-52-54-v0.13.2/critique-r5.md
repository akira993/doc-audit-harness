あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

R4 の 9 件への対応（自己申告）— PLAN rev.5 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md` に反映済み:
1. 採用: DoD 10 のラベルを doc-graph 6-state（7 messages）／symbol-graph 6-state／semanticSearch 8-state に統一し、見出し数値を契約テストで固定。
2. 採用: 旧「25 件」を削除、固定名から再計算して 32 件に統一（DoD 8）。
3. 採用: `test_disabled_with_invalid_min_score_is_disabled_by_config`（semanticSearch）を追加（§0-4、DoD 8）。
4. 採用: 必須 subTest 入力を列挙（key `true`/`"x"`/`[]`/`null`、bin `[]`/`1`/`null`/`""`、minScore `"0.4"`/`true`/`null`/`NaN`/`Infinity`/`-Infinity`）（DoD 8）。
5. 採用: config に有効 bin を置けないケースは既定名（graphify/ccc/codegraph）の記録用 stub を PATH 先頭に置いて非起動を検査（DoD 8）。
6. 採用: 状態行検査は `→` の右辺のみを対象に（DoD 10）。
7. 採用: ja §7 も肯定形の固定文 5 つを文言で指定（DoD 17）。
8. 採用: symlink 案内を「readlink で実体を特定し、その内容をバックアップ／VCS と比較」に（§0-5b）。
9. 採用: 「4 か所」の残骸を削除し 5 か所に一本化（§0-2）。

# 依頼
これは上限ラウンド（R5）である。PLAN rev.5 を再批判せよ。対応済み・boss 裁定済み事項の再指摘は不要。新しい実質的な指摘が無ければ「指摘なし・実装承認」と明記せよ。残る指摘がある場合は、必ず「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分して締めよ。
