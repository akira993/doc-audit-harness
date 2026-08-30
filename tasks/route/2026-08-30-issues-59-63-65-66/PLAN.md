# PLAN — docaudit v0.16.0: #63 sealed-config verify-on-read ＋ #59 Phase-4 flip 計測・carry-forward

作成: 2026-08-30 boss（Fable/Opus）。**v8**（Sol R1〜R5＋Opus 敵対レビュー R1・R2 反映。E-1 は advisor 裁定で flip 計測を維持。R2-1 は advisor 助言に基づき方針 B。R3-1 は信頼クラスの明示＋fail-closed で対応）。入力: `00-issue-review.md`、`01-survey.md`、`02-critique-r1.md`、`03-critique-r2.md`、`04-critique-r3.md`、GitHub #63 / #59、ユーザー決定（対象 #63＋#59 → v0.16.0、#63 は verify-on-read）。

## 1. 目的

1. **#63** — run 中に `.claude/doc-audit.json` を「書き換え → 消費者に読ませる → 復元」する TOCTOU を閉じる。方式は **verify-on-read**: open-run が EVIDENCE（会話内でのみ保持され、ディスク上の攻撃者が書けない唯一の成果物）に載せた `config` sha を基準に、**plugin engine の判定経路上で設定を読むすべての消費者**（スクリプトも SKILL 本文の値参照も）が「自分が実際に読んだバイト列の sha == 封印 sha」を検査し、不一致なら fail-closed する。検知は gate の taint 記録に一元化し、次回 open-run は設定が復元されていても `--accept-config` を要求する。
   - 採らない案: 凍結コピー＋`CFG` 再束縛（コピー先が live と同じ信頼クラス）。
   - **脅威境界と信頼クラス**（Sol R2-1 → 方針 B）: 攻撃者は run 中に repo 内ファイルを書ける主体。plugin engine（`$SD` 配下、repo 外）は信頼される。**project 側 harness（`.claude/commands/check-docs.md`、`.claude/skills/doc-lint/SKILL.md`、`scripts/check-docs.py`）と config の `docAuditCommands` が指す任意コマンドは、その定義ファイル自体が repo 書き込み者に改変可能**であり、config 改竄より安価な経路（コマンド定義や engine 複製を書き換えて所見 0 にする）が常に存在する。よって Phase-4 で実行される project コマンドの所見は「repo 書き込みレベルの信頼」で扱い、その config 読みは検証対象に含めない（含めても防御にならない）。sealed-config の保証は **plugin engine の判定経路を完全に**覆う。ただし Phase 0.5 で SKILL が **直接起動する engine 複製**（:302）には defense-in-depth として sha を付ける（§5.1 S6）。Sol 案 A（sha を受け取れないコマンドの所見を report-only に降格）は doc-lint の FAIL が NEEDS FIX を起こさなくなる製品契約変更で #63 の範囲外。将来ユーザーが厳格化を望む場合の選択肢として REVIEW に残す。
   - **run をまたぐ状態の信頼クラス**（Sol R3-1）: `docaudit-last-run.json`・`docaudit-history.json`・anchor は repo 内にあり、repo 書き込み者に改変可能である（既存設計。EVIDENCE は run 終了と共に消えるため、run をまたいで改変不能な置き場は存在しない）。よって acceptance marker（`configAcceptanceRequired`）と隔離失敗 marker は **セキュリティ境界ではなく、検知済み改竄をユーザーに可視化し既定で止める運用安全機構**である。run 内で検知された改竄は、その場の REFUSED 報告と last_run record が一次の監査痕跡であり、これは marker 削除で消えない（会話・report に出ている）。このクラスで採るのは fail-closed のみ: last_run が **存在するが不正 JSON／型不正**なら exit 6 相当（`last-run-unreadable`、`--accept-config` で続行）、欠落は cold start（fresh install と区別不能。ADOPTION に明記）。
2. **#59** — Phase-4 codex review（サンプリング）を決定的検査器の契約で扱うのをやめる。旧 ledger（P1）と新信頼クラス（P3/P4）は撤回済み。(a) gate が flip を決定的キー（blocking 所見の正規化済み file 集合）で、同一入力条件（worktreeDigest × contractVersion × configSha × carryForwardSha の 4 項目。S10 が正）の直近 full record と比較して **warning**、(b) gate が書いた history だけを出所とする data-only carry-forward（**検証済み repo path＋severity のみ**、自由文は再投入しない）、(c) 契約文言の是正。
3. **再発防止の構造**: 消費者 registry（§9）を単一の真実として PLAN に固定し、テスト内の同一 registry と実コード／SKILL.md の等値を CT で検査する。件数は registry から導出し、変更には PLAN 改訂を伴わせる。

## 2. 入力・参照資料

- `00-issue-review.md`、`01-survey.md`、`02-critique-r1.md`、`03-critique-r2.md`（対応表は REVIEW.md）、GitHub #63/#59、`59-design-note.md`（撤回済み）
- 事実（抜粋。詳細は 01-survey）: `CFG` は SKILL.md:13 で 1 回束縛。open-run.py:157-162 が raw bytes の sha256 を EVIDENCE.config に載せる（exit 0/2/4/6、exit 6 は「現在 sha ≠ expectedConfigSha」のときのみ :164-174、marker は消さず迂回するだけ）。gate は decide-verdict.py:684-701 で live 1 回読み＋封印比較、不一致で `config_taint` → last_run `config-changed`（:1001-1011）。gate/seal-run/classify-run/plan-dispatch は `change-set-sha.py` に config **path** を渡して再読させ、seal-run は子の失敗を exit 2 に畳む（seal-run.py:49,54,77）。SKILL:421 は seal-run の exit 5 以外を即 release。history は EVIDENCE.history（plan-dispatch.py:152、Phase 2 で封印）で照合、不一致は `.tainted-<runid>` へ隔離（:990、失敗は握り潰して release :1022）、書き戻しは `{"entries":...}` のみ（:946）。plan-dispatch は `entries` だけ検査して `historyStatus="ok"`（plan-dispatch.py:94,108）。Phase-4 evidence finding は `{severity, source, title}`。codex 出力 schema は `file` 非空文字列のみ要求。`generic-layers.py` は scaffold が harness 本体として複製（scaffold.py:164）。`/check-docs`・`doc-lint` テンプレートは `scripts/check-docs.py --config .claude/doc-audit.json` を呼ぶ（scaffold.py:81,113）。`import-audit-scope.py --check` は `configSha` を返す（`absent`/`not-imported` でも返す :286,:589,:635）。SKILL 本文の config 値参照: `phase3Backend`（:81）、`maxImpactedDocs/docGlobs/semanticSearch.minScore`（:380）、`docAuditCommands`（:305,:530）、`boundaryCommand`（:548）、`reviewCommands`（:549）、`codexReview.model`（:585）、`codexReview.timeoutMs`（:605）、`reportPath`（:663）、`contextMode`（:131-140）、`harness`（:268 付近）。`mdq-index.sh` は config を 2 回、`compute-baseline.sh` は 3 回読む。`impact-supplement.py` と `fix-scope.py` は `--config` 任意（config 無しの契約テストあり）。`skills/init/SKILL.md:101` は封印外で `set-config-key.py` を呼ぶ。`validate_repo_path` は実行 OS の `isabs` に依存（docaudit_paths.py:37）。dir-framework は `engineVersion:"0.15.0"`。テスト基線 655 OK。既存 exit code 0/1/2/3/4/5/6（5 は seal-run.py:60,62 の drift、SKILL.md:418 が分岐。Opus m-1）。exit 7 は未使用（実測）。

