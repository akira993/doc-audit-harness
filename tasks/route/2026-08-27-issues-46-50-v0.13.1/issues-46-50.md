<!-- Issue #46 -->
# docs: README.md is stale since v0.10.0 (missing --import-audit-scope, codex Phase-3/required, Phase-5 status lines, What's new 0.11–0.13)

## 概要
`README.md` は v0.10.0（commit `a9b8a17`）以降一度も更新されておらず（`git log --oneline -5 -- README.md`）、v0.11.0 / v0.12.0 / v0.13.0 の利用者向け変更が反映されていない。手順が失敗する記述は無いが、v0.13.0 の主要機能が README から到達不能になっている。

検出: 2026-08-27 の文書整合レビュー（v0.13.0 出荷直後、HEAD `3a6068b`）。

## 所見
1. **[medium] `README.md:95` — init のフラグ一覧に `--import-audit-scope` が無い。** `skills/init/SKILL.md:4` の `argument-hint` は `[--scaffold] [--harness] [--refresh] [--reask] [--import-audit-scope]`。Issue #44 の機能が README からは見つからない。audit 側 `[--full] [--break-lock] [--accept-config]` は `skills/audit/SKILL.md:4` と一致。
2. **[medium] `README.md:25` — codex の説明が Phase-4 レビュー限定で「absent なら graceful no-op」のまま。** `config-schema.md:26` の `phase3Backend:"codex"`（fail-closed、`skills/audit/SKILL.md:399-416`）と `config-schema.md:36` の `codexReview.required:true`（非 completed は REFUSED）では成り立たない。
3. **[medium] `README.md:61-67` — Usage example のロールアップに codex-review 行・counts 行が無い。** `skills/audit/SKILL.md` Phase 5 は codex-review 4 状態行（:655-662）、run-class / cache / harness / pre-flight / mdq 等の状態行、`counts.verdictFlipsUnchangedContent`（:608-609）を必須としている。「illustrative」ではあるが実出力と大きく異なる。
4. **[medium] `README.md:66` — 例の `/code-review ⚠ 1 medium` が README:14-15 自身（`/code-review` は user-invocation-only）と `skills/audit/SKILL.md:666`（`not-model-invocable` 表示）に矛盾。** 自律実行の既定では出ない表示を代表例にしている。
5. **[low] `README.md:72-81` — 「What's new in 0.10.0」節しか無い。** 抜けている版: 0.11.0（bare-path detection / per-layer corpus config / report self-exclusion）、0.12.0（#37 gate-writes-report、#28 codex Phase-3 backend）、0.13.0（#44 audit-scope import、#40 saturation + `excludeDocPathTokens`、#39 `regressionRecheck` + flip counts、#42 `codexReview.required`、#43 engine 修正）。
6. **[low] `README.md:37` — skills-dir インストールが `cp -R` のみ。** `docs/ADOPTION.md:206-208` は同じ cp の後に `.git` と `tests` を落とす任意手順を示しており README 側だけ欠落。
7. **[low] `docs/PROMPTS.md` / `docs/PROMPTS.ja.md` — `--import-audit-scope` を扱うパターンが無い**（存在しないフラグは 0 件、両言語パリティは維持）。

## 提案
- 1〜4 は README の該当行を現行挙動に合わせる。3 は「主要行のみ抜粋」と明記する案でも可。
- 5 は版ごとの追記をやめ、`docs/ADOPTION.md` の版別記述（:139, :244, :281, :465）へのリンク 1 行に置き換えると負債化しない。


<!-- Issue #47 -->
# docs: digestExclude allowed values are documented as globs (.claude/state/**) but tree-digest.py rejects globs → REFUSED

## 概要
`digestExclude` の許可値をスキーマ・ADOPTION の表記どおりに書くと、`tree-digest.py` が glob を拒否して seal が失敗し、run が **REFUSED** になる。実装は正しく、文書の記法が誤り。

検出: 2026-08-27 の文書整合レビュー（HEAD `3a6068b`）。`tree-digest.normalize()` を直接呼んで実測済み。

