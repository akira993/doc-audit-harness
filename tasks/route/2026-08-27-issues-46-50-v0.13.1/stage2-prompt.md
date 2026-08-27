# S2 実装依頼 — docaudit v0.13.1 版バンプ・テスト・契約テスト・release-handoff

あなたは worker（実装者）である。boss（Fable）が確定した計画 `tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`（rev.8）の
**S2（版バンプ 5 面・engine-shas・既存テスト更新・契約テスト 8 本・release-handoff.sh 派生＋test 再照準）だけ**を実装する。
S1（文書修正）は既に boss がコミット済み（HEAD に含まれる）。S1 対象文書の本文は S2 で **変更しない**（版行・refresh 行を除く）。

## 進め方

1. 最初に PLAN.md 全文（特に §0・§6 S2・§7・§8・§10・§11・§12）を読む。§10 のリテラル本文・正規表現は**導出せずそのまま書く**。
2. 版バンプ前に `git diff --name-only main..HEAD` に `skills/init/**` が無いことを確認してから、`engine-shas.json` に `"0.13.1"` を `0.13.0` の
   3 hash のコピーで追加する。`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run` で `stampVersion: 0.13.1` を確認。
3. 契約テスト `tests/test_v0131_docs_contracts.py` は PLAN §6 (23) の (a)(b)(c)(d)(f)(g)(h)(i) の 8 本。各 test は対象件数を assert メッセージに
   含め、抽出 0 件を明示的に fail させる。**S1 済みの現物に対して全 8 本が緑になる**ことを確認し、さらに各 test が「誤った文書で赤になる」ことを
   一時的な改変（作業ツリー内で改変→実行→`git checkout -- <file>` で復元）で 1 本ずつ確認して報告に記す（復元後 `git status --short` が
   S2 の変更だけであること）。
4. `release-handoff.sh` は `cp tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`
   の後に PLAN §6 (24)／§10 の差し替えを行う。`! grep -q '0\.13\.0' <新 script>` と `bash -n` を確認。
5. `tests/test_release_handoff.py` は PLAN §6 (25) の範囲のみ変更。一括置換禁止（`:304` の `"a" * 39` は SHA 長）。
6. 作業後、§8 の検証コマンド（S2 該当分。detached 検証は boss が行うので不要）を全て実行し、**各コマンドの実出力（数値・exit code）を報告に貼る**。
   フルスイートは `python3 -m unittest discover -s tests -t .` で **`Ran 495 tests … OK`（skip 0）** を確認する。
7. git commit はしない（boss が行う）。`git status --short` と `git diff --stat` を報告に含める。新規ファイル 2 本（契約テスト・handoff script）は
   untracked のままでよい。

## 報告書式（最後に `tasks/route/2026-08-27-issues-46-50-v0.13.1/stage2-report.md` へ書き出す）

- 冒頭 1 文で結果（完了／未完了とその理由）。
- DoD (20)〜(26) ごとに「変更ファイル:行」「確認コマンドと実出力」を 1 行ずつ。
- 契約テスト 8 本それぞれの「緑の根拠（件数）」と「赤にする改変→赤の出力→復元」の記録。
- §8 検証コマンドの実出力（全て）。
- 許可外ファイルの変更が必要と判断した箇所があれば、修正せず「報告のみ」の節に列挙。
- 未検証・未対応があれば明示（黙って省略しない）。

---

以下は PLAN.md から転記した **完了条件（S2）／変更範囲／検証コマンド一式／S2 確定仕様／意図的差分リスト／リリース手順**（原文）。

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

## 完了条件（S2）— PLAN §6 より

### S2（版バンプ・テスト・handoff）
- (20) 5 面 = `0.13.1`: `plugin.json` version／`engine-shas.json` の最大キー／ADOPTION en/ja の `claude plugin list … Version 0.13.1`／
  `scaffold.py --harness --dry-run` の `stampVersion`。`test_i` の期待集合を `{"0.13.1"}` に。
- (21) `engine-shas.json` に `"0.13.1"` を追加し、3 hash は `0.13.0` と同値（本パッチは check-docs/doc-lint テンプレート・engine を
  触らない — `git diff --name-only main..HEAD` に `skills/init/**` が無いことを確認してからコピー）。
  `python3 skills/audit/scripts/scaffold.py --repo-root <tmp> --harness --dry-run` が exit 0。
