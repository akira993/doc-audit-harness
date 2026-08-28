boss 判定: 報告のとおり、`tests/test_v0131_docs_contracts.py` の付録ファイル数更新と `docs/ADOPTION.md`／`docs/ADOPTION.ja.md` の付録ファイル一覧への `probe-record.py` 追記は正当な波及である。PLAN §7 の許可範囲に `tests/test_v0131_docs_contracts.py` を追加した（`docs/ADOPTION*.md` は元から許可）。
次を実施せよ（単独作業、collab 不使用、commit しない）:
1. ADOPTION en/ja の付録ファイル一覧（`test_c_appendix_file_map_matches_files` が照合する一覧）に `probe-record.py` を、既存の行形式・並び順（他スクリプトと同じ書式）で 1 行ずつ追記。説明は 1 文（Phase-0 probe 結果の run-dir 記録と Phase-5 再束縛、表示専用）。
2. `tests/test_v0131_docs_contracts.py` の固定件数を 42 → 43 に更新（他の assert は変えない）。
3. フルスイートを再実行し `Ran N`・skip 0・失敗 0 を確認。`python3 -m unittest -v tests.test_v0131_docs_contracts tests.test_probe_record tests.test_v014_contracts tests.test_v013_contracts` も実行。
4. 報告: 変更差分の要点、テスト結果（出力ごと）、PLAN との乖離（無ければ「無し」）。
