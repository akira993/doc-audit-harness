# PLAN — Issues #39〜#44 一括対応 → docaudit v0.13.0（rev.8, 2026-08-27 — 実装承認済み）

boss = Fable（本セッション）。worker = Sol/Terra/Luna（`direnv exec . codex exec`、CODEX_HOME=~/.codex-doc-audit-harness）。
rev.2〜rev.6 = Sol R1〜R5（計 96 件）。rev.7 = Opus R1（BLOCKER 2・MAJOR 5・非ブロッキング 8）。rev.8 = Opus R2（5 点）＋
R3 条件（契約テスト (e)(f) の 2 句）を反映し **Opus が実装承認**。本書は**自己完結**とする（「rev.N のとおり」参照は禁止）。
対応表は REVIEW.md。

## 0. インタビュー決定（route 手順 1、2026-08-27）

1. **#44 方向**: `.claude/audit-scope.json` を正本とし、docaudit 側が impactMap を**生成**する（生成物と正本の整合を Phase 0 で
   検査し、drift は監査停止。scope の sha は manifest に封印し gate でも照合）。実行時直接読みは不採用。impactMap は必須キーの
   まま。**audit-scope 未導入プロジェクトの挙動は変えない**（全利用者向けの変更は §10 末尾「互換性影響一覧」に限る）。
2. **範囲**: #39〜#44 を 1 ブランチ・1 PR・1 版（v0.13.0）で。
3. **#39/#41 深度**: 最小実装。多数決（`phase3Votes`）は据え置き・別 Issue 起票案（要ユーザー追認）。
4. **boss 裁定（Opus R1 後）**: (a) flip 集計は `changeSetSha` を数え上げ条件から外す（Sol R1 #1 の部分的撤回。Issue #39 の
   実測は remediation commit を挟んだ 2 run 間で 24 件）。(b) handoff は前回 v0.12.0 の二段スクリプト・既存試験を単段に
   縮約して再利用し、新規試験は Release 内容・単一 tag push・Issue close 集合・同期先 preflight に限る（再開表・分岐別
   期待回数表の全面新設は不採用）。(c) S4 を S4a（封印連鎖）／S4b（#42）に分割。

## 1. 目的

| Issue | 目的（1 文） | 出荷形 |
|---|---|---|
| #44 | audit-scope.json と impactMap の二重管理を、audit-scope → impactMap の決定論的生成＋生成物照合（drift で停止・scope sha 封印）で単一 owner 化する | `import-audit-scope.py`＋init/audit SKILL Phase 0 配線＋`auditScope` キー＋impactMap 項目 `source`＋manifest `auditScopeSha` |
| #40 | heuristic 飽和を可視化し、mapped 主・heuristic 従を明文化する | `counts.docCorpus`・`heuristicSaturation`＋飽和 WARN＋`excludeDocPathTokens`＋docs（コスト主因＝anchor の古さ） |
| #39 | 前回 FAIL 文書の再検証（opt-in）＋内容不変でのブレ件数報告＋契約の限界の明記 | provenance `regression`＋impact/provenance/manifest の封印連鎖（`read-manifest.py`）＋`counts.verdictFlipsUnchangedContent`＋docs |
| #41 | Phase 3 の 3 盲点を明示し codex review に横断観点を持たせる | docs＋codex review プロンプト観点 |
| #42 | codex-review 不実行が CONSISTENT に埋没する問題を、config 由来 strict mode（REFUSED）＋決定論的判定表＋表示分離＋probe 範囲明示で塞ぐ | `codexReview.required`＋`codex-review-plan.py`＋evidence `codexReview.state` 厳格検証＋gate＋`phase4Required`＋probe＋設計 spec 追記 |
| #43 | generic-layers.py の 3 LOW 欠陥修正＋stamp SHA 更新 | fixture 保存→修正＋対テスト＋版 bump＋engine-shas（同一 Stage） |
| release | fail-closed な単段 handoff | v0.12.0 handoff の単段縮約＋Release 内容・単一 tag push・Issue close 集合・同期先 preflight の試験 |

## 2. 入力・参照資料

- Issue #39〜#44。#44 参照実装 `~/Projects/dir-framework`（HEAD `5ff26a9`、doc-audit.json 無し）。boss 実測: 24 規則すべて
  構文限定変換を通過、tracked 46 件で等価（REVIEW.md）。Issue #39 実測: 2 run 間は remediation commit `892b500`+`118ff46`
  のみ（changeSetSha は相違）、内容不変 24/88 文書が verdict 変化。
