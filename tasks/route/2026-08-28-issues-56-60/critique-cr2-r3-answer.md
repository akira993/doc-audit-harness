メタ認知: 収束を急がず、rev.3で追加された検証コード自体を誤判定の対象として確認した。probe本体より、比較基準と自動テスト発見条件に欠陥が残る。

## 結論

**rev.3 は差し戻し。実装承認しない。**  
probeの実装方針は概ね成立するが、cr1の回帰テストを保護できず、実行されないダミーテストでもDoDを通せる。

## (A) 計画自体の欠陥

### CR2-22 — 既存テスト保持の比較基準がPR #62実装前

既存 `test_*` 名の比較元は `ef995f0` である。[PLAN-cr2.md:96](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:96)

しかしcr1実装は `04a0624` であり、その間に次の回帰テストが追加されている。

- graph 3本の `test_control_character_bins_are_rejected_or_normalized_when_disabled`
- [test_v014_contracts.py:233](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:233) の `test_cr1_reopen_gate_and_status_order_contracts`
- [test_probe_record.py:174](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:174) の `test_context_normalization_and_display_controls_are_one_line`

実測では `test_probe_record.py` は `ef995f0` で8件、`04a0624` で9件、`test_v014_contracts.py` は9件から10件に増えている。特にC10は `test_cr1_reopen...` の修正を要求するのに、そのテストを削除してもAST検査が通る。[PLAN-cr2.md:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:35)

推奨: 既存テスト名の基準をcr2実装開始点 `04a0624` にし、意図的な統合改名だけ対応表で許可する。

### CR2-23 — 必須名が実行可能なテストかを検証しない

`names()` はファイル内の全 `FunctionDef` を集めるだけで、`unittest.TestCase` のメソッドかを確認しない。[PLAN-cr2.md:87](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:87)

必須名をモジュール直下や非TestCaseクラスへ置けばAST検査は合格するが、`unittest` は実行しない。全体件数Nも固定されていないため、対象0件でも見逃せる。[PLAN-cr2.md:68](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:68)

推奨: TestCase派生クラスのメソッドだけを検査し、verbose出力で必須の完全修飾テストIDが各1回実行されたことを確認する。

### CR2-24 — 正例4種・制御文字33種の実施を機械固定していない

DoDは正例4種を列挙するが、ASTが要求するのは `test_bin_positive_paths` という名前だけである。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)、[PLAN-cr2.md:79](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:79)

内部スペース1件しか実行しないテストでも通る。これはcr1で「テスト名はあるがsentinelと空白正例がない」状態を見逃した問題と同型である。

推奨: 各6ファイルで正例ID集合を4種完全一致、制御文字集合を `set(range(32)) | {127}` 完全一致でassertする。

### CR2-25 — 公開文書の「control-character」が実装範囲より広い

実装契約は拒否対象をASCII C0とDELに限定する。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)

一方、schemaとADOPTION案は無限定の `control-character`／「制御文字」と記す。[PLAN-cr2.md:27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:27)、[PLAN-cr2.md:28](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:28)

実測では内部のU+0080、U+0085、U+009FはいずれもUnicode上の制御文字だが、`strip()`・C0/DEL検査・UTF-8変換を通り有効になる。文書は拒否、実装は受理となる。

推奨: 公開文を `ASCII control character (U+0000–U+001F or U+007F)` とその和訳に限定する。

### CR2-26 — config-schema更新がDoDに束縛されていない

PLANは6 seamの新境界条件とdisabled出力3形をschemaへ記録する。[PLAN-cr2.md:27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:27)

しかしDoD (1)〜(9) と§8にschema内容の検査がない。現行テストも4 seamについて一般的な `enabled`／`invalid-config`／absent句を見るだけで、graph 3行、新しい空白・UTF-8条件、disabled出力差を検証しない。[test_v014_contracts.py:135](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:135)

旧schemaのまま、または一部だけ変更しても全DoDを通る。

推奨: 6 seam各行について境界条件句とseam別disabled句を完全一致で固定する。

### CR2-27 — return後検査が複合ブロック内を見ない

AST検査は `FunctionDef.body` 直下だけを走査する。[PLAN-cr2.md:90](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:90)

次は検出できない。

```python
def helper():
    with resource:
        return value
        write_fixture()  # 到達不能だが検査を通る
```

`if`、`with`、`try`、ループ内でも同じである。

推奨: 全てのstatement-listを再帰的に走査して、各ブロック内の無条件終了文以降を拒否する。

## (B) worker 指示で吸収できる細部

### CR2-28 — sentinel fixtureの成立条件を明示していない

DoDは負例でsentinel不起動を要求するが、CLI 3本について「どの実行ファイルがmarkerを書くか」が固定されていない。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)

単に未使用のmarkerパスを用意するだけなら、検査は常に成功する。reasonと出力形のassertがあるため差し戻し級ではないが、sentinel自体の判別力は弱い。

推奨: 既定名stubをPATHに置いてmarkerを書かせ、invalid/disabled全負例でmarker不変を確認する。

## 新規指摘なしと判断した点

- `command -v -- "$BIN"` と後続の `"$BIN" ...` はBash 3.2で整合する。
- UTF-8バイト直書きはgraphの `read -r STATE BIN`、CLIのbase64経路とも値を保持する。
- disabled出力の3形、Codex 2回・他5本1回、seam別出力キーは整合した。
- `bin_nul` と33文字走査中のNUL重複は役割が異なり問題ない。
- ADOPTION期待段落の英日生成、CM合成文の完全一致、scope検査には新規欠陥なし。
- 新しいセキュリティ上の注入・外部書込み経路は見つからなかった。