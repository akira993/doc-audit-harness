結論：計画自体に実装を止める欠陥はありません。worker 指示で吸収できるテスト上の細部が1件だけ残るため、これを条件に実装承認します。

1. `active` の単純な部分一致は、正しい `not active` 行を誤って落とす

   - (a) DoD は右辺に「他 reason の固定句を含まない」ことを要求し、`ok` の固定句を `active` としています（[PLAN.md:220](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:220)、[PLAN.md:223](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:223)）。しかし正しい非稼働メッセージは `not active` を含みます（[SKILL.md:679](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:679)、[SKILL.md:690](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:690)）。単純な `in` 検査では `active` を検出して誤失敗します。
   - (b) 深刻度: **low**
   - (c) 推奨: `ok` は裸の `active` ではなく、`✓ <seam>: active (`、doc-graph の警告は `⚠ doc-graph: active but` という文脈付きパターンで検査する。

### 総括

- 計画自体の欠陥（PLAN を直してから実装）: **なし**
- worker 指示で吸収できる細部: **#1のみ**
- 判定: **実装承認**

設定判定32件、6/6/8状態、PATH stub、英日固定文、deny 5箇所、AST 11件、3 fixture SHA、`.gitignore` 優先順位には新しい矛盾を確認しませんでした。リポジトリは変更していません。