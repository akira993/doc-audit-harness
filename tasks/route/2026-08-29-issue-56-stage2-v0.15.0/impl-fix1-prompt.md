最終レビューで P2 指摘が 1 件出た。以下を修正せよ（これ以外は変更しない）:

指摘: `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/release-handoff.sh:65-66` は #63 の OPEN しか
検証しないため、#59 が既に CLOSED でも「#59 remains open for the mechanical cross-version resume
prohibition.」という Release notes をそのまま公開してしまう。

修正:
1. `release-handoff.sh` — 既存の #63 OPEN 検証と同型で、公開前に **#59 も OPEN であることを検証**する
   （`die "tracking issue #59 must be OPEN (got: $state)"` 型。notes の変更は不要 — OPEN を前提条件化する）。
2. `tests/test_release_handoff.py` — `test_issue_63_not_open_stops_before_publication` と同型の
   **#59 版の負テスト**（#59 を CLOSED にすると非 0 終了・publication 副作用なし・エラーメッセージ確認）を
   追加する。

変更してよいのはこの 2 ファイルのみ。完了後に
`python3 -m unittest tests.test_release_handoff -v` と `bash -n tasks/route/2026-08-29-issue-56-stage2-v0.15.0/release-handoff.sh`
を実行し、結果（Ran N tests, OK）を報告せよ。commit は不要（boss が行う）。