## 所見
1. **[high] `skills/audit/references/config-schema.md:29`** —「only `.claude/state/**`, `.mdq/`, `.codegraph/`, `graphify-out/`, and `.cocoindex_code/` are accepted」。`docs/ADOPTION.md:324` / `docs/ADOPTION.ja.md:305` も「`.claude/state/**` or known generated-data directories」。
   実装 `skills/audit/scripts/tree-digest.py:23-24` は `*` `?` `[` を含む値を無条件で拒否する:
   ```
   '.claude/state/**' -> ERROR digest excludes may not contain globs
   '.claude/state/'   -> .claude/state
   ```
   `seal-run.py:63-69` が `ValueError` で失敗し、`decide-verdict.py:291-298` が `Refused` を送出する。他キー（`docGlobs` / `diffGlobs` / `protectedGlobs`）が全て glob なので、利用者は `**` を有効な記法と読む。
2. **[medium] 許可リストから `.claude/worktrees` が漏れている。** `tree-digest.py:25-27` と `start-run.py:18-21`（`BUILTIN_EXCLUDES`）は `.claude/worktrees` / `.claude/worktrees/*` を許可する。

## 提案
- 記法を非 glob の literal プレフィックス（`.claude/state`（配下含む）、`.claude/worktrees`、`.mdq`、`.codegraph`、`graphify-out`、`.cocoindex_code`）に改め、「glob は使用不可（`*?[` を含む値は REFUSED）」を config-schema と ADOPTION（en/ja）の 3 か所に明記する。
- 併せて `tests/` に「文書の例示値がそのまま `normalize()` を通る」契約テストを 1 本足すと再発しない。


<!-- Issue #48 -->
# docs: skills/audit/SKILL.md — generic-layers --config missing (L241), doc-graph update-failed branch, --available bool binding (+6 low)

## 概要
`skills/audit/SKILL.md` のスクリプト呼び出し 43 本を各 `--help` / 実装と突合した結果、フラグ誤記・exit code 誤りは 0 件だったが、そのまま実行すると 1 コマンドが argparse エラーになる／表示が実態を誤伝える medium 3 件と、変数束縛の記述不足 low 6 件がある。

検出: 2026-08-27 の文書整合レビュー（HEAD `3a6068b`）。medium 3 件は実物で追認済み。

## medium
1. **`SKILL.md:241` — `generic-layers.py --layer all --format json` に必須の `--config` が無い。** `--help` は `--config CONFIG` が `required=True`。記述どおりだと `error: the following arguments are required: --config`（exit 2）で Phase 0.5 の broken 診断が失敗する。`SKILL.md:254` に完全形があるので同じ形に揃える。
2. **`SKILL.md:674-677` — doc-graph 状態行に `reason:update-failed` の枝が無い。** `SKILL.md:185` は reason 4 値を宣言し、`graphify-probe.sh:81` は `update-failed` を emit するが、Phase 5 は `DOC_GRAPH_AVAILABLE` false → 「install: …」の 💡 行に落ちる。インストール済みで update 失敗した利用者に「インストールせよ」と出る。symbol-graph（:672 `index-failed`）・semanticSearch（:683）とは非対称。
3. **`SKILL.md:150-153, 513` — `CODEX_REVIEW_AVAILABLE` の束縛ワンライナーが無く、隣の `CODEX_REVIEW_REASON` と同型で書くと `True`/`False` になる。** `codex-review-plan.py:18` は `choices=["true","false"]` のため `invalid choice: 'True'`（exit 2）。`SKILL.md:372` の `SEALED_PHASE4_REQUIRED` は `str(...).lower()` を明示している。同じ形を明記する。

