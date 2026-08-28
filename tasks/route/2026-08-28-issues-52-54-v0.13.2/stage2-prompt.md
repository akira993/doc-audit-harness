# S2 実装依頼 — docaudit v0.13.2: 版バンプ・engine-shas・ADOPTION §7 段落・契約テスト再照準・release-handoff

あなたは実装担当（worker）。boss（Claude）が確定した計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（rev.8）に従って **S2 のみ** を実装する。
S1a・S1b（#52〜#54 の本体）は反映・commit 済みの tree が前提。PLAN.md を最初に全文読むこと（§0-6・§0-7・§0-8 と DoD (16)〜(19) が仕様の正）。

## 事前承認（boss）
PLAN.md §7「許可（S2）」に列挙された既存ファイルの上書きと、新規ファイル（`release-handoff.sh`、`stage2-report.md`）の作成を **包括的に承認済み**である。この範囲内の上書きについて個別確認のために停止してはならない。許可外ファイルの変更が必要になった場合のみ、修正せず報告せよ。

## S2 の範囲
1. 版バンプ 5 面: `.claude-plugin/plugin.json` の `version` → `0.13.2`、`docs/ADOPTION.md:224`／`docs/ADOPTION.ja.md:206` の `claude plugin list` 行 → `Version 0.13.2`、
   refresh 段落（en `ADOPTION.md:284`／ja `.ja.md:264-265`）を PLAN §0-6 の **行単位の完全文言**に。`skills/audit/references/engine-shas.json` に `0.13.2` entry
   （`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run` で `stampVersion` と hash を確認。テンプレート不変なら 0.13.1 と同一 hash）。
2. ADOPTION §7 に `**v0.13.2 behavior changes:**`／`**v0.13.2 の挙動変更:**` 段落（`v0.12.0` 段落の直後、同型）。en は PLAN DoD (17) の固定文 ①〜⑤ をこの文言で
   （文書慣習どおりハードラップ・コードスパン付きでよい。契約テストは空白正規化＋バッククォート除去後に `assertIn`）、ja も DoD (17) の固定文 5 つをこの文言で。
   契約テスト `test_v0132_behavior_changes_paragraph` を `tests/test_v0132_contracts.py` に追記（検査方法は DoD (17) のとおり）。
3. 既存契約テストの再照準: `tests/test_v013_contracts.py` test_i の集合 `{"0.13.2"}`、test_j の allowlist（refresh 行 regex を新文言に。en/ja）、
   `tests/test_v0131_docs_contracts.py` test_g の target 集合に `"0.13.1"`、`tests/test_scaffold.py` の `0.13.1` → `0.13.2`（:214-218, :242-246, :312）。
4. `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` を前版 `tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh` と同型で作成:
   `TAG_NEW="docaudit--v0.13.2"`、`RELEASE_TITLE="docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)"`、notes は
   `Ships issues #52, #53, and #54.` と「Absent docGraph/semanticSearch/symbolGraph keys now report not-configured; CocoIndex initialization requires .cocoindex_code/settings.yml;
   fix-scope docGlobs default aligned; seal failures stop the run.」を含め（必須語 `#52` `#53` `#54` `not-configured` `settings.yml`）、Issue close ループは `52 53 54`、
   close コメントは `Shipped in docaudit v0.13.2 (PR #$PR_NUMBER, tag docaudit--v0.13.2).`。`bash -n` 通過。
   `tests/test_release_handoff.py` を新 script に再照準（HANDOFF パス、TAG、TITLE、ISSUES `range(52, 55)`、PRECLOSED、REQUIRED_BODY、Issue 番号を参照する全箇所）。
5. 報告に `Ran N tests` の実数（`python3 -m unittest -v tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff tests.test_v0132_contracts`）を添える。

## 注意
- `.gitignore` が `tasks/` を無視するため新 script は未追跡でよい（boss が `git add -f` する）。`git` への書き込みは行わない。CHANGELOG は作らない。`README.md` は触らない（badge 自動追従）。
- `tests/test_release_handoff.py` は 454 行あり v0.13.1 固有値が本体にも散在する（`:424` tag refspec、`:436,:457` Issue close 件数、`:442,:449` Issue 番号など）。`grep -n '0\.13\.1\|46\|47\|48\|49\|50' tests/test_release_handoff.py` で全箇所を洗い出してから再照準し、洗い出し結果（件数）を報告に書く。
- Terra の sandbox では 30 秒超のフルスイートが完走しないことがある。フルは boss が実行する。
- 対象外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。`?? .claude/` は対象外。