## 3. 担当

boss = Fable/Opus（計画・レビュー・検証再実行・branch/commit。実装は書かない）。

## 4. 実行者

worker = GPT-5.6 Sol `high`（差し戻しは同一セッション resume、effort `medium` 既定）。計画批判 Sol `xhigh`。worker の `workspace-write` は `.git` を書けないため branch/commit は boss。

## 5. 成果物

### 5.1 #63 verify-on-read

- **S1** `skills/audit/scripts/sealed_config.py`（新規モジュール兼 CLI）
  - `load_sealed_config(path, expected_sha) -> (raw, doc)`: `O_NOFOLLOW` で 1 回だけ読み、`"sha256:"+sha256(raw)` を `expected_sha`（必須）と比較。不一致は `SealedConfigMismatch`。
  - CLI: `python3 sealed_config.py --config PATH --expect-sha SHA (--print | --get DOTTED.KEY [--default JSON] [--raw])`。成功 exit 0。`--print` は検証済み JSON 全体。`--get` は値を JSON で出力（欠落時は `--default`、無ければ `null`）。`--raw` は値が文字列のときクォート無しで出力、`null` は空文字列、文字列以外なら exit 2。不一致: **exit 7**＋stderr `sealed-config-mismatch: expected <sha> observed <sha>`。読めない・JSON 不正・引数不正: exit 2。
- **S2** Python 消費者を S1 経由に統一し `--expect-config-sha` を追加（§9.1 registry の列「フラグ」に従う）:
  - 必須: `change-set-sha.py`、`classify-run.py`、`codex-review-plan.py`、`plan-dispatch.py`、`resolve-impact.py`、`start-run.py`。
  - 条件付き必須（`--config` を渡したときのみ必須）: `fix-scope.py`、`impact-supplement.py`（R2-6）。
  - 任意（渡されたときだけ検証。audit からの呼び出しは CT-1 で付与を強制）: `set-config-key.py`（`/docaudit:init` が封印外で呼ぶ）、`generic-layers.py`（harness 複製として sha 無しで起動される。**複製先は単独ファイルで動く契約のため `sealed_config` を import せず、同じ exit 7／token／読み 1 回の最小封印読取をファイル内に内包する**。worker 報告 2026-08-31 の boss 裁定、方式 1）。
  - 子プロセス pass-through: `classify-run.py` / `plan-dispatch.py` / `decide-verdict.py` / **`seal-run.py`**（R2-2）→ `change-set-sha.py` へ同じ sha。親は子の exit 7 を**そのまま exit 7 として保持**（seal-run は exit 2 に畳まない）。gate は子 exit 7 を `config_taint=True` に流す。
  - `decide-verdict.py`（`--expect-json`）と `seal-run.py`（`--evidence`）は `evidence["config"]` を expected として S1 を使う。
- **S3** shell 消費者（`mdq-index.sh`、`ax-probe.sh`、`codex-probe.sh`、`codegraph-probe.sh`、`graphify-probe.sh`、`cocoindex-probe.sh`、`compute-baseline.sh`）に `--expect-config-sha`（必須）を追加し、config の読み取りを **`sealed_config.py --print` 1 回**に統合（mdq-index.sh の 2 回、compute-baseline.sh の 3 回を廃止）。不一致は exit 7＋token。**補足（実装レビュー R1、boss 承認）**: 直接起動時に config が不正 JSON／欠落／`--config` 省略の場合も `sealed_config.py` の入力エラーとして exit 2（旧契約の exit 0＋`invalid-config` JSON は廃止）。run 内では open-run が config を object として検証済みで、到達し得るのは改竄（exit 7）のみ。SKILL の "Always exits 0" と ADOPTION の該当文を実装に合わせる。
- **S4** `open-run.py`:
  - `--expect-config-sha SHA`（`--break-lock`/`--release` 以外で必須）: 封印しようとするバイト列の sha と不一致なら exit 2＋stderr `config-changed-before-open`。SKILL は `import-audit-scope.py --check` の `configSha` を `PRECHECK_CONFIG_SHA` に束縛して渡す。
  - **pre-check の一体化**（Opus M-3）: `import-audit-scope.py --check` は `configSha` を計算したのと同一バイト列から導出した `scopePath`（`auditScope.path`、既定 `.claude/audit-scope.json`）を出力に含め、`--scope` は省略可（省略時は同バイト列から導出）。SKILL は :25 の独立読みを廃し、`--check` 出力から `AUDIT_SCOPE_PATH` を束縛する。これで pre-open の独立読みは :14（`ANCHOR_PATH`、S4 の anchorPath 照合で閉じる）だけになる。
  - `--anchor-path` が封印 config の `anchorPath` と不一致なら exit 2。
  - exit 6 の述語: last_run に `configAcceptanceRequired:true` がある **または** 旧述語（`verdict=="REFUSED" && reason=="config-changed" && expectedConfigSha != 現在 sha`。v0.15.x の gate が書いた last_run との互換。Opus M-2）が成立する限り、exit 6。旧述語は **`configAcceptanceRequired` キーが存在しない last_run にのみ**適用する（marker を消費した後の last_run に旧述語が再発火しないため。Opus V7-8）。last_run が存在するが不正 JSON／object でない場合も exit 6（`last-run-unreadable`）。**marker 消費は 1 トランザクション**（R3-2）: (1) last_run を読み検証、marker あり＆`--accept-config` 無しなら lock 取得前に exit 6、(2) lock 取得、(3) `--accept-config` 時は last_run の他フィールド（`runid`/`reportStatus`/`ts` 等）を保持したまま `configAcceptanceRequired:false` を atomic replace で書く、(4) 書き込み失敗なら lock を解放して exit 2（open 不成立）。`previousReportStatus` は (1) で読んだ値を使う。
  - **隔離失敗からの回復 — 単一の回復規則**（R3-3/R4-1/R5-1〜3）:
    - 「隔離待ち」は last_run の `historyQuarantineFailed:true` **または** lock holder JSON の `historyQuarantineFailed:true` で表す。gate は S5 で両方に書く（holder は **同一 inode 上の rewrite**: `ftruncate(0)` → 書き込み → `fsync`。atomic replace は inode が変わり EVIDENCE.lockIno 検査を壊すため禁止）。両方の書き込みが失敗した場合（disk full・EIO 等の二重障害）は stderr に `quarantine-marker-unpersisted` を出して exit 3（release せず）。この残余（marker 未永続化＋その後の `--break-lock`）は §1 の運用安全クラスの既知の限界として ADOPTION に明記し、これ以上の機構は追加しない。
    - **last_run の unreadable 正規化**（R5-3）: parse 失敗・非 object・`configAcceptanceRequired`/`historyQuarantineFailed` が非 bool のいずれも単一の `last-run-unreadable` 状態。unreadable では両 marker が立っていた可能性があるとみなし、`--accept-config` **かつ** live history が存在すれば隔離（cold start）を要求する。
    - **通常 open**（Opus C-1: 実行中 run の lock を奪わない）: 現行どおり **`O_CREAT|O_EXCL` を先行**させ、既存 lock があれば flock の有無に関係なく無条件 exit 4（Phase 0〜4 の間は誰も flock を保持していない二層設計＝SKILL.md:851-852 を維持）。lock が無いときだけ、(a) last_run を検証（unreadable 正規化）、(b) `configAcceptanceRequired`（または旧述語）→ exit 6、(c) fresh lock 作成（`O_EXCL` 失敗は exit 4）、(d) **lock 保持下で**隔離待ち（last_run marker または unreadable）→ `docaudit-history.json` を `.tainted-<runid>-<epoch>` へ rename、失敗または live 残存なら作成した lock を unlink して exit 2 `history-quarantine-pending`（Opus V7-7: lock 無しの rename 競合を避ける）、(e) marker を消した last_run を atomic replace（失敗は lock 解放＋exit 2）。
    - **`--release` / `--break-lock`**（Opus M-8: 緊急脱出路を塞がない）: `O_NOFOLLOW` で開く → exclusive flock（取れなければ `gate-running` で拒否＝既存） → fd/path inode 一致 → holder object 検証 → `--release` は holder runid == `--runid` → **holder の `historyQuarantineFailed:true` を last_run へ best-effort でマージ**（失敗しても続行） → 旧 lock を unlink、exit 0。隔離は行わず、次の通常 open の (c) に委ねる。残余（holder marker のマージ失敗＋last_run marker 未永続化 → 次 open で tainted history が正規化）は §1 の運用安全クラスの既知限界として ADOPTION に明記。
