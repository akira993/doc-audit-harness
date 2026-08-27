# S1 実装依頼 — docaudit v0.13.1 文書整合（Issues #46〜#50）

あなたは worker（実装者）である。boss（Fable）が確定した計画 `tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`（rev.8）の
**S1（文書・references・example の修正）だけ**を実装する。S2（版バンプ・テスト・handoff）は別依頼で行うので、**版番号 `0.13.1` を書かない、
テストを変更しない、engine-shas.json を触らない**。

## 進め方

1. 最初に PLAN.md 全文（特に §0 決定事項・§6 完了条件 S1・§7 変更範囲・§8 検証コマンド・§9 S1 確定仕様）と Issue 本文
   `tasks/route/2026-08-27-issues-46-50-v0.13.1/issues-46-50.md` を読む。Issue の提案と PLAN が食い違う場合は **PLAN が優先**
   （例: #47 の「REFUSED」表現は使わない、#50-4 の `auditScope` は example.json に入れない、#50-5 はコメント 1 行のみ）。
2. 各所見について、修正前に実装ファイル（PLAN §2 の file:line）を実際に読んで文言を実装に合わせる。文書どうしの推測で書かない。
3. en/ja は必ず対にして編集する（ADOPTION.md ↔ ADOPTION.ja.md、PROMPTS.md ↔ PROMPTS.ja.md）。ja は「である体」。
4. 作業後、§8 の検証コマンド（S1 該当分）を全て実行し、**各コマンドの実出力（数値・exit code）を報告に貼る**。フルスイートは
   `python3 -m unittest discover -s tests -t .` で **`Ran 487 tests … OK`（skip 0）** を確認する（S1 はテストを変えないため件数は 487 のまま）。
5. git commit はしない（boss が行う）。`git status --short` と `git diff --stat` を報告に含める。

## 報告書式（最後に `tasks/route/2026-08-27-issues-46-50-v0.13.1/stage1-report.md` へ書き出す）

- 冒頭 1 文で結果（完了／未完了とその理由）。
- Issue 所見ごと（#46-1〜7、#47-1〜2、#48-1〜9、#49-1〜5、#50-1〜5）に「変更ファイル:行」「実装側の根拠 file:line」「DoD 番号」を 1 行ずつ。
- §8 検証コマンドの実出力（全て）。
- 許可外ファイルの変更が必要と判断した箇所があれば、修正せず「報告のみ」の節に列挙。
- 未検証・未対応があれば明示（黙って省略しない）。

---

以下は PLAN.md から転記した **完了条件（S1）／変更範囲／検証コマンド一式／S1 確定仕様**（原文）。

### ⚠ 追加注意（Opus 申し送り）
- §9 の #47 完成文は PLAN 上では可読性のため折り返されている。**表セルは 1 物理行**でなければ壊れる（契約テスト (a) の「ちょうど 1 行」も落ちる）。折り返しを解いて書け。
- 3 文書（config-schema.md:29、ADOPTION.md:324、ADOPTION.ja.md:305）はいずれも表の `digestExclude` 行。ja も同じ順序（①拒否文→②マーカー ```digestExclude` で受理されるプレフィックス:``→③6 値→セル末）で書く。

---

## 0. 決定事項（route 手順 1 の代替 — 自律実行につき boss 裁定、ユーザー指示で要件確定）

ユーザー指示: 「Issue で挙がっているドキュメントの更新を実施し、パッチアップデートまで完了。docs-only のはずなので
自動 push・自動マージ可。手戻りが発生しないよう丁寧に」。

1. **版は 0.13.1（パッチ）。** 対象 Issue は open の 5 件 `#46 #47 #48 #49 #50` のみ（HEAD `3a6068b` 時点で全件実物追認済み）。
2. **runtime 挙動は変えない（docs-only）。** #50-5（`fix-scope.py:87` の `docGlobs` 既定 `[]`）は Issue 提案 B を採る:
   `fix-scope.py` に「意図的 fail-closed（docGlobs 省略時は pre-flight fix path を全拒否）」のコメント 1 行（追加 1 行・削除 0 行）と、
   `config-schema.md` の `docGlobs` 行＋ **ADOPTION en/ja の `docGlobs` 行**に注記 1 文（Sol R1-10）。既定値の整合（提案 A）は最終報告で別 Issue 候補として提示。
