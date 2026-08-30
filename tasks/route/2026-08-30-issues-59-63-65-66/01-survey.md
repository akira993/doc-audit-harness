# ファクトシート

## A. 監査実行中の live config 消費者

### 1. `SKILL.md`

`CFG` は [skills/audit/SKILL.md:13] で一度だけ `.claude/doc-audit.json` に束縛され、後続の再束縛はありません。

`--config "$CFG"` または `$CFG` の Python 読み取り箇所：

- Phase 0 前: anchor、audit-scope 読み取り、scope check — [SKILL.md:14,25-26]
- Phase 0: `mdq-index.py`、context-mode、ax、codex、codegraph、graphify、cocoindex — [SKILL.md:76,131-140,161-162,176-183,204,225,245]
- Phase 0.5: harness 設定・`set-config-key.py`・generic layer・copied engine — [SKILL.md:268-274,297,302,305]
- Phase 1/2: `fix-scope.py`、baseline、`resolve-impact.py`、`impact-supplement.py`、`classify-run.py`、`plan-dispatch.py`、`start-run.py` — [SKILL.md:333,355,373,379,392,398,404]
- Phase 4: generic layer、`codex-review-plan.py` — [SKILL.md:538,579]
- Phase 5: `decide-verdict.py` — [SKILL.md:695-696]

Phase 3 Workflow は live config を直接渡さず、sealed manifest 由来の値と probe 結果を渡します [SKILL.md:425-438,484-487]。

### 2. `skills/audit/scripts/` の config 読み取り

`--config` 引数を読み、JSON を開くスクリプト：

- `change-set-sha.py` — [change-set-sha.py:137-141]
- `classify-run.py` — [classify-run.py:22,29-30]
- `codex-review-plan.py` — [codex-review-plan.py:17,23-24]
- `decide-verdict.py` — [decide-verdict.py:592,684-707]
- `fix-scope.py` — 任意 `--config`; [fix-scope.py:54,82-85]
- `generic-layers.py` — [generic-layers.py:582,592-593]
- `impact-supplement.py` — 任意 `--config`; [impact-supplement.py:193,219-220]
- `plan-dispatch.py` — [plan-dispatch.py:53,68-72]
- `resolve-impact.py` — [resolve-impact.py:138,146-147]
- `set-config-key.py` — [set-config-key.py:13,17-18]
- `start-run.py` — [start-run.py:182,215-219]

Shell script 経由の config 読み取り：

- `ax-probe.sh`: `--config`、`json.load(open(...))` — [ax-probe.sh:17-20,26-45]
- `codex-probe.sh`: 同様 — [codex-probe.sh:18-21,27-45]
- `cocoindex-probe.sh`: `--config`、JSON 読み取り — [cocoindex-probe.sh:28,39]
- `codegraph-probe.sh`: `--config`、JSON 読み取り — [codegraph-probe.sh:21,40]
- `graphify-probe.sh`: `--config`、JSON 読み取り — [graphify-probe.sh:25,37]
- `mdq-index.sh`: `--config`、設定本体と `indexing.roots` の読み取り — [mdq-index.sh:20,27-50,68-80]
- `compute-baseline.sh`: `--config`、`anchorPath`/`diffGlobs` の読み取り — [compute-baseline.sh:15-20,30-35,66]

ハードコードされた `.claude/doc-audit.json` を使うもの：

- `open-run.py` — [open-run.py:152-162]
- `seal-run.py` — [seal-run.py:49-53]

両方を使うもの：

- `classify-run.py` は引数 config を読み、さらに `change-set-sha.py` に同じ config を渡す — [classify-run.py:29-30,42-49]
- `plan-dispatch.py` も同様 — [plan-dispatch.py:68-72,84-90]
- `decide-verdict.py` も live config を読み、`change-set-sha.py` に config path を渡す — [decide-verdict.py:684-707,808-815]
- `start-run.py` は引数 config のみを読み、manifest を作る — [start-run.py:215-219,262-284]
- `import-audit-scope.py` は `--config` と `--scope` の両方を持つ — [import-audit-scope.py:555-566]。scope は `read_bytes(scope_path)` で読む — [import-audit-scope.py:475-489,601-602]。

