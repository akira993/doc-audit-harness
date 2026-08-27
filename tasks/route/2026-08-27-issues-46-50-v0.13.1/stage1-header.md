# S1 実装依頼 — docaudit v0.13.1 文書整合（Issues #46〜#50）

あなたは worker（実装者）である。boss（Fable）が確定した計画 `tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`（rev.8）の
**S1（文書・references・example の修正）だけ**を実装する。S2（版バンプ・テスト・handoff）は別依頼で行うので、**版番号 `0.13.1` を書かない、
テストを変更しない、engine-shas.json を触らない**。

## 進め方

1. 最初に PLAN.md 全文（特に §0 決定事項・§6 完了条件 S1・§7 変更範囲・§8 検証コマンド・§9 S1 確定仕様）と Issue 本文
   `tasks/route/2026-08-27-issues-46-50-v0.13.1/issues-46-50.md` を読む。Issue の提案と PLAN が食い違う場合は **PLAN が優先**
   （例: #47 の「REFUSED」表現は使わない、#50-4 の `auditScope` は example.json に入れない、#50-5 はコメント 1 行のみ）。
2. 各所見について、修正前に実装ファイル（PLAN §2 の file:line）を実際に読んで文言を実装に合わせる。文書どうしの推測で書かない。
3. en/ja は必ず対にして編集する（ADOPTION.md ↔ ADOPTION.ja.md、PROMPTS.md ↔ PROMPTS.ja.md）。ja は「である体」。
4. 作業後、§8 の検証コマンド（S1 該当分）を全て実行し、**各コマンドの実出力（数値・exit code）を報告に貼る**。フルスイートは
   `python3 -m unittest discover -s tests -t .` で **`Ran 487 tests … OK`（skip 0）** を確認する（S1 はテストを変えないため件数は 487 のまま）。
5. git commit はしない（boss が行う）。`git status --short` と `git diff --stat` を報告に含める。

## 報告書式（最後に `tasks/route/2026-08-27-issues-46-50-v0.13.1/stage1-report.md` へ書き出す）

- 冒頭 1 文で結果（完了／未完了とその理由）。
- Issue 所見ごと（#46-1〜7、#47-1〜2、#48-1〜9、#49-1〜5、#50-1〜5）に「変更ファイル:行」「実装側の根拠 file:line」「DoD 番号」を 1 行ずつ。
- §8 検証コマンドの実出力（全て）。
- 許可外ファイルの変更が必要と判断した箇所があれば、修正せず「報告のみ」の節に列挙。
- 未検証・未対応があれば明示（黙って省略しない）。

---

以下は PLAN.md から転記した **完了条件（S1）／変更範囲／検証コマンド一式／S1 確定仕様**（原文）。