- 本 repo アンカー（Evidence Pack＋boss 実機確認＋Sol/Opus 引用）:
  - `scaffold.py:247-300,145-161,164,27`。doc-audit.json/impactMap を書く既存経路は無い。
  - `resolve-impact.py`: ローカル `glob_to_regex` `:45-62`／`matches` `:68`、`tokens_for()` `:128-132`、mapped `:188-196`、
    `doc_files` `:200-201`、cap/counts `:249-273`。`glob_to_regex` 複製は `docaudit_paths.py:8`・`generic-layers.py:29`・
    `impact-supplement.py:45`（変更しない）。`validate_repo_path` `:37`。
  - `impact-supplement.py:5-9`（優先順位 docstring）、`:274-300`（`residual = max_impacted_docs - len(impacted)`）。
    `SKILL.md:322` 付近（順序記述 `mapped ≥ heuristic ≥ graphify ≥ semantic`）。
  - `compute-baseline.sh:33,48-49`（変更しない）。`start-run.py:162`（config sha 再照合）、`:171-174,190-191,201-210`。`seal-run.py:34`。
  - `plan-dispatch.py:74,92-99`。`check-verdicts.py:23,96,106,174,216`（exit 0・直接読取は診断専用として維持）。
    `codex-dispatch.py:47,67-73,92-126`。
  - `decide-verdict.py:24-25,252-275,629,724-725,785-790,198-224,817-826,832,875,33-40,380-387`。
  - `docaudit_cache.py:11-19`、`:68-83`（cache 適格タプル `(contentSha, changeSetSha, contractVersion, backend)`）、`:86`。
  - `open-run.py:87-111,129-134,138,164-172,191-209`。`SKILL.md:19-24`（`--break-lock` は「run only open-run --break-lock … and exit」
    の早期 exit 段落）、`:25`（lock 取得側の open-run 行）、`:335`（CACHED は検証器へ送らない）。
  - `write-evidence.py:38-50`。`codex-probe.sh:28-37`、`:44-51`（`enabled:false` → `reason:disabled-by-config`、available:false）、`:55`。
  - `SKILL.md:300-341`（Phase 2: supplement `:309` → plan-dispatch `:329` → start-run `:335`、末尾に**封印前 manifest の生 parse**
    指示 `phase3Backend/phase4Required/…`）、`:359`（seal-run）、`:373`（codex-dispatch 行）、`:379`、`:389`（workflow 起動）、
    `:428`（Phase 4 gate は `phase4Required` を直接使用）、`:474-512`（`:477` 無条件 full skip、`:485` baseline 検査）、`:514-521`、
    `:600-672`（`:617-619` codex 行）。
  - `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md:192,345-356,386-394`（codex 行 3 状態・
    非ブロッキングの SSoT — v0.13.0 で改訂対象）。
  - `generic-layers.py:175-178,187-198,201-223,226-234,246,270-284,306-311,325-354`。既存 engine fixture は 0.10.1 のみ。
  - provenance 消費側（7 面）: `agents/doc-impact-verifier.md:15,36-38`、`-light.md:37-38`、`workflow-template.js:2,153,160`、
    `codex-dispatch.py:92-126`、`impact-supplement.py:5-9`、`docs/ADOPTION.md:173`／`.ja.md:158`、`docs/PROMPTS.md:64-66`／
    `.ja.md:63-65`。加えて `tests/test_workflow_template.py:361-366`（全 provenance 値のタプル assert）。
  - 版文字列 5 面: `.claude-plugin/plugin.json:3`、`engine-shas.json:17`、`docs/ADOPTION.md:139,206,229,266`、
    `docs/ADOPTION.ja.md:124,191,214,250`、`tests/test_scaffold.py:213,216-217,283`。
  - 前回 handoff: `tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh`（228 行、`:106` 対象 tag のみ push、`:198`
    `DOCAUDIT_SKILLS_DIR`）、`tests/test_release_handoff.py`（435 行、`:268` override 使用）。
  - テスト 368 件 green（2026-08-27）。

## 3. 担当（boss）

Fable。計画・批判運営・全行 diff レビュー・検証再実行・route-close。実装は書かない。

## 4. 実行者（worker）— 各 Stage 末に**フルスイート green**

| Stage | 内容 | モデル / effort |
|---|---|---|
| S1 | #43: 0.12.0 engine fixture 保存＋hash 固定 → 3 修正＋対テスト → 版 bump 0.13.0（5 面）・`engine-shas.json`・`test_scaffold`。`tests/test_v013_contracts.py` 骨格 | Terra `medium` |
| S2 | #40／#39 resolve-impact（`--history`・`regression`・`historySha`）／plan-dispatch（`historySha` 照合＋dispatch.json 内 `impactSha`）／impact-supplement 優先順位／`test_workflow_template.py` タプル更新／契約 assert | Terra `medium` |
| S3 | #44 `import-audit-scope.py`＋テスト＋config-schema／init SKILL・audit SKILL Phase 0 配線／`source` 互換試験／契約 assert | Terra `medium`（不足時 `high`） |
| S4a | 封印連鎖: `read-manifest.py`／start-run（`provenance`・`auditScopeSha`・照合）／seal-run／decide-verdict（provenance・auditScopeSha の REFUSED 条件・flip 集計）／codex-dispatch（read-manifest 経由）／check-verdicts 診断／SKILL Phase 2-4 の manifest 再束縛／統合試験 2 本＋契約 assert | Sol `high` |
| S4b | #42: `codex-review-plan.py`／decide-verdict（`required`・`codexReview` evidence・表示分離）／start-run `phase4Required`／codex-probe／SKILL Phase 4-5 配線／設計 spec 追記＋契約 assert | Sol `high` |
| S5 | #41 docs／ADOPTION・PROMPTS・config-schema 最終整合／`release-handoff.sh`（単段縮約）＋handoff 試験 | Terra `medium`（純文書は Luna `medium` 可） |

各 Stage は独立 codex セッション（ID を REVIEW.md へ）。差し戻しは `codex exec resume <ID> -c model_reasoning_effort=medium`。

## 5. 成果物

- 新規: `skills/audit/scripts/import-audit-scope.py`、`skills/audit/scripts/read-manifest.py`、`skills/audit/scripts/codex-review-plan.py`、
  `tests/test_import_audit_scope.py`、`tests/test_read_manifest.py`、`tests/test_codex_review_plan.py`、`tests/data/audit-scope/`、
  `tests/data/engine-0.12.0.py`、`tests/test_v013_contracts.py`、`tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh`、同 `pr-body.md`。
- 変更: `resolve-impact.py`、`generic-layers.py`、`decide-verdict.py`、`start-run.py`、`seal-run.py`（必要最小）、`check-verdicts.py`
  （診断のみ）、`plan-dispatch.py`、`codex-dispatch.py`、`impact-supplement.py`、`codex-probe.sh`、`skills/audit/SKILL.md`、
  `skills/init/SKILL.md`、`skills/audit/references/`（config-schema.md、default-heuristics.md、engine-shas.json、workflow-template.js）、
  `agents/doc-impact-verifier*.md`、`docs/ADOPTION*.md`、`docs/PROMPTS*.md`、
  `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md`（改訂追記）、`.claude-plugin/plugin.json`、
  `tests/test_*.py`（§11）。
