boss レビュー結果: 差し戻し 1 件。それ以外（3 probe・SKILL.md Phase 0/5・config-schema・ADOPTION・テスト 4 本）は PLAN どおりで承認。

差し戻し 1: `skills/init/SKILL.md:36` の mdq（`indexing` seam）の文を「conditional-force indexing」→「opt-in indexing」に変えているが、mdq の意味論は本版で変わっていない（キー不在でも導入済みなら有効）ので「opt-in」は事実と異なる。同じ段落に CocoIndex が含まれるため段落単位の契約テスト `test_three_seams_no_longer_documented_as_auto_used` に掛かったのが原因と理解している。
修正: 意味を保ったまま禁止語を使わない言い換えにする。例: 「Also run `command -v mdq`: if present, this repo can use indexing (on by default when `mdq` is installed; `enabled:false` opts out) — propose an `indexing` block in Step 2.」他 seam（context-mode/ax/codex）の文は変えない。

修正後: `python3 -m unittest -v tests.test_v0132_contracts tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe` を実行し結果を報告、`stage1b-report.md` に「boss 差し戻し 1 への対応」節を追記して終了。git への書き込みは行わない。