- **S5** `decide-verdict.py` 早期 taint 経路 `--taint-observed {config,history} --observed-by <ID>`（ID は §9.4 の固定列挙。列挙外は exit 2）:
  - identity: EVIDENCE の runid/runDir/lockIno と lock ファイルの holder runid・inode・flock 取得を検査。**非所有（lock 欠落／holder runid 相違／inode 相違／flock を他プロセスが保持）の 4 ケースでは何も書かず exit 3**（R2-5）。manifest/dispatch の有無に依存しない。
  - `config`: last_run `{runid, verdict:"REFUSED", reason:"config-changed", expectedConfigSha: evidence.config, configAcceptanceRequired:true, observedBy, ts, reportStatus:"not-requested"}` を書き、**書き込み成功後にのみ** release、exit 3。live が復元済みでも記録。既存 gate 内 mismatch 経路（:1001-1011）も同形式に統一。
  - `history`: `docaudit-history.json` → `.tainted-<runid>` へ隔離し last_run `reason:"history-changed"`（marker なし）。**隔離に失敗（`os.replace` 例外、または隔離後も live history が存在）したら last_run と lock holder JSON の両方に `historyQuarantineFailed:true` を書き（last_run に書けなくても holder には自 run の lock fd で書く）、release せず exit 3＋reason `history-quarantine-failed`**（lock ファイルが残り次回 open は exit 4。`--break-lock` 後も S4 の marker により open-run が隔離を再試行し、成功するまで開かない）。既存 gate の隔離失敗経路（:990,:1022）にも同じ規則を適用（R2-4/R3-3）。
  - `--observed-by` は SKILL が起動した **top-level スクリプト**の ID（§9.4）。子プロセス（`change-set-sha.py`）や open-run（lock 取得前で封印が無い）は observer にならない（R3-5）。record には任意の `detail`（≤ 200 文字、制御文字なし）で子の情報を添えてよい。
- **S6** `skills/audit/SKILL.md`:
  - `CONFIG_SHA` は checkpoint 値ではなく EVIDENCE.config からの導出値。各 turn 開始・各フェーズの最初の消費者呼び出し前に再導出（R1-7）。
  - §9.1 の全 call site に `--expect-config-sha "$CONFIG_SHA"`（open-run は `"$PRECHECK_CONFIG_SHA"`）。
  - **SKILL 本文の config 値参照は §9.2 registry の束縛行に置換**: `VAR="$(python3 "$SD/scripts/sealed_config.py" --config "$CFG" --expect-sha "$CONFIG_SHA" --get KEY --default DEFAULT [--raw])"`。VAR の代入行はこの 1 形式のみ。Read ツール・`json.load(open(...))` で config を読むことを Guardrails で禁止。
  - Phase 0.5 installed（:293-303）の **互換表**（R3-4）: 3 生成物が揃わない → 既存どおり `HARNESS_STATE=broken`（pre-flight 不要・plugin generic は非 evidence 診断。既存契約、本 route では変更しない）。3 生成物が揃う場合、`scripts/check-docs.py` の engine stamp が **現 plugin 版と完全一致（== 0.16.0）** のときだけ複製を `--expect-config-sha "$CONFIG_SHA"` 付きで直接起動。stamp が **それ以外（旧版・未来版・欠落・不正・modified）** なら複製を起動せず、plugin の `generic-layers.py --layer all ... --expect-config-sha "$CONFIG_SHA"` を pre-flight engine（evidence）として実行し、harness WARN＋`/docaudit:init --harness --refresh` 案内（commands[] entry に `kind:"script-backed"`、`command` に plugin engine と理由を記録）。「将来版は互換」とは仮定しない。dir-framework 等 0.15.x harness への観測可能な挙動変更として ADOPTION に明記。
  - harness decline（:268-282）: `set-config-key.py --expect-config-sha` で書き込み → release → **`import-audit-scope.py --check` を再実行して `PRECHECK_CONFIG_SHA`/`AUDIT_SCOPE_PATH`/`AUDIT_SCOPE_STATE` を再束縛** → open-run（R2-3）。この再 open は現行どおり**散文で「通常の open-run コマンドを再実行」と指示し、新しい literal な `open-run.py` 行を追加しない**（追加すると CT-1 の N が 23 になる。Opus m-5）。
  - 停止規約（Guardrails）: 消費者が **exit 7 または stderr に `sealed-config-mismatch`／`sealed-history-mismatch`** を返したら、その時点で `decide-verdict.py --run-dir ... --runid "$RUNID" --expect-json "$EVIDENCE" --taint-observed <config|history> --observed-by <ID>` を実行して REFUSED を報告する。**この判定は seal-run（:419-423）を含む既存の release 分岐より前に置く**。gate を経由せず `open-run.py --release` で終わらせない。
  - Phase-4 docAuditCommands（:530）と harness 複製の信頼クラスを Guardrails に明記（§1）。