- 記録: `PLAN.md`、`REVIEW.md`。

## 6. 完了条件（DoD）— 機械判定可能な形で

- [ ] `python3 -m unittest discover -s tests -t .` 全 green（≥ 368＋新規、各 Stage 末と最終で実数記録。boss 再実行で追認）。
- [ ] #44 `tests/test_import_audit_scope.py`:
      (i) 構文限定変換の正例・反例（両方言で食い違う具体パス `*/foo` vs root `foo`、`**/*` vs root ファイル、`?` vs `a/b`）。
      許可範囲で `fnmatch.translate` と resolve-impact の `matches` が合成パス集合で一致。
      (ii) 検査順序: `scope absent && metadata absent` は git 列挙前に `absent`／exit 0（CR/LF 名を含む非導入 fixture で git を 1 回も
      呼ばないことを shim で固定）。導入時は tracked＋untracked を NUL 列挙し CR/LF 名は error；scope の規則キー・影響先文字列
      自体の CR/LF も error。`equivalenceChecked ≥ 1`（0 件 error）。
      (iii) 重複 key／空影響先／不在影響先／非文字列／不正値／`docGlobs` 外／`impact:none` 以外の object を拒否。report 除外の
      対試験（`auditReportsInCorpus` false → report path の影響先のみ拒否、true → 受理）。(iv) `impact:none` スキップ。
      (v) `--write` 順序契約: run-base 不在なら symlink 検査後に 0o700 で作成（`.claude/state` 不在の fresh repo 試験）→ lock
      （O_EXCL＋O_NOFOLLOW → flock → inode 一致確認）→ lock 内で config/scope を読み直し expect SHA 照合（exit 4）→ 生成 →
      原子置換 → inode 一致確認して unlink。故障注入を replace 前（旧 config 不変・lock 不在）と replace 後 dir fsync（完成 JSON
      のみ存在・lock 不在）に分離。flock 保持中は `--break-lock` 拒否（実プロセス）。flock 前 unlink（inode 不一致）は無変更停止。
      `source:"audit-scope"` 項目の全置換と他項目保全（`note` が `auto: audit-scope` で始まる手書き項目を含む）。初回作成:
      `--base-config -`（stdin）＋`--expect-base-config-sha <sha>` 必須、既存 config があれば拒否、stdin bytes の sha 不一致で exit 4。
      (vi) `--check` 4 経路の drift（scope 変更／auto 手編集／auto 削除／metadata ありで scope 消失）＋重複 auto 項目 1 件削除の
      drift（multiset）＋`absent`／`not-imported`／`in-sync`。`auditScope` metadata 型異常（非 object、`path` 非文字列/絶対/repo 外、
      `sha256` 形式違反、`rules` 非 int または bool、`importedAt` 非文字列）は error。反復 `--doc-glob`: 2 つの glob にだけ属する
      影響先を各 1 件用意し両方受理。カンマを含む 1 glob。
      (vii) `--config`/`--scope` の包含・symlink 拒否（存在検査と分離）。custom `--scope` の metadata 保存と Phase 0 契約。
      (viii) `source` 互換: 有無だけが異なる config で resolve-impact 出力が完全一致。
      boss 実物検査: dir-framework 一時コピー・config 不在で `--check --json --doc-glob '**/*.md'` → `rules=24`・拒否 0・
      `equivalenceChecked=46`。
- [ ] #40: `counts.docCorpus`・`counts.heuristicSaturation`（docCorpus 0 は 0.0・warning なし・正常終了）、9/9 で WARN、丸め前比較、
      `excludeDocPathTokens:true` の効果、cap 超過 `warnings[]`、型検証表（§10）。ADOPTION に「コスト主因は anchor の古さ」段落。
- [ ] #39 resolve/plan-dispatch: `regression` 条件・既存 provenance 優先・full/既定 false/history 不在は無音・破損 warning・
      `historySha` 不一致で非 0・dispatch.json 内 `impactSha`。統合試験 2 本（実プロセス、工程 resolve → supplement → plan-dispatch →
      start-run → seal-run → returns/phase4 evidence → decide-verdict）: (A) regression ≥ 1 件が dispatch に残り cached でない、
      (B) mapped 2・regression 2・heuristic 2 を用意し `maxImpactedDocs: 3` → impacted は **mapped 2＋regression 1、heuristic 0、
      `truncated=true`**（順序 mapped ≥ regression ≥ heuristic ≥ graphify ≥ semantic の固定。regression が cap 落ちする以上
      heuristic は残らない — rev.7 の「heuristic 1 件が残る」は矛盾のため rev.8 改で訂正）。両方で manifest `provenance` ==
      impact.json provenance、partition 通過。
- [ ] #39 gate（flip 集計、§10 の定義）: 3 ケース — (i) 全 4 フィールド一致・verdict 相違 → 1、(ii) **Issue #39 型**: `contentSha`・
      `contractVersion`・`backend` 一致・`changeSetSha` 相違・verdict 相違 → 1（`counts.verdictFlipsUnchangedContentSameChangeSet`
      は 0）、(iii) `contentSha` 相違 → 0。
