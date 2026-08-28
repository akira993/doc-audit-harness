# 結論

**rev.1 のまま実装開始すべきではありません。**  
特に #59 は、計画どおりの正常実装でも gate が REFUSED になるうえ、失敗した run の情報を後続 run へ残す設計です。これは担当者の実装上の工夫では吸収できません。

確認済み前提は HEAD `dfdb8a9`、tracked 差分なし、`?? .claude/` です。`gh issue view 56..60` は GitHub 接続不可で全件失敗したため、Issue 本文との直接照合だけは未実測です。また PLAN の「551 tests OK」と [investigate-report.md:172](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/investigate-report.md:172) の「一時領域を作れず多数 error」は測定環境が異なる可能性があり、現環境では基準テスト成功を再確認できません。

## 指摘

### R1-1 — Critical・バグ回帰 — ledger は実際には内容照合の除外対象ではない

PLAN は ledger を「digest 除外済み」としていますが、固定除外一覧に新しいファイルはありません。[PLAN.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:80)、[start-run.py:18](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:18)、[start-run.py:253](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:253)

封印後に `record` が ledger を作成・更新すると、gate の再計算で作業内容不一致になります。[decide-verdict.py:800](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:800)、[decide-verdict.py:904](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:904)。しかも除外一覧を持つ `start-run.py` は変更許可範囲外です。[PLAN.md:207](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:207)

**推奨:** ledger 更新を gate の最終確認後・lock 保持中の状態更新処理へ統合し、必要な `start-run.py`／`decide-verdict.py` の変更を許可するよう設計し直す。

### R1-2 — Critical・セキュリティ — REFUSED run の ledger が後続 run に残る

PLAN は Codex 完了直後、gate 呼出し前に ledger を永続化します。[PLAN.md:94](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:94)。しかし gate が排他的な保持を開始し、HEAD・設定・作業内容を検証するのは後です。[decide-verdict.py:658](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:658)、[decide-verdict.py:904](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:904)

そのため後で REFUSED になっても ledger は残り、次回へ取り込まれます。これは「汚染された永続状態を後続 run へ持ち越さない」という既存契約と正面衝突します。[SKILL.md:772](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:772)

**推奨:** ledger の更新候補は run dir 内に置き、gate が成功する場合だけ最終確認後に永続領域へ確定する。

### R1-3 — Critical・セキュリティ — 汚染 ledger が gate の入力を間接的に減らせる

PLAN の「汚染で抑止できるのは non-blocking のみなので CONSISTENT は偽造できない」は保証できません。[PLAN.md:99](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:99)

有効な JSON の ledger を改変し、既知の high 所見を medium として登録すれば、プロンプトは「再報告するな」と指示します。その結果が出力から消えれば、gate は今回の `phase4.json` しか見ないため検出できません。[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:83)、[decide-verdict.py:894](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:894)

実際にモデルが抑止されるかは確率的ですが、**「偽造不能」という安全保証が成立しないことは確定**です。

**推奨:** プロンプトから抑止命令を除き、Codex は毎回独立に全所見を返し、既知 non-blocking の表示上の重複排除だけを結果取得後に決定的処理する。

### R1-4 — High・セキュリティ — path/title 注入とリポジトリ外アクセスが未防御

現行 schema は `file` と `title` に「空でない文字列」しか要求しません。[codex-review-output.schema.json:12](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/codex-review-output.schema.json:12)。改行、制御文字、命令文、`../`、外部絶対パスを許したまま、PLAN は次回プロンプトへ verbatim で挿入します。[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:83)

また `--ledger L` の保存先を固定パスへ限定せず、親ディレクトリや最終ファイルのリンク拒否もありません。中間ディレクトリがリンクなら、一時ファイル＋置換でもリポジトリ外へ書けます。

**推奨:** `file` は既存 `validate_repo_path` 相当で通常ファイルだけを許し、title/file の改行・制御文字・長さを制限し、保存先は repo root から内部計算した固定パスをリンク不追跡で扱う。

### R1-5 — High・バグ — 「結果に無い＝解決済み」は成立しない

