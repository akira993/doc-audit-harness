差し戻し1件を修正しました。mdq は「導入済みなら既定で有効、`enabled:false` で無効化」と、従来の意味を保つ表現になっています。

指定テスト結果:

```text
Ran 64 tests in 6.352s
OK
```

[stage1b-report.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1b-report.md) に「boss 差し戻し 1 への対応」と再発防止の学び、実測結果を追記しました。

`git diff --check` も成功しています。git への書き込みは行わず、`.claude/` にも触れていません。