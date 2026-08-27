修正完了しました。回帰再検証は、最新 FAIL かつ現在の文書内容ハッシュが履歴の `contentSha` と一致する場合だけ追加されます。

変更内容:

- [resolve-impact.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py)
  - `docaudit_cache.content_sha()` で現在の内容を照合。
  - 内容変更済みの文書は regression tier に追加しない。
- [test_resolve_impact.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_resolve_impact.py)
  - 内容不変の最新 FAIL。
  - 内容変更済み FAIL の除外。
  - cap 境界で heuristic 2件が保持されるケースを追加。
- [test_wp12_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_wp12_contracts.py)
  - 統合試験の履歴を実際の文書ハッシュに更新。
- 英日 ADOPTION に「現在の内容ハッシュが履歴と一致する文書のみ」を追記。

試験感度確認では、内容ハッシュ条件だけを一時的に外して実行しました。

- (b): 変更済み文書が regression に入り、試験失敗。
- (c): regression 2件が heuristic 2件を押し出し、試験失敗。
- 確認後、修正版へ復元済みです。

検証結果:

- 指定対象試験: 62件成功、失敗0件。
- フルスイート: 487件成功、失敗0件、skip 0件。
- `git diff --check`: 問題なし。

フルスイートの末尾:

```text
Ran 487 tests in 140.651s

OK
```

最終状態:

```text
 M docs/ADOPTION.ja.md
 M docs/ADOPTION.md
 M skills/audit/scripts/resolve-impact.py
 M tests/test_resolve_impact.py
 M tests/test_wp12_contracts.py
?? .claude/
```

`.claude/` は既存の未追跡項目です。git 操作は行っていません。