PLAN は carry した blocking が今回の出力に無ければ削除します。[PLAN.md:90](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:90)。一方、差分レビューの範囲は基準点から HEAD の差分と影響文書です。[SKILL.md:549](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:549)

範囲外、出力打切り、単なるサンプリング漏れでも「解決済み」と誤認します。これは #59 が解消しようとする再現性問題を再導入します。

**推奨:** carried entry ごとに `still-present`／`resolved`／`out-of-scope` を出力 schema で明示し、検査範囲内で明示的に `resolved` となったものだけ削除する。

### R1-6 — High・バグ — key 衝突と trim が blocking を消す

file を `casefold()`・空白正規化すると、大文字小文字を区別する環境の `Docs/A.md` と `docs/a.md`、空白数の異なるファイル名が衝突します。[PLAN.md:88](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:88)

さらに最大500件の trim は severity を考慮しないため、大量の medium/low により古い blocking が削除され、「blocking は毎回再検証」が破れます。[PLAN.md:92](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:92)

**推奨:** file は検証済み相対パスを大小・空白そのままで key 化し、blocking は trim 対象外とする。

### R1-7 — High・バグ — #58 の symlink root 対応は計画どおりには動かない

`safe_path` の前に repo root は既に `realpath` 化されています。[import-audit-scope.py:551](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:551)。したがって `safe_path` 内で `abspath(repo)` と `realpath(repo)` を比べても同じ値になり、元の `/tmp` や symlink root の表記は復元できません。

DoD (1) の symlink root 経由 exit 0 と矛盾します。

**推奨:** 入力された見かけ上の root と実体確認用 root を別々に保持して `safe_path` へ渡す仕様に変更する。

### R1-8 — High・セキュリティ — #58 の `normpath` が `..` 拒否を迂回する

既存検査は `..` 成分を明示的に拒否します。[docaudit_paths.py:43](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:43)。しかし PLAN は先に `normpath` します。

実測:

```text
input=/repo/sub/../.claude/doc-audit.json
normpath=/repo/.claude/doc-audit.json
prefixMatch=True
relpath=.claude/doc-audit.json
```

`<root>/../x` のテストだけでは、repo 内へ戻る `..` を検出できません。

**推奨:** 正規化前の絶対パス成分を検査し、`.`・`..`・空成分を含む入力を先に拒否する。

### R1-9 — Medium・回帰 — mdq のキー集合前提が現行契約と矛盾する

PLAN は全分岐を `{mdqAvailable,reason,bin}` に揃えるとしていますが、現行は成功時 `dbDir`、索引失敗時 `rc` を返し、無効化時は `bin` がありません。[mdq-index.sh:46](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:46)、[mdq-index.sh:85](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:85)

既存テストも `dbDir` と `rc` を固定しています。[test_mdq_index.py:63](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:63)

**推奨:** 共通必須キーと理由別追加キーを分け、`dbDir`／`rc` を維持する契約へ書き直す。

### R1-10 — High・バグ — #57 の再開情報では Phase-5 を復元できない

保存対象は9 seam、表示行は7本です。特に mdq は `indexing`／`mdqHealth`／`mdqDegrade` の3件を1行へまとめますが、部分欠落時の優先順位がありません。[PLAN.md:70](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:70)、[SKILL.md:668](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:668)

さらに codex-review 行は Phase-0 availability ではなく、Phase-4 の `completed` 等で分岐します。[SKILL.md:684](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:684)。`phase0-probes.json` だけでは復元できず、ledger summary もプロセス内変数にしかありません。

**推奨:** 9記録→7表示の対応表を作り、codex state は hash 確認済み `phase4.json`、ledger summary は gate の確定結果から復元する。

### R1-11 — High・セキュリティ — probe-record の所有・形状・リンク防御が不足

`phase0-probes.json` を EVIDENCE に入れないこと自体は、表示専用なら [SKILL.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:41) に直接違反しません。しかし PLAN は任意 object を受け、run dir 最終要素のリンクしか拒否しません。[PLAN.md:62](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:62)

中間リンク、最終 JSON のリンク読み、正確な `RUN_DIR` 所有、lock identity、seam 別の型・必須キーを確認しません。改変された有効 JSON によりレポート表示を偽装できます。