## 報告（最後に `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage2-report.md` へ書き出す）
1. 変更ファイル一覧と要旨。2. PLAN DoD (16)〜(19)・(21)・(22) の各項目について実行コマンドと実測結果（engine-shas の hash 一致/不一致を明記）。3. テストコマンドと `Ran N tests` 実数。
4. 未対応・判断に迷った点・対象外ファイルの変更が必要と判断した点。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認

---
# 以下、PLAN.md の完了条件・変更範囲・検証コマンド一式（原文。S2 に該当する項目に従う）
## 6. 完了条件（DoD）— 機械判定可能な形で

### S1-#52
- (1) `fix-scope.py` の `docGlobs` 既定が `["docs/**/*.md", "*.md"]`（`grep -c 'get("docGlobs", \[\])' skills/audit/scripts/fix-scope.py` == 0）。
  `DENIED_PARTS` と並ぶ **basename deny 集合（casefold 比較で `claude.md`／`agents.md`）** があり、分類理由文字列は既存 deny と同型（例 `agent instruction file`）。
- (2) 動作テスト `tests/test_v0132_contracts.py::TestFixScopeDefaults::test_omitted_doc_globs_uses_shared_default_and_denies_agent_files`
  と `test_explicit_doc_globs_still_denies_agent_files`: `docGlobs`・`protectedGlobs` とも無しの config で `--paths` に
  `docs/a.md`／`README.md`／`SECURITY.md`／`src/app.py`／`docs/logs/x.md`／`AGENTS.md`／`CLAUDE.md`／`docs/CLAUDE.md` を渡すと
  `allowed == ["README.md","SECURITY.md","docs/a.md"]`（実装は `sorted(set(...))` — Sol R2-12）、denied 5 件の理由がそれぞれ docGlobs 不一致／
  組込み deny（logs）／agent 指示ファイル×3。さらに `docGlobs: ["**/*.md"]` 明示でも `AGENTS.md`・`docs/CLAUDE.md`・**`docs/claude.md`（小文字）**が denied
  （basename deny は docGlobs より優先、大小文字非区別）。**前提（Opus B7）**: `validate_repo_path` は実在の通常ファイルを要求する（`docaudit_paths.py:37,61-63`）ため
  `--paths` に渡す全 path を空ファイルとして作成する。小文字ケースは `docs/claude.md` のように **同一ディレクトリに case-twin を作らない**（macOS の大小文字非区別 FS 対策）。
- (3) 構造テスト `test_v0132_contracts.py::TestFixScopeDefaults::test_doc_globs_default_is_shared_across_eleven_call_sites`: §0-2 の 7 ファイルを AST で走査し、`.get("docGlobs", <literal>)` の literal 既定が全て
  `["docs/**/*.md", "*.md"]` であること、**検査した call site 数が正確に 11 件で、対象ファイル集合が §0-2 の 7 ファイル**であることを assert（ファイル別内訳は
  コメントに残すのみで assert しない — Opus N2）。
- (4) fail-closed 注記の撤去: `grep -c 'fail.closed\|fails closed' skills/audit/scripts/fix-scope.py` == 0。`config-schema.md` の `docGlobs` 行・
  ADOPTION en/ja の `docGlobs` 行に `fail-closed`／`rejects every path`／`全パスを拒否` が無く、代わりに「pre-flight fix path も同じ既定」の旨がある。
  組込み deny の列挙 **5 か所**（`config-schema.md:30`・`:154`、`SKILL.md:281`、`ADOPTION.md`・`ADOPTION.ja.md` の `protectedGlobs` 行）すべてに
  `CLAUDE.md`／`AGENTS.md` と case-insensitive（ja: 大文字小文字を区別しない）の旨が含まれる（契約テスト `test_builtin_deny_documented_in_five_places` で
  5 箇所を個別に検査）。