- **S7** 文書: `docs/ADOPTION.md`（:586-596 config 変更→消費者レベル検知・exit 7・acceptance marker・復元後も `--accept-config` 必須；:476-484 sealed evidence；`v0.16.0 behavior changes`（installed 旧 stamp の fallback、全 tree 同期必須、downgrade で `phase4Runs` 消失）；3c の部分コピー手順 :256 改訂；**信頼クラス段落**: 「configured docAuditCommands の所見は repo 書き込みレベルで信頼される。sealed-config の保証は plugin engine の判定経路を完全に覆う」）、`docs/ADOPTION.ja.md`（同内容）、`skills/audit/references/config-schema.md`（history 文書 schema・`phase4Runs`）、README（必要箇所）。

### 5.2 #59 flip 計測・carry-forward

- **S8** Phase-4 evidence（SKILL.md:622-631）: codex-review 由来 finding に `"file"` を追加、`codexReview.promptVariant`（`full`/`diff`/`null`）と `codexReview.carryForwardSha`（文字列。S11 の出力、未添付は `"none"`。Opus V7-4）を追加。gate: `source:"codex-review"` の finding は `file` が非空文字列でなければ REFUSED。`file` は `docaudit_paths.normalize_finding_path(repo, value)` で正規化（R2-14 の順序: (1) Windows drive/UNC（`^[A-Za-z]:`、`^\\\\`、`^//`）は OS 非依存に不正、(2) 先頭 `./` 除去（`\` は変換しない。含む入力は (5) で unresolved）、(3) そのまま repo 相対として妥当かを `validate_repo_path` 相当で検査、(4) 不成立のときだけ末尾 `:<digits>(:<digits>)?` を除去して再検査、(5) **正規化前の入力文字列**に対して 絶対・`..`・制御文字・`"`・`\`・空・直列化後 512 bytes 超のいずれかなら **unresolved**（(2) の置換後に `\` を検査しても死文になるため。Opus m-3））。unresolved は verdict の所見としては残るが `findings`/flip 集合/carry-forward から除外し、`unresolvedFileCount` として record と warning に載せる（R2-10）。
- **S9** history 新キー `phase4Runs`: gate は §9.7 の eligibility を満たす run だけ record を追加: `{runid, ts, worktreeDigest, contractVersion, configSha, carryForwardSha, unresolvedFileCount, truncated:false, findings:[{file, severity}]}`（`carryForwardSha` は Phase-4 evidence の `codexReview.carryForwardSha`＝S11 が出力し SKILL が evidence に載せる値。未添付は `"none"`。Opus M-5）（`head`・`title`・`source` は持たない。severity は `CRITICAL|HIGH|MEDIUM|LOW` の 4 値）。**findings は `source=="codex-review"` の finding のみ**から作り、(file, severity) で重複排除し `(severity rank desc, file asc)` の canonical 順で保存（R3-8/R3-10）。**flip 用集合は完全保持**する: 上限は findings ≤ 500・file ≤ 512 bytes（record 最大 ≈ 300 KiB。parser の record 上限 512 KiB はこの最大より大きい値で固定し、writer→parser の最大境界を CT-5 で往復検査。R3-7）。超過時は先頭 500 件を保存し `truncated:true` とし、その record は flip 比較の対象から外す（比較不能を warning）。`blockingFiles` は保存せず導出。**保持 5 件、上限 6 件**（Opus M-6/V7-1）。trim 規則: 新しい順に 5 件を残すが、**「最新 record と異なる worktreeDigest を持つ最新の record」（= 次の carry-forward source）は 5 件に含まれなくても必ず残す**（同一 digest の再実行が続いても source が押し出されず、prompt 入力が黙って変わらない。advisor 裁定）。gate は書き込み前に同じ parser で round-trip 検証し、失敗時は record を追加せず warning。history 全体（`entries`＋`phase4Runs`）を同じ atomic 書き込みで保存。
  - **共通 parser** `docaudit_cache.parse_history_document(data) -> (entries, phase4Runs, warnings)`（常に 3 値。正常時 `warnings=[]`、退化時に理由文字列を入れる。`entries` 不正は例外＝corrupt）（R2-8）: `data` が list（旧版 top-level array）なら `entries=data, phase4Runs=[]` として受理。`entries` は既存 `parse_history`、`phase4Runs` は **字句検査のみ**（ファイルシステム非依存。R4-2）: 件数 ≤ 6（保持 5＋carry-forward source guard 1。Opus V7-1）・必須キー・型・severity 列挙・file が字句的に正規形（先頭 `./`・`/`・drive/UNC なし、`..` 成分なし、`\`・`"`・制御文字なし、JSON 直列化後 ≤ 512 bytes）・findings ≤ 500・`truncated` bool・`carryForwardSha` 文字列・record の **canonical 直列化**（`json.dumps(record, sort_keys=True, separators=(",",":"), ensure_ascii=True)`）≤ 512 KiB・`phase4Runs` 全体の canonical 直列化 ≤ 1 MiB（Opus M-6）を検査（R4-5: file 直列化 ≤ 512 × 500 件＋固定 overhead < 300 KiB で上限内。CT-5 は `"`・`\` を含まない最悪形＝非 ASCII 6 倍膨張で境界を往復）。record 内の未知キーは無視（前方互換）。存在・通常ファイル・symlink の検査は S11 の carry-forward 選択時だけ行う。**`phase4Runs` の不正は corrupt ではなく退化**（Opus M-4）: `(entries, [], warning)` を返し、決定的 PASS cache（`entries`）を道連れにしない。corrupt は `entries` 不正のときだけ。使用者と挙動は §9.6 の真理値表に従う（R3-9）。
- **S10** flip 計測: 現 run が §9.7 の eligibility を満たすとき、`worktreeDigest`・`contractVersion`・`configSha`・`carryForwardSha` の 4 つが一致し `truncated:false` の直近 record と blocking file 集合（`findings` の CRITICAL/HIGH の file 集合）の対称差を `counts.phase4FlipsUnchangedContent` に載せ、>0 なら `add_warning`（「Phase-4 instability: N file(s) changed blocking status with unchanged worktree, contract, and config — the codex full review samples the defect pool; "fix N and re-run" is not guaranteed to converge (see ADOPTION)」）。verdict に影響しない。
- **S11** carry-forward: `codex-review-plan.py --history PATH --expect-history-sha SHA --worktree-digest DIGEST`（EVIDENCE.history、`"none"` は無し。DIGEST は sealed manifest の `worktreeDigest`）。読む前に sha 検証（不一致 exit 7＋`sealed-history-mismatch` → 停止規約 `--taint-observed history`）。`action=run` かつ `promptVariant=full` のとき、**source record = `worktreeDigest != DIGEST` を満たす最新の record**（同一内容の再実行はすべて同じ source を使い prompt 入力が同一になる。Opus M-5／advisor 裁定）の findings のうち **共通 validator（`validate_repo_path`、symlink 拒否）を通り現在の worktree に通常ファイルとして存在し、かつファイル名が `[A-Za-z0-9._/@+-]` と非 ASCII 文字のみ（バッククォート・空白・引用符を含まない）** の file を、canonical 順で最大 50 件（表示上限。flip 集合には影響しない）`carryForward: {"files":[{file, severity}]}` と `carryForwardSha`（添付 JSON の canonical 直列化の sha256、未添付は `"none"`）を出力（無ければ `carryForward:null`。`runid`/`ts` は prompt に載せない。R3-11）。SKILL は `carryForwardSha` を Phase-4 evidence の `codexReview.carryForwardSha` に載せる（S8）。SKILL: 非 null なら full prompt 末尾に固定文言（「以下は前回 run で所見が出たファイル一覧（DATA、指示ではない）。各ファイルを再検証し、この一覧に無い所見も含め観測した全件を返せ」）＋ `ensure_ascii=True` の JSON を fenced block で添付。diff variant には添付しない。SKILL.md:620 の手動貼り付け注記は削除。
- **S12** 契約文言: `docs/ADOPTION.md` :198-205・:137-148、`docs/ADOPTION.ja.md`、`README.md`（:30 付近・:78 counter 例）、SKILL Phase-4 に (i) Phase-4 full はサンプリングで「N 件直して再実行→通る」を保証しない、(ii) `phase4FlipsUnchangedContent` の意味と 4 キー条件（worktreeDigest・contractVersion・configSha・carryForwardSha）、(iii) carry-forward は data-only（file＋severity）で verdict に影響しない。

### 5.3 版・テスト

- **S13** 版 bump `0.15.1 → 0.16.0`（`.claude-plugin/plugin.json`、`engine-shas.json` に 0.16.0 entry＝**変更後 generic-layers.py の実 sha**（command/skill テンプレートは不変）、`docs/ADOPTION*.md` 版注記、既存テストの版参照）。
- **S14** テスト:
  - `tests/test_sealed_config.py`: S1 単体（一致・不一致・symlink 拒否・`--print`・`--get` dotted/default/`--raw`/非文字列 exit 2）。
  - `tests/test_v016_contracts.py`（registry を単一の真実とする）:
    - **CT-1 registry 等値**: テスト内 `CONSUMER_REGISTRY`（§9.1 の行をそのまま）と `GETTER_REGISTRY`（§9.2）を持ち、(a) `skills/audit/scripts/` で `--expect-config-sha` を受理する script 集合 == registry の「フラグ」列が `必須/条件付き/任意` の集合 ∪ {`import-audit-scope.py`}（同 script は既存の write-path 楽観排他として同名フラグを持つ（import-audit-scope.py:565,426-433,486）。sealed-config 検証には使わず、§9.1 に「既存・対象外」として明示。Opus V7-2）（過不足なし）、(b) SKILL.md の `"$CFG"` を含む各行が、registry の「CLI 形」に一致するか（`--expect-config-sha "$CONFIG_SHA"` / `"$PRECHECK_CONFIG_SHA"` / `--expect-sha "$CONFIG_SHA"`）、または exemption 行（内容で識別、3 個のみ: `ANCHOR_PATH=`・`import-audit-scope.py ... --check`・`decide-verdict.py`。`AUDIT_SCOPE_PATH=` は exempt しない。Opus V7-5）であること、(c) GETTER_REGISTRY の各 (key, VAR) について SKILL.md に `VAR="$(python3 "$SD/scripts/sealed_config.py" --config "$CFG" --expect-sha "$CONFIG_SHA" --get key` 形式の束縛行が **ちょうど 1 行**あり、VAR の他の代入行が無いこと、(d) 各 shell 消費者が `sealed_config.py` を **ちょうど 1 回**呼び `json.load(open(` を含まないこと、(e) `decide-verdict.py` の `OBSERVERS` 列挙 == §9.4。出力 `call sites N／exempt M／getters G／scripts K／observers O` を stdout に出し、§9.5 の期待値と一致を assert。
    - **CT-2 pair tests**: registry の全 script について「一致 sha → 正常 exit」「不一致 sha → registry の mismatch exit＋token」の対を fixture 上で実起動（open-run は exit 2＋`config-changed-before-open`、seal-run は子経由で exit 7、decide-verdict は REFUSED exit 3）。出力 `対象 K 本を検査`。
    - **CT-2b 実行時計測**（R3-6）: `PYTHONPATH` に test 用 `sitecustomize.py` を置き、各プロセスで (i) config path の open 回数を **`builtins.open` と `os.open` の両方**をフックして記録（Opus 実測: `os.open` だけでは `json.load(open())` を捕捉できない。macOS 15／CPython 3.14 で親・`subprocess` 子・bash 内 `python3 -c` の全てにロードされることは実測済み）、(ii) `sys.argv` をログに記録。一致 sha の正常経路で registry の全 Python 消費者（shell 消費者の内蔵 python を含む）を実行し、**config の open 回数が §9.1 の「読み」列どおり**（直接 = 1 回、`seal-run.py` = 0 回、`set-config-key.py` = 読み 1 回＋書き込み。Opus M-7）、pass-through 親（classify-run・plan-dispatch・seal-run・decide-verdict）の子 `change-set-sha.py` の argv に同じ `--expect-config-sha` が含まれることを assert。さらに親の検証成功後・子起動前に config を差し替えるケース（sitecustomize が親の最初の open 完了を検知してファイルを書き換える）で子が exit 7 になり親が exit 7／taint を返すことを assert。
    - **CT-3 TOCTOU E2E**: open-run → 改竄 → probe exit 7 → 復元 → `--taint-observed config` → last_run marker → 次 open-run が sha 一致でも exit 6 → `--accept-config` で開き marker が消費される → その次は通常 open。gate 実行中に子 `change-set-sha.py` が読む config を差し替え → `config-changed` taint。seal-run の子経由 exit 7 が SKILL の release 分岐より前に token 判定されること（SKILL テキスト順序の契約検査）。
    - **CT-3b 非所有**: `--taint-observed` の 4 非所有ケースで last_run/history/lock が不変・exit 3。
    - **CT-4 open-run**: `--expect-config-sha` 不一致 → exit 2 token；anchorPath 不一致 → exit 2；decline 再 open で precheck 再実行後は成功；last_run が不正 JSON → exit 6 `last-run-unreadable`、`--accept-config` で開く；marker 消費の書き込み失敗（last_run をディレクトリに置換）→ lock 解放＋exit 2、他フィールド保持の確認；`historyQuarantineFailed` marker → 次の通常 open で隔離再試行成功なら open、失敗で exit 2 `history-quarantine-pending`（`--break-lock` 自体は隔離せず marker をマージして exit 0。その**後の次の通常 open** で同様。Opus V7-6）。
    - **CT-4c 回復状態表（table-driven、R5-5／Opus C-1）**: {holder marker のみ／last_run marker のみ／両方／holder 不正 JSON／last_run 非 object／marker 非 bool／marker なし} × {通常 open（lock 不在）／通常 open（**lock 存在・flock 非保持** → 無条件 exit 4、history・last_run 不変）／`--release`（runid 一致・不一致）／`--break-lock`} × {隔離成功／失敗（`.tainted-*` 先置き）} の各組み合わせで、期待 exit・lock の有無・history の位置・last_run 内容（release/break 後に holder marker が last_run へマージされていること）を assert。flock 競合（別プロセスが保持）と inode 差替えは全モードで何も変えず exit。marker 書き込み二重障害（state dir と lock を read-only 化）→ exit 3・`quarantine-marker-unpersisted`・release なし。
    - **CT-4d plan-dispatch funnel**: `impact.historySha` 不一致 → exit 7 token（既存 test_plan_dispatch.py:40 の exit 3 期待を更新）→ `--taint-observed history --observed-by plan-dispatch.py` → 隔離。
    - **CT-5b eligibility（table-driven）**: §9.7 の valid 8 行すべてで期待どおり（record 有無）、invalid class（キー欠落・列挙外 state・`null`×`completed`・`full`×`not-active`・mode 不整合）すべてで REFUSED。
    - **CT-4b harness 互換表**: stamp == 0.16.0 → 複製直接起動（sha 付き）；stamp 0.15.1／未来版／欠落／modified → plugin engine を evidence として起動＋WARN（SKILL テキスト契約＋fixture 実行）。
    - **CT-5 gate/history**: `file` 欠落 → REFUSED；正規化（`./docs/a.md`・`docs/a.md:10` が `docs/a.md` と同一、`docs/spec:10` が実在すればそのまま、`docs\a.md`・`C:/x`・`../x` は unresolved。worker Q1 裁定: `\` は変換せず拒否）；record 生成と 2 run 連続蓄積；3 キー一致で集合相違 → counter/warning、`contractVersion`/`configSha` 相違 → 0；diff variant は record 無し；旧 history（キー無し）cold start；不正 `phase4Runs`（非 list・`..` file・`"` を含む file・501 件・canonical 直列化 513 KiB・全体 1 MiB 超）→ §9.6 どおり 4 reader すべてで **退化**（`entries` の cache/regression は維持、`phase4Runs` は空＋warning、gate は隔離せず新 record から再構築）；`entries` 不正 → 4 reader すべてで corrupt（plan-dispatch `historyStatus:"corrupt"`、resolve-impact は regression 無し、codex-review-plan は `carryForward:null`、gate は隔離）；record の未知キーは無視して valid；**保存後に path が symlink 化しても history は valid のまま、carry-forward からだけ除外**（R5-4／Opus V7-3）；旧版 top-level array は valid；保持 5（同一 digest の再実行を 6 回続けても carry-forward source が残り、6 回目の prompt 入力が不変）；writer→parser の最大境界（500 件 × 512 bytes）が往復で valid；501 件目以降は `truncated:true` で flip 比較対象外＋warning；入力順を変えても record と flip が不変（canonical 順）；非 codex-review の file 無し finding は record に影響しない；manifest mode と `promptVariant` の不一致 → REFUSED；round-trip 失敗時は record 追加なし；隔離失敗（`.tainted-<runid>` をディレクトリで先置き）→ release せず exit 3、lock 残存、last_run に `historyQuarantineFailed:true`。
    - **CT-6 codex-review-plan**: history 有り full → `carryForward.files` は実在 file のみ；diff → null；sha 不一致 → exit 7 token → `--taint-observed history` → 隔離＋last_run＋次 run cold start；`"none"` → null。
    - **CT-7 文書契約**: ADOPTION（en/ja）・README・SKILL・config-schema に S7/S12 の文言、`phase4FlipsUnchangedContent`、`--expect-config-sha`、`sealed-config-mismatch`、`configAcceptanceRequired`、全 tree 同期、installed 旧 stamp fallback、信頼クラス段落。
  - 既存テストの更新（フラグ追加に伴う呼び出し修正、`test_wp12_contracts.py`、`test_decide_verdict.py`、`test_start_run.py`、`test_codex_review_plan.py`、`test_impact_supplement.py`（config 無し契約は維持）、`test_scaffold.py`（新 sha）等）。