3. **#48-6（`AX_BIN`/`SYMBOL_GRAPH_BIN` 未参照）** も docs-only: SKILL.md の当該束縛を残しつつ「`bin` 上書きは Phase 0 probe にのみ
   効く（Phase 3 の `workflow-template.js` は `ax`/`codegraph` 固定。Workflow に渡るのは可否 boolean のみ `SKILL.md:419`）」を
   SKILL.md、config-schema.md の表（`webExtract`/`symbolGraph` 行）**および詳細節（`config-schema.md:216-220`、`:260-270`）**に注記（Sol R1-9）。
   `workflow-template.js` は変更しない。
4. **#46-5（README「What's new in 0.10.0」）** は節ごと削除し、版リテラルを含まない 1 行
   （「Release notes: GitHub Releases、版別の互換性影響は docs/ADOPTION.md §7」形式）に置換する。
   README は release-procedure 上の bump 対象ではない（badge は自動追従、手編集禁止）。
5. **#49-4（§5 表 −9 キー）** は表冒頭に「主要キーの抜粋。完全な一覧は `skills/audit/references/config-schema.md`」の注記を
   en/ja に追加し、ADOPTION en/ja のどこにも出現しない 3 キー（`layerGlobs`、`frontMatterOverrides`、`auditReportsInCorpus` — Opus O4-1 実測。
   Issue #49 の名指し 2 件は落丁）だけ行を追加する（23 → 26 行、en/ja 同数）。`indexing` は example.json に出るため追加しない。
6. **#47 の文書契約（Sol R1-1、R2-1、R3-1）**: glob を含む `digestExclude` は `tree-digest.py` が拒否 → `seal-run.py` が exit 2 で失敗し
   manifest は未 seal のまま（`seal-run.py:63-70`: 失敗時は `digest` も付与されない）。その後の挙動は経路により非対称
   （workflow backend は SKILL.md:418 で未 seal のまま verifier を起動し得る／codex backend は dispatch が非空の場合に限り
   `codex-dispatch.py:60` で未 seal を拒否（空 dispatch は SKILL.md:394 で dispatcher を呼ばず先へ進む — R5-2）／gate に到達すれば
   `EVIDENCE required keys are missing`（`decide-verdict.py:316,653`）で verdict `REFUSED` を出力）で、単一の後続経路は無い（R4-1）。
   **SKILL.md の手順は変えない**（停止分岐の追加は実行手順＝runtime の変更であり、run 解放は lock 削除の状態変更を伴う。R3-1）。
   文書契約は **seal 失敗までに限定**: 「glob を含む値は `tree-digest.py` が拒否し、`seal-run.py` が exit 2 で失敗する。run は seal されない
   （en 固定句 `the run is not sealed`／ja 固定句 `run は seal されない`）」。**「verdict なし」「Phase 3 冒頭で停止」とは書かない**（gate は
   REFUSED も verdict として出力する `decide-verdict.py:1027`、SKILL.md:602 — R5-1）。gate の具体的な拒否理由も書かない。
   「seal-run の exit 5 以外の非 0 に明示的な停止分岐が無く、後続挙動が backend で非対称」は最終報告で別 Issue 候補として提示。
   許可値は 6 種のプレフィックス（`.claude/state`、`.claude/worktrees`、`.mdq`、`.codegraph`、`graphify-out`、`.cocoindex_code`）**のいずれかで
   始まる非 glob の literal path（各プレフィックス自身とその配下 path。6 種すべてに掛かる — `tree-digest.py:25-27`、Opus O2-5）**。
   `*` を含む `.claude/worktrees/*` は拒否される（Issue #47 所見 2 の表記は誤り。Sol R1-13）。
   **3 文書とも当該記述は表の `digestExclude` 行のセル内**（config-schema.md:29、ADOPTION.md:324、.ja.md:305 — Opus O1-1 実測）。セル内の
   記述順を固定する: ① glob 拒否文（契約語 `tree-digest.py`・`seal-run.py`・**literal `exit 2`**（`exits 2` は不可）と未 seal 固定句を含む。
   `*` `?` `[` のコードスパンはここに置く）→ ② 固定マーカー（en: `Accepted \`digestExclude\` prefixes:`、ja: `\`digestExclude\` で受理される
   プレフィックス:`。各文書 1 回）→ ③ バッククォート付き 6 値（各 1 回）→ セル末（次の `|`）。**「他のコードスパンを置かない」制約はマーカー
   以降セル末までにのみ適用**（第 1 列の `` `digestExclude` `` や①のコードスパンは制約外）。契約テスト (a) はマーカー以降セル末までの
   コードスパンを読む（R4-2）。契約語と固定句は同じセル（同じ行）内で検査する（R4-5）。