- [ ] 封印連鎖:
      - `read-manifest.py --run-dir --evidence`: manifest を一度だけ bytes で読み、`EVIDENCE.manifest` と sha256 照合後に同じ bytes を
        `json.loads` して stdout に出す。不一致は非 0・出力なし。`tests/test_read_manifest.py`（改変・置換競合）。
      - start-run: impact.json sha == dispatch.impactSha を照合してから manifest に `provenance`（keys == impacted、enum 7 値）を転記。
        config に `auditScope` があれば scope 実 bytes の sha を metadata と照合（不一致 error）し manifest に `auditScopeSha` を封印
        （無ければ `null`）。
      - seal-run → decide-verdict: (a) impact.json sha == dispatch.impactSha、(b) manifest.provenance == impact.json provenance、(c) 型・
        enum、(d) `auditScopeSha` 非 null なら状態確定直前に scope 実 bytes と照合 — 違反は REFUSED。
      - codex-dispatch は `read-manifest.py` と同じ関数で manifest を読む（`--evidence` 必須）。不一致は子 0 回で非 0。
      - SKILL: Phase 2 末尾の manifest 生 parse は**封印前値で Phase 2 内のみ有効**。**封印後に使う manifest 値はすべて**
        `read-manifest.py` の出力変数から**再束縛**し、Phase 2 の変数名を再利用しない — Phase 3 backend 選択、workflow 起動
        （`:389`）、codex-dispatch の `--timeout-seconds`（`phase3CodexTimeoutSeconds`、`:373`）、Phase 3 の tree-digest 再確認の
        `--exclude`（`digestExclude[]`、`:421`）、Phase 4 の `phase4Required`（`:428`）。`preflightRequired` は Phase 0.5（封印前）
        専用のため対象外。
      - check-verdicts は provenance を `manifestMismatch` 診断に含める（exit 0）。**診断専用のため直接読取を維持する（意図的除外）**。
      試験: plan-dispatch 後 impact 改変 → start-run error／seal 後 manifest 改変 → read-manifest 非 0・codex-dispatch 子 0 回／
      全 SHA 整合 fixture で provenance のみ `unknown` → enum 専用 reason で REFUSED／`--check` 後 seal 前に scope 改変 → gate REFUSED。
- [ ] #42:
      - `codex-review-plan.py --mode --config --available <bool> --available-reason <str>（既定 not-installed） --baseline-ok <bool>`
        → `{action: run|skip|not-active, state, promptVariant: diff|full, reason}`。`tests/test_codex_review_plan.py` は
        **4 軸 16 行**（`available × mode × required × baseline-ok`）の真理値表で action/state を固定。`enabled` は軸に含めない
        （probe が `enabled:false` を `available:false, reason:disabled-by-config` に畳むため。判定表は `--config` から `required`
        のみを読む）。規則: `available:false` → not-active（`reason` = `--available-reason`）；full＋required → run/full；
        full＋optional → skip `skipped-full-run`；incremental＋baseline-ok → run/diff；incremental＋baseline NG → `ref-invalid`
        （run しない）。`state` の値域は gate の enum と同一定数。
      - SKILL Phase 4 手順 3 は判定表スクリプトの出力で分岐し、`action=run` のときだけ `codex exec` を起動（model 選択・retry・state
        記録は run 経路で共有）。契約テスト: Phase 4 のコマンド行に `codex-review-plan.py` があり `--available` の値が
        `"$CODEX_REVIEW_AVAILABLE"` で束縛されていること、`codex exec` 行がその後にあること。
      - gate: config 由来 `required`。evidence `codexReview` 存在時は厳格検証（object・`state` 文字列・enum 5 値、違反 REFUSED）、不在は
        互換。`required:true` かつ `state ≠ completed`（欠落含む）→ REFUSED（history・anchor 非更新、last-run は理由つき更新）。
        `enabled:false`＋`required:true`、`required` 非 bool → REFUSED。表示分離（内部 verdict 3 値、degrade 時のみ report 表示
        `CONSISTENT (codex-review did not run: <state>)`、stdout/last-run/anchor は素の値）。`start-run`: `required:true` なら mode
        無関係に `phase4Required:true`。Phase 5 codex 行 4 状態（not-active／skipped-full-run／completed／did-not-run(<state>)）を
        個別試験。
      - codex-probe.sh: `--version` に加え同じ `$BIN` で `exec --help` を実行（ネットワーク不使用・モデル非起動）。失敗時
        `codexReviewAvailable:false, reason:probe-exec-failed`。**`probeCommands[]`（定義）**: probe JSON の出力キー。実行した
        コマンド列を文字列配列で記録する（例 `["<bin> --version", "<bin> exec --help"]`）。設定キーではない。
      - 設計 spec `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md` に v0.13.0 改訂節を追記（4 状態・
        `codexReview.required` による REFUSED・判定表スクリプト経由・full+required の実行）。
- [ ] #43: 対テスト（`-`／`10.`／引用内 list／非ゼロ列 tab の 4 ケース × 「継続段落は検査される」「空行後の ci+4 以上はマスク」
      「空行なし深インデント継続文は検査される」の 3 面）、複数行 link 後続 finding の path・message・line 完全一致＋link/inline
      code/URL 由来 finding 0 件、`hasattr(module, "_token_base")` False、`tests/data/engine-0.12.0.py` の正規化 hash == engine-shas
      `0.12.0`、0.12.0 stamp → 0.13.0 更新、`test_engine_shas_match_current_generated_bodies`。
