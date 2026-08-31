PLAN.md を v3 に改版した。再読して再批判せよ（修正はまだ行わない）。

## 前回指摘との対応(自己申告)
1. (phase4Required 全体強制) → **あなたの推奨(専用フラグ新設)とは別の代替案を採用した**: start-run.py の変更を撤回し、code-review 層を codexReview と完全対称に「Phase 4 の既存ライフサイクルに従う」設計にした(S3)。空 diff では codexReview 同様走らず、報告書が Phase 4 不要の理由を示す(codexReview.required が空 diff で REFUSED を出さない precedent と一致)。専用フラグより単純で、既存分類への回帰リスクがゼロ。**この代替が R1-3(黙殺懸念)と R2-1(過剰起動)の双方を満たすか、正面から裁定せよ。**
2. (P5 が Unicode legacy を殺す) → 採用。charset 制約を公式名前空間(P7)内に限定し、P5 は「空・空白のみ」だけに縮小。P8 は文字集合制約なし(S1 表改訂)。
3. (phase4Required 軸欠落) → 採用。§9.8 を phase4Required 明示軸つきで全面改訂し、false ⇔ "none" sentinel の双方向契約を gate 検査に追加。
4. (state×findings 整合) → 採用。source=="code-review" 所見は「P6 かつ state==ran」でのみ許可、他は REFUSED(S4・§9.8 末尾)。
5. (UNSPECIFIED の波及) → 採用。source=="code-review" 限定の正規化・blocking とし、共通 findings_fail() の severity 集合は不変(S4)。
6. (三重実装) → 採用。共通分類関数 classify_review_command を新規 library docaudit_review.py に置き、planner と gate が呼ぶ(start-run は #1 の再設計で消費者から外れた)。表駆動テスト tests/test_docaudit_review.py を新設(S1・S7)。
7. (legacy 供給源の二重化) → 採用。legacy 実行値は planner の command に一本化、REVIEW_COMMANDS_JSON は security 専用(S2-1)。
8. (e2e 順序) → 採用。start-run → seal-run → write-evidence → decide-verdict の本番順序(S7)。
9. (required 正規化) → 採用。refuse/not-active 行は常に required:false(S1)。
10. (fresh run の過大記述) → 採用。P6 設定のプロジェクトに限定(S4・S8)。

## 再批判の観点
- 対応 #1 の代替案の妥当性(最優先)。特に「required:true でも空 diff では走らない」が許容できる契約か、codexReview.required の実挙動と本当に対称か(decide-verdict.py の実装で確認せよ)。
- 双方向契約(false ⇔ none)の追加が既存の正当な evidence 経路を壊さないか(preflight evidence・taint 経路・quarantine 経路で phase4Required=false かつ phase4 が none 以外になる正当ケースは無いか)。
- docaudit_review.py 新設の副作用(check-docs-engine sha・installed harness 複製・engine-shas.json の対象ファイル集合に library が含まれるか確認)。
- 新規に見つかる欠陥。既出の再確認は不要。

報告形式は前回と同じ。
