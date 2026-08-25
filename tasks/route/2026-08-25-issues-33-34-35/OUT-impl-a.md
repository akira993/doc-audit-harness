段階 A の実装と対象テストは完了しましたが、全体テストは段階 C で更新する配布内容の照合値が古いため、まだ green ではありません。

- [generic-layers.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:63)
  - #33: コード領域マスク、bare path 検出、安全な正規化、リポジトリ外参照の除外、backtick の FAIL/WARN 判定
  - #34: `layerGlobs`、`frontMatterOverrides`、不正設定 WARN、text の pass 集計修正
  - #35: self-contained レポートマッチャ、既定 corpus 除外、明示 `--paths` 維持、semantic 集合統合
- [test_generic_layers.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_generic_layers.py:347)
  - 24 件追加、合計 58 件すべて成功
  - 既存テストの期待値変更は 0 件です。
- 手動 fixture: `docs=1 / findings=4 / fail=2 / warn=2`。path・line は仕様どおりでした。
- `git diff --check`: 問題なし
- 追跡対象の変更は上記2ファイルのみです。既存の未追跡 `.claude/` は触れていません。

対象テスト:

```text
Ran 58 tests in 1.953s

OK
```

指定された全体テスト:

```text
Ran 281 tests in 51.486s

FAILED (failures=5, errors=5)
```

失敗10件はすべて scaffold 系で、根本原因は次の1点です。

```text
scaffold: engine-shas.json is stale for: check-docs-engine
```

`engine-shas.json` と版の更新は段階 C の範囲なので、段階 A では変更していません。途中、実行状態確認とリポジトリ外 fixture 作成が環境保護に拒否されましたが、許可範囲内で再実行・fixture 作成へ切り替えて検証済みです。