- [ ] #41: ADOPTION en/ja 盲点節、codex review プロンプト 3 観点（diff／full 両変種）。
- [ ] `tests/test_v013_contracts.py`（意味単位検査。S1 骨格、各 Stage で追加）:
      (a) init SKILL front matter を解析し `argument-hint` に `--import-audit-scope`；
      (b) audit SKILL Phase 2 の `resolve-impact.py` コマンド行に `--history "$CLAUDE_PROJECT_DIR/.claude/state/docaudit-history.json"`；
      (c) Phase 0: `import-audit-scope.py --check` 行が `--break-lock` 早期 exit 段落の**後**・**lock 取得側**（`--break-lock` を含まない）
      `open-run.py` 行の**前**にあること；check 行の `--scope "$AUDIT_SCOPE_PATH"` と bind 行の `auditScope.path` 参照；`drift`/`errors`
      分岐が lock 取得側 open-run を呼ばず停止し、停止メッセージに `diff.missing/extra` と復旧コマンド（`/docaudit:init
      --import-audit-scope`）を含む記述；`not-imported` 分岐のみ継続；
      (d) init の `--write` 行が `--expect-config-sha "$CONFIG_SHA" --expect-scope-sha "$SCOPE_SHA"`、初回行が `--base-config -
      --expect-base-config-sha "$DRAFT_SHA"`、各変数の bind 行が `--check` 出力参照；
      (e) Phase 4 evidence 組み立てに `codexReview`/`state`、`codex-review-plan.py` 行（`--available "$CODEX_REVIEW_AVAILABLE"
      --available-reason "$CODEX_REVIEW_REASON"`、後者の bind 行が probe JSON の `reason` 参照）→ `codex exec` 行の順；
      (f) Phase 3 workflow 起動行・Phase 3 codex-dispatch 行の `--timeout-seconds`（`:373`）・Phase 3 tree-digest 再確認の
      `--exclude`（`:421`）・Phase 4 の `phase4Required` 参照（`:428`）が**すべて** `read-manifest.py` の出力変数名（Phase 2 の
      変数名ではない）、Phase 3 codex-dispatch 呼出し行に `--evidence "$EVIDENCE"`；
      (g) 7 消費側＋`test_workflow_template.py` タプルに `regression`；(h) config-schema の**設定キー表**に 5 キー行＋impactMap
      項目の `source`、**`## Codex review (Phase 0/4)` 節**に probe 出力キー `probeCommands` の記述（設定キーではないので表には
      載せない）；
      (i) **版 5 面**の一致；(j) 出荷物 path 集合（`skills/`、`agents/`、`docs/`、`.claude-plugin/`、`README.md`、`tests/`）内の
      `0.12.0` 残存が §12 許容リストに限られる。
- [ ] handoff（§12）: 既存 `test_release_handoff.py` を単段版へ縮約して維持し、追加試験 4 点（Release 内容・単一 tag push 否定・
      Issue close 集合・同期先 preflight）。
- [ ] boss の `codex exec review`（Sol `high`）1 回＋全行 diff レビューで差し戻し 0。
- [ ] route-close: `/docaudit:audit` CONSISTENT（incremental/full の別を記録）。

## 7. 変更範囲

**許可パス**: `skills/audit/scripts/{resolve-impact.py, generic-layers.py, decide-verdict.py, codex-probe.sh, import-audit-scope.py(新規),
read-manifest.py(新規), codex-review-plan.py(新規), codex-dispatch.py, impact-supplement.py, check-verdicts.py, start-run.py, seal-run.py,
plan-dispatch.py}`、`skills/audit/SKILL.md`、`skills/init/SKILL.md`、`skills/audit/references/`、`agents/doc-impact-verifier*.md`、
`tests/`、`docs/ADOPTION*.md`、`docs/PROMPTS*.md`、`docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md`
（改訂追記のみ。他の spec は対象外）、`.claude-plugin/plugin.json`、`tasks/route/2026-08-27-issues-39-44-v0.13.0/`（`git add -f`）。
**変更しない**: `tree-digest.py`・`write-verdict.py`・`write-evidence.py`・`open-run.py`・`docaudit_paths.py`・`compute-baseline.sh`。
EVIDENCE のキー集合。
**禁止**: `~/Projects/dir-framework` 書き込み、`.gitignore`、`~/.claude/skills/docaudit/`、`.claude/`、セルフマージ・`gh pr merge`・
`gh release create`、generic-layers.py の repo 内 import、report token 追加。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。** durable 規約変更は上記 spec 1 本のみ
（AGENTS.md / PROJECT.md は 0 ファイル更新）。

## 8. 検証コマンド一式

```bash
python3 -m unittest discover -s tests -t .                                                        # 各 Stage 末＋最終
python3 -m unittest tests.test_generic_layers tests.test_scaffold tests.test_v013_contracts -v    # S1
python3 -m unittest tests.test_resolve_impact tests.test_impact_supplement tests.test_workflow_template tests.test_wp12_contracts tests.test_v013_contracts -v   # S2
python3 -m unittest tests.test_import_audit_scope tests.test_v013_contracts -v                    # S3
python3 -m unittest tests.test_decide_verdict tests.test_start_run tests.test_check_verdicts tests.test_codex_dispatch tests.test_read_manifest tests.test_v013_contracts -v  # S4a
python3 -m unittest tests.test_decide_verdict tests.test_codex_probe tests.test_start_run tests.test_codex_review_plan tests.test_v013_contracts -v  # S4b
python3 -m unittest tests.test_release_handoff tests.test_v013_contracts -v                       # S5
python3 skills/audit/scripts/import-audit-scope.py --repo-root <tmp-copy> --check --json --doc-glob '**/*.md'   # boss 実物検査
/docaudit:audit                                                                                   # route-close
```

## 9. #44 確定設計 — `import-audit-scope.py`

**入力**: `--repo-root`、`--config`（既定 `.claude/doc-audit.json`）、`--scope`（既定 `.claude/audit-scope.json`）、`--doc-glob`（反復可）、
`--check`（既定）｜`--write`、`--json`、`--expect-config-sha`・`--expect-scope-sha`（`--write` 必須）、`--base-config -`＋
`--expect-base-config-sha <sha>`（初回作成。config が存在すれば拒否。stdin bytes を lock 内で一度だけ読む）。stdlib のみ。

