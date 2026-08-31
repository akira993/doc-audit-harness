メタ認知: 最終ラウンドという締切効果で収束を急がず、v5 内部の正本同士と、gate 実行前後の時系列だけを再確認した。

結論: **収束ではない**。新規の実質的欠陥が3件残る。

1. **Major — gate stdout の `codeReviewStatus` は公開報告書の状態行に利用できない**

   根拠: S4/S5 は gate 出力を受け取ってから code-review 状態行を描画する設計である。[PLAN.md:150](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:150>)、[PLAN.md:180](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:180>)。しかし現行ライフサイクルでは、全状態行を含む報告書テンプレートを gate 起動前に完成させ、gate が報告書を公開した後で stdout を返す。[SKILL.md:699](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:699>)、[SKILL.md:732](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:732>)。既存 placeholder に code-review 状態用の項目もない。[SKILL.md:710](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:710>)、[decide-verdict.py:553](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:553>)。stdout は事後の画面表示には使えても、既に公開された報告書には反映できない。

   推奨修正: `{{GATE_CODE_REVIEW_STATUS}}` placeholder を追加し、gate が検証済み状態から固定文言を埋める契約と、checkpoint (h) resume＋`reportPath` 有効の報告書 e2e を PLAN に規定する。

2. **Major — P8 の正常な evidence state が S4 内で矛盾している**

   根拠: EVIDENCE enum と §9.8 は `legacy-ran`／`legacy-not-run` を正常値とする。[PLAN.md:148](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:148>)、[PLAN.md:347](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:347>)。一方、個別 enforcement は P8 に旧値 `legacy` のみを許可している。[PLAN.md:166](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:166>)。状態一覧にも旧 `legacy` が残る。[PLAN.md:111](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:111>)。この記述どおりの gate は、正常な P8 evidence をすべて REFUSED にする。

   推奨修正: S2 の状態一覧と S4 の P8 enforcement を `legacy-ran|legacy-not-run` に統一し、旧 `legacy` を完全に削除する。

3. **Major — `review-command` 偽所見の遮断をテスト計画が判別できない**

   根拠: S4 は `source=="review-command"` を P8＋`state=="legacy-ran"` の場合だけ許可する。[PLAN.md:172](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:172>)。しかし§9.8 の「全行に適用する追加検査」は `source=="code-review"` しか記載せず、`review-command` を欠く。[PLAN.md:352](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:352>)。S7 も legacy 固有の対照ケースを要求していない。[PLAN.md:205](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:205>)。P1/P3、P6、または P8＋`legacy-not-run` に偽の `review-command` 所見を混入できる誤実装でも通り得る。

   推奨修正: §9.8 とS7に `source=="review-command"` × config分類 × state の対照表を追加し、P8＋`legacy-ran` だけを受理することを固定する。

| 区分 | 指摘 |
|---|---|
| 計画自体の欠陥（PLAN修正後に実装） | #1、#2 |
| worker 指示で吸収できる細部 | #3 |

ファイルへの修正は行っていない。