設定を読まないスクリプト：

`check-verdicts.py`、`codex-dispatch.py`、`docaudit_cache.py`、`docaudit_paths.py`、`harness-command-kind.py`、`inventory.py`、`mdq-health.py`、`probe-record.py`、`read-manifest.py`、`sibling-scan.py`、`tree-digest.py`、`write-anchor.sh`、`write-evidence.py`、`write-template.py`、`write-verdict.py`。各ファイルの引数・読み取り処理には config reader がありません [skills/audit/scripts/]。

live `audit-scope.json` を読むもの：

- `import-audit-scope.py` — [import-audit-scope.py:475-489,601-602]
- `start-run.py` — config の `auditScope` metadata を検証し、指定 path の raw bytes を SHA-256 化 — [start-run.py:141-170]
- `decide-verdict.py` — barrier で metadata path を読み、sealed SHA と比較 — [decide-verdict.py:203-216]

### 3. Phase 3 Workflow / verifier

Workflow は `workflow-template.js` で、Phase 3 の verifier agent を選択します [workflow-template.js:75-99,143-178]。

Workflow が受け取る環境・設定由来値は `mdqAvailable`、`mdqHealthy`、`cmAvailable`、`axAvailable`、`symbolGraphAvailable`、`runId`、`runDir`、`scriptsDir` です [workflow-template.js:90-99]。`CODEGRAPH_DIR` は Phase 0 の `codegraph-probe.sh` が読み、実行時にも環境変数として設定します [codegraph-probe.sh:31,103]。

Verifier agent は指定された doc と changed source を読むだけで、唯一の書き込みは担当 verdict file です [agents/doc-impact-verifier.md:8-16]。config 自体を読む処理はありません [agents/doc-impact-verifier.md:18-51]。

## B. `open-run.py` sealing

config は JSON 正規化後ではなく、ファイルの raw bytes 全体を SHA-256 化します [open-run.py:157-162]。ハッシュ関数は `sha(data)` です [open-run.py:21-22]。

open 時に作られるもの：

- `docaudit-run/` は mode `0700` — [open-run.py:210-212]
- `lock` は `O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW`、mode `0600` — [open-run.py:193-209]
- run directory 内の manifest 等は open 時には作られません [open-run.py:210-227]

初期 EVIDENCE JSON のキーは次の通りです：

```json
{
  "runid": "...",
  "runDir": "...",
  "anchor": "sha256:..." | "none",
  "config": "sha256:...",
  "lockIno": 123,
  "preflight": "none",
  "phase4": "none"
}
```

[open-run.py:221-227]

以前の report 状態が `pending`、`failed`、`written-durability-unknown` の場合だけ `previousReportStatus` が追加されます [open-run.py:224-227]。テストは `preflight` と `phase4` の sentinel を確認します [tests/test_wp12_contracts.py:14-21]。完全な success JSON の固定文字列例はテスト内にはありません。

`--accept-config` は、直前の `REFUSED/config-changed` の `expectedConfigSha` と現在の SHA が違う場合の exit 6 拒否を無効化します [open-run.py:164-174]。

終了コード：

- `0`: open/release 成功 — [open-run.py:25-27,227]
- `2`: 引数、path、config、anchor、run directory 等のエラー — [open-run.py:135-137,151-161,183-185,217-218]
- `4`: lock 保持中 — [open-run.py:193-204]
- `6`: 未承認 config 変更 — [open-run.py:170-174]

audit-scope は open 時には seal されません。open-run は anchor と config だけを読む [open-run.py:157-188]。audit-scope SHA は start-run の manifest 作成時に初めて計算されます [start-run.py:141-170,262-266]。

## C. `decide-verdict.py` gate

### config checks

- live config の single read と signature 保存 — [decide-verdict.py:684-685]
- sealed EVIDENCE の config SHA と比較 — [decide-verdict.py:699-701]
- mismatch 時に `config_taint=True`、`Refused` — [decide-verdict.py:699-701]
- barrier 直前にも config signature を再確認 — [decide-verdict.py:904-920]
- mismatch 時の last-run `reason="config-changed"` — [decide-verdict.py:1001-1011]
- config taint 時は report を信頼せず、exit 3 — [decide-verdict.py:1001-1028,1035-1036]

