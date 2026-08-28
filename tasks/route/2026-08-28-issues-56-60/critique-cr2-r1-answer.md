メタ認知: 15件の所見を個別に直す発想へ引っ張られやすく、「6 probe 共通化」が既存契約を壊す点を見落としやすい。テストが green であることも健全性の証明とは扱わない。

## 結論

**rev.1 は差し戻し。実装承認しない。**  
A2 の状態分割そのものは `make_rebind()` の到達可能な組合せを覆うが、状態分類に1件の誤りがある。B5 は既存の出力形・互換性・テスト計画との矛盾が複数残る。

## (A) 計画自体の欠陥

### CR2-1 — `ref-invalid` は Codex 実行済み状態ではない

PLAN は `unknown/non-null` で `{completed, execution-failed, ref-invalid}` に caller 情報欠損の接尾辞を付け、「Codex が実行を試みた枝のみ」と説明する。[PLAN-cr2.md:16](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:16)

しかし `ref-invalid` は baseline 不正により `action:"skip"` を返す実行前の分岐である。[codex-review-plan.py:41](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:41)

影響: 実行していない run に `caller info unavailable` が付き、説明と表示が食い違う。

推奨: 接尾辞対象を `{completed, execution-failed}` のみにする。

### CR2-2 — A2 の DoD は5行表の排他条件を検証しない

`make_rebind()` は probe 有りを `complete`、無しを `unknown` とし、`reviewState` だけ独立して残す。[probe-record.py:279](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279) 既存テストが固定する部分状態は `unknown + completed` の1例だけである。[test_probe_record.py:190](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:190)

DoD (1) は文言と順序だけなので、例えば `reviewState=null` を `state=unknown` 判定より先に評価する誤実装でも、必要文言を残せば通り得る。[PLAN-cr2.md:48](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:48)

推奨: 5行の左辺条件を完全一致で固定し、`unknown + 非null` の6状態について表示・reason・接尾辞の有無を表で検査する。

### CR2-3 — `mdq` の disabled 出力形と「6 probe 統一」が矛盾する

PLAN は `enabled:false` 時に「出力 bin を既定名に」と6本共通で定義する。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)

一方、既存 `mdq` の disabled 出力は `bin` キーを持たない。[mdq-index.sh:55](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:55) テストも `{mdqAvailable, reason}` を完全一致で固定している。[test_mdq_index.py:179](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:179)

影響: `bin` を追加すれば既存 JSON 消費者を壊し、追加しなければ schema の統一文が虚偽になる。

推奨: `mdq` の disabled 出力は従来どおり `bin` 無しとする例外を明記する。

### CR2-4 — graph 3 probe の正当な disabled bin まで既定名へ変わる

現行 graph 3 probe は `enabled:false` でも、妥当なカスタム `bin` はそのまま出力する。[codegraph-probe.sh:40](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:40)、[graphify-probe.sh:44](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:44)、[cocoindex-probe.sh:46](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:46)

PLAN は妥当な値まで常に既定名へ変更するが、その互換性変更は15所見の修正に必要ない。DoD にも `enabled:false + valid custom bin` がない。

推奨: 既定名への置換は「disabled かつ bin が不正」の場合だけに限定する。

### CR2-5 — CLI 3 probe では「6本共通契約」を証明できない

共通条件には全33個の ASCII 制御文字、UTF-8不能文字、disabled 先勝ち、内部スペース正例が含まれる。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)

しかし CLI 3本の DoD は既存20 IDに空白・空白のみ・dashの3件を加えるだけで、既存の制御文字検査は NUL 1件だけである。[PLAN-cr2.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:49)、[test_mdq_index.py:125](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:125)

また同じ DoD の「すべて sentinel 不起動」は、直前の「内部スペース正例では stub が起動」と自己矛盾する。

実測では現行 CLI 3本へ lone surrogate を入れると、Python の例外後に `rc=0`、`reason:not-installed`、空 `bin` となり、共通契約を満たさない。

推奨: CLI 3本にも graph と同じ境界値表を適用し、invalid/disabled は不起動、内部スペース正例は起動1回と期待を分ける。

### CR2-6 — UTF-8判定後の出力が環境依存

graph の計画は `.encode("utf-8")` 成功後に通常の `print` を使う。[PLAN-cr2.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:23) しかし `PYTHONIOENCODING=ascii` では、UTF-8にできる `é` や日本語も `print` で失敗する。

CLI 側も base64 復号後に通常の `print` を使うため同じ問題がある。[mdq-index.sh:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:49)

影響: 正当な非ASCII実行パスが、環境によって invalid または出力不能になる。

