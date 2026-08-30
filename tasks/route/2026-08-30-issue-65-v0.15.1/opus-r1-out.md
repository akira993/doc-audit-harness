# Opus R1 — 全体敵対レビュー（PLAN rev.6 / docaudit v0.15.1）

**判定: 実装承認不可（差し戻し）。ブロッキング 4 件を PLAN rev.7 に反映すれば承認可。** 4 件はいずれも「正しく実装した worker が機械ゲートで落ちる／指示どおりに実装できない」型の欠陥であり、Sol が個別修正を逐次的に見た結果、修正同士の組み合わせと実ファイルの実体との照合が抜けた層に集中している。

検証は read-only で行い、repo は変更していない（本ファイルの Write のみ）。

---

## 0. 先に確定させた事実（PLAN の数値主張の再実測）

| 主張（PLAN） | 実測 | 判定 |
|---|---|---|
| フルスイート 630・skip 0 | `python3 -B -m unittest discover -s tests` → `Ran 630 tests in 198.811s` / `OK` | 一致（G1 の `≥654` = 630+18+1+2+3 は整合） |
| probe テスト 20 method | `grep -c '^    def test_' tests/test_codegraph_probe.py` = 20 | 一致 |
| handoff テスト 24 method | 同上 `tests/test_release_handoff.py` = 24 | 一致 |
| test_scaffold の "0.15.0" 7 箇所 | :214,217,218,242,245,246,312 | 一致 |
| #66 古い記述 13 行・15 出現 | README 3・ADOPTION.md 4・ADOPTION.ja.md 4・SKILL.md 2（:3,:778）＝13 行／出現 7・3・2・2・1＝15 | 一致（ただし REVIEW.md:10 のベースラインは「12 行」— 下記 軽微 4） |
| engine-shas 9 キー | 0.10.0〜0.15.0 | 一致 |
| ADOPTION 版行・refresh 行 | `docs/ADOPTION.md:235,315` / `docs/ADOPTION.ja.md:214,289` | 一致 |
| codegraph 1.5.0 の規則 | `directory.js:84-102` `codeGraphDirName()` = `trim()` → 空/`.`/`includes('..')`/`includes('/')`/`includes('\\')`/`isAbsolute` で既定へ。`isInitialized()` :134-142 = dir 存在＋isDirectory＋`existsSync(codegraph.db)` | 一致（PLAN §2 の記述は一次ソースどおり） |

---

## ブロッキング（PLAN を直すべき）

### B-1. `skills/audit/SKILL.md` の分岐説明は 216-218 に跨るのに、許可範囲・G11 が 216-217

- **file:line** — PLAN §5.3 / §7 / G11(b) が許可範囲を `SKILL.md: 216-217` と固定。実体:
  ```
  216|fresh: `.codegraph/` absent → `codegraph init .` (first run,
  217|confirmed 96ms on this repo); `.codegraph/` present → `codegraph sync .` (confirmed idempotent,
  218|fast); it never touches `.gitignore` itself (codegraph self-generates `.codegraph/.gitignore`).
  ```
- **問題** — 218 行頭の `fast);` は 217 の sync 節の**続き**である。§5.3 が要求する書き換え（「`<dir>/codegraph.db` が通常ファイルなら sync／無ければ init／symlink・非通常なら実行せず index-failed」）を素直に書けば 218 に必ず及び、G11(b)（旧側範囲が 216-217 に含まれること）で **正しい実装が FAIL** する。落とさずに済ませるには「217 を `(confirmed idempotent,` で終える」という PLAN に書かれていない暗黙制約を worker が当てる必要がある。
- **推奨** — §5.3・§7・G11(b) の許可範囲を **216-218** に拡張する（`config-schema.md` 側の 280-282 は実体と一致しており変更不要。ただし 283 行頭が `self-generates ...` で始まるため、282 の置換文は主語 `codegraph` で終える必要がある — §5.3 に 1 行注記を）。

### B-2. §5.4 の「:560 付近に注記を入れてよい」と G11(c)「insert opcode 0 件」は両立不能

- **file:line** — PLAN §5.4（`:560` 付近に注記 1 行を入れてよい）× PLAN §5.7 G11(c)（`insert`／`delete` は位置を問わず 0 件）。
- **根拠（実測）** — `difflib.SequenceMatcher` は 1 行挿入を `equal / insert / equal` として報告する:
  `[('equal',0,2,0,2), ('insert',2,2,2,3), ('equal',2,4,3,5)]`。したがって注記を入れた瞬間に G11 は FAIL する。
