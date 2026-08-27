S4bの実装は完了し、最終476件がすべて成功しました。実モデル呼び出し、ネットワーク利用、コミット操作、禁止ファイルの変更は行っていません。

実装内容:

- 16通りの決定論的判定表と共有状態定数を追加。
- gate に `codexReview.required`、証拠の厳格検査、REFUSED、任意失敗時の警告・表示分離を実装。
- `required:true` なら対象文書0件でも Phase 4を必須化。
- probe に `exec --help` と `probeCommands` を追加。
- SKILL Phase 0/4/5、設定表、設計specを更新。
- EVIDENCEキー、report token、`write-evidence.py` は未変更。

検証結果:

- 着手前: 465件成功、対象外2件
- 重点テスト: 120件成功、対象外1件
- 最終全体: 476件成功、対象外1件
- `git diff --check`: 成功
- probeの文法確認: 成功
- 既存 `test_generic_layers.py` 由来のファイル閉じ忘れ警告は出ましたが、失敗はありません。

主要3件の一時revert確認:

- full＋required を旧skipへ戻すと、真理値表2ケースが失敗。
- gateのrequired停止を外すと、未完了4状態が誤って成功し、4ケースが失敗。
- `exec --help` 検知を外すと、利用不可のfake binを利用可能と誤判定して失敗。

いずれも直後に復元し、重点120件と全体476件を再実行して成功を確認しました。途中、SKILLのモデル再試行説明が既存契約の2行要件を満たさず `1 != 2` となりましたが、再試行側にも封印済みrun classを明記して解消しました。

注意点:

- 着手時から `?? .claude/` が存在し、事前条件の「作業状態が空」とは一致しませんでした。変更禁止のため一切触れていません。
- 設計specは `.gitignore` の対象で、通常の変更一覧に表示されません。bossが取り込む際は明示的に追加する必要があります。
- `tasks/` は変更禁止だったため、計画正本やタスク文書へのレビュー追記は行っていません。

変更ファイル一覧:

- [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md)
- [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md)
- [codex-review-plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py)
- [codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh)
- [decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py)
- [docaudit_cache.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py)
- [start-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py)
- [codex-review設計spec](/Users/akiratakahashi/Projects/doc-audit-harness/docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md)
- [test_codex_review_plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py)
- [test_codex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py)
- [test_decide_verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py)
- [test_start_run.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_start_run.py)
- [test_v013_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py)
- [wp12_helpers.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/wp12_helpers.py)

テスト件数（前後）: 465件 → 476件。  
許可外変更の必要有無: なし。