7. **#50-4 の example.json（Sol R1-2）**: `auditScope` は importer 専用（`start-run.py:141-150` が path 実在・64 桁 hash・rules・importedAt を
   必須にし、静的な既定値が存在しない）ため **JSON 本体には追加しない**。`_note` に「`auditScope` は `/docaudit:init --import-audit-scope`
   が生成する。手書きしない」の 1 文のみ。`regressionRecheck: {"enabled": false}`、`codexReview.required: false`、
   `phase3Backend: "workflow"`、`models: {"light": {...既定値...}}` は追加する（いずれも既定値相当で挙動不変）。
8. **リリース経路**: ブランチ `docs/v0.13.1-issues-46-50` → PR（`pr-body.md`）→ boss が `gh pr merge --merge`（PR #45 と同じ merge commit
   方式、branch protection 無し）→ `release-handoff.sh <merge-sha> <pr>`（tag `docaudit--v0.13.1`・Release・#46〜#50 close・
   skills-dir 同期。同期は v0.13.0 と同じくユーザー既承認の範囲）。auto-mode classifier がマージを拒否した場合は、それ以前の
   成果（push 済み branch・open PR・commit 済み handoff script・green テスト）を durable にしたまま、完全な手順
   「`gh pr merge N --merge` → `git checkout main && git pull --ff-only` → `ps` で docaudit 実行中プロセス無しを確認 →
   `printf 'y\n' | bash tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh $(git rev-parse HEAD) N`」をユーザーへ渡す
   （handoff は branch==main・HEAD==origin/main==SHA を必須にする。Sol R2-10）。
9. **Stage 分割**: S1 = 文書・references・example の修正（#46〜#50 本文）／S2 = 版バンプ 5 面・engine-shas・テスト更新・
   契約テスト追加・handoff script＋test 差し替え。いずれも Terra `medium`（所見は実物追認済みだがテスト結合の判断を伴うため Luna は不採用）。
10. CHANGELOG は作らない（本 repo の慣習。release notes は GitHub Release 本文）。
11. **記録コミットの単位（Sol R1-12）**: 新 `release-handoff.sh` は S2 のテスト再照準と**同一 commit** に `git add -f <path>` でファイル名を
    明示して追跡する（S2 commit 単体で green にする）。route 記録（PLAN/REVIEW/prompt/answer/report/pr-body）は最後にファイル名を列挙して
    `git add -f`（`*-session.log` は追跡しない）。

---

## 完了条件（S1）— PLAN §6 より

### S1（#46〜#50 本文）
- (1) `#47`: `grep -c '\.claude/state/\*\*' skills/audit/references/config-schema.md docs/ADOPTION.md docs/ADOPTION.ja.md` が全て 0。
  3 か所とも §0-6 の固定マーカー行で literal プレフィックス 6 種を列挙し（マーカーは各文書 1 回、6 値は同一物理行）、同じ段落（表では同じ行）に
  「glob 不可（`*` `?` `[` を含む値は `tree-digest.py` が拒否 → `seal-run.py` が exit 2 で失敗 → run は seal されない）」を、§0-6 の
  固定句（en `the run is not sealed`／ja `run は seal されない`）を含めて明記（gate の理由・「verdict なし」・「停止」は書かない — R4-1、R5-1）。
  マーカー行の例示値は全て `tree-digest.normalize()` を通る（S2 契約テスト (a)）。
  SKILL.md の手順は変更しない（R3-1）。
