完了。R2のA-1〜C-7をすべて修正し、最終全件検査は713件すべて成功しました。

## 完了条件の実測

1. 全件検査

```text
Ran 713 tests in 304.922s

OK
```

スキップ・失敗なし。既存 `tests/test_generic_layers.py` から未閉鎖ファイルの `ResourceWarning` が複数出ましたが、検査結果は成功です。事前基線は前ラウンド実測の `Ran 655 tests / OK`、boss追認時は697件でした。

2. CT-1

```text
call sites 22／exempt 3／getters 13／scripts 21／observers 19
```

期待値 `N=22／M=3／G=13／K=21／O=19` と一致。

3. CT-2

```text
対象 21 本を検査
```

21本すべてに一致・不一致の対を検査。mismatch exit値はregistryから取得します。

4. `json.load(open` 残存

shellは0件。SKILLは封印前の免除1件のみです。

```text
skills/audit/SKILL.md:14:Also bind `ANCHOR_PATH="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("anchorPath",""))' "$CFG")"` for the run lifecycle and Phase 5.
```

5. `"$CFG"` 残存

指定された免除3行のみです。

```text
14: ANCHOR_PATH=...
25: import-audit-scope.py --check
733: decide-verdict.py
```

6. 構文検査

- `python3 -m py_compile skills/audit/scripts/*.py`: exit 0
- `bash -n skills/audit/scripts/*.sh`: exit 0

7. 版・ハッシュ

`test_engine_shas_match_current_generated_bodies` を含むscaffold検査:

```text
Ran 21 tests in 0.694s

OK
```

`0.15.1` のソース上の残存は、英日ADOPTIONの履歴節・旧版更新経路、`engine-shas.json` の過去版entry、旧版引き渡し検査のみです。加えて、検査で生成された `tests/__pycache__` 2件と既存 `.mdq` 索引にも一致しました。

8. 指定個別検査

```text
Ran 16 tests in 12.630s

OK
call sites 22／exempt 3／getters 13／scripts 21／observers 19
対象 21 本を検査
```

```text
Ran 9 tests in 0.433s

OK
```

## R2対応内容

- A-1: `--repo-root` を必須化し、carry-forwardの実在判定に使用。SKILLの呼び出しも更新。
  - 該当: [codex-review-plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:83)、[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:611)、[test_codex_review_plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:180)
  - 検証: repo外cwdから実在ファイルを正しくcarry-forwardする検査が成功。

- A-2: impact-supplementの3プレースホルダを、封印済みgetterから得た実変数に置換。
  - 該当: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:398)
  - 検証: CT-1、CT-7、全件検査。

- A-3: seal-runのexit 7／`sealed-config-mismatch` はreleaseせず、config taint停止規約へ流すと明記。
  - 該当: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:447)、[test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:634)
  - 検証: CT-3が段落順序と分岐内の除外を検査。

- A-4: harness getterを`--default null`にし、`null`時のみ`HARNESS_STATE=unset`と定義。
  - 該当: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:284)
  - 検証: CT-1 getter registryとCT-4b。

- B-1: 直接起動probeの不正・欠落・省略configをexit 2／JSONなし、封印不一致をexit 7と英日文書・SKILLに反映。
  - 該当: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:95)、[ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:276)、[ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:249)
  - 検証: probe直接起動契約12件、CT-2、全件検査。

- B-2: scripts-only部分コピー手順を削除し、tree全体同期だけを残した。
  - 該当: [ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:249)、[ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:226)
  - 検証: CT-7文書契約。

- C-1: 保持上限/source guard、501件切詰め、退化再構築、round-trip失敗、容量境界、unresolved数、4キーflip差異の7検査を追加。
  - 該当: [test_v016_phase4_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_phase4_contracts.py:99)
  - 検証: `Ran 7 tests in 20.916s / OK`。
  - 併せてhistory parserのwarningが上書きされる実装欠陥を修正: [decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1121)。

- C-2: 二重永続化障害、不正last-run、release markerマージ、flock保持、既存lock時のhistory不変を追加。
  - 該当: [test_wp12_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_wp12_contracts.py:239)
  - 検証: `TestOpenRun` 19件、CT-4cとも成功。

- C-3: 別fdがflock保持中のtaintを無書込みexit 3として検査。
  - 該当: [test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:715)
  - 検証: CT-3b成功。

- C-4: gate子プロセス直前のconfig差し替えを再現し、`config-changed` taintとacceptance要求を検査。
  - 該当: [test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:642)
  - 検証: CT-3成功。

- C-5: history SHA不一致→taint→隔離→次run cold startの連鎖を追加。
  - 該当: [test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:944)
  - 検証: CT-6成功。

- C-6: 5文書を個別token表で検査し、日英のdata-only条件を対称化。
  - 該当: [test_v016_docs_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_docs_contracts.py:13)、[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:140)
  - 検証: 文書契約検査成功。

- C-7: CT-2のmismatch exitをregistry列から取得。
  - 該当: [test_v016_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:224)
  - 検証: CT-2成功。

途中の対象検査では、C-4の差し替え時点とA-3の改行契約に各1回失敗し、原因を修正後に再実行して成功しました。また誤ったunittestメソッド名を1回指定して`AttributeError`になりましたが、正しい対象名で成功を確認しています。最終指定検査・全件検査には失敗もスキップもありません。

PLANとの食い違い、新たな未裁定判断、許可外ファイルの変更が必要な箇所はいずれもありません。git操作は行っていません。

## `git diff --stat`

bossがステージした既存実装に対する今回の未ステージR2差分:

```text
 docs/ADOPTION.ja.md                       |   6 +-
 docs/ADOPTION.md                          |   6 +-
 skills/audit/SKILL.md                     |  56 +++++---
 skills/audit/references/config-schema.md  |   2 +-
 skills/audit/scripts/codex-review-plan.py |   3 +-
 skills/audit/scripts/decide-verdict.py    |   4 +-
 tests/test_codex_review_plan.py           |  35 ++++-
 tests/test_v014_contracts.py              |  11 +-
 tests/test_v015_contracts.py              |   4 +-
 tests/test_v016_contracts.py              | 213 +++++++++++++++++++++++++++---
 tests/test_v016_history_common.py         |   3 +
 tests/test_wp12_contracts.py              | 130 ++++++++++++++++++
 12 files changed, 421 insertions(+), 52 deletions(-)
```

新規の [test_v016_docs_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_docs_contracts.py) と [test_v016_phase4_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_phase4_contracts.py) は、git操作禁止のため未追跡のままです。ステージ済み本体は `56 files changed, 2936 insertions(+), 418 deletions(-)` です。