**検査順序**: (0) `--config`/`--scope` のパス安全（包含・symlink）。(1) scope 不在かつ metadata 不在 → `absent` exit 0（git を呼ばない）。
(2) metadata 型契約（object、`path` repo 内 relative、`sha256` 64hex、`rules` int ≥ 0 かつ非 bool、`importedAt` 文字列。違反 error）。
(3) scope 読み込み・規則検証（重複 key（`object_pairs_hook`）・最上位非 object・値の型（非空文字列配列 or `{"impact":"none"}` のみ）・
裸 catch-all（`*`・`**`・`**/*`）・CR/LF）。(4) 影響先の実在（`validate_repo_path`）・docGlobs（report 除外後 corpus）一致（外は
「`docGlobs` を拡張してから再実行」の指示つき error）。(5) tracked＋untracked を NUL 列挙し CR/LF 名は error、規則ごとの等価二次
検査（`equivalenceChecked`、0 件 error）。(6) 変換・再生成・照合。error ≥ 1 で何も書かず exit 1。

**変換（構文限定）**: fnmatch の `*` 連続は `.*`、docaudit の `**`（`/` 非後続）も `.*`。各 `*` 連続 → `**`。置換後 `**` の直後が `/`
（fnmatch `*/`・`**/`。docaudit では `(?:.*/)?` に化ける）、`?`（fnmatch は `/` を跨ぐ）、`[`（docaudit に文字クラス無し）、先頭 `./`、
末尾 `/`、空、裸 catch-all は拒否。

**`--write` 順序**: run-base（`.claude/state/docaudit-run`）不在なら各構成要素の symlink 検査後に 0o700 で作成 → lock（O_EXCL＋
O_NOFOLLOW → `flock(LOCK_EX|LOCK_NB)` → fd/path inode 一致確認、holder `{"owner":"import-audit-scope","runid":null,"startedAt"}`、
既存は exit 3）→ lock 内で config（または stdin draft）/scope を読み直し expect SHA 照合（exit 4）→ `source=="audit-scope"` 項目を
全置換（他項目は `note` 内容にかかわらず順序・内容保全）し `auditScope:{path,sha256,importedAt,rules}` を加えた完成 config を一時
ファイル→`os.replace` で原子作成（indent=2・ensure_ascii=False・末尾改行）→ `finally` で inode 一致を確認して unlink・flock 解放。
`{"impact":"none"}` は `skippedNoImpact[]`（heuristic が同文書を拾い得る旨を出力）。

**`--check`**: 再生成 auto 項目（multiset）と config の `source=="audit-scope"` 項目・metadata を照合。`absent`／`not-imported`（exit 2）
／`drift`（exit 2。metadata ありで scope 消失・sha 不一致・multiset 不一致）／`in-sync`。JSON `{state, rules, translated,
skippedNoImpact[], errors[], equivalenceChecked, configSha, scopeSha, diff:{missing[],extra[]}}`。

**配線**:
- audit SKILL Phase 0: `--break-lock` 早期 exit 段落の後段で `AUDIT_SCOPE_PATH`（config `auditScope.path`、無ければ既定）を bind し
  `--check --json --scope "$AUDIT_SCOPE_PATH"` → `drift`／`errors` は lock 取得側 open-run を呼ばず停止（メッセージに
  `diff.missing/extra` と復旧コマンド `/docaudit:init --import-audit-scope` を含む）、`not-imported` は 💡 で継続 → open-run。
  Phase 5 の status 行は追加しない。
- init SKILL: `--import-audit-scope`（既存 config があっても許可される例外、argument-hint に追加）: `--check --json` の diff と
  `configSha/scopeSha` を提示 → AskUserQuestion 承認 → `--write --expect-config-sha "$CONFIG_SHA" --expect-scope-sha "$SCOPE_SHA"`。
  初回 init: Step 3 承認後、承認済み draft を Write tool で `$TMPDIR` 等 repo 外に書き、その sha を `DRAFT_SHA` として
  `--write --base-config - --expect-base-config-sha "$DRAFT_SHA" --expect-scope-sha "$SCOPE_SHA" < draft` で完成 config を一度で作成。
  Step 2 の impactMap 起草は scope があれば `--check --json --doc-glob <draft の docGlobs>` の変換結果を STARTER に（mentions 起草
  より優先）。
- docs: config-schema.md に `auditScope` 行と impactMap 項目の任意キー `source`（予約値 `audit-scope`）。ADOPTION §6 に
  「audit-scope.json がある場合」節。run 間の import は `--accept-config` 不要（exit 6 は実行中 config 変更で REFUSED した場合のみ）、
  run 中は lock で拒否。

**不採用**: UNMAPPED fail-closed の Phase 2 持ち込み（将来 `impactMap.strict` として別 Issue）。DOTALL 化。compute-baseline の変更。
Phase 5 audit-scope status 行。

## 10. #40 / #39 / #42 / #43 / #41 確定設計（自己完結）

**#40**（resolve-impact.py）
- `counts.docCorpus = len(doc_files)`（report 除外後）、`counts.heuristicSaturation = round(len(heur_only)/docCorpus, 3)`（pre-cap。
  docCorpus 0 なら 0.0）。**比較は丸め前**。`heuristics.saturationWarnRatio`: bool を除く数値（int/float）、既定 0.5、`0` で無効、
  負数/1 超/文字列/bool は warning＋既定値。`heuristicOnly > 0` かつ比率 ≥ 閾値で `warnings[]` に `heuristic saturation: <heur>/<corpus>
  docs (<pct>%) reached only by the token heuristic — impactMap is not carrying the selection; promote couplings from
  mapGapCandidates to impactMap`（corpus 下限なし）。
- `heuristics.excludeDocPathTokens`（bool、既定 false、非 bool は warning＋既定値）: true なら docGlobs に一致する変更パスから token を
  生成しない。`regressionRecheck` 非 object／`enabled` 非 bool は warning＋既定値。