- (22) ADOPTION refresh 行（en:281、ja:261-262）を §10 の**リテラル本文どおり**に更新し、`test_j` の許容正規表現を §10 の**リテラルどおり**に
  同じ commit で更新（`re.fullmatch` のため行全体一致が必要。更新先だけの差し替えでは赤になる — Opus O1-3）。更新先 `0.13.1` と旧版集合 `{0.10.1, 0.11.0, 0.12.0, 0.13.0}` は en/ja
  とも S2 契約テスト (g) が複数行単位で検査（Sol R1-6）。`tests/test_scaffold.py` の現行版アサーション（:214-218, 242-246, 312）を 0.13.1 に、
  0.12.0 の歴史 refresh テスト（:226-237）は維持。
- (23) 契約テスト **新規** `tests/test_v0131_docs_contracts.py`（skip 0、各 test は対象件数を assert メッセージに含め、対象 0 件を fail にする）:
  (a) 期待集合 `EXPECTED = {".claude/state", ".claude/worktrees", ".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}` を test に固定。
      config-schema.md／ADOPTION.md／ADOPTION.ja.md それぞれで §0-6 の固定マーカー（en `Accepted \`digestExclude\` prefixes:`／ja
      `\`digestExclude\` で受理されるプレフィックス:`）が**ちょうど 1 行**に出現することを assert し、その行のマーカー以降**行末（表セルでは
      次の `|` まで）**のコードスパンを順序付きで抽出: **件数 6・重複なし・集合が `EXPECTED` と完全一致**（余分も不足も fail。句読点では
      切らない — R4-2）。抽出した全値を `tree-digest.normalize()` に通す。負例 `.claude/state/**` と `.claude/worktrees/*` が `ValueError`
      になることも同 test で確認。さらに同じ段落（config-schema.md では同じ表行）に契約語 `tree-digest.py`・`seal-run.py`・`exit 2` の
      3 つ全てと、未 seal の固定句（en 2 文書 `the run is not sealed`／ja `run は seal されない`）が存在することを 3 文書で assert
      （R4-5、R5-3）（Sol R2-5、R3-4）／
  (b) SKILL.md で文字列 `generic-layers.py` を含む**全行**（散文の :241 を含む。3 行以上あることを assert）が `--config` を含む（Opus O4-3）／
  (c) 実体側: `skills/audit/scripts/` 直下の通常ファイル（`__pycache__`・`*.pyc` 除外、36）＋`skills/audit/references/` 直下の通常ファイル（6）
      の**リポジトリ相対 path 集合**。文書側: ADOPTION en/ja 付録フェンス内の行のうち `skills/audit/scripts/` または `skills/audit/references/`
      を含む行から path を復元した集合（tree 記号を除去）。両者の完全一致を、不足（実体にあって文書に無い）と余分（文書にあって実体に無い）
      の別 assert で報告し、実体側 42 件を assert（Sol R2-2）／
  (d) README Modes 節の `/docaudit:audit` 行と `/docaudit:init` 行を**別々に**抽出し、それぞれ `skills/audit/SKILL.md`（3 flag）／
      `skills/init/SKILL.md`（5 flag）の `argument-hint` flag 集合と完全一致（取り違え検出。R3-5）／
  (f) example.json が JSON として読め、`_note` 以外のトップレベルキー集合が `config-schema.md` **先頭の表**（`| key | type | required | meaning |`
      ヘッダから最初の空行まで。後続表のセル語 `installed`/`format` 等を拾わない — Opus O4-5）のキー集合（第 1 列。`models.light` 行は
      S1 で `models` に改める。32 件を assert）の部分集合。さらに値の完全一致: `phase3Backend == "workflow"`、`regressionRecheck == {"enabled": false}`、
      `codexReview == {"enabled": true, "bin": "codex", "required": false}`（既存 2 キーも固定。R3-6）、
      `models == {"light": {"enabled": true, "maxChanged": 10, "maxImpacted": 15, "maxDiffLines": 200, "maxDiffBytes": 65536}}`
      （example は boss 管理の固定成果物であり `sensitiveTokens` は載せない方針のため dict 完全一致で足りる — R3-6 の緩和案は不採用）、
      `"auditScope" not in keys`（Sol R2-3）／
  (g) ADOPTION en/ja それぞれで「refresh 段落」（en: `templates can be updated directly to` を含む段落、ja: `へ直接更新できる` を含む段落。
      段落＝空行区切り、複数行を結合）が**ちょうど 1 件**あり、段落中の版番号を抽出した結果が、更新元集合 `{0.10.1, 0.11.0, 0.12.0, 0.13.0}`
      と更新先 `{plugin.json の version}`（= 0.13.1）の和集合と**完全一致**（Sol R2-6）／
  (h) ADOPTION en/ja 構造パリティ: コードフェンス外の見出しレベル列が en==ja **かつ `##` 見出し数 == 15**、§5 表の第 1 列キー列が en==ja
      **かつ 26 件で `layerGlobs`・`frontMatterOverrides`・`auditReportsInCorpus` を含む**（Opus O4-1）、付録フェンス内の tree 行（`├`/`└` を含む行、root 行除く）列が en==ja
      **かつ各 51 件**（現状 45 ＋ 追加 6。R3-8）（Sol R2-7）／
  (i) Python 側は `ast` で `decide-verdict.py` を解析し、`ast.Assign` の target 名が `FAIL_SEVERITIES` である set literal（1 件）と、
      `Compare.left` が `Name(id="severity")` かつ演算子 `NotIn` で右辺が set literal のノード（1 件。:329 の Subscript 左辺・:830 の `field`
      左辺は除外）を取り出す。該当ノードが各ちょうど 1 件でなければ fail（Opus O4-4）。件数 3 と 5 を assert。文書側は ADOPTION en/ja でヘッダ `| severity | gate effect |`／`| severity | gate への効果 |`
      を持つ表が**ちょうど 1 つ**あり、表を**行単位**で解析: データ行が**ちょうど 9 行**、第 1 列のコードスパン語は 8 severity が**各 1 回**
      （重複行は fail — 辞書化前にリストで検査）、catch-all 行は第 1 列が言語別固定文（en `any other value`／ja `上記以外の値`）で
      **ちょうど 1 行**、第 2 列先頭コードスパン トークン（`non-blocking`／`blocking`／`REFUSED`）への写像が `{PASS,WARN,MEDIUM,LOW,INFO} →
      non-blocking`、`{FAIL,HIGH,CRITICAL} → blocking`、catch-all → `REFUSED` で Python 側集合と完全一致、catch-all 行に
      `unknown finding severity` を含む（Sol R2-8、R3-2、R4-3）。
  計 8 test（(e) は落とす）。全 test で「抽出 0 件」は明示的に fail させる。
