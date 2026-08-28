あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 状況
PR #61（v0.14.0、あなたが R1〜R5 で批判した PLAN rev.8 の実装）は main `ef995f0` に merge 済み（tag 未作成）。merge 後の `/code-review` が 10 件（最高 medium）を出した。所見の全文と修正計画は `tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md`（新規、§0 に所見を転記）。
実装は branch `fix/v0.14.0-code-review-followup`（= main）上で行い、版は 0.14.0 のまま。

## 依頼
`PLAN-cr1.md` を実コード（merge 後の `skills/audit/SKILL.md`・`probe-record.py`・6 probe・テスト）に照らして批判せよ。特に:
1. A1「再開していない run では会話変数へフォールバック」が、あなたが R4-7/R5 で要求した「完全性判定と表示値をモデルに任せない」と矛盾しないか。再開の有無をオーケストレータがどう判定するか（`RUNID`/`EVIDENCE` の復元有無で判定できるか）、判定不能時の安全側は何か。
2. A2 の reopen 後再記録が、reopen 後の新 `EVIDENCE`（runDir 変更）と probe-record の runDir 検査で成立するか。
3. D10 の共有ヘルパー `probe-config.py` が 3 probe の判定表・出力形・exit code を**完全同値**に保てるか（同値性を証明する検査は何か）。NUL 区切り＋`read -r -d ''` の罠（bash 3.2、末尾 NUL、空 roots）。
4. C8 の graph probe 変更が `test_v0132_contracts` の完全一致集合や Opus B5 のキー集合不変を壊さないか。
5. DoD (1)〜(9) の判別力（正しい実装でも誤った実装でも通る検査、対象 0 件で通る検査）。
6. code-review の所見のうち PLAN が誤読・過小対応しているものがあれば指摘。逆に、対応不要（既存挙動で足りる）と判断できる所見があれば根拠つきで。
指摘は CR1-N で番号を振り、根拠（file:line／実測）と推奨 1 つ。最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、無ければ「rev.1 で実装承認」と明言せよ。日本語 Markdown。