- (2) `#48-1`: `grep -n 'generic-layers.py' skills/audit/SKILL.md` の全行が `--config` を含む（現状 :241 のみ欠落）。
- (3) `#48-2`: SKILL.md **Phase 5 節内**（`## Phase 5` 見出しから次の `## ` 見出しまで）の doc-graph 状態行に `reason:update-failed` の枝が
  あり、その枝は「install:」の 💡 行を出さない（symbol-graph の `index-failed` 枝と同型）。同時に :674 のラベル `3-state:` を `4-state:` に
  改める（Opus O2-2。`grep -c '4-state' skills/audit/SKILL.md` ≥ 1）。判定は節を切り出して `update-failed` を数える（Phase 0 の :185 は対象外）。
- (4) `#48-3`: `CODEX_REVIEW_AVAILABLE` の束縛ワンライナーが `str(...).lower()` 形で明記され、`codex-review-plan.py --available` の
  `choices=["true","false"]` と整合。`grep -n 'CODEX_REVIEW_AVAILABLE=' skills/audit/SKILL.md` が 1 件以上。
- (5) `#48-4〜9`（low 6 件）: 各 1 か所修正。(4) `BASELINE_OK` の束縛（SKILL.md:511）: incremental では現行どおり `git rev-parse --verify
  "$BASELINE_SHA^{commit}"` の成否で束縛、**full mode では `rev-parse` を実行せず `BASELINE_OK=false` を束縛する**（`codex-review-plan.py:35,38`
  が full mode で `baseline_ok` を読まないため出力不変。`--baseline-ok` は `required=True, choices=["true","false"]` なので未束縛は exit 2 —
  Opus O2-1）／(5) gate stdout キー列挙に `codexReview:{state,required,degraded}` と `{{GATE_VERDICT}}` の degraded 書き換え文を追加／
  (6) `AX_BIN`/`SYMBOL_GRAPH_BIN` に「Phase 0 probe のみ」注記（§0-3）／(7) SKILL.md:237 の `HARNESS_ACTIVE` 束縛指示 1 文を**削除**
  （repo 全体で参照 0 件。Opus O4-2）／(8) :130 の列挙から `CM_HEALTHY` を**外し**、:124 の中央分岐限定である旨を 1 句添える（Opus O4-2）／
  (9) 「Phase 4 step 3e」→ 実在ラベルに修正。
- (6) `#46`: README に `--import-audit-scope`（Modes 節の init 行＋説明 1 行）、codex 説明が Phase-3 backend（fail-closed）と
  `codexReview.required` に言及、Usage example が codex-review 行・counts 行を含み `/code-review ⚠` を代表例にしない
  （「主要行のみ抜粋」を明記）、`## What's new in 0.10.0` 節が消え版リテラル無しのリンク 1 行に置換、skills-dir install に `.git`/`tests`
  を落とす任意手順 1 行。`grep -c -- '--import-audit-scope' README.md docs/PROMPTS.md docs/PROMPTS.ja.md` が全て 1 以上。
  PROMPTS は en/ja 同一節番号・同一構造で追加（`grep -c '^## ' docs/PROMPTS.md` == `.ja.md`）。
- (7) `#49-1`: ADOPTION §2 codex 段落（en/ja）に (a) `required:true`∧`enabled:false` → REFUSED、(b) `required` 非 boolean →
  `required` の値によらず REFUSED、**(c) Phase 4 evidence の `codexReview` が object でない／`state` が文字列でない／既知状態
  （`CODEX_REVIEW_STATES`）外 → `required` の値によらず REFUSED**（`decide-verdict.py:786-795`、Sol R1-5）の 3 文。
  `config-schema.md:251-253` の条件節から非 boolean を切り出して別文にする。