**推奨:** EVIDENCE の runDir と lock identity を検証し、全パス成分をリンク不追跡で扱い、write/read の双方で seam 別 schema を検証する。

### R1-12 — High・互換性 — `$HOME` 未設定で probe が JSON を出さない

現行 shell は未設定変数をエラーにする設定です。[codex-probe.sh:13](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:13)。PLAN の式は `HOME` も未設定なら失敗します。

実測:

```text
bash: HOME: unbound variable
exit_code=127
```

また `CODEX_HOME=""` では実効値は `$HOME/.codex` なのに、単なる「設定済み」判定なら source は `env` になります。

**推奨:** 空文字列を未設定扱いと明記し、HOME も無い場合の有効な JSON 結果を定義して境界テストを追加する。

### R1-13 — Medium・互換性/セキュリティ — 「実効 CODEX_HOME」は wrapper 環境を表さない

PLAN 自身が `direnv exec` 相当の wrapper を推奨しています。[PLAN.md:112](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:112)。probe が読むのは wrapper 実行前の呼出し側環境であり、wrapper 内の値ではありません。「実効」と表示すると誤診を誘発します。

また環境変数は任意文字列ですが、JSON・状態行へ入れる際の引用符、改行、制御文字処理が未指定です。

**推奨:** 名称を「calling-shell で観測した値」とし、wrapper 内は観測外と明記したうえで JSON serializer により出力する。

### R1-14 — Medium・互換性 — ADOPTION §7 の5文では移行経路を網羅できない

不足または現仕様では虚偽となる点があります。

- 非文字列 `bin` が従来は文字列化されたが、今後は機能停止する点。
- indexing 不正時に対話確認で停止する点。
- #57 の「再開後に状態行を復元」は現仕様では Phase-4 codex stateを復元できない点。
- #59 の「blocking は毎 run 再検証」は absence削除・trim・diff範囲により保証されない点。
- 永続 ledger に版番号がなく、将来の形式変更や未知版判定ができない点。

**推奨:** 仕様修正後、旧入力→新結果→利用者対応の移行表と ledger の `schemaVersion` を追加する。

### R1-15 — High・テスト不足 — DoD (2)(12)(19)(20) は commit 後に常に空になり得る

Stage ごとに commit する計画なのに、禁止ファイル確認は引数なしの `git diff`／`git status` です。[PLAN.md:115](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:115)、[PLAN.md:201](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:201)

禁止ファイルを変更して commit すれば検査対象は0件になります。さらに既存 `?? .claude/` は、その配下に新しい誤書込みが増えても同じ1行に見えます。

**推奨:** `dfdb8a9..HEAD` の変更ファイル集合を許可一覧と機械比較し、禁止ファイルは基準 commit と byte 比較する。

### R1-16 — High・テスト不足 — 核心経路の端から端までの検査がない

主な不足は次です。

- DoD (1): repo 内へ戻る `..`、絶対パス中間 symlink、config/scope 双方。
- DoD (3): helper は常に config を作って渡すため、不正JSON・不在・引数省略をそのまま試せない。[test_mdq_index.py:26](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:26)
- DoD (4): 期待 JSON から既存 `promptVariant:null` が欠落し、probe→planner→phase4→gate REFUSED の接続がない。[codex-review-plan.py:32](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:32)
- DoD (7): HOME 未設定、CODEX_HOME 空、環境変数の確実な削除、JSON特殊文字がない。
- DoD (9)〜(12): ledger の内容照合不一致、REFUSED run 非永続化、注入、外部path、衝突、diff範囲、blocking trim、9→7表示を検査しない。

**推奨:** 各問題について、入力から最終 gate／状態行までを一つに接続した統合テストを DoD に追加する。

### R1-17 — Medium・テスト不足 — 固定文言と総件数は誤実装でも通る

DoD (5)(8)(10)(12)(15) は主に文字列の存在確認です。実行されない説明文や重複した行があっても通り、値の入力元・順序・排他性を保証しません。

