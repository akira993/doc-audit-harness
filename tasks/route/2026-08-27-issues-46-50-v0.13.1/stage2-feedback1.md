# S2 差し戻し 1（最終レビュー `codex exec review` の P1）

S2 は boss がコミット済み（`026705f`）。ただし最終レビューで P1 が 1 件出た。修正してから報告せよ。

1. **[P1] `tests/test_v0131_docs_contracts.py:91` の literal `"0.12.0"` が `test_j_only_allowlisted_0_12_0_references_remain` を赤にする。**
   `test_j` は `git ls-files` の `tests/` 配下を走査し、許可リストに無い `0.12.0` を検出する。ファイルが追跡された今（HEAD に収録済み）、
   フルスイートはこの 1 件で失敗し、`release-handoff.sh` の公開前テストも停止する。
   修正: `test_j` 自身と同じ方式で文字列を分割する（例: `"0." "12.0"`）。`test_j` の許可リストは変更しない（`tests/test_v013_contracts.py` は触らない）。
   同じファイル内に他の `0.12.0` literal が無いか確認すること（`grep -n '0\.12\.0' tests/test_v0131_docs_contracts.py` が 0 件になること）。

修正後: `python3 -m unittest tests.test_v013_contracts tests.test_v0131_docs_contracts -v` の実出力（`Ran 18 tests … OK`）と
`grep -n '0\.12\.0' tests/test_v0131_docs_contracts.py` の結果（0 件）を `stage2-report.md` の末尾に「ラウンド 2」として追記せよ。
git commit はしない（boss が行う）。他のファイルは変更しない。
