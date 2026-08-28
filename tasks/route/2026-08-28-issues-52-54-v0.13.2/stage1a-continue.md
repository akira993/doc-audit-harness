前回のセッションは全体試験（フルスイート）の待機中に外部要因で停止した（あなたの誤りではない）。作業ツリーの変更は残っている。続きを行え:
1. フルスイートは実行しない（boss が実行する）。代わりに `python3 -m unittest -v tests.test_v0132_contracts tests.test_read_manifest tests.test_import_audit_scope tests.test_wp12_contracts tests.test_codex_dispatch tests.test_v013_contracts tests.test_v0131_docs_contracts` と `python3 -m py_compile skills/audit/scripts/fix-scope.py skills/audit/scripts/read-manifest.py` を実行して結果を確認する。
2. fixture 3 点（`tests/data/dir-framework-scope/`）の sha256 が PLAN の固定値と一致することを `shasum -a 256` で確認する。
3. 未完了の実装があれば完了させる。
4. `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1a-report.md` を書いて終了する（内容は最初の依頼の「報告」節どおり。フルスイート未実行であることを明記）。