## low
4. `SKILL.md:511` — `BASELINE_SHA` は incremental（:306）でしか束縛されないが full でも `git rev-parse --verify "$BASELINE_SHA^{commit}"` を無条件実行（`codex-review-plan.py:35-40` は full で `--baseline-ok` を無視するため実害なし）。
5. `SKILL.md:606-607` — gate stdout の解析キー列挙に `codexReview:{state,required,degraded}`（`decide-verdict.py:978,1028`）が無い。`{{GATE_VERDICT}}` の説明（:580-589）に degraded 時の `CONSISTENT (codex-review did not run: <state>)` 書き換え（`decide-verdict.py:961-963`）が無い。
6. `SKILL.md:138, 174` — `AX_BIN` / `SYMBOL_GRAPH_BIN` を束縛させるが以降未参照。`workflow-template.js:123,132-134` は `ax` / `codegraph` をハードコードしており、`webExtract.bin` / `symbolGraph.bin` の上書きが Phase 3 に伝わらない。
7. `SKILL.md:237` — `HARNESS_ACTIVE` を束縛させるが未参照（Phase 5 は `HARNESS_STATE`）。
8. `SKILL.md:130` — 「bind `CM_AVAILABLE`/`CM_HEALTHY`/`CM_STATUS`」だが `CM_HEALTHY` を束縛するのは 3 分岐中 1 つだけ（:121-126）。
9. `SKILL.md:657` — 「Phase 4 step 3e」というラベルは存在しない（:163 は「step 3」）。

## 参考（不一致ではないと判定）
- `import-audit-scope.py --check` は文書の 4 状態に加え `error`（`errors[]` 非空を伴う）を返すが、`SKILL.md:28` の「or `errors[]` is non-empty, stop」で捕捉される。


<!-- Issue #49 -->
# docs: ADOPTION en/ja — incomplete REFUSED conditions, Phase-4 severity vocabulary, file map −6, §5 config table −9 keys

## 概要
`docs/ADOPTION.md` / `docs/ADOPTION.ja.md` は英日パリティ（見出し 35 対 35・表 4 本・v0.13.0 追加 5 節・数値）に違反 0 だったが、実装との突合で REFUSED 条件の記載漏れ・severity 語彙の不完全・付録ファイルマップと §5 表の欠落が両言語共通で見つかった。

検出: 2026-08-27 の文書整合レビュー（HEAD `3a6068b`）。

## 所見
1. **[medium] codexReview の REFUSED 条件が実装より狭い。** `ADOPTION.md:134-135` / `.ja.md:119`、`:323` / `.ja.md:304` は「`required:true` で非 completed → REFUSED」のみ。実装 `decide-verdict.py:713-718, 866-869` はさらに (a) `required:true` かつ `enabled:false` → `Refused("codexReview.required conflicts with enabled:false")`、(b) `required` が非 boolean → **`required` の値によらず**無条件 REFUSED、(c) phase4 evidence の `codexReview` が非オブジェクト／`state` が `CODEX_REVIEW_STATES` 外 → REFUSED。
   `config-schema.md:251-253` は (a)(b) を書いているが「With `required:true`, … a non-boolean `required` makes the gate REFUSED」と条件節に含めており自己矛盾（非 boolean のとき `required:true` は成立しない）。`"required": "true"`（文字列）の打ち間違いで strict mode 未使用の全 run が REFUSED になることが文書から予測できない。
2. **[medium] Phase-4 severity マッピングが不完全。** `ADOPTION.md:447-448` / `.ja.md:420-421` は「high → FAIL、medium → WARN」のみ。実装 `decide-verdict.py:30` は `FAIL_SEVERITIES = {"FAIL","HIGH","CRITICAL"}`、`:276-279` は `PASS/WARN/MEDIUM/LOW/INFO` 以外を `Refused("unknown finding severity")` にする。`docAuditCommands` に `ERROR` / `BLOCKER` 等を出すツールを配線すると run 全体が REFUSED になるが、どこにも書かれていない。
3. **[medium] 付録のファイルマップ（`ADOPTION.md:599-646` / `.ja.md:561-608`）が実物より 6 件少ない。** `skills/audit/scripts/` 36 本に対し 31 本。欠落: `codex-dispatch.py`、`codex-review-plan.py`、`import-audit-scope.py`、`read-manifest.py`、`write-template.py`、および `references/codex-phase3-verdict.schema.json`。本文（`:55`, `:57`, `:129`, `:471`）はこれらを参照しており自己矛盾。`import-audit-scope.py` は v0.13.0 の主要機能。
4. **[medium] §5 の config 表（`ADOPTION.md:301-325` / `.ja.md:282-306`、23 行）が正本 `config-schema.md:8-39`（32 キー）より 9 キー少ない。** 欠落: `layerGlobs`、`frontMatterOverrides`、`auditReportsInCorpus`、`indexing`、`contextMode`、`webExtract`、`symbolGraph`、`docGraph`、`semanticSearch`。うち 6 つは §2 散文と `docs/examples/doc-audit.example.json:6-12` に登場するため、表だけ読むと「未文書のキー」に見える。`auditReportsInCorpus` と `layerGlobs` は ADOPTION からは完全に不可視。
5. **[low] `ADOPTION.ja.md:95` と `:320`（v0.13.0 追記箇所）だけ「です・ます体」**で、他は「である体」。