- **補強（Sol も boss も未指摘）** — G11(a) は「**行 3** と **行 778**」という**固定行番号**で期待文字列を照合する。これは「挿入が 1 行も無い」ことに依存した設計であり、insert が起きた場合に FAIL するのではなく**黙って別の行を検査する**（gate 全体としては (c) が先に FAIL するので通り抜けはしないが、(a) の健全性が (c) に依存する結合設計になっている）。行番号固定と可変長編集の許可は同居させてはいけない。
- **推奨（1 つ）** — §5.4 の注記許可の文を**削除**（トークン改名は #66 で追跡済みで、本版に注記を入れる利益は無い）。あわせて G11 の機構を difflib opcode から**行単位比較**へ置き換える: 「(1) 総行数が e1c0b19 と同一、(2) 許可行 `{3, 216-218, 560-563, 778}` 以外の全行が e1c0b19 と完全一致、(3) 行 3 と行 778 は期待文字列と完全一致」。difflib より決定的で、実装が単純で、行番号固定の前提を構成的に満たす。

### B-3. `ascii()` 相当のエスケープを **誰が生成するか**が未規定（bash 単独では実装不能）

- **file:line** — PLAN §5.1: python3 → bash の受け渡しは「`STATE\0BIN\0DIRNAME\0` の **3 フィールド**、bash は `IFS= read -r -d ''` を 3 回」と固定。一方で同じ §5.1 が「stderr に `DIRNAME` を出すときは python の `ascii()` 相当のエスケープ表現（U+2028/2029 も含めて逃がす。`printf '%q'` は使わない）」を要求し、その stderr は分岐表の行 1・2（`codegraph dir <DIRNAME> is a symlink` / `... is not a directory`）で **bash 側**が出す。
- **問題** — bash には `ascii()` 相当が無い（`printf '%q'` は明示的に禁止されている）。worker は (i) 3 フィールド固定を破って 4 番目を足す、(ii) エラー経路で python3 を再呼び出しする、(iii) 禁止された `%q` を使う、のいずれかを勝手に選ぶことになる。N14 は「1 行・ASCII・エスケープ表現を含む」ことしか見ないので、(iii) を選んだ実装は U+2028 ケースで落ちるが、その原因が PLAN の指示不備であることは B1 まで判明しない。
- **推奨（1 つ）** — 受け渡しを **4 フィールド `STATE\0BIN\0DIRNAME\0DIRNAME_ESC\0`**（`read` を 4 回）とし、`DIRNAME_ESC = ascii(DIRNAME)` を python 側で生成すると PLAN に明記する。

### B-4. `test_v0131_docs_contracts.py` の版集合を素直に書くと `test_j` が落ちる（`0.12.0` リテラル罠）

- **file:line** — PLAN §5.5 は `tests/test_v0131_docs_contracts.py:90` の期待集合を engine-shas 全キーへ同期せよと指示。現行 :91 は
  `target = {"0.10.1", "0.11.0", "0." "12.0", "0.13.0", ...}` と **文字列を分割**して書かれている。
- **根拠** — `tests/test_v013_contracts.py:203-242` `test_j_only_allowlisted_0_12_0_references_remain` は `git ls-files` のうち `skills/ agents/ docs/ .claude-plugin/ tests/` 配下と `README.md` の**全行**を走査し、リテラル `0.12.0` を含む行が path 別 allowlist（:206-225）に**完全一致**しなければ FAIL する。`tests/test_v0131_docs_contracts.py` は allowlist の dict に**存在しない**（= 出現 0 件が要求）。分割記法はこの走査を回避するための仕掛けである。
- **問題** — worker が §5.5 の指示どおり 10 版の集合をリテラルで書くと G1（フルスイート）が FAIL し、原因が「自分の書いた版集合ではなく別ファイルの走査テスト」であるため、場当たり的に allowlist を足すか列挙を旧 6 版へ戻す誘因になる（Sol R5-1 が警戒したのと同じ失敗モード）。
- **推奨（1 つ）** — リテラルを増やすのではなく、`target` を **`engine-shas.json` のキーから導出**させる（`set(json.loads(read(SHAS))) | {plugin_version}`）。リテラル `0.12.0` が消えて罠が構造的に消滅し、テストの意味も「docs の列挙 == engine-shas の全キー」というより正確な契約になる。PLAN §5.5 にこの導出方法を明記すること。

---

## 縮小提案（ユーザー判断。落としても #65/#66 の目的は達成される）

プロンプトが名指しした 5 点について立場を示す。