### S1-#53
- (5) SKILL.md Phase 3 節（`## Phase 3` から次の `## ` まで）に、(i) exit 5 分岐、(ii) `Any other non-zero exit` 分岐、(iii) `read-manifest.py` 失敗分岐の
  3 つがあり、**3 分岐すべての文（または直後の文）に `--release --runid "$RUNID"` を含む完全な解放コマンド**（`--run-base`・`--repo-root`・`--anchor-path` を
  伴う）がある。(ii) は `read-manifest.py` を呼ばないこと・verifier を起動しないこと・`seal-run:` の stderr 報告を含む。契約テストは節を切り出し
  3 固定句と解放コマンドの出現を検査（`--release --runid` の出現数 ≥ 3 かつ各固定句の後 3 行以内に出現）。既存 `tests/test_v013_contracts.py:101-103`（test_f）が
  依存する行頭 `` `SEALED_MANIFEST="$(python3 "$SD/scripts/read-manifest.py" `` の行の形は崩さない（Opus N5）。行番号は rev.7 時点で組込み deny 本文が
  `SKILL.md:284`／`config-schema.md:157`（Opus N3。内容一致を優先）。
- (6) `read-manifest.py`: `{"sealed":false}`／`sealed` 無し／`[]`／`null` の 4 入力で exit 2・stdout 空・stderr に `manifest is not sealed`
  （hash は各入力の実バイト列に一致させる）。`tests/test_read_manifest.py` に固定名で 4 ケース追加: `test_sealed_false_is_rejected`、
  `test_missing_sealed_key_is_rejected`、`test_array_manifest_is_rejected`、`test_null_manifest_is_rejected`。既存 6 テストは fixture が `"sealed":true` で改変不要。
- (7) `codex-dispatch.py` は変更しない。`python3 -m unittest tests.test_codex_dispatch` green。

### S1-#54-1
- (8) 3 probe とも §0-4 判定表を満たす。各 probe テストに次の **固定名**で追加（#3 は既存 `test_disabled_by_config`）: `test_absent_key_is_not_configured`、
  `test_empty_object_key_is_enabled`（stub が呼ばれる）、`test_non_boolean_enabled_is_invalid_config`（`"false"`）、`test_non_object_key_is_invalid_config`、
  `test_invalid_json_config_is_invalid_config`、`test_missing_config_file_is_invalid_config`、`test_non_object_top_level_is_invalid_config`、
  `test_non_string_bin_is_invalid_config`（subTest: `[]`・`""`）、`test_omitted_config_flag_is_invalid_config`（`--config` 自体を渡さない）、
  `test_disabled_with_invalid_bin_is_disabled_by_config`（`{"enabled":false,"bin":[]}` → `disabled-by-config`。Sol R3-4）
  （graphify／codegraph／cocoindex 各 10 件）＋ cocoindex のみ `test_non_finite_or_non_number_min_score_is_invalid_config` と
  `test_disabled_with_invalid_min_score_is_disabled_by_config`（`{"enabled":false,"minScore":"x"}` → `disabled-by-config`。Sol R4-3）（2 件）。**計 32 件追加**。
  必須 subTest 入力（Sol R4-4）: `test_non_boolean_enabled_is_invalid_config` は `"false"`・`1`；`test_non_object_key_is_invalid_config` は `true`・`"x"`・`[]`・`null`；
  `test_non_string_bin_is_invalid_config` は `[]`・`1`・`null`・`""`；`test_non_finite_or_non_number_min_score_is_invalid_config` は `"0.4"`・`true`・`null`・
  `NaN`・`Infinity`・`-Infinity`（config は Python `json.dumps` で書き、NaN/Infinity literal を含める）。
  **外部 tool 非起動の検査（Sol R4-5）**: `available:false` の各ケースで、config に有効な `bin` を置けるケースは stub path を `bin` に置き、置けないケース
  （キー不在・キー非 object・不正 JSON・config 不在・top-level 非 object・`bin` 不正）は **既定名（`graphify`／`ccc`／`codegraph`）の記録用 stub を `PATH` 先頭に
  配置**して、**`calls.log` が不在**であることを assert（`command -v` の非実行は契約に含めない — Sol R2-10）。併せて `.codegraph/`・`graphify-out/`・
  `.cocoindex_code/`・`.gitignore` が生成／変更されないことを assert。**cocoindex の非起動系ケースでは fixture repo に `.cocoindex_code/settings.yml` を必ず置く**
  （Opus B4: 置かないと `not-initialized` の早期 return で stub が呼ばれず、判定未実装でも通る偽陽性になる）。`test_empty_object_key_is_enabled` は 3 probe とも
  既定名 stub を `PATH` 先頭に置き（`{}` は `bin` を持てない）、cocoindex 版はさらに `.cocoindex_code/settings.yml` を置く（Opus O2-R4）。config 不在系のケースは既存 `run_script` ヘルパーが
  使えないため別ヘルパーを用意する。
- (9) reason 列挙: SKILL.md の 3 probe 段落（:176, :190, :204 の `reason ∈`）と `config-schema.md` の 3 節に `not-configured`／`invalid-config` を追加。
  契約テスト: 各 probe 段落の列挙集合 == {既存 reason} ∪ {`not-configured`, `invalid-config`}（semanticSearch は `gitignore-modified` も）で**完全一致**。
- (10) Phase-5 状態行: 3 ブロックを `*_REASON` 変数による排他表に書き直し（`AVAILABLE` 単独の catch-all 枝なし）。`not-configured` 枝は `install:` を含まず
  「installed」と言わない。ラベル **doc-graph `6-state`（7 messages）、symbol-graph `6-state`、semanticSearch `8-state`**（§0-4 と同値。契約テストで見出しの
  数値も固定 — Sol R4-1）。契約テスト（Sol R2-9）: 各ブロックの箇条書きを reason ごとに 1 行へ対応付け（**各 reason はちょうど 1 つの箇条書きにのみ現れる**。doc-graph の `ok` は gitignoreOk true/false の 2 行を許容）、各行が
  **`→` の右辺（利用者向けメッセージ）だけを取り出して** reason 固有の **記号＋固定句** を含み、かつ他 reason の固定句を含まないことを対応表で検査
  （Sol R3-3、R4-6: 条件側の `disabled-by-config`／`index-failed` の文字で通らないようにする）: `not-configured`→`💡`＋`not configured`、
  `invalid-config`→`⚠`＋`is invalid`、`not-installed`→`💡`＋`install:`、`disabled-by-config`→`💡`＋`disabled`、`index-failed`/`update-failed`→`⚠`＋`failed`、
  `not-initialized`→`💡`＋`isn't indexed yet`、`gitignore-modified`→`⚠`＋`changed while ccc index ran`、`ok`→ 文脈付き `✓ <seam>: active (`
  （doc-graph の gitignoreOk false 行のみ `⚠ doc-graph: active but`）。`ok` の検査は裸の `active` ではなく上記の文脈付きパターンを使う（Sol R5-1:
  `not active` を含む正しい非稼働行を誤検出しない）。テスト名 `test_phase5_status_lines_map_each_reason_to_one_branch`。`docs/ADOPTION.md:197-198`／`.ja.md:179-180` の状態行要約に `not configured`／`未設定` と
  `invalid`／`不正` を追加。
