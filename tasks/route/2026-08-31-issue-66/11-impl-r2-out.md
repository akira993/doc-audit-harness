R2-1を修正しました。レビュー開始前の再開ではPhase 4到達時に通常起動し、開始後に中断されたcheckpoint行(g)だけを`not-run`に固定します。

変更は次の2ファイルのみです。

- [skills/audit/SKILL.md:595](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:595)
- [tests/test_v015_contracts.py:214](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v015_contracts.py:214)

旧文言は0件。重点検査9件も`OK`でした。git操作は行っていません。

補助的なSKILL構造検査は、環境に`yaml`部品がないため従来どおり実行不能でした。必須のフルスイートは成功しています。

```text
Ran 739 tests in 322.597s

OK
```