メタ認知: 所見が1件だけという前提で対象を狭めすぎず、9出力箇所と検収処理自体を確認した。

## 結論

rev.1 は実装承認できない。計画自体の欠陥が3件ある。

## 計画自体の欠陥

### CR3-1 — cr3 allowlistとscope検査の比較開始点が両立しない

cr3の許可一覧は今回の6 probe＋6テストだけだが、scope検査は引き続き `BASE_COMMIT=ef995f0` を使う。[PLAN-cr3.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md:22) [allowlist.txt:2](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/allowlist.txt:2)

`scope-check.py` はその比較開始点からHEADまでの累積差分を検査する。[scope-check.py:12](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/scope-check.py:12)

指定条件での実測結果は終了値1だった。

```text
docs/ADOPTION.ja.md
docs/ADOPTION.md
skills/audit/SKILL.md
skills/audit/references/config-schema.md
tests/test_probe_record.py
tests/test_v014_contracts.py
scope_rc=1
```

いずれもcr2で正当に変更されたファイルであり、正しいcr3実装でもDoD (6) を満たせない。

推奨: cr3 scope検査の `BASE_COMMIT` を `79938a5` またはworker開始時点へ変更する。累積禁止ファイルは既存の個別 `git diff` で維持する。

### CR3-2 — 9 emitのうち3箇所が回帰テストを通らない

計画の新テストは各probeでU+2028入りbinを `not-installed` にするため、次の独立emitを実行しない。

- mdq成功: [mdq-index.sh:97](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:97)
- mdq失敗: [mdq-index.sh:103](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:103)
- ax成功: [ax-probe.sh:66](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:66)

既存の非ASCII正例はJSON往復だけを確認し、ASCII出力か、物理1行かを確認しない。[test_mdq_index.py:260](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:260) [test_ax_probe.py:207](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_ax_probe.py:207)

したがって、未検証箇所を `ensure_ascii = False` や変数経由のFalseにした誤実装は、文字列grepと全テストを通り得る。ax成功時のversionに非UTF-8バイトが含まれる経路も未検証である。

推奨: U+2028入りの実行可能stubでmdq成功・mdq失敗・ax成功も生成し、9 emitすべてについてASCII・物理1行・JSON往復を確認する。ax stubのversionには非UTF-8バイトも含める。

### CR3-3 — DoD (3)(4) に対応する検証処理がない

DoDは次を要求する。[PLAN-cr3.md:19](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md:19)

- `Ran N >= 609`
- `79938a5`以前の全テスト名を保持

しかし§8には件数比較も、基準commitとのAST比較もない。[PLAN-cr3.md:27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md:27) 新規6メソッド以外の既存テストを削除しても、残ったsuiteがgreenなら合格する。

さらに新規テストの実行回数は「各1回」という契約に対し `-ge 1` である。[PLAN-cr3.md:32](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md:32)

推奨: `79938a5` 基準のTestCase名包含と各IDの `... ok` 1回検査を§8へ再掲し、`Ran N` を数値で609以上と検査する。

## worker指示で吸収できる細部

### CR3-4 — surrogateescapeの期待値比較を明記すべき

非UTF-8 `CODEX_HOME` はPOSIXのsubprocess経由で再現できる。実測では、

```text
env_roundtrip True
rc 0
stdout_len 0
stderr_has_UnicodeEncodeError True
```

となり、現行不具合も再現した。ただしJSON復元後の値はbytesではなく `\udcff` を含む文字列になる。

推奨: テストでは `os.fsencode(out["callerCodexHome"]) == b"/tmp/h\xffome"` と比較するようworker指示に固定する。

## 再確認できた点

- 対象の `ensure_ascii=False` は実測9箇所。mdq disabled分岐の固定`printf`はbinを含まず、対象外で正しい。
- 既存の非ASCII正例・境界値テスト12本は実測green。
- `ensure_ascii=True` ではJSONがASCII化され、復元後の非ASCIIパスは元値と一致するため、`PYTHONIOENCODING=ascii` 契約を壊さない。
- U+2028は現行validation、base64、Bash変数を通過できる。テスト入力として成立する。

ファイル変更は行っていない。