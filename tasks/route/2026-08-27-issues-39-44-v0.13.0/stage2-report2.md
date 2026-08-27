S2 差し戻し3点と不足テスト・文書を修正し、フルスイートは **成功408件／失敗0件／skip 6件** です。

主な修正:

- A-1: `bool` を先に判定し、`False` も警告＋既定値 `0.5` に修正。
- A-2: history の生 bytes を読んだ直後に `historySha` を計算。破損時も同じハッシュを保持。
- A-3: `heuristic ∧ regression` は provenance `heuristic` とし、`mapGapCandidates` に復帰。
- full mode では regression と `historySha` 出力を無効化。
- 指定された飽和境界、型検証表、cap 順序、history 状態、source 互換テストを追加。
- [test_plan_dispatch.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_plan_dispatch.py) を新設し、履歴照合・`impactSha`・EVIDENCE 不変を検証。
- 英日 ADOPTION に anchor の古さと実測コスト、欠陥クラス横断掃除の説明を追加。
- [skills/init/SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md) に、新規 draft 向けの `regressionRecheck` 提案と既存設定を変更しない旨を追加。

検証結果:

- 対象群: 96件成功、skip 6件
- resolve-impact＋plan-dispatch: 35件成功
- フルスイート: `Ran 414 tests in 113.308s`
  - 成功408件
  - 失敗0件
  - skip 6件
- `git diff --check`: 問題なし

A-1〜A-3 の試験感度は、該当コードだけを一時的に旧状態へ戻し、次の失敗を確認してから修正版へ復元しました。

- A-1: `False` に対する invalid warning 不在で型検証表が失敗。
- A-2: 破損 history の `historySha` が `null` になり失敗。
- A-3: `heuristic ∧ regression` が `regression` になり provenance 試験が失敗。

最終 `git status --short`:

```text
 M agents/doc-impact-verifier-light.md
 M agents/doc-impact-verifier.md
 M docs/ADOPTION.ja.md
 M docs/ADOPTION.md
 M docs/PROMPTS.ja.md
 M docs/PROMPTS.md
 M skills/audit/SKILL.md
 M skills/audit/references/config-schema.md
 M skills/audit/references/default-heuristics.md
 M skills/audit/references/workflow-template.js
 M skills/audit/scripts/codex-dispatch.py
 M skills/audit/scripts/impact-supplement.py
 M skills/audit/scripts/plan-dispatch.py
 M skills/audit/scripts/resolve-impact.py
 M skills/init/SKILL.md
 M tests/test_resolve_impact.py
 M tests/test_v013_contracts.py
 M tests/test_workflow_template.py
?? .claude/
?? tests/test_plan_dispatch.py
```

`.claude/` は着手前からの未追跡項目です。許可外変更は不要で、git 操作・パッケージ導入・削除操作は行っていません。