- (10b) Phase 0 の 3 probe 段落が `SYMBOL_GRAPH_REASON`／`DOC_GRAPH_REASON`／`SEMANTIC_SEARCH_REASON` を **probe JSON の `["reason"]` から代入する完全な式**で
  束縛する（契約テスト `test_phase0_binds_reason_from_each_probe_json` は `<VAR>_REASON=` … `["reason"]` の対応 3 組と、`<VAR>_PROBE_JSON="$(bash "$SD/scripts/<probe>.sh"`
  の捕捉行 3 本を検査。Sol R3-2、Opus B6）。
- (11) `skills/init/SKILL.md:147-163` の symbolGraph／docGraph／semanticSearch の OMIT 文 3 か所に「absent key ⇒ the audit reports `not-configured`
  and never runs the tool」の 1 句（mdq／context-mode／ax／codex の OMIT 文は変更しない）。契約テスト: init SKILL.md 内の `not-configured` 出現が
  ちょうど 3 回で、各出現行（またはその箇条書き）が上記 3 キー名のいずれかを含む。

### S1-#54-2
- (12) `cocoindex-probe.sh`: 初期化済み判定は `[[ -f "$REPO_ROOT/.cocoindex_code/settings.yml" ]]`。テスト追加 `test_legacy_dir_without_settings_is_not_initialized`
  （dir のみ → `not-initialized`、`calls.log` 不在）。既存 `test_stub_installed_reports_ok`／`test_stub_index_failure_reports_index_failed` は fixture に
  `settings.yml` を置いて green に保つ。config-schema.md:39 の「runtime reads only `enabled` and `bin`」は「the probe validates `enabled`/`bin`/`minScore`;
  Phase 2 uses `minScore`」に更新（Sol R3-7、契約テストで文字列検査）。
