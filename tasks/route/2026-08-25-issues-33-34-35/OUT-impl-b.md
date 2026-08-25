段階 A の差し戻し2件と段階 B を実装し、対象134件は全成功、全体テストは想定済みの照合値未更新による scaffold 10件だけが失敗しました。

主な変更:

- [generic-layers.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:142)
  - `frontMatterOverrides` を `globs: string[]` に修正
  - 配列内のいずれかに一致し、設定配列は先勝ち
  - [コロン付き実在ファイルを先に解決](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:325)
- [change-set-sha.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/change-set-sha.py:44)
  - 広すぎた glob をテンプレート由来 regex に変更
  - `auditReportsInCorpus` にかかわらず機構出力を除外
- [sibling-scan.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/sibling-scan.py:154)
  - `--report-pattern` を regex として全体一致判定
- [resolve-impact.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:92)
  - full corpus と heuristic pool からレポートを除外
  - mapped は維持
- [impact-supplement.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:69)
  - 任意の `--config` を追加
  - 未指定時の従来動作と、検索元なしの場合の完全な no-op を維持
- [start-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:23)
  - corpus 数からレポートを除外
  - レポートだけのリポジトリを空 corpus として処理
- [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:300)
  - `impact-supplement.py` 呼び出しへ `--config "$CFG"` を追加
- [契約テスト](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_report_matcher_contract.py:22)
  - 5実装と `decide-verdict.py` の判定一致をケース表で固定

`decide-verdict.py` 自体は正本を動的に読み込む既存構造のため、変更なしで regex 統一が反映されています。

検証結果:

```text
Ran 134 tests in 16.868s

OK
```

全体テスト:

```text
Ran 294 tests in 55.934s

FAILED (failures=5, errors=5)
```

10件はすべて次の同一原因です。

```text
scaffold: engine-shas.json is stale for: check-docs-engine
```

これは段階 C で更新する照合値です。それ以外の失敗はありません。

既存テスト期待値の意図的変更:

1. `machineryExcludedCount`: 8→9  
   PLAN §5.6 の `_02` suffix レポート除外に対応。
2. `changed` に `docs/logs/doc_audit_policy.md` を追加  
   PLAN §5.6 の過剰除外解消に対応。
3. sibling-scan の glob／`doc_audit_x.md` fixture を regex／日付suffixレポートへ変更  
   PLAN §5.6 のマッチャ統一に対応。

`compute-baseline.sh`、版数、照合値、scaffold は変更していません。`git diff --check` も問題ありません。