boss 差し戻し（軽微・1 点）: `tasks/route/2026-08-28-issues-56-60/release-handoff.sh` の Release notes 3 行目
`- Ships #56 #57 #58 #59 #60 invalid-config phase0-probes.json CODEX_HOME.` はキーワードの羅列で利用者向け文として不自然。次の 1 文に置き換えよ（必須語 `#56 #57 #58 #59 #60 invalid-config phase0-probes.json CODEX_HOME` は他の行と合わせて全て含まれ続けること）:
`- Ships invalid-config semantics for the indexing / contextMode / webExtract / codexReview keys, display-only Phase-0 probe persistence in $RUN_DIR/phase0-probes.json, caller CODEX_HOME / auth.json visibility in the codex probe, and absolute --config/--scope paths for import-audit-scope.py (see ADOPTION §7 for v0.14.0 behavior changes).`
`release_is_valid` の必須語リストと `tests/test_release_handoff.py` の期待は変えない（`#56`〜`#60` は 1〜2 行目、`invalid-config`／`phase0-probes.json`／`CODEX_HOME` は上の文に含まれる）。
実施後: `bash -n` と `python3 -m unittest -v tests.test_release_handoff` を実行し、結果と最終 notes 全文を報告。commit なし、単独作業。