### S-1. G13（ignored 範囲の manifest）— **削除を推奨**

- **根拠（実測）** — `git ls-files docs/superpowers/` = **0 件**、`git ls-files .envrc` = **0 件**（＝出荷物に一切載らない）。一方 `git ls-files tasks/route/2026-08-29-issue-56-stage2-v0.15.0/` = **21 件**（追跡済み）で、追跡ファイルの改変は ignore 規則に関係なく `git diff` に出るため **G8 が既に完全にカバー**している。
- したがって G13 の固有カバー範囲は「出荷されない未追跡 ignored ファイル」だけで、守っている脅威が出荷物に到達しない。対価は manifest の事前生成・`--ignored-manifest` 引数・A2 の違反 fixture（boss が `docs/superpowers` を書き換えて戻す作業）。**負債側が大きい。**
- 推奨: G13 と `--ignored-manifest` 引数を削除。どうしても残すなら対象を `.envrc` のみに縮める。

### S-2. N12 の trim 表（26 コードポイント × 前後 2 位置）— **縮小可。ただし U+FEFF は必須維持**

- **根拠（実測）** — JS trim 集合 J（PLAN §5.1 の明示リスト）と Python `str.strip()` 集合 P の差は
  `J∖P = {U+FEFF}`、`P∖J = {U+001C, U+001D, U+001E, U+001F, U+0085}` のみ。**残り約 22 コードポイントは両実装で同挙動＝判別力ゼロ**（`strip()` 誤用も explicit クラスも同じ結果になる）。
- 方向の違いが重要で、Sol も PLAN も区別していない:
  - **U+FEFF 方向**（JS は剥がす／Python は剥がさない）: probe が `\uFEFFfoo` のまま判定・export し、codegraph は再 trim して `foo` を操作する。**export が保険にならない唯一の probe 内乖離**であり、実際に偽 `ok`／取り違えを生む。→ **必須**。
  - **U+001C〜1F, U+0085 方向**（Python が余分に剥がす）: probe は export により codegraph と必ず一致するので probe 内では無害。影響は Phase-3 verifier との整合のみで、PLAN §5.1 自身がその完全閉鎖を **#63 の範囲外**と宣言している。→ 代表 1 件で十分。
- **なお現行 PLAN の表は U+0085 を落としている**（`P∖J` に含まれるのに N12 の「剥がれない」側は U+001C〜001F のみ）。表を維持するなら U+0085 を追加すべき。
- 推奨: 表を **8 行程度**へ縮小（先頭・末尾の U+FEFF、U+001C 1 件、ASCII 空白、NBSP、無効入力リスト、有効入力リスト）。全表維持でも table-driven なら実行コストは小さいので、維持したい場合の追加条件は「U+0085 を足す」こと。

### S-3. `CODEGRAPH_DIR` 尊重そのもの — **維持を推奨**（ただし切り出し可）

- 現行出荷版は probe が `.codegraph` だけを見るため、override 利用者は毎 run `init` が走っていた（1.5.0 では rc=0 の no-op）。db 基準分岐だけ入れて `CODEGRAPH_DIR` を無視すると `.codegraph/codegraph.db` は**永久に不在**なので、やはり毎 run `init`（no-op）→ **`reason:"ok"` を返し続けながら索引が一切更新されない silent staleness** が恒久化する。#65 の主題（永久 index-failed の自己回復）と同型の欠陥をもう一方の分岐に残すことになるので、同版で直すのが筋。
- ただし「#65 だけの最小版として出し、`CODEGRAPH_DIR` は別 Issue」という選択も成立する。その場合 S-2 の trim 表・N10〜N12・N14・N15・NUL 受け渡し・ASCII エスケープ（＝ B-3 の原因）が**まるごと不要**になり、本版の複雑度と worker のリスクは半減する。**費用対効果でこの分割を選ぶのは合理的**で、ユーザー判断に値する。

### S-4. N15（不正 UTF-8 env）— **維持**

- 1 行（`os.environb` + `errors="replace"`）＋テスト 1 本で、`os.environ` の surrogateescape 値を UTF-8 で書き出したときの `UnicodeEncodeError` を防ぐ。probe の「常に JSON・exit 0」契約に直接効き、コストが最小。S-3 で `CODEGRAPH_DIR` 対応ごと切る場合のみ不要になる。

### S-5. G11 — **維持するが機構を変更**（B-2 の推奨に統合）

---

## プロンプトが名指しした 3 つの組み合わせの裁定（調べた結果シロ）

