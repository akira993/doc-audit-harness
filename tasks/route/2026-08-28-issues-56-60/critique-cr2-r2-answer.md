メタ認知: 「反映済み」という自己申告に引っ張られず、実際の既存分岐と検証コードを基準にした。特に共通化が既存差異を消していないかを疑った。

## 結論

**rev.2 は差し戻し。実装承認しない。**  
`command -v --` とUTF-8バイト伝送の方式は成立するが、既存契約との不一致とDoDの判別力不足が残る。

## (A) 計画自体の欠陥

### CR2-4 対応不十分 — disabled時の妥当なカスタムbinは6本共通の現行挙動ではない

PLAN は6本すべてについて、`enabled:false` でも妥当なカスタムbinを保持し、「現行挙動維持」とする。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)

実際の現行契約は3種類に分かれる。

- mdq: `bin` キーなし。[mdq-index.sh:55](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:55)
- ax/codex: `enabled:false` をbin読取りより先に判定するため、妥当なカスタム値でも既定名。[ax-probe.sh:35](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:35)、[codex-probe.sh:36](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:36)
- graph 3本: 妥当なカスタム値を保持。[codegraph-probe.sh:40](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:40)

DoDどおり実装すると ax/codex の既存JSON値が黙って変わる。

推奨: 検証条件だけを共通化し、disabled時の出力値は上記既存3形を維持する。

### CR2-11 対応不十分 — CM検査は値型・位置・一意性を検証しない

§8 はSKILL全体から最初の類似オブジェクトを探し、英字だけのキー名を抽出する。[PLAN-cr2.md:73](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:73)

次の誤実装でも通る。

- Phase 0外に正しい囮を置く
- 値を `"false"` や `"null"` にする
- 同じliteralを複数置く
- `"extra_key"` のような英字以外を含む余分キーを加える

A1が要求する未引用のboolean/nullを証明していない。[PLAN-cr2.md:8](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:8)

推奨: Phase 0だけを抽出し、A1の合成指示全文がちょうど1回、完全一致することを検査する。

### CR2-14 — Codex正例の「stub 1回起動」は正しい実装を落とす

DoDは6本すべての正例でstubを1回起動すると定める。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)

Codex probeは正常確認で必ず2回実行する。

1. `"$BIN" --version`
2. `"$BIN" exec --help`

根拠: [codex-probe.sh:81](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:81)

影響: 正しい実装が失敗するか、検査を通すために `exec --help` を削る回帰を誘発する。

推奨: Codexは2回の引数列完全一致、他5本は1回と分ける。

### CR2-15 — `command -v --` の修正を識別するテストがない

PLANは先頭`-`を許可するが、DoDの正例にはその値がない。[PLAN-cr2.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:23)、[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)

したがって、いずれかのprobeに旧 `command -v "$BIN"` が残る、または先頭`-`を再び拒否しても全計画テストが通る。

推奨: PATH上の`-x` stubについて、6本すべてで検出から所定の後続呼出しまで成功する正例を追加する。

### CR2-16 — 必須テスト名をファイル別に検証していない

DoDは3種類のテストを6 probeそれぞれに要求するが、AST検査は全ファイルのメソッド名を一つの集合へ潰す。[PLAN-cr2.md:58](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:58)、[PLAN-cr2.md:85](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:85)

実測では現HEADの `test_output_key_sets_per_branch` はCLI 3ファイルにしか存在しないが、この名前については既に集合条件を満たす。また、本文で要求する `test_disabled_by_config` は検査リストから欠落している。

推奨: `テストファイル → 必須メソッド名集合` の対応表で各ファイルを個別検査する。

### CR2-17 — 既存テストの削除を検出できない

フルスイートは終了値とskip 0だけで、`Ran N` のNを検査しない。[PLAN-cr2.md:68](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:68)

許可された8テストファイルから既存テストを削っても、新規必須名が数個残ればAST検査とフルスイートは通る。今回の起点である「テスト差分の見逃し」を人手精読だけに再度依存している。

推奨: `ef995f0` の各対象ファイルにある既存 `test_*` 名集合が実装後も包含されることを機械検査する。

### CR2-18 — CLI 23 IDは件数だけで既存20 IDの維持を証明しない

現行CLI 3本は20 IDの名前集合を直接固定している。[test_mdq_index.py:125](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:125)、[test_ax_probe.py:88](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_ax_probe.py:88)、[test_codex_probe.py:105](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py:105)

rev.2のDoDは追加3名と `len(CASES)==23` しか固定しない。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52) 既存IDを落として別名を足す、または3ファイル間で集合が異なっても通る。

推奨: 既存20 ID＋追加3 IDの正確な集合をCLI 3ファイルそれぞれで完全一致させる。

### CR2-19 — 日本語ADOPTIONの生成規則が本文と検査で矛盾する

本文は⑦を「1スペース区切り」で追加すると定める。[PLAN-cr2.md:29](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:29)

しかし日本語の `tail` には先頭スペースがなく、検査は `exp.rstrip()+tail` なので、期待値は次になる。[PLAN-cr2.md:95](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:95)、[PLAN-cr2.md:105](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:105)

```text
…（POSIX パスのみ）。symbolGraph / docGraph / …
```

本文どおり空白を入れた正しい実装は検査で落ちる。

推奨: 言語別の区切り文字を明示し、生成コードも同じ値を使う。

### CR2-20 — ADOPTIONが whitespace-only の互換性変更を明示しない

実装契約とschemaは `whitespace-only` と `whitespace-padded` を別条件としている。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)、[PLAN-cr2.md:27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:27)

一方、ADOPTION英語置換句は `whitespace-padded` だけである。[PLAN-cr2.md:28](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:28) `"   "` が新たに `invalid-config` になることが移行文から判別できない。

推奨: ADOPTION英日とも `whitespace-only` を独立条件として明記する。

## (B) worker 指示で吸収できる細部

### CR2-21 — 正例の出力キー表記がmdqに当てはまらない

DoDは6本すべてで `<seam>Bin` 完全一致と書くが、mdqの正例キーは `mdqBin` ではなく `bin` である。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)、[mdq-index.sh:94](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:94)

推奨: 6本の実際の出力キーを対応表でworker指示に固定する。

## 実測上、指摘なし

- Bash 3.2.57で `command -v --` は動作し、PATH上の先頭`-`名も後続の `"$BIN" --version` 等ではコマンド名として実行できる。
- `sys.stdout.buffer` からのUTF-8直書きは、graph側の `read -r STATE BIN` で非ASCIIと連続内部空白を保持した。
- CLIのbase64復号からバイト直書き、コマンド置換まで値を保持した。末尾改行は除去されるが、末尾空白・制御文字は事前拒否対象なので契約上問題ない。
- 既存 `bin_nul` と33文字走査中のNULは重複してよい。前者は既存20 IDの回帰固定、後者は全制御文字の網羅検査で役割が異なる。
- ADOPTIONの基準となる2置換句は、英日とも `ef995f0` 内で各1回であり、その部分は一意。
- 新しいセキュリティ上の注入・外部書込み経路は見つからなかった。