DoD (17) の「551より増える」も、無関係なテストを1本追加すれば満たせます。新規ファイルが0テストでも、他の増加で隠せます。

**推奨:** 必須テスト名と各ファイルの最低実行件数を事前固定し、対象節内の出現回数・入力元・順序まで検査する。

## 決定 §0-1〜§0-9 の判定

| 決定 | 判定 |
|---|---|
| §0-1 版を0.14.0 | 指摘無し。新しい永続形式を含む minor 判断は妥当 |
| §0-2 #56第1段のみ | 自動 close 回避に指摘無し。Issue本文は直接未確認 |
| §0-3 #58 | **要修正** — R1-7、R1-8 |
| §0-4 #56 | **要修正** — R1-9、R1-16 |
| §0-5 #57 | **要修正** — R1-10、R1-11 |
| §0-6 #59 | **実装開始不可** — R1-1〜R1-6 |
| §0-7 #60 | **要修正** — R1-12、R1-13 |
| §0-8 Stage分割 | モデル選定は指摘無し。ただし commit 方針と差分検査が矛盾 — R1-15 |
| §0-9 S2固定内容 | **要修正** — R1-14、R1-16、R1-17 |

## DoD (1)〜(20) の検査力

| DoD | 判定 | 理由 |
|---:|---|---|
| 1 | 不十分 | `..`、絶対中間リンク、両 option の網羅不足 |
| 2 | 無効 | commit/stage 後は差分0件 |
| 3 | 矛盾・不十分 | mdq既存キー破壊、入力表とtool非起動証明不足 |
| 4 | 不十分 | `promptVariant` 欠落、gateまで未接続 |
| 5 | 不十分 | 固定文言・変数名の存在のみ |
| 6 | 弱い | 文書確認としてのみ有効 |
| 7 | 不十分 | HOME未設定、空値、特殊文字なし |
| 8 | 弱い | 分岐への実接続を証明しない |
| 9 | 不十分 | 所有、リンク、seam schema、失敗時原子性なし |
| 10 | 不十分 | 9→7対応、exactly-one、Phase-4復元なし |
| 11 | 不十分 | #59の安全性核心がほぼ0件 |
| 12 | 無効部分あり | 行の存在のみ。禁止ファイル差分検査も無効 |
| 13 | 不十分 | reset説明・形式版がDoD外 |
| 14 | 概ね有効 | 既存の5面・生成物hash照合は強い |
| 15 | 不十分 | 同じ担当者が文言と期待値を同時作成できる |
| 16 | 一部有効 | handoff動作は強いが旧版残存allowlist未定義 |
| 17 | 不十分 | 総件数増加で必須テスト0件を隠せる |
| 18 | 補助として有効 | 構文のみ。実行時障害は検出しない |
| 19 | 無効 | commit後cleanでも許可外変更を含められる |
| 20 | 無効 | 同上 |

## 計画自体の欠陥と、担当者指示で吸収できる細部

計画自体の欠陥は R1-1〜R1-17 のうち、JSON出力の具体的な作り方を除くほぼすべてです。特に永続化時点、gate との関係、解決判定、key、trim、再開時の対応、path安全境界を担当者裁量にしてはいけません。

担当者指示で吸収できるのは、PLAN が安全な契約を定めた後の次の細部だけです。

- JSON の並び順、一時ファイル名、警告文の細かな表現。
- テスト補助処理で環境変数を削除する方法。
- 外部 tool 呼出履歴を記録する共通処理。
- テストコードの共通化。

## PLAN を直すべき点・優先順

1. **#59 の永続化を gate 内の確定処理へ移し、変更禁止範囲を解除する。**
2. **ledger のプロンプト抑止を廃止し、path/title安全化、明示 resolved、衝突しないkey、blocking非trimを定義する。**
3. **#58 で見かけrootを保持し、正規化前に `.`／`..`／中間リンクを拒否する。**
4. **#57 の9記録→7表示、Phase-4 codex/ledger復元、所有・リンク・schema規則を固定する。**
5. **#56/#60の出力・環境境界を修正し、全差分を基準commit比較する端から端までのDoDへ置き換える。**

修正・上書きは一切行っていません。