## 提案
- 1: ADOPTION §2 の codex 段落に (a)(b) を各 1 文追加し、config-schema.md:251 の条件節から非 boolean を切り出す。
- 2: 受理 severity の完全な語彙（`PASS/WARN/MEDIUM/LOW/INFO` 非ブロッキング、`FAIL/HIGH/CRITICAL` ブロッキング、それ以外は REFUSED）を §7 か §8 に追記。
- 3: 6 件を両言語同時に追加。
- 4: 表冒頭に「主要キーの抜粋。完全な一覧は `skills/audit/references/config-schema.md`」と明記（表を肥大させない）。


<!-- Issue #50 -->
# docs: references/examples drift — default-heuristics regressionRecheck lacks content-hash condition, unread tool key, models.light notation, example.json 0.13.0 keys

## 概要
`skills/audit/references/` と `docs/examples/` の細部が v0.13.0 の実装に追従していない。単体では小さいが、`regressionRecheck` の説明は #39 の最終修正（`b0987fd`）前の意味のままで、利用者の理解を誤らせる。

検出: 2026-08-27 の文書整合レビュー（HEAD `3a6068b`）。

## 所見
1. **[medium] `skills/audit/references/default-heuristics.md:15-16` — `regressionRecheck` が「latest recorded verdict was FAIL」だけで内容ハッシュ条件が無い。** 実装 `resolve-impact.py:255-257` は `content_sha(repo, path) == entry["contentSha"]`（内容不変）の場合のみ `regression` に入れる。`config-schema.md:32`（"for unchanged documents"）と `ADOPTION.md:183-184` / `.ja.md:166-167` は正しく、この 1 ファイルだけ古い。
2. **[low] `config-schema.md:37-39` — `symbolGraph` / `docGraph` / `semanticSearch` の `tool` キーが runtime 未読であることが未記載。** `:194`（indexing）と `:225`（webExtract）は「`tool` は予約、runtime は読まない」と明記。実装（`codegraph-probe.sh:36-37`、`graphify-probe.sh:39-40`、`cocoindex-probe.sh:40-41`）は `enabled` と `bin` しか読まない。`docs/examples/doc-audit.example.json:10-12` は `tool` を含むので有効なキーに見える。
3. **[low] `config-schema.md:28` / `ADOPTION.md:322` / `.ja.md:303` — 行キー表記 `models.light`。** 実装 `classify-run.py:33` は `config.get("models",{}).get("light",{})` のネスト。トップレベルに literal `"models.light"` を書く誤設定を誘発しうる。example.json にサンプルが無い。
4. **[low] `docs/examples/doc-audit.example.json` に v0.13.0 の新キー（`regressionRecheck`、`codexReview.required`、`auditScope`、`phase3Backend`）のサンプルが無い**（既定値で動くため矛盾ではない）。
5. **[low・コード側] `skills/audit/scripts/fix-scope.py:87` の `docGlobs` 既定値が `[]`。** 他の 12 箇所（`resolve-impact.py:95,196`、`start-run.py:43,254`、`generic-layers.py:65,598`、`change-set-sha.py:46`、`impact-supplement.py:71`、`import-audit-scope.py:148,422,588`）は `["docs/**/*.md","*.md"]`。`docGlobs` 省略時に pre-flight の fix path が全パスを deny する（安全側だが理由が未文書）。

## 提案
- 1 は 1 句追記。2・3 は注記 1 行ずつ。4 は example.json に既定値付きのサンプルを追加。5 は既定値を揃えるか、意図的なら fix-scope.py と config-schema.md にその旨を書く。


