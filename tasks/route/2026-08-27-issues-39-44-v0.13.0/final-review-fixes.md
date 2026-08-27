boss 差し戻し（最終レビュー P2）— `skills/audit/scripts/resolve-impact.py` の regression 再検証。git 操作は不要。

**欠陥**: `regressionRecheck.enabled` のとき、history の最新 entry が FAIL というだけで `regression` に追加しており、その entry の
`contentSha` と**現在の文書内容**を比較していない。PLAN §10 #39 と `docs/ADOPTION.md` の契約は「前回 FAIL・**内容不変**の再検証」。
文書が修正済みでも regression tier の枠を消費し、cap 到達時に heuristic 候補を押し出す。

**修正**: 候補追加の条件に「`docaudit_cache.content_sha(repo, path)`（history と同じ算出方式）が entry の `contentSha` と一致する」を
追加せよ。不一致（内容が変わった）文書は regression に**追加しない**（通常の mapped/heuristic 判定に委ねる）。
`counts.regression` と `historySha` の意味は変えない。

**テスト**（`tests/test_resolve_impact.py`）: (a) 最新 FAIL・内容不変 → `regression` に入る（既存）、(b) 最新 FAIL・内容変更後
→ `regression` に入らず `counts.regression == 0`、(c) cap 境界（mapped 2・内容変更済み FAIL 2・heuristic 2・`maxImpactedDocs: 4`）
で heuristic 2 件が残る（変更済み FAIL が枠を消費しないこと）。修正を revert すると (b)(c) が赤になることを確認して方法を報告。

**docs**: `docs/ADOPTION.md`・`.ja.md` の regression 説明に「現在の内容ハッシュが履歴と一致する文書のみ」を 1 句追記（既に
そう書いてあれば不要）。

完了後、`python3 -m unittest tests.test_resolve_impact tests.test_wp12_contracts -v` とフルスイート（`> /tmp/suite.log 2>&1` →
`tail -3`）を実行し、件数を報告せよ。