- cap 超過の stderr 警告を `warnings[]` にも入れる。
- docs: ADOPTION §6 に「健全な設定は選択の大半が mapped。heuristic は残差」「**コストの主因は anchor の古さ（maxImpactedDocs では
  ない）**。実測 92 docs ≈ 3.6M tokens、単一 commit 窓の中央値 ≈ 18 docs」。default-heuristics.md 同期。

**#39**
- resolve-impact.py: `--history PATH`（任意）。`regressionRecheck.enabled`（既定 false）。incremental のみ。`parse_history` で読み、path
  ごとの最後の entry が `FAIL` なら候補。docGlobs 一致・report 除外・実在を満たすものを provenance 集合に `regression` として追加。
  `provenance()` は既存規則を優先し、`regression` 単独のときのみ `"regression"`。**cap 優先順位 `mapped ≥ regression ≥ heuristic ≥
  graphify ≥ semantic`**（`SKILL.md:322` 付近の順序記述・`impact-supplement.py:5-9` docstring・`docs/ADOPTION*.md` の該当行も同順に
  更新）。`counts.regression`。history 不在は無音（`counts.regression=0`）、破損は `warnings[]` に 1 行。有効時 `historySha`（読んだ
  history bytes の sha256、不在は null）。
- plan-dispatch.py: impact.json に `historySha` があれば自身の読取 SHA と照合し不一致は非 0（「history changed between resolve and
  dispatch」）。supplement 後 impact.json の sha256 を `impactSha` として **dispatch.json 内**に記録（EVIDENCE のキー集合は不変）。
- 封印連鎖は §6 のとおり（read-manifest.py／start-run／seal-run／decide-verdict／codex-dispatch／SKILL 再束縛／check-verdicts 診断）。
- 7 消費側＋`test_workflow_template.py` に `regression`: 「前回 FAIL・内容不変の再検証。以前の指摘クラスが実際に解消しているかを
  確認する。impactMap-gap 候補ではない」。SKILL Phase 2 のコマンドに `--history "$CLAUDE_PROJECT_DIR/.claude/state/
  docaudit-history.json"`。init draft は `regressionRecheck:{enabled:true}` を提案（既存 config には触れない）。
- decide-verdict.py（**flip 集計、boss 再裁定後の定義**）: history 追記の直前に、dispatch された各 path について最後の history entry が
  `contentSha`・`contractVersion`・`backend` 一致かつ `verdict` 不一致なら flip としてカウント（`changeSetSha` は条件に**含めない**）。
  gate stdout JSON `counts.verdictFlipsUnchangedContent` と `counts.verdictFlipsUnchangedContentSameChangeSet`（上記のうち
  `changeSetSha` も一致した件数）。N>0 で `warnings[]` に `verdict instability: N document(s) changed verdict with unchanged content
  since the previous run (M with an unchanged change set) — single-pass verification samples the defect pool; "fix these N and
  re-run" is not guaranteed to converge (see ADOPTION)`。docs に「文書内容が不変でもコード側の変更で verdict が正当に変わり得る。
  同一 change set の件数 M が純粋なブレの下限」と注記。
- docs: ADOPTION en/ja・SKILL Phase 5 に「単発検証の限界」と「欠陥クラス単位で横断掃除する」推奨。多数決は据え置き。

**#42**
- config `codexReview.required`（bool、既定 false）。config-schema.md に追記。必須性は config のみから導出（gate は `decide-verdict.py:629`
  で SHA 固定済み config を読む）。
- phase4 evidence（`write-evidence.py --name phase4` payload）に `codexReview: {state}`（state ∈ `{completed, execution-failed,
  ref-invalid, skipped-full-run, not-active}` — **判定表 `codex-review-plan.py` の `state` 値域と同一集合**。gate・判定表・テストは
  同じ定数を参照する）。SKILL Phase 4 手順 3 の末尾で orchestrator が `CODEX_REVIEW_STATE` から組み立てる。evidence 内の
  `required` は読まない。
- 判定表 `codex-review-plan.py`・gate 条件・表示分離・`phase4Required`・Phase 5 4 状態・probe・`probeCommands[]`・設計 spec 追記は §6 のとおり。
- full 用プロンプトの対象は「`manifest.head` で識別され `worktreeDigest` で封印された現在の worktree（未 commit・未追跡を含む）に
  おける impacted 全文書 vs code」。`-s read-only`・`--output-schema` は diff 変種と同一。#41 の 3 観点は両変種に入れる。
- SKILL Phase 0・ADOPTION に「probe は CLI 存在と `exec` サブコマンド到達の確認であり、Phase 4 の実呼び出し形状（sandbox/permission/
  wrapper 引数）は検証しない。wrapper が必要な環境は `codexReview.bin` に wrapper を指定し、確実性が要るなら `codexReview.required:
  true`（最初の baseline 確立後に有効化を推奨）」。

**#43**（generic-layers.py）
1. `_mask_indented`: CommonMark 準拠の簡易状態機械。tab は**次の 4 列境界**まで展開して列を数える。list 項目行（`_strip_container_markers`
   で marker を剥がせる行）で `content_indent = marker 列 + marker 幅 + 後続空白（5 以上は 1）`。**インデントコードは段落を中断できない**:
   直前の非空行が段落（非コード・非空）なら、インデント量にかかわらず継続段落としてマスクしない。空行の後の非空行のみ、
   `indent ≥ content_indent + 4`（list 外は `≥ 4`）でコード。`content_indent ≤ indent < +4` は継続、`< content_indent` で list 終了
   （状態破棄、以後は list 外規則）。引用 `>` は container 剥離後の列で判定。入れ子 list は最内の項目で更新。