## 6. 完了条件（機械判定）

1. `python3 -m unittest discover -s tests` 全 green（基線 655 以上）。**boss が再実行して追認**。
2. CT-1 出力 `call sites N／exempt M／getters G／scripts K／observers O` が §9.5 の期待値と一致。worker の実測が異なる場合は実装を変えるのではなく **報告**し、boss が registry（PLAN §9）を改訂する。
3. CT-2 出力 `対象 K 本を検査` が K と一致し、各本に一致／不一致の対がある。
4. `grep -n 'json.load(open' skills/audit/scripts/*.sh` のヒットが 0、`skills/audit/SKILL.md` の残ヒットが :14 相当（`ANCHOR_PATH=` 行、封印前）の **1 行のみ**（Opus M-1。残ヒット全件を用途付きで報告）。
5. `grep -n '"\$CFG"' skills/audit/SKILL.md | grep -v 'CONFIG_SHA'` の残りが exemption **3 行**（`ANCHOR_PATH=`・`import-audit-scope.py --check`・`decide-verdict.py`）のみ。
6. `python3 -m py_compile skills/audit/scripts/*.py`、`bash -n skills/audit/scripts/*.sh` が exit 0。
7. `0.15.1` の残存は履歴節・過去版参照のみ（一覧報告）。engine-shas.json 0.16.0 entry が実 sha と一致（test_scaffold）。
8. worker 報告は各 CT の出力実数と `git diff --stat` を含む。boss が全 diff を読み、CT-2/CT-3 が対象コードを実際に経由することを確認。

