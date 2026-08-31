boss レビュー（差し戻し R2、P1 1 件）。最終 codex review の指摘を boss が妥当と判断した。修正せよ。git 操作はしない。

## R2-1 [P1] 「resumed run は一律 not-run」が広すぎ、レビュー開始前の中断でも code-review が省略される
- 対象: `skills/audit/SKILL.md:601-603` 付近（step 3 の `For action=run` 段落）と、関係する場合は cross-turn 表の行 (g)。
- 問題: 監査がレビュー**開始前**に会話の区切りをまたいだ場合（例: Phase 0 の確認質問・pre-flight 承認後の再開）も「resumed run」に読めるため、code-review が起動されず not-run になる。required:true では監査全体が誤って REFUSED、任意設定でも新機能が黙って省略される。
- 意図（PLAN S2-6）: not-run に固定するのは **code-review を起動した後に中断された run の再開**（checkpoint 行 (g) の状態）のみ。それより前の再開では、Phase 4 到達時に通常どおり新規に起動する。
- 修正: step 3 の文言を「An audit resumed after the review was started (checkpoint row (g)) binds `CODE_REVIEW_STATE=not-run` and never folds findings left in the conversation from before the interruption; an audit resumed before any code-review invocation starts the review normally when Phase 4 is reached.」の趣旨に限定する（行 (g) の記述と整合させる）。
- 波及: `tests/test_v015_contracts.py` の契約タプルに「A resumed run never upgrades to `ran` ...」の旧文言が固定されているため、新文言に合わせて更新すること。他に同文言を固定するテストが無いか grep で確認。
- 検証: 変更ファイルは SKILL.md と該当テストのみ。最後にフルスイートを 1 回実行し `Ran N tests` と `OK` を verbatim で報告。
