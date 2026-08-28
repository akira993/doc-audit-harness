boss 差し戻し（最終レビュー `codex exec review` の P2 ×2）。S1b/S2 は commit 済み（HEAD `8c05ac1`）。単独作業・collab 不使用・commit なしで次を修正せよ。

1. **`probe-record.py::make_rebind`／`unknown_rebind`**: `rebind["codex-review"]` に `"bin"`（記録の `codexReviewBin`、unknown 形では `null`）を追加する。理由: SKILL の再開段落は欠けた運用変数（availability／reason／**binary**）を `rebind` から復元してよいとしているが、現状 codex-review だけ bin を捨てており、`codexReview.bin` に wrapper を指定した監査が Phase 4 前に再開されると wrapper を呼べない（誤った CLI 実行や required 監査の REFUSED）。他 seam（symbol-graph 等）は既に `bin` を持つ。`tests/test_probe_record.py` の `rebind` 期待値（complete／unknown 両形）を更新。
2. **`skills/audit/SKILL.md` Phase-5 codex-review 行**: `rebind.codex-review.reason=invalid-config` の枝を**最初に**評価する（`phase4-not-required` 枝・`reviewState=null` 枝・既存 4-way より前）:
   `- rebind.codex-review.reason=invalid-config → ⚠ codex-review: doc-audit.json codexReview is invalid — not probed this run; fix the key. [non-blocking]`
   理由: `SEALED_PHASE4_REQUIRED=false`（影響文書なし等）の run では Phase 4 が走らず `codexReviewState=phase4-not-required` になるため、config 不正が「not run (phase 4 not required)」の表示に隠れ、`config-schema.md` が約束する ⚠ 状態行が出ない。既存の 4-way リテラル（`CODEX_REVIEW_STATE=not-active` 等）は温存。`tests/test_v014_contracts.py` に「この枝が codex-review ブロック内で `phase4-not-required` 枝・`reviewState=null` 枝・`CODEX_REVIEW_STATE=not-active` 行より前にある」順序 assert を追加。
3. `config-schema.md` の `codexReview` 行に矛盾があれば整合させる（無ければ変更しない）。
4. 検証: `python3 -m unittest -v tests.test_probe_record tests.test_v014_contracts tests.test_v013_contracts tests.test_v0132_contracts tests.test_wp12_contracts tests.test_harness_contract`、フルスイート（`Ran N`・skip 0）、`py_compile probe-record.py`。
5. 報告: 変更差分の要点、テスト結果、PLAN との乖離（無ければ「無し」）。