1. **`PRECLOSED={"65"}` × close 対象 #65 のみ × resume テスト — 整合**。`PRECLOSED` は handoff スクリプト側の定数ではなく **テスト側のシミュレーション定数**である（`tests/test_release_handoff.py:428-441`: `assertTrue(PRECLOSED)` / `assertEqual(PRECLOSED, ISSUES)` の後、fake の state で当該 issue を CLOSED にしてから `ISSUES - PRECLOSED` = 空集合の close 呼び出しを検査）。v0.15.0 も `ISSUES = PRECLOSED = {"56"}` で同型。「commit 件名に #65 を書かない」方針と矛盾しない。
2. **解決済み DIRNAME の export × 不正 UTF-8 の U+FFFD 置換 × N12 fixture 規則 — 整合**。probe は `\ufffd.codegraph-win` を UTF-8（`EF BF BD ...`）で export し、Node は受け取った bytes を同じく U+FFFD に復号してから同じ bytes で syscall を発行するため、export の有無に関わらず同一ディレクトリを指す。fixture 規則（選ばれるべき dir にだけ db）とも矛盾しない。
3. **G8 の具体配列 × G10 の任意生成物 × §7 の許可一覧 — 整合**。3 者は同一の有限配列を共有する設計で、`prompts/opus-r1.md`・`opus-r1-out.md` も §7・G10 の任意生成物配列に含まれている。実測: 両 route dir は現時点で `git ls-files` に 0 件（= 全て force-add 待ち）で、`.gitignore` に `tasks/` があるため `*-log.txt`・`PLAN.rev*.md` は `--untracked-files=all` にも現れない。

---

## (c) 波及先の取りこぼし

- **repo 内の複写は 13 行で完全**（追加作業不要）。`grep -rln` で全ファイルを走査した結果、古い記述を持つのは README.md / docs/ADOPTION.md / docs/ADOPTION.ja.md / skills/audit/SKILL.md の 4 ファイルのみ。`skills/init/SKILL.md`・`docs/examples/`・`skills/audit/references/*.md`・テンプレートには**無い**。紛らわしい 2 箇所は誤検出:
  - `skills/audit/SKILL.md:522-523`「Built-in `/code-review` and `/security-review` cannot run inside Workflow」は **Workflow（subagent）内での話**で現在も真 → 触らない。
  - `docs/ADOPTION.md:124`「which cannot be invoked autonomously」は **openai-codex plugin** の話 → 触らない。
- **分岐説明の複写も 3 箇所で完全**: `SKILL.md:216-218`・`config-schema.md:280-282`・`codegraph-probe.sh:12-16`。PLAN が全て押さえている。
- **`~/.claude/skills/docaudit/` の同期は追加作業不要**。現物は古い記述を保持している（`README.md:10,14,26` 等で確認）が、handoff の rsync FILTERS（v0.15.0 版 :149-157）は `/tests/ /tasks/ /docs/superpowers/` 等のみ除外し **README.md と docs/ を同期対象に含む**ため、release handoff の最終段で自動的に更新される。
- **repo 外の実害 1 件（本 PLAN 範囲外・フォローアップ推奨）**: `~/Projects/dir-framework/docs/runbooks/initial-setup.md:50` に「`.codegraph/` が空でも存在すると probe は sync を選び失敗し続ける」という回避手順が明文で書かれている。v0.15.1 でこの記述は stale になる（自己回復するため）。dir-framework 側の Issue として起票を推奨。
- **contract テストの巻き添えは無い（確認済み）**: `tests/test_v014_contracts.py:209-210` と `tests/test_v015_contracts.py:141-142` は SKILL.md を `"**code-review status line**"` という**見出し行（:777）で分割している**だけで、:778 の本文は検査していない（`grep -rn 'not-model-invocable' tests/` = 0 件）。:777 を変更しない限り、許可外ファイルである `test_v014_contracts.py` に手を入れる必要は生じない。

---

## (d) worker 実行可能性（B-3 以外）

