boss 判定: `tests/test_v0131_docs_contracts.py::test_g_refresh_paragraph_versions` の版列挙更新は正当な追随であり、このファイルは PLAN §7 の許可範囲（S1b で追加済み）に含まれる。S2 でも変更を許可する。
次を実施せよ（単独作業・collab 不使用・commit なし）:
1. `tests/test_v0131_docs_contracts.py::test_g_refresh_paragraph_versions` の期待値を新しい refresh 段落（`0.10.1 … 0.13.2` → `0.14.0`）に合わせて更新する。他の assert は変えない。
2. ja §7 段落の文言を 2 点修正する（en の固定文と意味を揃える）:
   - 「`enabled` に JSON の真偽値を指定できます」→「`enabled` は JSON の真偽値でなければなりません」（必須の意味。en は `now require a JSON boolean enabled`）。
   - 「リポジトリ直下にある絶対パスの `--config`／`--scope`」→「リポジトリルート配下の絶対パスの `--config`／`--scope`」（en は `under the repository root`。「直下」は誤り）。
   `test_v014_behavior_changes_paragraph` の ja 期待文も同じ修正を反映する。
3. フルスイート `python3 -m unittest discover -s tests -t . -v > /tmp/s2-full.log 2>&1; tail -3 /tmp/s2-full.log; grep -c ' \.\.\. skipped' /tmp/s2-full.log` と `python3 -m unittest -v tests.test_v0131_docs_contracts tests.test_v013_contracts tests.test_v014_contracts tests.test_release_handoff tests.test_scaffold` を実行。
4. 報告: 変更差分の要点、テスト結果（`Ran N`・skip・失敗は出力ごと）、修正後の ja §7 段落全文、PLAN との乖離（無ければ「無し」）。
