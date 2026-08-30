あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド5（最終・上限）: PLAN rev.5 の再批判

`tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md` を rev.5 に改訂した（rev.4 は `PLAN.rev4.md`）。**停止規則**: rev.5 は Sol 主導の最終改訂である。本ラウンドの指摘は boss が「計画自体の欠陥」と「worker 指示で吸収できる細部」に区分して記録し、次に Opus による全体敵対レビュー（費用対効果の低いゲートの縮小を含む）へ進む。このラウンドで PLAN を再改訂するのは、**誤った成果物（probe・テスト・文書・版）が完了判定を通って出荷される具体的経路**を示す指摘に限る。gate.py をさらに堅くする提案は、その経路を示せない限り「細部」に区分する。

前回指摘との対応（自己申告）:
1. （HIGH trim 表）→ 採用。N12 に表駆動 subTest: 先頭/末尾に付けた `U+0009〜000D, 0020, 00A0, 1680, 2000〜200A, 2028, 2029, 202F, 205F, 3000, FEFF` は剥がれ、`U+001C〜001F` は剥がれず有効値として保持。
2. （HIGH Phase-3 伝播）→ **却下（根拠）**: 現行出荷版は probe が `-d .codegraph` だけを見て codegraph は `CODEGRAPH_DIR` を尊重するため、`CODEGRAPH_DIR` 利用者では既に「probe は既定 dir・codegraph は別 dir・毎 run init」の乖離がある。本版は Phase-0/Phase-3 の乖離を厳密に縮小するのであって導入しない。解決済み dir と repo root を Workflow の sealed 引数として渡す完全閉鎖は封印入力の設計（#63）に属し、本版の範囲外として持ち越し済み。
3. （HIGH stdin）→ 採用。テスト helper は全ケースで `input=b"STDIN-SENTINEL\n"` と `timeout=30` を明示。fake は読めた内容を記録し、期待は常に `""`。
4. （HIGH G10）→ 採用。必須成果物と任意生成物（物理存在時のみ追跡必須）を分離。§5.6 の glob 表記を配列参照に統一。
5. （HIGH G3+G12）→ 一部採用。PRECLOSED は **`{"65"}`**（rev.4 の「空」は :428 と矛盾する実バグだった）。新規 3 テストの必須 assert（#66 OPEN→close 66 無し・close 65 有り／#66 非 OPEN→非 0 終了かつ release create 無し／残骸 4 語 0）を固定。無意味テストの最終防衛は B1（boss が新規・変更 method 本文を全て読む）と明記。AST 判定の一般化は不採用。
6. （HIGH G11）→ 採用。`difflib` opcode で、SKILL.md 行 3・778 は期待行と完全一致（行 3 の新文字列 `(not started by the audit itself yet)` を PLAN で固定）、他は `replace` のみ許可・旧側範囲が許可範囲内、`insert`/`delete` は位置を問わず 0。
7. （HIGH G13）→ 一部採用。`.envrc`（ignored）を追加、エントリに種別・mode・symlink 先を含める。ignored 全体への拡張は却下: `tests/__pycache__` は G1 の unittest 実行自体が書き換え、`.mdq/` は SessionStart hook、`.serena/`・`.brv/` はツールのキャッシュで自発変化するため偽 FAIL になる。`AGENTS.md` は本 repo に実体がない（実測）。
8. （MEDIUM G8 接頭辞）→ 採用。許可集合は具体配列のみ。
9. （MEDIUM G2 fixture）→ 採用。既存 method の一時改名。
10. （MEDIUM G8 fixture）→ 採用。scratch worktree で禁止→許可パスへ `git mv` コミット。

## 依頼

rev.5 を読み直し、**新規の**指摘のみ。各指摘に「計画自体の欠陥／細部」の区分を付け、計画自体の欠陥については **誤った成果物が出荷される具体的経路**を 1 行で示せ。末尾に HIGH 一覧と「実装に進めてよいか」の 1 行。
