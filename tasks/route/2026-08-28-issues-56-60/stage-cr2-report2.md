差し戻し6点を修正し、全検査が成功しました。コミットは行っていません。

### 変更内容

- [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:646)
  - 指定された共通規則文へ置換。
  - `PROBE_REBIND` 直後の独立段落として1回だけ配置。

- graph 3 probe テスト
  - 固定された全 reason を実際に生成し、reason 集合とJSONキー集合を完全一致で検査。
  - codegraph 6種、graphify 6種、cocoindex 8種。

- 6 probe の正例テスト
  - stub の起動回数と引数列を検査。
  - `dash_name` は PATH 上の相対名 `-x` を使用。
  - 呼び出し期待値：
    - mdq: `index --root .`
    - ax: `--version`
    - codex: `--version`、`exec --help`
    - codegraph: `init .`
    - graphify: `update .`
    - cocoindex: `index`

- 6 probe の境界値テスト
  - 既定名、負例値そのもの、空白除去後名の sentinel を作成し、全 marker の不変を検査。
  - `enabled:false`＋妥当カスタム bin の3種類の出力も固定。
  - graph 3本の一時領域を自動後片付け方式へ変更。

### 検証結果

対象テストと既存契約テスト：

```text
Ran 142 tests in 50.554s

OK
```

フルスイート：

```text
Ran 603 tests in 187.252s

OK
```

§8 の機械検査：

```text
tests-ast-clean
forbidden-clean
scope-clean
adoption-paragraph-clean
```

6 probe の文法検査と `git diff --check` も成功しました。skip、expected failure、unexpected success はありません。

### PLAN との乖離

無し。許可外ファイルの変更、`tasks/**` の変更、コミットは行っていません。既存の未追跡 `.claude/` にも触れていません。