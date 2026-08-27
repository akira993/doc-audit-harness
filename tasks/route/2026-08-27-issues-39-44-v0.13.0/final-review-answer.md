クリーンな取得環境で公開手順のテストが失敗し、再確認対象の選択も文書化された条件を満たしていません。手元の全テストは成功しますが、未追跡ファイルによって失敗が隠れています。

Full review comments:

- [P1] release-handoff.sh を追跡対象に含める — /Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:18-19
  この参照先は `tasks/` の除外設定により差分にも追跡対象にも含まれていません。クリーンな checkout ではスクリプトが存在せず、`tests.test_release_handoff` が終了値 127 で失敗するため、スクリプトを追跡対象へ追加するか、追跡済みの場所を参照してください。

- [P2] 内容ハッシュが一致する FAIL だけを再確認する — /Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:254-256
  `regressionRecheck` を有効にすると、履歴の `contentSha` を現在の文書と比較せず、最新判定が FAIL というだけで `regression` に追加されます。文書が修正済みでも高優先度の枠を消費し、`maxImpactedDocs` 到達時には実際の heuristic 候補を押し出します。`docs/ADOPTION.md:315` の「内容不変」という契約どおり、現在の内容ハッシュが履歴と一致する場合だけ追加してください。