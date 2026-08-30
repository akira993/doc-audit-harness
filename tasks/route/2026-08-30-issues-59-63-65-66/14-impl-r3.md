完了。R3-1／R3-2を修正し、最終フルスイート716件が成功しました。git操作は行っていません。

## R3-1

対応内容:

- 7本のshell消費者で、config JSONを単一引数ではなくstdin経由でPythonへ渡すよう変更。
- config解析処理が非0終了した場合は、stderrへ固有メッセージを出してexit 2。
- mdqのdecision／roots、compute-baselineの3処理すべてに適用。
- NUL区切りが必要なcodegraphは一時ファイル経由とし、後片付けを設定。
- 300 KiB超の有効な`impactMap`を持つconfigで、7本すべてが一致SHA・exit 0・JSON objectを返す検査を追加。

該当箇所:

- [ax-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:32)
- [codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:33)
- [codegraph-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:33)
- [graphify-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:38)
- [cocoindex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:40)
- [mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:33)
- [compute-baseline.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:33)
- [test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:365)

検証:

```text
Ran 17 tests in 13.526s

OK
call sites 22／exempt 3／getters 13／scripts 21／observers 19
対象 21 本を検査
```

既存probe／mdq／compute検査も担当側実測で:

```text
Ran 129 tests in 123.975s

OK
```

`sealed_config.py --print`は各shellで引き続き1回です。shell内の`json.load(open`は0件です。

## R3-2

対応内容:

- `load_sealed_config(..., with_signature=True)`を追加。
- configを読んだ同一fdの`os.fstat`から`(st_ino, st_size, st_mtime_ns)`を返却。
- fdと`os.lstat(path)`のinode不一致・パス消失を`SealedConfigMismatch`として処理。
- gateは返却された署名を使い、読取後の別statを廃止。
- 読取完了直後に同一内容・別inodeへ交換する競合を再現し、`REFUSED`／`config-changed`／taint／acceptance要求を検査。

該当箇所:

- [sealed_config.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/sealed_config.py:29)
- [decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:939)
- [test_sealed_config.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_sealed_config.py:47)
- [test_decide_verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py:49)

検証:

```text
Ran 10 tests in 0.444s

OK
```

```text
Ran 1 test in 0.545s

OK
```

担当側では`tests.test_decide_verdict`全73件も成功しています。

## 最終検証

```text
Ran 716 tests in 304.367s

OK
```

失敗・スキップなし。既存`tests/test_generic_layers.py`由来の`ResourceWarning`は出ていますが、R3対象外の既知警告で、結果は成功です。

- Python構文検査: exit 0
- shell構文検査: exit 0
- `git diff --check`: exit 0
- PLANとの不一致・新たな未裁定判断: なし
- 許可外ファイルの変更: なし

`git diff --stat`:

```text
 skills/audit/scripts/ax-probe.sh         |  9 ++++--
 skills/audit/scripts/cocoindex-probe.sh  | 10 ++++--
 skills/audit/scripts/codegraph-probe.sh  | 17 +++++++++--
 skills/audit/scripts/codex-probe.sh      |  9 ++++--
 skills/audit/scripts/compute-baseline.sh | 19 +++++++++---
 skills/audit/scripts/decide-verdict.py   |  4 +--
 skills/audit/scripts/graphify-probe.sh   | 10 ++++--
 skills/audit/scripts/mdq-index.sh        | 19 ++++++++----
 skills/audit/scripts/sealed_config.py    | 23 +++++++++++---
 tests/test_decide_verdict.py             | 52 ++++++++++++++++++++++++++++++++
 tests/test_sealed_config.py              | 11 +++++++
 tests/test_v016_contracts.py             | 28 +++++++++++++++++
 12 files changed, 178 insertions(+), 33 deletions(-)
```