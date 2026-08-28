あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

R3 の 14 件への対応（自己申告）— PLAN rev.4 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md` に反映済み:
1. `*_REASON` の中断後復元: **不採用**。既存の `*_AVAILABLE` 束縛と同一の寿命・再開規約（SKILL.md:49）であり、状態行は非ブロッキングの情報行で、本変更で前提は悪化しない。別 Issue 候補「Phase-0 probe 結果の run-dir 永続化」として最終報告に載せる（§0-4）。boss 裁定につき再指摘不要。
2. 採用: `<VAR>_REASON=` … `["reason"]` の完全な式を 3 組検査（DoD 10b、テスト名固定）。
3. 採用: doc-graph 6-state（7 messages）、symbol-graph 6-state、semanticSearch 8-state。reason ごとに記号＋固定句＋他 reason の句を含まない排他検査（DoD 10）。
4. 採用: 評価順序（解析→キー存在→object→enabled 型→enabled:false 確定→bin→minScore）を固定、複合テスト `{"enabled":false,"bin":[]}`→`disabled-by-config`。
5. 採用: `minScore` は `math.isfinite` 必須（表 10 行）。
6. 採用: subTest 表（bin `[]`/`""`、minScore `"0.4"`/`true`/`NaN`/`Infinity`、enabled `"false"`/`1`、`--config` 省略）— 各 probe 10 件＋cocoindex 1 件、計 31 件、全て固定名（DoD 8）。
7. 採用: config-schema.md:39 の文言を「probe validates enabled/bin/minScore; Phase 2 uses minScore」に更新＋契約検査（DoD 12）。
8. 採用: `.gitignore` 変化は exit code より優先、`test_gitignore_change_wins_over_index_failure`（DoD 13）。
9. 採用: 状態行に symlink の readlink 案内（§0-5b）。
10. 採用: 判定表見出しから `command -v` を削除。
11. 採用: 3 fixture の sha256 を固定（audit-scope `d681…0982d`、paths `b1a1…d91d`、config `9723…599c` — boss 実測、貴方の値と一致）。
12. 採用: §7 は en 肯定形固定文 5 つを文言指定、ja は同順・同コードスパン＋固定語（DoD 17）。
13. 採用: DoD の全テスト method 名を PLAN に列挙（DoD 2,3,4,5,6,8,9,10,10b,11,12,13,14,15,17,20）。
14. 採用: 組込み deny の文書は 5 か所を個別検査（DoD 4）。

# 依頼
PLAN rev.4 を再批判せよ。対応済み事項・boss 裁定済み事項の再指摘は不要。実物で確認できる範囲は確認してから指摘すること。出力形式は前回と同じ。新しい実質的な指摘が無ければ「指摘なし・実装承認」と明記せよ。残るものが worker 指示で吸収できる細部のみなら、その旨を明記して承認せよ。