- (24) `release-handoff.sh`（本ディレクトリ）: v0.13.0 版から TAG `docaudit--v0.13.1`、TITLE
  `docaudit v0.13.1 — documentation consistency (#46–#50)`、notes 本文（完全 SHA・`#46`〜`#50`・`digestExclude`・`docs-only`）、
  Issue 集合 `{46..50}`（5 件）に差し替え。usage・コメント・一時ファイル名・診断文も含め `grep -c '0\.13\.0' <新 script>` が **0**（Sol R1-11）。
  構造（preflight → unittest at SHA → tag → 単一 refspec push → Release → close → 同期）は不変。`bash -n` が通る。
- (25) `tests/test_release_handoff.py`: docstring・定数（HANDOFF path、TAG、TITLE、ISSUES、REQUIRED_BODY）に加え、**本体の v0.13.0 固有値**
  （`:424` refspec → `TAG` から導出、`:436/:457` の close 件数 → `len(ISSUES)`、`:442/:449` の Issue 番号 → `ISSUES` から導出）を
  定数由来に書き換える（Sol R1-3）。再開テスト（`test_resume_release_with_three_closed_closes_only_remaining_three`）は
  `PRECLOSED = {"46", "47"}` を定数化し、期待 close 集合・件数を `ISSUES - PRECLOSED`（= `{"48","49","50"}`、3 件）から導出する
  （5 件構成では「3 件済み・残り 3 件」が成立しない。Sol R2-4。テスト名は残り件数に合わせて改名可）。同テストで `PRECLOSED` が非空かつ
  `ISSUES` の真部分集合であることを assert する（R3-10）。それ以外のロジックは変えない。
  全分岐が新 script で green。