推奨: 伝送箇所はUTF-8バイトを標準出力へ直接書き、ASCII出力環境下の非ASCII実行パス正例を6本すべてで検査する。

### CR2-7 — UTF-8不能条件が公開仕様から欠落する

実装条件には「UTF-8にエンコード可能」があるが、予定する schema 文と ADOPTION 文には列挙されていない。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)、[PLAN-cr2.md:25](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:25)

実測:

```text
json.loads('"\\ud800"') → lone surrogate を受理
.encode("utf-8") → UnicodeEncodeError
```

したがって実際の設定ファイルから到達可能である。

推奨: schema と ADOPTION 英日双方に「UTF-8へ符号化不能」を明記する。

### CR2-8 — 既存の改行入り `bin` 正例が新契約と直接衝突する

既存テストは改行を含む Codex 実行ファイルを作り、利用可能かつ値が完全一致することを要求する。[test_codex_probe.py:233](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py:233)

新契約では改行は制御文字として `invalid-config` になる。PLAN はこのテストの移行方法を定めていないため、worker が単に削除・弱体化してもフルスイートを通せる。

推奨: 同テストの `bin` は引用符・バックスラッシュ・内部スペースだけの正例に替え、改行拒否は sentinel 付き負例へ移すと明記する。

### CR2-9 — leading `-` の全面禁止は不要な互換性回帰

実測した Bash 3.2.57 では次の結果だった。

```text
command -v "-v"       → rc 0（誤判定）
command -v -- "-v"    → rc 1
```

つまり所見 #10 の原因は option 終端を付けていないことであり、`bin` 自体を一律禁止する必要はない。`-dir/tool` のような既存値まで invalid になる。[PLAN-cr2.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:22)

推奨: `command -v -- "$BIN"` に変更し、leading `-` の禁止を契約から外す。

### CR2-10 — ADOPTION の検査が同一段落内の余分な改変を許す

§8 の検査は変更行に見出し文字列が含まれることしか見ない。[PLAN-cr2.md:70](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:70) §7 は1物理行なので、その行の別文変更や余分な第8文も通る。

既存契約テストも期待文の包含と合計数だけで、段落全体の一致を要求しない。[test_v014_contracts.py:40](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:40)

推奨: `ef995f0` の段落へ指定した句変更と第7文追加だけを施した期待値を生成し、段落全体を完全一致させる。

### CR2-11 — A1 の検査は「exactly 3 keys」を証明しない

A1 はJSONの3キー・真偽値/nullの型・余分キー無しを要求する。[PLAN-cr2.md:8](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:8)

一方、DoD は3キー名の literal 存在だけで、§8 は `contextModeAvailable` が1回以上あるかしか見ない。[PLAN-cr2.md:48](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:48)、[PLAN-cr2.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:67)

文字列 `"false"`、余分キー、別段落へのキー名追加でも合格する。

推奨: Phase 0 の合成文を抽出し、3キー・値型・余分キー無しを完全一致で検査する。

### CR2-12 — DoD (8) は今回と同じ見落としを機械的に防がない

DoD 冒頭は「すべて非0終了で判定」とするが、(8) は人間の精読だけで終了値を持たない。[PLAN-cr2.md:47](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:47)、[PLAN-cr2.md:55](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:55)

実測では、現在の到達不能な `write()` と迷子の assert を残したまま対象35テストが green になる。さらにフルスイート用コマンドは `Ran N` を表示するだけで、件数を検査していない。[PLAN-cr2.md:64](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:64)

推奨: 変更テストの必須メソッド名集合と、無条件 `return` 後の文を拒否する機械検査を DoD に追加する。

## (B) worker 指示で吸収できる細部

### CR2-13 — `test_probe_record` が dangling symlink を残す

`TemporaryDirectory` 化後も、その兄弟に `self.root + "-link"` を作るが cleanup がない。[test_probe_record.py:221](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:221) 監査対象ロジックには影響しないが、テスト終了後に壊れたリンクが残る。

推奨: symlink 作成直後に `addCleanup(os.unlink, link)` を登録する。

## 判定補足

- C7 の corpus 復元と専用存在検査、C8 の `gitignoreOk` を元メソッドへ戻す方針自体は妥当。
- `git diff ef995f0 -- tests/` の変更8ファイルを確認した範囲では、申告済み2件以外の到達不能文・迷子 assert は見つからなかった。ただし CR2-8 の既存 fixture 衝突と CR2-13 の後始末漏れが残る。
- セキュリティ上の新しい書き込み経路・注入経路は、この修正計画には見つからなかった。