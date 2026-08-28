最終レビュー P2 を修正しました。

- `shasum` 依存を完全に除去し、Python標準の `hashlib.sha256` を使用
- 指紋計算失敗時は `ccc index` を起動せず `reason:"index-failed"`
- `shasum` が利用不能な環境を再現するテストを追加
- 指紋計算失敗時の外部処理非起動もテストで確認

検証結果:

```text
Ran 37 tests in 3.840s
OK
```

`bash -n` と `git diff --check` も成功し、probe 内の `shasum` は0件です。

[stage1b-report.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1b-report.md) に「最終レビュー P2 への対応」を追記しました。git への書き込みは行っていません。