- (26) フルスイート `Ran N tests … OK`、**N ≥ 495**（487 + 契約テスト 8）、skip 0。boss が再実行して一致を確認。
- (27) S2 commit に `git add -f tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh` を含め、commit 後に
  `git cat-file -e HEAD:tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`（exit 0）で **HEAD 収録**を確認し、
  `git worktree add <tmp> HEAD` の detached checkout でスイートを回して green（index への add だけでは不十分。Sol R2-9。handoff は
  approved SHA の detached checkout でスイートを回すため、script が HEAD に無いと test が exit 127 で落ちる）。

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

## 10. S2 確定仕様

- 版バンプ対象は §6 (20)〜(22) の 5 面＋テスト 3 本。README は触らない。
- **refresh 行のリテラル本文と test_j 正規表現（Opus O1-3。worker は導出せずこのまま書く）**:
  - `docs/ADOPTION.md:281`（1 行）: `Existing unmodified stamped 0.10.1, 0.11.0, 0.12.0, or 0.13.0 templates can be updated directly to 0.13.1 with`
    （次行 :282 `` `/docaudit:init --harness --refresh`; user-modified templates remain untouched. `` は不変）。
  - `docs/ADOPTION.ja.md:261`: `変更されていない stamp 付きの 0.10.1、0.11.0、0.12.0、または 0.13.0 テンプレートは、`／`:262`:
    `` `/docaudit:init --harness --refresh` で 0.13.1 へ直接更新できる。利用者が変更したテンプレートは ``（:263 `そのまま残る。` は不変）。
  - `tests/test_v013_contracts.py` test_j の `allowed["docs/ADOPTION.md"]` 第 3 要素:
    `rf"Existing unmodified stamped 0\.10\.1, 0\.11\.0, {old}, or 0\.13\.0 templates can be updated directly to 0\.13\.1 with"`。
    `allowed["docs/ADOPTION.ja.md"]` 第 3 要素: `rf"変更されていない stamp 付きの 0\.10\.1、0\.11\.0、{old}、または 0\.13\.0 テンプレートは、"`。
    他の要素は不変。
- `engine-shas.json` の `0.13.1` は `0.13.0` の 3 hash をコピー（§6 (21) の前提確認つき）。
- `release-handoff.sh` は前版を `cp` して定数・notes・`ensure_release` の必須文字列・Issue ループ `46 47 48 49 50`・usage・コメント・
  一時ファイル名・完了メッセージを差し替える。`RELEASE_TITLE` は `tests/test_release_handoff.py` の `TITLE` と完全一致させる。
- `tests/test_release_handoff.py` は §6 (25) の範囲で v0.13.0 固有値を定数由来に書き換える。

---

## 11. 意図的差分リスト（既存テストの変更を許す箇所）

`tests/test_v013_contracts.py`（test_i `{"0.13.1"}`、test_j の ADOPTION refresh 行パターン 0.13.0→0.13.1）、`tests/test_scaffold.py`
（現行版リテラル 0.13.0→0.13.1、SHAS["0.13.0"]→["0.13.1"]、歴史 0.12.0 テストは維持）、`tests/test_release_handoff.py`（§6 (25)）。
これ以外の既存 assert 変更は禁止（必要なら報告のみ）。

---

## 12. リリース手順（単段・fail-closed）

1. boss: S1 commit（`docs(...)` Conventional Commits、Issue 番号付き）→ S2 commit（`chore(release): bump docaudit to v0.13.1` — engine-shas・
   テスト・契約テスト・`git add -f …/release-handoff.sh` を同一 commit に）→ 記録コミット（ファイル名列挙で `git add -f`、`*-session.log` 除外）
   → `git push -u origin docs/v0.13.1-issues-46-50`。
2. boss: `gh pr create --title "docaudit v0.13.1 — docs consistency (#46〜#50)" --body-file pr-body.md` → `gh pr merge <N> --merge`。
3. boss: `git checkout main && git pull --ff-only` → `ps` で docaudit 実行中プロセス無しを確認 →
   `printf 'y\n' | bash tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh <merge-sha> <N>`。
4. §6 (28) を実測し REVIEW.md の route-close に記録。memory の route-state を v0.13.1 に更新。

---

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。状態変更コマンド前に証拠がその操作を支持するか確認
- **上書き承認**: PLAN §7 の S2 許可 path の上書き・新規作成は本依頼で包括的に承認済み。個別確認で停止しない。
