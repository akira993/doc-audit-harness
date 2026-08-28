あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

R2 の 13 件への対応（自己申告）— PLAN rev.3 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md` に反映済み:
1. basename deny を `casefold()` 比較に（§0-2、DoD 1-2。小文字 `claude.md` のテストを追加）。
2. 組込み deny の列挙を 4 か所（config-schema.md:30・:154、SKILL.md:281、ADOPTION en/ja）更新対象に（§0-2、DoD 4）。
3. 判定表 6〜8 行を「probe 単体呼び出し時の防御」と明記し、Phase-5 の `invalid-config` はキー単位の不正（4・5・9・10 行）で到達すると定義（§0-4 ※）。boss 実測: `open-run.py:157-162` は config を hash するだけで JSON 解析しない。
4. `bin` 非文字列／空、semanticSearch の `minScore` 非数値も `invalid-config`（表 9・10 行、DoD 8 に固定テスト名を追加、計 25 件）。
5. 判別基準を「probe の利用不能自体は FAIL 根拠にならない（候補・証拠は間接影響する）」に訂正（§0-4）。
6. `SYMBOL_GRAPH_REASON`／`DOC_GRAPH_REASON`／`SEMANTIC_SEARCH_REASON` の束縛を契約化（§0-4、DoD 10b）。
7. gitignore 状態行を「index 実行中に変化 — 手動確認」に変更、原因断定と `git checkout` 案内を削除（§0-5b、DoD 14）。
8. AST 検査は N=11・ファイル別内訳（2/2/2/1/1/2/1）を PLAN に固定（§0-2、DoD 3）。
9. 状態行は reason→固定句の対応表で完全一致検査、§7 は en/ja それぞれ固定句 9 個＋移行句で検査（DoD 10・17）。
10. `command -v` 非実行を契約から外し、外部 tool 非起動（calls.log 不在）のみ検査（DoD 8）。
11. 件数 +Δ を廃し、固定テスト名の網羅（`unittest -v` 出力の grep）で判定（DoD 20）。
12. 期待順序を `["README.md","SECURITY.md","docs/a.md"]` に（DoD 2）。
13. fixture は空ファイル → JSON 上書きの順序固定、`audit-scope.json` の由来 sha256 `d68186952fee…0982d`（boss 実測）をテストで assert（§0-12、DoD 15）。

# 依頼
PLAN rev.3 を再批判せよ。対応済み事項の再指摘は不要。新規に入れた規則（casefold deny、表 9・10 行、`*_REASON` 束縛、対応表検査、fixture sha）が既存コード・文書・他の新規則と矛盾しないかを中心に、実物で確認できる範囲は確認してから指摘すること。
出力形式は前回と同じ。新しい実質的な指摘が無ければ「指摘なし・実装承認」と明記せよ。