2. `extract_bare_paths`: `_LINK_RE.sub` を改行保持（`_blank_keep_newlines` 相当）に置換。順序 `_LINK_RE → _INLINE_CODE_RE → _URL_RE` は維持。
3. `_token_base` を削除。
- S1 の先頭で `tests/data/engine-0.12.0.py` を保存し正規化 hash == engine-shas `0.12.0` を固定してから修正。修正後 `engine-shas.json` に
  0.13.0 エントリ（`_harness_sources()`→`_normalized_sha()` で算出）。`test_scaffold` の版固定を 0.13.0 に更新し、0.12.0 stamp →
  0.13.0 の更新テストを追加。

**#41**
- ADOPTION en/ja に「Phase 3 の構造的盲点」節: (1) 複数文書間の矛盾 (2) docGlobs 外（src コメント・dotfile・生成物ヘッダ）の参照
  (3) 手順の実行可能性。文言は「Phase 3 単独ではこれらを保証しない。Phase 4 の code/security review・codex review（incremental、
  または full＋required）・gate の sibling scan が横断的な補完層」（「唯一」の断言はしない）。固定 report 行は不採用。
- SKILL Phase 4 のプロンプト構成（diff／full 両変種）に 3 観点を追加（変更に関係する範囲で: 他文書・`.env*`/`.envrc`/src コメント
  との矛盾、`X.md §N` 型参照の実在、手順の前提条件）。

**互換性影響一覧（全利用者に影響。docs と Release notes に明記）**: gate の REFUSED 条件追加（provenance 整合・`auditScopeSha`・
`codexReview` evidence 厳格検証・`required` 型）、manifest `provenance`/`auditScopeSha`・dispatch `impactSha` の追加（版跨ぎの
in-flight run は `--break-lock`）、Phase 3/4 の manifest 読取が `read-manifest.py` 経由に、codex-dispatch の `--evidence` 必須化、
Phase 4 の codex 分岐が判定表スクリプト経由に、`counts` の追加キー、Phase 5 codex 行の 4 状態化、check-docs エンジン 3 修正、
設計 spec の改訂。`regressionRecheck`・`excludeDocPathTokens`・`required`・`auditScope` は既定で無効／不在。

## 11. 意図的差分リスト

- `test_scaffold.py`（版・engine-shas）、`test_resolve_impact.py`（counts 追加キー・historySha）、`test_start_run.py`／`test_decide_verdict.py`
  ／`test_wp12_contracts.py`／`test_check_verdicts.py`／`test_codex_dispatch.py`（manifest `provenance`/`auditScopeSha`、dispatch `impactSha`、
  gate stdout 追加キー、codex-dispatch の `--evidence` 必須化）、`test_codex_probe.py`（`probeCommands[]`、偽 bin の `exec --help`）、
  **`test_workflow_template.py:361-366`（provenance タプルに `regression` を追加）**、`test_release_handoff.py`（単段版へ縮約、二段固有
  分岐は削除、`DOCAUDIT_SKILLS_DIR` は維持）。上記以外の既存 assert 変更は禁止（必要なら報告のみ）。

## 12. リリース手順（単段・fail-closed、v0.12.0 handoff の縮約）

- 版 0.13.0。`0.12.0` 残存の許容リスト（出荷物 path 集合内）: `docs/ADOPTION.md:139`・`.ja.md:124`、「v0.12.0 behavior changes」
  段落（en/ja）、`--refresh` 版遷移説明、`engine-shas.json` の 0.12.0 キー、`tests/test_scaffold.py` の旧 stamp 更新テスト、
  `tests/data/engine-0.12.0.py`。
- ブランチ `feat/v0.13.0-issues-39-44`、Conventional Commits、`pr-body.md`。マージはユーザー。
- **Release title（完全一致）**: `docaudit v0.13.0 — audit-scope import, regression recheck, strict codex review`。tagName
  `docaudit--v0.13.0`。body 必須要素: 完全 SHA・`#39`〜`#44`・`codexReview.required`・`--break-lock`。
- `release-handoff.sh <approved-merge-full-sha> <pr-number>`: 前回スクリプトから v0.11.0 遡及段を削除し版を差し替える。順序: 引数検証
  → fetch → branch==main・HEAD==origin/main==SHA・tracked clean → **同期先 preflight**（`DOCAUDIT_SKILLS_DIR` override 維持。正規化
  した同期先が `DOCAUDIT_SKILLS_ROOT`（既定 `~/.claude/skills`）配下・非 symlink・書込可能）→ 対象 SHA で unittest → tag（既存は
  SHA 一致検証）→ **単一 refspec push** `git push origin refs/tags/docaudit--v0.13.0:refs/tags/docaudit--v0.13.0` → Release → Issue
  close（集合 `{39..44}` 各 1 回、冪等）→ 同期確認（`y` のみ）→ 同期（archive 方式・hide/protect filter・`rsync --delete`・diff 検証・smoke）。
- 試験: 既存 `test_release_handoff.py` の分岐（SHA 引数・fetch・tag 不一致・再開・symlink・完全成功・不正 Release）を単段版へ縮約して
  維持。**追加 4 点**: (1) 全成功・再開ケースで tag → approved SHA、Release tagName/title/body を検査、(2) ローカルに無関係 tag を
  置いても push されない、(3) Issue close の対象集合が `{39,40,41,42,43,44}` で各 1 回、(4) 同期先 preflight 失敗（symlink／root 外）
  で tag/Release/close/rsync が 0 回。

## 13. 進行順序

1. 手順 3: Sol R1〜R5 完了（上限） → 手順 3.5: Opus R1 反映（rev.7）→ Opus 再依頼で「指摘なし・実装承認」→ PLAN 確定。
2. S1 → boss diff/テスト再実行 → S2 → S3 → S4a → S4b → S5。
3. 手順 5: `codex exec review`（Sol high）→ 手順 6。
4. 手順 7: route-close → 手順 8: 報告（handoff はユーザー実行）。