## 7. 変更範囲

**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/**`（新規 `sealed_config.py` 含む）、`skills/audit/references/config-schema.md`、`skills/audit/references/engine-shas.json`（0.16.0 entry のみ）、`.claude-plugin/plugin.json`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`README.md`、`tests/**`。

**禁止**: `skills/init/**`、`agents/**`、`skills/audit/references/codex-review-output.schema.json`、`skills/audit/references/workflow-template.js`、`skills/audit/scripts/scaffold.py` のテンプレート文字列（engine 複製の読み込み部は不変。command/skill テンプレートは変更しない）、`.claude/**`、`tasks/**`、`.github/**`、`.gitignore`、git 操作全般。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。** 隣接コードのリファクタ・整形・無関係な文言修正は禁止。

## 8. 検証コマンド一式

```sh
python3 -m unittest discover -s tests
python3 -m unittest tests.test_v016_contracts -v
python3 -m unittest tests.test_sealed_config -v
python3 -m py_compile skills/audit/scripts/*.py
bash -n skills/audit/scripts/*.sh
grep -n '"\$CFG"' skills/audit/SKILL.md | grep -v 'CONFIG_SHA'
grep -n 'json.load(open' skills/audit/scripts/*.sh skills/audit/SKILL.md
grep -rn '0\.15\.1' --exclude-dir=tasks --exclude-dir=node_modules --exclude-dir=.git .
git diff --stat
```

## 9. Registry（単一の真実。件数は本表から導出）

### 9.1 スクリプト消費者（SKILL call site と sha の供給源）

| # | script | SKILL 行（v0.15.1） | sha 供給 | フラグ | 読み | 正常 exit | mismatch exit | observer ID |
|---|---|---|---|---|---|---|---|---|
| 1 | `open-run.py` | :29 | `$PRECHECK_CONFIG_SHA` | 必須 | 直接 | 0 | 2 `config-changed-before-open` | — |
| — | `import-audit-scope.py` | :26（exemption） | （既存の同名フラグは write-path 楽観排他。sealed-config 検証に不使用） | 既存・対象外 | 直接（封印前） | 0 | — | — |
| 2 | `mdq-index.sh` | :76, :444 | `$CONFIG_SHA` | 必須 | 直接（1 回） | 0 | 7 | `mdq-index.sh` |
| 3 | `ax-probe.sh` | :161 | 同上 | 必須 | 直接 | 0 | 7 | `ax-probe.sh` |
| 4 | `codex-probe.sh` | :176 | 同上 | 必須 | 直接 | 0 | 7 | `codex-probe.sh` |
| 5 | `codegraph-probe.sh` | :204 | 同上 | 必須 | 直接 | 0 | 7 | `codegraph-probe.sh` |
| 6 | `graphify-probe.sh` | :225 | 同上 | 必須 | 直接 | 0 | 7 | `graphify-probe.sh` |
| 7 | `cocoindex-probe.sh` | :245 | 同上 | 必須 | 直接 | 0 | 7 | `cocoindex-probe.sh` |
| 8 | `set-config-key.py` | :274 | 同上 | 任意 | 直接（書き込み前） | 0 | 7 | `set-config-key.py` |
| 9 | `generic-layers.py` | :297, :310, :538 | 同上 | 任意 | 直接 | 0 | 7 | `generic-layers.py` |
| 10 | `scripts/check-docs.py`（installed 複製、stamp == 現 plugin 版のみ） | :302 | 同上 | （複製側は #9 と同じ） | 直接 | 0 | 7 | `check-docs.py` |
| 11 | `fix-scope.py` | :333 | 同上 | 条件付き | 直接 | 0 | 7 | `fix-scope.py` |
| 12 | `compute-baseline.sh` | :355 | 同上 | 必須 | 直接（1 回） | 0 | 7 | `compute-baseline.sh` |
| 13 | `resolve-impact.py` | :373 | 同上 | 必須 | 直接 | 0 | 7 | `resolve-impact.py` |
| 14 | `impact-supplement.py` | :379 | 同上 | 条件付き | 直接 | 0 | 7 | `impact-supplement.py` |
| 15 | `classify-run.py` | :392 | 同上 | 必須 | 直接＋子 | 0 | 7 | `classify-run.py` |
| 16 | `plan-dispatch.py` | :398 | 同上 | 必須 | 直接＋子 | 0 | 7 | `plan-dispatch.py` |
| 17 | `start-run.py` | :404 | 同上 | 必須 | 直接 | 0 | 7 | `start-run.py` |
| 18 | `seal-run.py` | :416 | EVIDENCE.config | （`--evidence`） | 子のみ（親は config を開かない。seal-run.py:49-53） | 0 | 7 | `seal-run.py` |
| 19 | `codex-review-plan.py` | :579 | `$CONFIG_SHA`（＋`$HISTORY_SHA`） | 必須 | 直接 | 0 | 7 | `codex-review-plan.py` |
| 20 | `decide-verdict.py` | :696 | EVIDENCE.config（`--expect-json`） | （なし。exemption） | 直接＋子 | 0 | 3 REFUSED `config-changed` | —（gate 自身が inline 記録） |
| 21 | `change-set-sha.py` | （子のみ） | 親から pass-through | 必須 | 直接 | 0 | 7 | —（親 ID＋`detail`） |
| — | `sealed_config.py` | §9.2 の getter 行 | `$CONFIG_SHA` | 必須 | 直接 | 0 | 7 | `sealed_config.py` |

exemption（`"$CFG"` を含むが sha 無し、内容で識別）: :14 `ANCHOR_PATH=`、:26 `import-audit-scope.py --check`（:25 `AUDIT_SCOPE_PATH=` は S4 の一体化で廃止。Opus M-3）（`configSha` を open-run へ渡す）、:696 `decide-verdict.py`（EVIDENCE 経由）。

### 9.2 SKILL 本文の値参照（getter registry）

| key | 束縛変数 | default | mode | 使用箇所（v0.15.1 行） |
|---|---|---|---|---|
| `phase3Backend` | `PHASE3_BACKEND_CONFIG` | `"workflow"` | `--raw` | :81 |
| `contextMode` | `CM_CONFIG_JSON` | `{}` | JSON | :131-140（既存の判定ロジックは stdin/変数から） |
| `harness` | `HARNESS_CONFIG_JSON` | `{}` | JSON | :268 付近 |
| `docAuditCommands` | `DOC_AUDIT_COMMANDS_JSON` | `null` | JSON | :305（harness-command-kind へ pipe） |
| `maxImpactedDocs` | `MAX_IMPACTED_DOCS` | `200` | JSON | :380 |
| `docGlobs` | `DOC_GLOBS_JSON` | `[]` | JSON（comma-join は python で） | :380 |
| `semanticSearch.minScore` | `SEMANTIC_MIN_SCORE` | `0.4` | JSON | :380 |
| `boundaryCommand` | `BOUNDARY_COMMAND` | `null` | `--raw` | :548 |
| `reviewCommands` | `REVIEW_COMMANDS_JSON` | `{}` | JSON | :549 |
| `codexReview.model` | `CODEX_MODEL_CONFIG` | `null` | `--raw` | :585 |
| `codexReview.timeoutMs` | `CODEX_TIMEOUT_MS` | `300000` | JSON | :605 |
| `reportPath` | `REPORT_PATH_CONFIG` | `null` | `--raw` | :663 |
| `docAuditCommands`（Phase 4 再導出） | `DOC_AUDIT_COMMANDS_P4_JSON` | `null` | JSON | :530 |

各 key につき getter 行は **1 行**（docAuditCommands は 0.5 と Phase 4 で別変数 2 行 = 上表 13 行。Opus m-2。CT-1(c) の「ちょうど 1 行」は変数名ごと: Phase 4 用は `DOC_AUDIT_COMMANDS_P4_JSON`）。→ getter 行 **G=13**。

### 9.3 対象外（根拠付き）

| 対象 | 根拠 |
|---|---|
| Phase-4 `docAuditCommands` の各コマンド（`/check-docs`・`doc-lint`・model-driven）と、その定義ファイル（`.claude/commands/check-docs.md`、`.claude/skills/doc-lint/SKILL.md`、`scripts/check-docs.py`） | 定義ファイル自体が repo 書き込み者に改変可能で、config 改竄より安価な同効果の経路が常にある。所見は repo 書き込みレベルの信頼。stamp 検査は版のみで本文完全性ではない（§1、方針 B） |
| `CODEGRAPH_DIR`（codegraph-probe.sh:31,103） | boss プロセスの環境変数。ファイル改竄の対象外 |
| `.claude/audit-scope.json` の内容 | 内容は消費されず sha 比較のみ。impactMap 等価性の pre-check→open 窓は S4（`--expect-config-sha`）で、scope path の pre-check 内の窓は `--check` の一体化（同一バイト列から `scopePath` を導出）で閉じる |
| `workflow-template.js` / `agents/*.md` / references | config を直接読まない（Sol R1/R2 で確認） |

### 9.4 observer ID（`decide-verdict.py` の `OBSERVERS` 固定列挙）

SKILL が直接起動し、run 中（lock 取得後）に exit 7 を返し得る top-level スクリプトのみ（R3-5）: `mdq-index.sh`、`ax-probe.sh`、`codex-probe.sh`、`codegraph-probe.sh`、`graphify-probe.sh`、`cocoindex-probe.sh`、`set-config-key.py`、`generic-layers.py`、`check-docs.py`、`fix-scope.py`、`compute-baseline.sh`、`resolve-impact.py`、`impact-supplement.py`、`classify-run.py`、`plan-dispatch.py`、`start-run.py`、`seal-run.py`、`codex-review-plan.py`、`sealed_config.py`。**O=19**。`open-run.py`（lock 取得前）、`change-set-sha.py`（子。親の ID＋`detail` で記録）、`decide-verdict.py`（gate 自身が inline で記録）は observer ではない。§9.1 の observer ID 列はこの定義で読み替える。

### 9.6 history reader 真理値表（R3-9）

| reader | absent（`"none"`） | valid（`phase4Runs` 欠落・旧 top-level array・未知キーを含む） | corrupt（**`entries` 不正のみ**。`phase4Runs` 不正は valid 扱いで `phase4Runs=[]`＋warning に退化。Opus M-4） | sha 不一致 |
|---|---|---|---|---|
| `resolve-impact.py`（regression） | regression 無し | 使用 | regression 無し＋warning、継続 | （sha は受け取らない。plan-dispatch 前のため EVIDENCE 未封印） |
| `plan-dispatch.py` | `historyStatus:"absent"` | `"ok"`、cache 可 | `"corrupt"`、cache 無効、継続 | `impact.historySha`（resolve-impact.py:338 が出力）と再読 sha の不一致（plan-dispatch.py:103、現行 exit 3）を **exit 7 `sealed-history-mismatch`** に改め、停止規約で `--taint-observed history --observed-by plan-dispatch.py`（R4-3） |
| `codex-review-plan.py` | `carryForward:null` | 使用 | `carryForward:null`＋warning、継続 | exit 7 `sealed-history-mismatch` → 停止規約 |
| `decide-verdict.py`（gate） | 既存 sentinel 検査 | 使用・追記 | 隔離（既存）、cold start | REFUSED＋隔離（既存） |

corrupt／退化の判定は 4 reader とも `parse_history_document` 1 本で行い、「片方で corrupt・片方で valid」を作らない。`phase4Runs` の退化は決定的 PASS cache（`entries`）を道連れにしない。

### 9.7 Phase-4 record eligibility（R3-10）

gate が受け取る Phase-4 evidence の (mode, promptVariant, state) の**完全列挙**（R4-4。`promptVariant` は planner が返し、`state` は Phase 4 実行後に SKILL が束縛する。Opus m-4）。state は `docaudit_cache.CODEX_REVIEW_STATES` = `completed/execution-failed/ref-invalid/skipped-full-run/not-active` の 5 値のみ。

| manifest.mode | `codexReview.promptVariant` | `codexReview.state` | gate の扱い |
|---|---|---|---|
| full | `full` | `completed` | record 追加・flip 計測 |
| full | `full` | `execution-failed` | record なし |
| full | `null` | `skipped-full-run` | record なし |
| full | `null` | `not-active` | record なし |
| incremental | `diff` | `completed` | record なし |
| incremental | `diff` | `execution-failed` | record なし |
| incremental | `null` | `ref-invalid` | record なし |
| incremental | `null` | `not-active` | record なし |
| （`phase4` が `"none"` sentinel） | — | — | 既存どおり（Phase 4 不要） |
| **上記以外**（`promptVariant` キー欠落・`carryForwardSha` キー欠落／非文字列・列挙外の値・mode と variant の不整合・`null`×`completed` 等。CT-5b で各 class を検査） | | | **REFUSED**（evidence 不正。旧版 SKILL が書いた promptVariant 無し evidence も REFUSED＝混在版は黙って通らない） |

record の findings は `source=="codex-review"` のみ。他 source の finding に `file` が無くても record・flip に影響しない。

### 9.5 期待値（CT-1 が出力・assert）

- call sites N = SKILL.md 内で `--expect-config-sha "$CONFIG_SHA"`／`"$PRECHECK_CONFIG_SHA"` を持つ script 呼び出し行数 = #1(1)+#2(2)+#3〜#7(5)+#8(1)+#9(**4**: :297, :310, :538 ＋ S6 の旧 stamp fallback 新設行)+#10(1)+#11(1)+#12(1)+#13(1)+#14(1)+#15(1)+#16(1)+#17(1)+#19(1) = **22**（Sol R3-5 で再計数。現行 SKILL の `"$CFG"` 行 26 = 束縛 :13 を除く call site 20＋一行読み 2（:140,:305）＋exempt 4（v7 で :25 廃止後は 3）。これに open-run 行と fallback 新設行を加えて 22。call site 数は :25 廃止の影響を受けない）
- exempt M = **3**（:25 廃止後）
- getters G = **13**
- scripts K（CT-2 の対象）= §9.1 #1〜#21 = **21**（#10 は plugin の `generic-layers.py` を複製した fixture で起動）
- observers O = **19**（§9.4）

worker の実測が上記と異なれば、実装を曲げず報告する（boss が registry を改訂）。

## 10. 影響・非対象の明示

- 非対象: #66 方式 B（別 route）。`59-design-note.md` の ledger（撤回）。Phase-3 verifier の `CODEGRAPH_DIR` 封印。dir-framework 側の `harness.engineVersion`（0.15.0）更新・harness refresh（出荷後 follow-up。0.16.0 では installed 旧 stamp が fallback＋WARN になる）。Sol 案 A（sha を受け取れないコマンドの所見を report-only 化）は将来の厳格化オプションとして REVIEW に記録。
- 互換: 混在版は exit 2 で止まる。v0.16.0 以降の更新は全 tree 同期＋in-flight run 無しが必須（ADOPTION 3c 改訂）。旧 gate（≤0.15）は書き戻し時に `phase4Runs` を落とす（downgrade の既知挙動）。