`verify_audit_scope_at_barrier` は config の `auditScope.path` を検証し、live scope bytes の SHA と manifest の `auditScopeSha` を比較します [decide-verdict.py:203-216]。呼び出し箇所は worktree drift、barrier 前、state write 前です [decide-verdict.py:804-807,906-920]。

### history schema

history file は `.claude/state/docaudit-history.json` です [decide-verdict.py:603-605]。各 entry の現在のキーは：

- `runid`
- `path`
- `contentSha`
- `changeSetSha`
- `contractVersion`
- `backend`
- `verdict`
- `ts`

`runid`〜`ts` は additions 作成時に設定されます [decide-verdict.py:926-936]。`backend` は `manifest["phase3Backend"]` 由来です [decide-verdict.py:719-722,931-936]。共通 validator は backend を optional として扱い、未指定時は `workflow` とします [docaudit_cache.py:52-67]。

history は `expected["history"]` と raw bytes SHA を照合してから parse されます [decide-verdict.py:727-747]。同じ path の最新 entry は全履歴を順に走査して `latest[path]` に置かれます [decide-verdict.py:219-229]。

現行の flip は「同一 path、同じ content SHA、contractVersion、backend、異なる verdict」です [decide-verdict.py:230-235]。同じ `changeSetSha` の subset も数えます [decide-verdict.py:236-238]。

history entry に `worktreeDigest`、blocking-finding files の集合、Phase-4 findings、タイトルはありません [decide-verdict.py:931-946]。

### Phase 4 findings

読み取る run-dir ファイルは `$RUN_DIR/phase4.json` です [decide-verdict.py:772-784]。期待される外側の schema は `findings` 配列で、Phase 4 手順書の形は次です：

```json
{
  "findings": [
    {"severity":"...", "source":"...", "title":"..."}
  ],
  "codexReview": {"state":"..."}
}
```

[SKILL.md:622-628]

Codex の元出力 schema は各 finding に `severity`、`title`、`file` を要求します [codex-review-output.schema.json:5-17]。

blocking severity は `FAIL`、`HIGH`、`CRITICAL` です [decide-verdict.py:27-30,262-288]。`WARN`、`MEDIUM`、`LOW`、`INFO` は non-blocking です [decide-verdict.py:276-288]。Phase 4 の blocking finding は `NEEDS_FIX` にします [decide-verdict.py:894-899]。

Phase-4 findings を history entry に記録する処理はありません。history additions は doc verdict 単位のみです [decide-verdict.py:926-946]。

### warning channel

gate は `warnings` 配列を stdout JSON に返し、report rendering にも渡します [decide-verdict.py:975-982,432-457]。

既存の warning 例：

- verdict flip warning — [decide-verdict.py:937-945]
- Codex degraded warning — [decide-verdict.py:870-878]
- report publication warning — [decide-verdict.py:558-583]

## D. Phase 4 pipeline

`codex-review-plan.py` の入力は `--mode`、`--config`、`--available`、`--available-reason`、`--baseline-ok` です [codex-review-plan.py:14-21]。

この script は prompt を作りません。config を読み、`codexReview` の存在と `required` だけを読みます [codex-review-plan.py:23-31]。

variant/action：

- config に `codexReview` がない: `not-active`
- unavailable: `not-active`
- full + required: `run`, `promptVariant:"full"`
- full + not required: `skip`
- incremental + baseline valid: `run`, `promptVariant:"diff"`
- incremental + baseline invalid: `skip`, `ref-invalid`

[codeX-review-plan.py:33-50]

履歴や previous run directory を読む処理はありません [codex-review-plan.py:1-61]。

Prompt は `SKILL.md` の Phase 4 手順で組み立てられます：

- diff variant は baseline、HEAD、changeSummary、impacted docs を含む — [SKILL.md:585-597]
- full variant は sealed `manifest.head` と `worktreeDigest` の current worktree を対象にする — [SKILL.md:589-597]
- Codex 出力は `codex-review-result.json` に書く — [SKILL.md:599-607]
- Phase 4 evidence は `phase4.json` に書く — [SKILL.md:622-631]