- (8) `#49-2`: ADOPTION **§8** の現行 severity 説明は `- **Verdict:**` 箇条書き項目の内部（`ADOPTION.md:446-448`／`.ja.md:419-421`）にある。
  その項目からは「`Severity mapping:` 以降の 1 文（`Phase-3 verdicts are used directly; for Phase-4 tools, high-severity → FAIL, medium → WARN.`）」
  のうち **Phase-4 の写像部分だけを削除**し、`Phase-3 verdicts are used directly` は箇条書きに残す。**表は当該箇条書きリストの直後に空行を挟んで
  独立段落として置く**（箇条書き内部に表を入れない — Opus O1-2。§7 には置かない — R3-7）。表の直前に 1 文の導入（en `Phase-4 severity mapping:`／
  ja `Phase-4 severity の写像:`）を置いてよい。表ヘッダは en `| severity | gate effect |`、
  ja `| severity | gate への効果 |`（各文書でこのヘッダは 1 回だけ出現 — 契約テスト (i) の一意抽出マーカー）。行は **severity 1 語につき 1 行**
  （計 8 行）＋「それ以外」1 行の 9 行。第 2 列の先頭はコードスパンの固定トークン（en/ja 共通）: `` `non-blocking` ``（PASS/WARN/MEDIUM/LOW/INFO）、
  `` `blocking` ``（FAIL/HIGH/CRITICAL）、`` `REFUSED` ``（それ以外の値 — 第 1 列は en `any other value`／ja `上記以外の値`、説明に
  `unknown finding severity`）。トークンの後に自由文の説明を置いてよい。行単位の対応は S2 契約テスト (i) で固定（R3-2）。
- (9) `#49-3`: 付録ファイルマップ（en/ja、`skills/audit/scripts/` を含むコードフェンス内）に `codex-dispatch.py`、`codex-review-plan.py`、
  `import-audit-scope.py`、`read-manifest.py`、`write-template.py`、`references/codex-phase3-verdict.schema.json` を追加。
  `skills/audit/scripts/` 36 本＋`references/` 6 本の全てが**付録フェンス内**に出現（本文の言及は不算入。S2 契約テスト (c)）。
- (10) `#49-4`: §5 表冒頭に抜粋注記（en/ja）＋ `layerGlobs`・`frontMatterOverrides`・`auditReportsInCorpus` の 3 行追加（表 26 行／26 行、
  キー列 en==ja。Opus O4-1）。
- (11) `#49-5`: `.ja.md:95` と `:320` の 2 行は**文全体を である体で書き直す**（文中形 `ますが`／`ですが`／`ください` も含む — Opus O4-6）。
  `grep -cE '(ます|です)(。|$|が)' docs/ADOPTION.ja.md` が 0（現状 2。恒久テストにはしない — Sol R1-14）。
- (12) `#50-1`: `default-heuristics.md` の `regressionRecheck` 行が「内容ハッシュが FAIL 記録時と一致する（未変更の）文書のみ」を含む。
- (13) `#50-2`: `config-schema.md` の `symbolGraph`/`docGraph`/`semanticSearch` 行に「`tool` は予約。runtime は `enabled` と `bin` のみ読む」注記。
- (14) `#50-3`: `models.light` 表記を `models: { light: {...} }` のネスト表記に改める（config-schema:28、ADOPTION.md:322、.ja.md:303）。
- (15) `#50-4`: example.json に §0-7 のとおり `regressionRecheck`、`codexReview.required`、`phase3Backend`、`models.light` のサンプルを追加
  （`auditScope` は `_note` のみ）。`python3 -c 'import json;json.load(open("docs/examples/doc-audit.example.json"))'` が成功。
- (16) `#50-5`: `fix-scope.py:87` 直前にコメント 1 行。`git diff --numstat -- skills/audit/scripts/fix-scope.py` が `1 0`（追加 1・削除 0）
  かつ追加行が `#` 始まり。`git diff --stat -- skills/audit/scripts` が `fix-scope.py` 1 ファイルのみ。config-schema.md の `docGlobs` 行と
  ADOPTION en/ja の `docGlobs` 行（:305／.ja.md:286）に「pre-flight fix path のみ、省略時は全拒否」の注記 1 文。
- (17) en/ja パリティ: コードブロック外の見出しレベル列が en==ja（現状 `##` 15／15）、§5 表のキー列が en==ja、付録フェンス内の path 列が
  en==ja（S2 契約テスト (h)。`grep '^#'` の生カウントは使わない — Sol R1-8）。