- (13) `.gitignore` 検出: テスト追加 `test_index_that_modifies_gitignore_is_reported`（stub `index` が `.gitignore` に追記 → `reason=="gitignore-modified"`、
  `semanticSearchAvailable==false`、**`.gitignore` は stub が書いたままで probe は書き戻さない**（バイト列一致））、
  `test_index_that_creates_gitignore_is_reported`（事前に不在 → stub が生成 → 同上、ファイルは残る）、`test_gitignore_change_wins_over_index_failure`
  （追記後に exit 1 → `gitignore-modified`。Sol R3-8）。計 3 件追加（(12) の 1 件と合わせて cocoindex は 4 件 — Opus O2-R5）。
- (14) 文書: SKILL.md:200-215 段落を `settings.yml` マーカー＋自動 init の原因＋検出の記述に更新。`config-schema.md:39` 行と `:297-320` 節、
  `ADOPTION.md:170-172`／`.ja.md:153-156`、`init/SKILL.md:155-158` の「`.cocoindex_code/` 不在／already exists」を `settings.yml` 基準に改める。
  加えて `.cocoindex_code/` の存在だけで初期化済みとする残存記述 4 か所（`skills/init/SKILL.md:52`、`cocoindex-probe.sh:13-17` ヘッダ、`config-schema.md:309`、
  `skills/audit/SKILL.md:211` — Opus N1）も `settings.yml` 基準に改める。契約テスト: 上記 5 文書それぞれで `.cocoindex_code/settings.yml` の literal が ≥1 回、
  かつ **`not-initialized` を説明する同一段落（表では同一行）内**に `settings.yml` が現れ、`.cocoindex_code/` の直後に `already exists`／`不在`／`present` が続く行が
  `settings.yml` を伴わずに残っていない。状態行に `reason:gitignore-modified` の枝（§0-5 文言。`checkout` を含まない）。

### S1-既往 red（§0-12）
- (15) `tests/data/dir-framework-scope/` の 3 fixture が存在し、`tests/test_import_audit_scope.py` の当該テストが fixture のみで green（`DIR_FRAMEWORK`
  参照 0、`skipTest` 呼び出し 0）。テスト名 `test_dir_framework_fixture_scope_is_not_imported_with_24_rules_and_48_paths`。3 fixture の sha256 literal（§0-12 の 3 値）と `"auditScope" not in config` を assert。`python3 -m unittest tests.test_import_audit_scope` green・skip 0。

### S2
- (16) `python3 -m unittest tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff` green。
  5 面の版が `0.13.2`、engine-shas に `0.13.2`（max semver）、refresh 段落 en/ja が `{0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.13.1, 0.13.2}` を含み §0-6 の行文言に一致。
- (17) ADOPTION §7 `**v0.13.2 behavior changes:**`／`**v0.13.2 の挙動変更:**` 段落が en/ja に 1 つずつあり、§0-7 の 4 点と移行注記を含む
  （契約テスト `test_v0132_behavior_changes_paragraph` — Sol R3-12: en 段落は次の **肯定形の固定文 5 つ**をこの文言で含む:
  ① `omitted docGlobs now defaults to ["docs/**/*.md","*.md"] for pre-flight fix classification; CLAUDE.md and AGENTS.md are always denied (case-insensitive)`
  ② `an absent docGraph / semanticSearch / symbolGraph key reports not-configured and never runs the tool; an invalid key reports invalid-config`
  ③ `CocoIndex counts as initialized only when .cocoindex_code/settings.yml exists; a .gitignore change during ccc index reports gitignore-modified and is never reverted by the audit`
  ④ `any seal-run.py or read-manifest.py failure releases the run and stops; read-manifest.py rejects an unsealed manifest`
  ⑤ `configs that relied on auto-detection must add the key via /docaudit:init`。
  ja 段落は同じ順序で次の **肯定形の固定文 5 つ**をこの文言で含む（Sol R4-7）:
  ① `docGlobs を省略した場合、pre-flight fix の分類は ["docs/**/*.md","*.md"] を既定とする。CLAUDE.md と AGENTS.md は大文字小文字を区別せず常に拒否される`
  ② `docGraph / semanticSearch / symbolGraph のキーが無い場合は not-configured を報告し tool を一切起動しない。キーが不正な場合は invalid-config を報告する`
  ③ `CocoIndex は .cocoindex_code/settings.yml が存在する場合のみ初期化済みとみなす。ccc index の実行中に .gitignore が変化した場合は gitignore-modified を報告し、監査は復元しない`
  ④ `seal-run.py または read-manifest.py が失敗した場合は run を解放して停止する。read-manifest.py は未 seal の manifest を拒否する`
  ⑤ `自動検出に頼っていた config は /docaudit:init でキーを追加するまで not-configured になる`
  （検査方法 — Opus B3: 段落を `" ".join(paragraph.split())` で空白正規化しバッククォートを除去してから `assertIn`。既存 `test_v0131_docs_contracts.py:93` と
  同じ正規化。本文は文書慣習どおりハードラップ・コードスパン付きで書いてよい）。