Codex findings は `critical→CRITICAL`、`high→HIGH`、`medium→MEDIUM`、`low→LOW` に正規化されます [SKILL.md:608-618]。

現行実装には codex-review-plan の sibling 実装や history carry-forward 実装はありません。手順書は previous finding を手動で prompt に貼ることを許可し、engine-side carry-forward は #59 追跡中と記載しています [SKILL.md:620]。

関連 config keys：

- `codexReview` — [docs/ADOPTION.md:137-148,367]
- `reviewCommands.code/security` — [docs/ADOPTION.md:350-352]
- `phase4Required` — manifest で生成される — [start-run.py:250-272]
- `phase4` evidence sentinel — [decide-verdict.py:772-784]

Phase 4 範囲は `SKILL.md:525-641` です。manifest から使う主なキーは `phase4Required`、`phase3Backend`、`runClass`、`digestExclude`、`head`、`worktreeDigest`、`provenance`、`dispatch`、`cached` です [SKILL.md:403-412,425-438,526-529,589-597]。

## E. Config writes

`set-config-key.py` は config 全体を読み、指定 top-level key を置換し、temporary file に書いて flush/fsync 後に `os.replace` します [set-config-key.py:17-38]。sealed hash や EVIDENCE は更新しません [set-config-key.py:30-45]。

audit の harness question で `harness.state=declined` を書くと、open-time snapshot が invalid になるため、lock release → fresh open → Phase 0 再実行となります [SKILL.md:267-281]。該当文は：

> “Because that approved config write invalidates the open-time config snapshot, release this run immediately...” [SKILL.md:275-279]

`start-run.py` の live reads：

- config read — [start-run.py:215-219]
- `phase3Backend`、timeout — [start-run.py:220-220]
- `auditScope` SHA — [start-run.py:224,141-170]
- `harness.state`、`docAuditCommands`、`codexReview` — [start-run.py:237-252]
- digest exclusions、doc globs、report pattern — [start-run.py:253-260]

manifest に書くキーは `runid`、`head`、`mode`、`baselineSha`、`changedSet`、`changeSetSha`、`impacted`、`provenance`、`auditScopeSha`、`dispatch`、`cached`、`runClass`、`phase4Required`、`preflightRequired`、`contractVersion`、`digestExclude`、`sealed`、`emptyCorpus`、`docGlobs`、`reportDate`、`reportCandidateRule`、および条件付き `phase3Backend`、`phase3CodexTimeoutSeconds` です [start-run.py:262-275]。

## F. Tests and quality gates

主要テスト：

- `test_wp12_contracts.py`: open-run、EVIDENCE、sealed chain、set-config-key — [tests/test_wp12_contracts.py:14-21,327-379,473-501]
- `test_decide_verdict.py`: gate、Phase 4、scope drift、history、flip counters — [tests/test_decide_verdict.py:1,41-74,949-995,1021-1035]
- `test_start_run.py`: manifest、audit-scope、Phase 3 backend、Phase 4 requirement — [tests/test_start_run.py:1,109-128,168-185,354-440]
- `test_codex_review_plan.py`: plan truth table — [tests/test_codex_review_plan.py:1,38-86]
- `test_scaffold.py`: generated harness、template SHA、version — [tests/test_scaffold.py:334-351]
- `test_v013_contracts.py`: SKILL/init/docs/version contract — [tests/test_v013_contracts.py:18-34,182-201]
- `test_v0131_docs_contracts.py`: docs、SKILL の text contract — [tests/test_v0131_docs_contracts.py:28-101]
- `test_v014_contracts.py`: config-change/reopen/status contract — [tests/test_v014_contracts.py:224-277]
- `test_v015_contracts.py`: v0.15.1 behavior/docs contract — [tests/test_v015_contracts.py:191-215]
- `test_workflow_template.py`: Workflow template parsing・verdict persistence — [tests/test_workflow_template.py:1,143-178]