- (18) 版リテラル: S1 は版番号を新規に書かない（`0.13.1` の記述は S2 でのみ追加）。`0.12.0` の新規出現 0（test_j）。
- (19) フルスイート `Ran 487 tests … OK`（S1 はテスト不変）。

---

## 7. 変更範囲

- **許可（S1）**: `README.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`docs/PROMPTS.md`、`docs/PROMPTS.ja.md`、
  `docs/examples/doc-audit.example.json`、`skills/audit/SKILL.md`、`skills/audit/references/config-schema.md`、
  `skills/audit/references/default-heuristics.md`、`skills/audit/scripts/fix-scope.py`（コメント 1 行追加のみ・削除 0）。
- **許可（S2）**: `.claude-plugin/plugin.json`、`docs/ADOPTION.md`／`.ja.md`（版行・refresh 行のみ）、
  `skills/audit/references/engine-shas.json`、`tests/test_v013_contracts.py`（test_i 期待集合・test_j 許容正規表現のみ）、
  `tests/test_scaffold.py`（現行版リテラルのみ）、`tests/test_release_handoff.py`（§6 (25) の範囲）、新規 `tests/test_v0131_docs_contracts.py`、
  新規 `tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`。
- **禁止**: `skills/audit/scripts/*.py|*.sh`（fix-scope.py のコメント 1 行以外）、`skills/audit/references/workflow-template.js`、
  `skills/audit/references/*.schema.json`、`agents/**`、`skills/init/**`、`tests/data/**`、上記以外の既存テストの assert 変更、
  CHANGELOG の新設、README badge、`.gitignore`、`data/**`、`docs/superpowers/**`、`.claude/**`。
- **標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。
- **S1 で触る文書に既に懸かっている既存 assert（Opus O3-2。テスト側の変更は許可しない。赤にする変更は実施せず報告せよ）**:
  `tests/test_v013_contracts.py:176-178`（config-schema.md の `| \`codexReview\` |` 行頭形式と `required:bool=false` の維持）、
  `:162-169` test_g（`docs/PROMPTS.md`／`.ja.md` に文字列 `regression` が残ること — 既存節を削らない）、`:157-160` test_f（SKILL.md Phase 3 以降に
  `SEALED_` 接頭辞無しの `RUN_CLASS` を書かない）、`tests/test_harness_contract.py:17-28`（SKILL.md の `Use only sealed \`manifest.phase3Backend\``・
  `Never silently fall back to Workflow`・`Phase-3 backend: <manifest.phase3Backend>`、config-schema.md の `` `"workflow"` (default when omitted) or `"codex"` ``
  を維持）。
- **S2 の注意（Opus O4-7）**: `tests/test_release_handoff.py` で `39`〜`44` の一括置換は禁止。`:304` の `"a" * 39` は SHA 長の境界値であり触らない。

---

## 8. 検証コマンド一式

```
python3 -m unittest discover -s tests -t .                       # 全体（S1: 487 / S2: ≥495, OK, skip 0）
python3 -m unittest tests.test_v0131_docs_contracts -v            # S2 契約テスト 8 本
python3 -m unittest tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff -v
python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run   # stampVersion 0.13.1
python3 -c 'import json;json.load(open("docs/examples/doc-audit.example.json"))'
grep -c '\.claude/state/\*\*' skills/audit/references/config-schema.md docs/ADOPTION.md docs/ADOPTION.ja.md   # 0 0 0
grep -n 'generic-layers.py' skills/audit/SKILL.md | grep -vc -- '--config'                                      # 0
grep -cE '(ます|です)(。|$|が)' docs/ADOPTION.ja.md                                                              # 0（DoD (11) と同一パターン）
grep -c -- '--import-audit-scope' README.md docs/PROMPTS.md docs/PROMPTS.ja.md                                  # 各 ≥1
git diff --numstat -- skills/audit/scripts/fix-scope.py                                                        # 1 0
git diff --name-only -- skills/audit/scripts                                                                   # fix-scope.py のみ
! grep -q '0\.13\.0' tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh                            # exit 0 = 残存なし
git cat-file -e HEAD:tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh                           # S2 commit 後、exit 0
bash -n tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh
# S2 commit 後の detached 検証（boss 実行。通常 checkout でフルスイート green＋tracked 差分 0 を確認した上で、HEAD 収録物だけで handoff test を回す。R3-9）
#   全体をサブシェルで実行。親 dir は mktemp -d で実在確認、worktree path は一意（PID 付き）、trap で登録解除を保証、
#   試験と後始末の終了状態を別々に保存し、いずれか非 0 なら非 0 を返す（R4-4、R5-4、R5-5、R5-6）。削除コマンドは git worktree remove のみ。
(
  set -u
  PARENT="$(mktemp -d)" && test -d "$PARENT" || exit 97
  WT="$PARENT/wt-$(git rev-parse --short HEAD)-$$"
  cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1; crc=$?; git worktree prune >/dev/null 2>&1; return $crc; }
  trap 'cleanup' INT TERM
  git worktree add --detach "$WT" HEAD || exit 98
  rc=0; (cd "$WT" && python3 -m unittest tests.test_release_handoff -v) || rc=$?
  trap - INT TERM; cleanup; crc=$?
  echo "detached handoff tests rc=$rc cleanup_rc=$crc"
  test "$rc" -eq 0 && test "$crc" -eq 0
)                                                                                                             # 18 tests OK, 終了状態 0
```
本 repo に lint／型チェック／quality:gate は無い（Python 標準ライブラリのみ、`unittest` が唯一の品質ゲート）。

---

## 9. S1 確定仕様（Issue ごと）

- **#47（high）**: config-schema.md:29 の `digestExclude` 行の meaning セルを、§0-6 の順序（①→②→③→セル末）を満たす次の完成文に改める
  （Opus O2-1。ja は同構造で である体）:
  「Non-glob literal paths only — each accepted prefix itself or any path below it (a trailing `/` is normalized away). Values containing `*`, `?`,
  or `[` are rejected by `tree-digest.py`; `seal-run.py` fails (exit 2) and the run is not sealed. Accepted `digestExclude` prefixes:
  `.claude/state`, `.claude/worktrees`, `.mdq`, `.codegraph`, `graphify-out`, `.cocoindex_code`.」
  — literal `exit 2` 必須（`exits 2` は不可 — Opus O1-1）。「停止」「verdict なし」は書かない（R5-1）。マーカー以降セル末までのコードスパンは
  6 値のみ（末尾 `/` の句はマーカーより前に置いた。Opus O2-2）。「配下 path も可」は 6 種すべてに掛かる（`tree-digest.py:25-27` の
  `KNOWN_ROOTS` 判定は先頭要素比較。Opus O2-5）。
  ADOPTION.md:324／.ja.md:305 も同旨（ja は である体）。末尾 `/` の正規化は上記完成文の①部分（マーカーより前）に含めてあり、マーカー以降には置かない（Opus O2-2）。
- **#48**: medium 3 件は Issue の提案どおり（:241 は :254 の完全形に揃える／doc-graph 状態行に `update-failed` 枝／
  `CODEX_REVIEW_AVAILABLE="$(python3 -c '...; print(str(...).lower())' ...)"` 形）。low 6 件は §6 (5) のとおり。実装ファイルは触らない。
- **#46**: README:25 の codex 説明を「Phase-4 adversarial review（`critical`/`high` は完了時に block 可、`codexReview.required:true` で
  未完了は REFUSED）＋ opt-in Phase-3 backend（`phase3Backend:"codex"`、fail-closed）」に。Usage example は SKILL.md Phase 5 の実出力形に
  合わせ主要行のみ抜粋（run-class／codex-review 状態行／counts 行を含む）。Modes 節に `--import-audit-scope`。
  PROMPTS en/ja に「§9 Import an existing audit-scope.json」相当の短い節を同一構造で追加（`/docaudit:init --import-audit-scope`）。
- **#49**: §6 (7)〜(11)。severity 表は **§8 の現行説明を置換**（en/ja 同じ位置。§7 には置かない — R3-7）。
- **#50**: §6 (12)〜(16)。example.json の `_note` は 2 文追加に留める（`auditScope` 手書き禁止・新キーは既定値）。

---

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。状態変更コマンド前に証拠がその操作を支持するか確認