1. **NUL 3 回読みの具体イディオムが未提示** — 現行 :28 は `read -r STATE BIN < <(python3 ...)` の 1 回読み。3（または B-3 後は 4）回読むには同一 fd を保持する必要があり、`{ IFS= read -r -d '' STATE; IFS= read -r -d '' BIN; IFS= read -r -d '' DIRNAME; } < <(python3 ...)` の形が要る。`medium` 相当が独力で当てる保証は無いので、PLAN §5.1 にこの 1 行を書くこと。
2. **python 側の出口が 4 本ある** — 現行ブロックは `not-configured`（:35 は**裸の `print`**）・`disabled-by-config`（:45）・`enabled`（:47）・`invalid-config`（:49）の 4 経路で出力する。NUL 形式への変換は 4 本すべてに必要で、1 本でも漏らすと bash 側の `read -d ''` が EOF まで読んで STATE に複数フィールドが入り、reason が壊れる。既存テスト（`test_absent_key_is_not_configured` 他）が検出するので G1 で落ちるが、指示として §5.1 に「4 経路すべて」と明記すれば往復が減る。
3. **fake の JSON 記録と `text=True` helper の整合** — §5.2 の `input="STDIN-SENTINEL\n"`（str）と `stdin_eof` の記録は整合している（helper が `text=True` のため str を渡す）。矛盾は見つからなかった。ただし fake は `sys.stdin.read()` を**必ず**実行する必要がある（`</dev/null` を外した実装で sentinel を読ませるため）ので、「fake は argv 記録の前後いずれかで必ず stdin を読み切る」ことを §5.2 に明記すること。
4. **G11 の期待行の生成方法** — B-2 の推奨（行単位比較）を採れば「行 3 = 旧行の `(not model-invocable)` を `(not started by the audit itself yet)` に置換した文字列」を gate 内で `old_line.replace(...)` として構成でき、期待行のハードコードが不要になる（行 778 のみ §5.4 の全文をリテラルで持つ）。現行 PLAN はこの生成方法を書いていない。

---

## 軽微

1. **auto-close 規則の精度** — §5.6 は「コミット**件名**に `#65` 等を書かない」だが、GitHub の auto-close は **commit message 全体および PR body** の closing keyword（`Closes #65` 等）で発火し、キーワードの無い裸の `#65` では発火しない。v0.15.0 の教訓（#59 が keyword で誤 close）を正確に反映するなら「commit message 全体と PR body で closing keyword + `#N` を書かない」と書くべき。#66 が誤 close されると handoff の事前条件（#66 OPEN）で停止する。
2. **N7・N8 は現在動作している構成を意図的に壊す** — `.codegraph` や `codegraph.db` が**有効な** symlink の場合、現行版は `sync` が通って `ok` になるが、v0.15.1 は実行せず `index-failed` になる。§5.5 の ADOPTION v0.15.1 ブロック案には「symlink や通常ファイル以外は実行せず index-failed」と書かれており文書化はされているが、「従来は動作していた構成」であることが読者に伝わる文にするのが望ましい。
3. **`config-schema.md` は G4 の対象 5 ファイルに含まれるが古い記述は 0 件**（実測）。無害だが、G4 の期待値 15→0 の内訳に「config-schema は元から 0」と注記があると A2 の fixture 設計時に迷わない。
4. **`REVIEW.md:10` のベースラインが stale** — 「SKILL.md 1 ＝ 12 行」とあるが実測は SKILL.md 2 行（:3 と :778）で合計 **13 行**（PLAN §2・G4 と一致）。REVIEW.md 側を 13 に直すこと。

---

## 検証した項目 / していない項目

**検証した（実測）**: フルスイート 630/OK/skip 0（198.8s）、probe 20・handoff 24 の method 数と全名称、`test_scaffold` の "0.15.0" 7 箇所、#66 古い記述 13 行・15 出現とその全文、engine-shas の 9 キー、ADOPTION の版行・refresh 行の行番号、`SKILL.md` 216-218 / 560-563 / 777-778 と `config-schema.md` 280-283 の実体、`test_v013_contracts.py:203-242`（test_j の走査範囲と allowlist）、`test_v0131_docs_contracts.py:90-96`、`test_v014/v015_contracts` の code-review 見出し依存、`test_release_handoff.py:273-290, 415-460` と 24 method 名、v0.15.0 handoff の rsync FILTERS と #59/#63 OPEN 事前条件、codegraph 1.5.0 `directory.js` の `codeGraphDirName`/`isInitialized` 実装、JS trim 集合と Python `strip()` 集合の差分、difflib の 1 行挿入 opcode、`git ls-files` による docs/superpowers・.envrc・両 route dir の追跡状態、dir-framework `initial-setup.md:50`。

**検証していない**: gate.py の実物（未作成）、release-handoff.sh の v0.15.1 版（未作成）、A3 の実機再現（codegraph を実際に走らせる repro は boss 実測の記録に依拠し、再実行していない）、`git worktree` を使った e1c0b19 ツリーでの gate 全体 FAIL（gate.py が無いため不能）、`.codegraph` symlink 構成での codegraph 1.5.0 の実挙動（`isInitialized` のコード読解のみ）。