他の test files は各 script の probe、digest、impact、cache、report、scaffold、write helper 等を対象にします [tests/*.py]。

fixture は `tests/wp12_helpers.py` の `RunFixture` が temporary git repo、config、run dir、history path を生成します [tests/wp12_helpers.py:28-55]。gate fixture の run lifecycle は [tests/wp12_helpers.py:75-168] にあります。

実行コマンド：

```sh
python3 -m unittest discover -s tests
```

この repository には `package.json`、Makefile、CI workflow はありません [リポジトリ直下のファイル一覧]。

実行結果：

```text
Ran 655 tests in 0.635s
FAILED (errors=669)
```

失敗原因は test fixture の `tempfile.TemporaryDirectory()` が `/tmp` 等の利用可能な一時 directory を見つけられなかったことです [tests/wp12_helpers.py:28-32]。lint/type check の実行定義は UNKNOWN です。

## G. 文書契約の該当箇所

- `README.md:30` — “key-gated Phase-4 review ... critical/high findings can block completion”
- `README.md:78` — `verdictFlipsUnchangedContent` と sibling counter の出力例
- `SKILL.md:66` — Phase-4 evidence checkpoint
- `SKILL.md:174-194` — Phase 4 Codex probe と blocking findings
- `SKILL.md:267-281` — config write、snapshot invalidation、reopen
- `SKILL.md:373,398` — history/config を渡す Phase 2 commands
- `SKILL.md:403-412` — manifest と unsealed values
- `SKILL.md:525-529` — Phase 4 gate
- `SKILL.md:573-620` — reviewCommands、Codex、full/diff、sampling、#59
- `SKILL.md:622-637` — Phase 4 evidence schema
- `SKILL.md:695-714` — gate output、counter、REFUSED
- `ADOPTION.md:124-150` — Codex review、required、blocking severity
- `ADOPTION.md:198-205` — reproducibility、verdict flip counters
- `ADOPTION.md:476-484` — sealed evidence、history/cache
- `ADOPTION.md:503-515` — Phase-4 severity mapping
- `ADOPTION.md:524-532` — sealed manifest と Phase 4
- `ADOPTION.md:586-596` — config change acknowledgement、engine SHA
- `ADOPTION.md:348,350,352,367` — auditScope、reviewCommands、codexReview schema
- `skills/init/SKILL.md:44-45,136-138` — Phase 4 Codex を config proposal に含める
- `docs/ADOPTION.ja.md:109-150` — 日本語の Phase 4/Codex/reproducibility 契約
- `docs/ADOPTION.ja.md:213,259,292` — version 0.15.1 関連

`docaudit-history` という表記の直接ヒットは `SKILL.md:373,398`、`ADOPTION.md:476-484` の history 関連記述にあります。`TOCTOU`、`tamper` の直接記述は、対象文書群では該当箇所を確認できません。

## H. Release plumbing

version `0.15.1` の locations：

- `.claude-plugin/plugin.json:3`
- `skills/audit/references/engine-shas.json:47`
- `docs/ADOPTION.md:236,286,320`
- `docs/ADOPTION.ja.md:213,259,292`
- `tests/test_release_handoff.py:1,19,24-25`
- `tests/test_scaffold.py:192,196,241,244-273,339`
- `tests/test_v013_contracts.py:201`

`engine-shas.json` は [skills/audit/references/engine-shas.json:47-51] にあります。生成対象の harness body は `scaffold.py` の `_harness_sources()` から得られ、normalized SHA と比較されます [tests/test_scaffold.py:334-351]。version、SHA table、docs、generated stamps の整合性は [tests/test_v013_contracts.py:182-201] で検証されます。

この repo 自体には `.claude/doc-audit.json` は存在しません。`.claude` 内で確認できるファイルは `.claude/settings.local.json` のみです。したがって relevant config keys は UNKNOWN です。

## Open questions / UNKNOWN

- Issue #59 の「blocking-finding files + worktreeDigest」を使う Phase-4 flip counter は現行コードに存在しません。
- Phase-4 findings の history carry-forward は未実装です。
- `package.json`、Makefile、CI による lint/type/quality gate は存在確認できません。
- `.claude/doc-audit.json` の実 repo 設定値は存在しないため UNKNOWN です。
- full test suite の 669 errors はコードの assertion failure ではなく、一時 directory を作れない実行環境エラーです。