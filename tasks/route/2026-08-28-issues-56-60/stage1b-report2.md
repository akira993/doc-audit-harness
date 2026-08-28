関連テストで別の固定件数が衝突したため、全体テストの前で停止しました。

変更済み:

- ADOPTION 英日付録に `probe-record.py` を追加
- 表示専用の記録と Phase-5 再束縛の説明を各1文追加
- `implementation paths` を 42 → 43 に更新

関連テスト結果:

```text
Ran 33 tests in 1.659s
FAILED (failures=1)

test_h_adoption_structures_stay_parallel
AssertionError: 52 != 51 : tree lines=52
```

付録へ1行追加したため、同じ [test_v0131_docs_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0131_docs_contracts.py:115) の付録行数も必然的に 51 → 52 になります。しかし「他の assert は変えない」という指示と衝突するため変更していません。

推奨対応は、この固定件数も 51 → 52 に更新することです。許可をいただければ更新し、関連テストとフルスイートを再実行します。全体テストは未実施です。