- (18) `tests/test_release_handoff.py` が新 script（`2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`、tag `docaudit--v0.13.2`、Issue 52-54、
  title `docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)`、notes 必須語 `#52 #53 #54 not-configured settings.yml`）を
  対象にして green。`bash -n` 通過。
- (19) test_j: `0.12.0` 残存は allowlist のみ（refresh 行 regex を §0-6 の新文言に更新）。

### 共通
- (20) フルスイート green・skip 0。件数の自己申告ではなく **固定テスト名の網羅**で判定（Sol R2-11、R3-13）: boss が `python3 -m unittest -v` の出力に
  DoD (2)(3)(4)(5)(6)(8)(9)(10)(10b)(11)(12)(13)(14)(15)(17) に列挙した固定テスト名がすべて現れることを grep で確認。契約テストの固定名（上記以外）:
  (4) `test_doc_globs_rows_no_longer_say_fail_closed`、(5) `test_phase3_three_stop_branches_release_the_run`、(9) `test_probe_reason_enumerations_match_fixed_sets`、
  (11) `test_init_skill_marks_three_omit_rules_as_not_configured`、(14) `test_settings_yml_marker_documented_in_five_files`、
  (§0-4 B1) `test_three_seams_no_longer_documented_as_auto_used`（Opus O2-R1）。worker は Stage 報告に `Ran N tests` の実数を添える。
- (21) `bash -n` が 3 probe＋handoff で通り、`python3 -m py_compile` が変更 .py 全てで通る。
- (22) 変更範囲外のファイルに差分が無い（`git status --short` で確認。未追跡 `?? .claude/` は本タスク以前から存在する worktree コピーで対象外 — Opus N4）。

## 7. 変更範囲

- 許可（S1）: `skills/audit/scripts/{fix-scope.py,read-manifest.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh}`、
  `skills/audit/SKILL.md`、`skills/init/SKILL.md`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
  `tests/{test_read_manifest.py,test_graphify_probe.py,test_cocoindex_probe.py,test_codegraph_probe.py,test_import_audit_scope.py,test_wp12_contracts.py}`、
  新規 `tests/test_v0132_contracts.py`、新規 `tests/data/dir-framework-scope/{audit-scope.json,doc-audit.json,paths.txt}`。
- 許可（S2）: `.claude-plugin/plugin.json`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`skills/audit/references/engine-shas.json`、
  `tests/{test_v013_contracts.py,test_v0131_docs_contracts.py,test_scaffold.py,test_release_handoff.py}`、
  新規 `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`。
- 禁止: `codex-dispatch.py`、`decide-verdict.py`、`seal-run.py`、`tree-digest.py`、`import-audit-scope.py`、`sibling-scan.py`、`mdq-index.sh`、
  `ax-probe.sh`、`codex-probe.sh`、`references/workflow-template.js`、`README.md`（badge 自動追従）、`agents/**`、`.gitignore`、`docs/superpowers/**`、
  `tasks/route/2026-08-27-*/**`、`.claude/**`、`~/Projects/dir-framework/**`（読み取りのみ可）。CHANGELOG を新設しない。
- 標準文言: **許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 8. 検証コマンド一式

```
python3 -m unittest discover -s tests -t .                       # フル（skip 0・件数を報告）
python3 -m unittest tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe tests.test_read_manifest tests.test_v0132_contracts
python3 -m unittest tests.test_wp12_contracts tests.test_codex_dispatch tests.test_import_audit_scope
python3 -m unittest tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff   # S2
bash -n skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh
bash -n tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh                                                        # S2
python3 -m py_compile skills/audit/scripts/fix-scope.py skills/audit/scripts/read-manifest.py
python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run | python3 -c 'import json,sys;print(json.load(sys.stdin)["stampVersion"])'  # S2
grep -c 'get("docGlobs", \[\])' skills/audit/scripts/fix-scope.py                                                              # 0
git status --short                                                                                                            # 許可外差分なし
```
