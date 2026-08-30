# REVIEW — docaudit v0.16.0（#63 verify-on-read ＋ #59 Phase-4 flip / carry-forward）

boss = Fable/Opus。PLAN: `PLAN.md`（同ディレクトリ）。

## セッション記録

| 用途 | モデル / effort | session id | 備考 |
|---|---|---|---|
| 事前調査（読み取り専用） | Luna medium `-s read-only` | `01a052b0-903e-73a1-83ca-f97d42022069` | 出力 `01-survey.md`。read-only サンドボックスでは `tempfile` 不可のためテストは boss が実測（655 OK） |
| 計画批判 | Sol xhigh `-s read-only` | `01a052c3-214e-7590-9730-4c6fae8784de` | R1 出力 `02-critique-r1.md`。R2 以降は `codex exec resume <id>`（フラグ無し） |
| 実装 | Sol high `-s workspace-write` | `01a0532a-eeb6-7bf1-b8cb-99ebb0a405fc` | R1 出力 `08-impl-r1.md`。差し戻しは `codex exec resume <id> -c model_reasoning_effort=medium` |

## ユーザー決定（2026-08-30）

- 対象は #63＋#59 → v0.16.0。#66 方式 B は別 route（#66 の文書是正は v0.15.1 で出荷済み）。
- #63 は verify-on-read（精査文書の凍結コピー案は「対策の付け替え」として不採用）。
- #59 は `59-design-note.md` の P1 ledger／新信頼クラスを撤回し、flip 計測（決定的キー）＋history 由来 data-only carry-forward。

## 計画批判ラウンド

### Sol R1（xhigh）— 出力 `02-critique-r1.md`

判定: **差し戻し（PLAN v1 → v2 全面改訂）**。Critical 3 / Major 10。全件採用。前提誤りの指摘も採用（dir-framework は 0.15.0 運用中）。

| # | 深刻度 | 要旨 | PLAN v2 での対応 |
|---|---|---|---|
| R1-1 | Critical | SKILL 本文が `phase3Backend`・`docAuditCommands`・`reviewCommands` 等を未検証で直接参照（7 箇所） | S1 `--get` 新設、§9.2 で全箇所を置換、Guardrails で Read/一行読み禁止、CT-1(d) |
| R1-2 | Critical | harness 複製の verify-before-read は窓が残る／Phase 4 docAuditCommands も live 読み／generic-layers.py は harness 本体で engine-shas が変わる | verify-before-read 撤回。harness 複製は「差し替え可能な実行ファイル＝設定と同じ信頼クラス」として脅威境界外に明示。engine-shas 0.16.0 は実 sha |
| R1-3 | Critical | pre-check（impactMap 等価性）と open の間で config を戻せる | open-run `--expect-config-sha`（importer の `configSha`）で封印前差し替えを exit 2 |
| R1-4 | Major | gate 内の子 change-set-sha の exit 7 が config_taint にならない | gate が子 exit 7 を明示判定 |
| R1-5 | Major | 復元後は open-run の exit 6 が発火しない | `configAcceptanceRequired:true` marker、marker がある限り exit 6 |
| R1-6 | Major | history mismatch を config funnel に流すのは誤り | `--taint-observed {config,history}` に一般化、history は既存隔離規約 |
| R1-7 | Major | cross-turn resume で CONFIG_SHA が未束縛 | CONFIG_SHA は EVIDENCE.config からの導出値（checkpoint しない） |
| R1-8 | Major | phase4Runs の構造検査なし、file 未正規化 | 共通正規化＋厳格 parser、不正は corrupt 隔離 |
| R1-9 | Major | 比較キーに contract/config が無い | worktreeDigest × contractVersion × configSha |
| R1-10 | Major | 保持 20 件が incremental で full record を追い出す | full＋completed のみ保存 |
| R1-11 | Major | init の set-config-key・fix-scope の非 config モードが必須化で壊れる | 任意フラグ 2 本を固定列挙、fix-scope は条件付き必須 |
| R1-12 | Major | 部分コピー手順で混在・旧 gate が phase4Runs を落とす | ADOPTION 3c 改訂、downgrade 挙動を文書化 |
| R1-13 | Major | CT-1〜6 が誤実装を通す | registry 固定集合・固定値 assert・対テスト・end-to-end に拡張 |

Sol が妥当と確認した点: `CODEGRAPH_DIR` の対象外扱い、S4 の必要性、workflow-template.js/agents に直接 config 読み無し、Phase 2 封印後〜Phase 4 に history を正当に書く経路無し、exit 7 は既存値と衝突しない。

### Sol R2（resume、effort 据え置き）— 出力 `03-critique-r2.md`

判定: **差し戻し（PLAN v2 → v3）**。Critical 1 / Major 12 / Minor 1。R2-1 を除き全件採用。

| # | 深刻度 | 要旨 | PLAN v3 での対応 |
|---|---|---|---|
| R2-1 | Critical | harness 複製を対象外にすると config 一時変更だけで所見を抑制できる | **方針 B**（ユーザーが boss に委任、advisor 助言）: Phase-4 コマンドは定義ファイル自体が repo 書き込み者に改変可能＝config 改竄より安価な同効果経路が常在。所見は repo 書き込みレベルの信頼として ADOPTION に明記。Phase 0.5 の engine 複製直接起動には sha を付け、stamp < 0.16.0 は plugin engine で代替＋WARN。Sol 案 A（report-only 降格）は製品契約変更のため不採用・将来オプションとして記録 |
| R2-2 | Major | seal-run の子再読と release 分岐が funnel を迂回 | pass-through＋exit 7 保持、token 判定を release 分岐より前に |
| R2-3 | Major | decline 再 open で precheck sha が古い／acceptance 消費時点未定義 | precheck 再実行、`--accept-config` は lock 取得時に一度だけ消費 |
| R2-4 | Major | 隔離失敗でも release される | 隔離失敗は release せず exit 3、lock 残存 → `--break-lock` |
| R2-5 | Major | 非所有時の `--taint-observed` 未定義 | 4 ケースで無書き込み、observer ID 固定列挙 |
| R2-6 | Major | impact-supplement の config 無し契約が壊れる | 条件付き必須 |
| R2-7 | Major | `--get` の型・既定値未定義 | `--raw` 追加、getter registry 表 |
| R2-8 | Major | plan-dispatch が phase4Runs を検査しない | `parse_history_document` を 3 者で共用 |
| R2-9 | Major | carry-forward の自由文注入 | `{file, severity}` のみ、実在 file のみ |
| R2-10 | Major | `<unresolved>` を flip キーに含めると誤判定 | 除外＋`unresolvedFileCount` |
| R2-11 | Major | writer が生成した record を reader が corrupt にし得る | title 廃止、round-trip 検証、blockingFiles 導出 |
| R2-12 | Major | 件数が整合しない | registry 表から導出（N=22/M=4/G=13/K=21/O=22） |
| R2-13 | Major | CT-1(d) が正しい SKILL を拒否し間接読みを見逃す | getter registry の等値検査に置換 |
| R2-14 | Minor | 正規化の順序・Windows path | exact 先・locator 後・drive/UNC 拒否 |

### Sol R3（resume）— 出力 `04-critique-r3.md`

判定: **差し戻し（PLAN v3 → v4）**。Critical 1 / Major 10。R3-1 は部分採用、他は採用。

| # | 深刻度 | 要旨 | PLAN v4 での対応 |
|---|---|---|---|
| R3-1 | Critical | acceptance marker は repo 内で改変可能 | **部分採用**: run をまたぐ状態（last_run/history/anchor）は既存設計から repo 書き込みクラスで、EVIDENCE は run 終了で消えるため改変不能な置き場は存在しない。marker を「運用安全機構（セキュリティ境界ではない）」と §1 に明示。fail-closed は採用（last_run 不正 JSON → exit 6 `last-run-unreadable`） |
| R3-2 | Major | marker 消費と lock の原子性未定義 | 4 段トランザクション、失敗時 exit 2 |
| R3-3 | Major | 隔離失敗後の裸 `--break-lock` で tainted history が正規化 | `historyQuarantineFailed` marker、open-run が隔離再試行 |
| R3-4 | Major | harness fallback が旧 stamp しか覆わない | stamp 完全一致のみ直接起動、他は plugin engine（`broken` は既存契約据え置き） |
| R3-5 | Major | N=21 誤り、O の意味が二重 | N=22、O=19（top-level のみ） |
| R3-6 | Major | CT が再読・pass-through 欠落を判別できない | CT-2b: sitecustomize で open 回数と子 argv を計測 |
| R3-7 | Major | 8 KiB 上限が最大入力と両立しない | ≤500 件・≤512 bytes、record 512 KiB、往復境界テスト |
| R3-8 | Major | 50 件 cap が flip 集合を欠く | 完全保持、`truncated` で比較無効化、canonical 順 |
| R3-9 | Major | corrupt 判定が reader 間で不統一 | §9.6 真理値表（resolve-impact 追加） |
| R3-10 | Major | source 選別・mode×variant 整合が未定義 | §9.7 eligibility 表、不整合は REFUSED |
| R3-11 | Major | carry-forward の runid/ts・symlink・文字種 | 除去・共通 validator・文字種制限・ensure_ascii |

### Sol R4（resume）— 出力 `05-critique-r4.md`

判定: **差し戻し（PLAN v4 → v5）**。Major 5。全件採用。件数 N=22/M=4/G=13/K=21/O=19 は Sol の再計数と一致。R3-1 の信頼境界の位置づけは Sol が受理。

| # | 深刻度 | 要旨 | PLAN v5 での対応 |
|---|---|---|---|
| R4-1 | Major | marker 書込み失敗＋`--release`/`--break-lock` で隔離待ちが解除される | lock holder JSON にも marker、open-run は全経路で隔離待ちを先に検査 |
| R4-2 | Major | parser の symlink 検査は filesystem 依存で正当な history を corrupt にする | parser は字句検査のみ、存在検査は carry-forward 時 |
| R4-3 | Major | resolve-impact→plan-dispatch の history sha 防壁が funnel から脱落 | exit 7 `sealed-history-mismatch` → taint funnel |
| R4-4 | Major | eligibility 表が不可能な組み合わせを受理 | planner 生成可能な 8 行を完全列挙、他は REFUSED |
| R4-5 | Major | 512 KiB が escape 最悪形で破られる | canonical 直列化で判定、`"`/`\` 禁止、直列化後 512 bytes |

### Sol R5（resume、最終）— 出力 `06-critique-r5.md`

判定: **上限到達（5 往復）。未収束だが残指摘は全て PLAN v6 に吸収**。Major 5。件数は Sol 再計数と一致（N=22/M=4/G=13/K=21/O=19）。

| # | 深刻度 | 要旨 | PLAN v6 での対応 | 区分 |
|---|---|---|---|---|
| R5-1 | Major | holder marker が disk 障害で永続化できず、break 後に tainted history が正規化され得る | 同一 inode rewrite（ftruncate→write→fsync）、二重障害は `quarantine-marker-unpersisted` exit 3。残余は §1 の運用安全クラスの既知限界として ADOPTION に明記（Sol の fail-safe holder 案は、gate 未到達 run（dir-framework で 6/15）の再開時に history を毎回失うため不採用） | 計画（吸収済み） |
| R5-2 | Major | 回復処理の flock・inode・runid 検査順と旧 lock の処分が未定義 | open-run 共通手順を 8 段で固定 | 計画（吸収済み） |
| R5-3 | Major | 非 object・marker 非 bool が不正 JSON と同じ回復にならない | `last-run-unreadable` に正規化 | 計画（吸収済み） |
| R5-4 | Major | CT-5 が parser 契約と矛盾（symlink） | CT-5 を反転 | 計画（吸収済み） |
| R5-5 | Major | 新経路のテスト不足 | CT-4c/4d/5b（table-driven）追加 | 計画（吸収済み） |

worker 指示で吸収する細部（Sol 分類）: 同一 inode rewrite の実装、fault injection fixture の構成。

### Opus 敵対レビュー R1（手順 3.5、change-reviewer read-only）

判定: **差し戻し（PLAN v6 → v7）**。Critical 1 / Major 8 / Minor 5 / ユーザー決定 1。テスト基線 655 OK を Opus も再実測。sitecustomize 方式の成立（macOS 15／CPython 3.14、親・子・bash 内 python）と `os.open` 単独フックの空振りを Opus が実測。

| # | 深刻度 | 要旨 | PLAN v7 での対応 |
|---|---|---|---|
| C-1 | Critical | Sol R5-2 の共通手順を字義どおり実装すると通常 open が実行中 run の lock を奪う（Phase 0〜4 は誰も flock を保持しない二層設計） | 通常 open は `O_EXCL` 先行・既存 lock は無条件 exit 4 を維持。回復は lock 不在時の last_run 由来のみ。CT-4c に行追加 |
| M-1 | Major | 完了条件 4 が exemption と矛盾し充足不能 | shell 0 件、SKILL 残ヒットは `ANCHOR_PATH=` 1 行 |
| M-2 | Major | exit 6 述語の置換で v0.15 last_run との upgrade 窓 | marker OR 旧述語 |
| M-3 | Major | `AUDIT_SCOPE_PATH` の独立読み（:25）が pre-check 内の窓 | `--check` が同一バイト列から `scopePath` を出力、:25 廃止（M=3） |
| M-4 | Major | `phase4Runs` 字句不正が決定的 PASS cache を道連れに隔離 | `phase4Runs` 不正は退化（`[]`＋warning）、corrupt は `entries` のみ、未知キー無視 |
| M-5 | Major | carry-forward が flip の比較条件を破る | source = 現 digest と異なる最新 record（再実行間で prompt 同一）、`carryForwardSha` を record と比較キーに追加 |
| M-6 | Major | history が 6 MB 級に膨らむ | 保持 5、全体 1 MiB、source を必ず残す trim 規則 |
| M-7 | Major | CT-2b の「1 回」が seal-run（0 回）・set-config-key（読み＋書き）で不成立 | 読み列で分岐、両フック |
| M-8 | Major | `--release`/`--break-lock` への隔離結合が緊急脱出路を塞ぐ | 回復は通常 open のみ、release/break は holder marker を last_run へ best-effort マージして unlink |
| m-1〜m-5 | Minor | exit 5 欠落／G の 13 行目／(5) の死文／§9.7 前置き／decline 再 open の literal 行 | すべて反映（m-5 は worker 指示） |

**E-1（ユーザー決定事項）**: flip 計測の縮小可否 → ユーザーが advisor に委任 → **advisor 裁定: 維持**（純粋な再実行が #59 の題そのもの。承認済み決定を費用理由で覆す根拠不足。M-5 対応で計測が実際に有効になる）。trim 規則に「carry-forward source を必ず残す」を固定。

### Opus 敵対レビュー R2（resume）— 判定: **差し戻し（v7 → v8、局所修正のみ）**

R1 の全指摘の反映を妥当と判定、件数 N=22/M=3/G=13/K=21/O=19 は Opus 再計数と一致。C-1×M-8×S5 と M-5×保持 5 の組み合わせは矛盾なしと確認。新規 Major 4 / Minor 6:

| # | 要旨 | v8 での対応 |
|---|---|---|
| V7-1 | parser 上限 ≤5 が trim（最大 6）と矛盾し record が毎回落ちる | 上限 6 |
| V7-2 | `import-audit-scope.py` の既存同名フラグで CT-1(a) が必ず落ちる | registry に「既存・対象外」行、集合等値から除外 |
| V7-3 | CT-5 の symlink 項が valid と corrupt を同時要求 | 括弧書き削除 |
| V7-4 | `carryForwardSha` が evidence schema と §9.7 に未定義 | S8 に追加、欠落は REFUSED |
| V7-5〜10 | exemption 識別子の残骸／CT-4 の `--break-lock` 文言／lock 無し rename 競合／旧述語の適用範囲／observer 列の矛盾／§9.2 断片表 | すべて反映（(c)(d) 順序入替、旧述語は marker キー無し last_run のみ、observer 3 セルを `—`、13 行目を表に統合） |

### Opus 敵対レビュー R3（resume）— 判定: **実装承認（ブロッキング指摘なし）**

V7-1〜V7-10 の反映を全件妥当と判定、件数 N=22/M=3/G=13/K=21/O=19 を再導出して不変を確認。非ブロッキング 2 点（CT-2/2b から `import-audit-scope.py` を除外／exit 6 は lock 作成前）は worker 指示（`prompts/08-impl-sol.md`）に転記。

## 手順 4: 実装（Sol high、workspace-write）

PLAN v8 で確定。branch `fix/v0.16.0-issues-63-59`（boss 作成）。worker プロンプト `prompts/08-impl-sol.md`。

### 実装ラウンド 1（`08-impl-r1.md`）— worker は実装前に停止し PLAN 内矛盾 3 点を報告（ファイル変更なし、基線 655 OK を実測）

boss 裁定（PLAN v8 に反映）: Q1 `docs\a.md` は unresolved（`\` は変換せず拒否）／Q2 flip 一致条件は 4 項目（S10 が正）／Q3 `parse_history_document` は常に 3 値。編集承認を与えて同一セッションを resume（`prompts/09-impl-sol-r1b.md`、effort high 据え置き）。

### 実装ラウンド 1b（resume、`09-impl-r1b.md`）— 途中停止: 複製版 `generic-layers.py` が `sealed_config` を import できない（複製先は単独ファイル）

boss 裁定: 方式 1（最小封印読取をファイル内に内包、import なし。scaffold・SKILL のコマンド形は不変）。PLAN S2 に追記。resume（`prompts/10-impl-sol-r1c.md`、high 据え置き）。

### 実装ラウンド 1c（resume）— boss 側 Bash 10 分制限で codex プロセスが kill（出力ファイル無し、作業ツリーに 47 files の途中変更が残存）

教訓: 長時間の実装委譲は `run_in_background` でも 10 分で kill される → **`nohup ... &` で切り離して起動し、出力ファイルの生成を `until` ループで待つ**。

### 実装ラウンド 1d（resume、nohup、`prompts/11-impl-sol-r1d.md`）— 完了報告 `11-impl-r1d.md`

worker 報告: 697 tests OK、CT-1 = 22/3/13/21/19、CT-2 = 21、py_compile/bash -n OK、engine sha 一致、PLAN 外判断なし、許可外変更なし。52 files changed ＋新規 4（`sealed_config.py`、`test_sealed_config.py`、`test_v016_contracts.py`、`test_v016_history_common.py`）。

**boss 追認（2026-08-31、`git add -A` でスナップショット後に再実行）**: `python3 -m unittest discover -s tests` → `Ran 697 tests in 278.856s / OK`（`boss-full-tests.log`）。`tests.test_v016_contracts -v` → 14 tests OK、`call sites 22／exempt 3／getters 13／scripts 21／observers 19`、`対象 21 本を検査`（`boss-ct.log`）。py_compile/bash -n OK。`"$CFG"` 無 sha 残 = :14/:25/:717 の 3 行、`json.load(open` 残 = SKILL :14 のみ、`0.15.1` 残存は履歴節のみ。→ 完了条件 1〜7 は実測で充足。

**boss diff 精読（sealed_config.py／open-run.py／decide-verdict.py／docaudit_cache.py／docaudit_paths.py／codex-review-plan.py／SKILL.md／Python 11 本／shell 3 本／engine-shas／plugin.json）の所見**:
- [B-1 Major] `codex-review-plan.py:139` carry-forward の repo root に `os.getcwd()` を使用。他スクリプトは `--repo-root` を受け取る契約で、cwd 依存は誤り（実在検査・symlink 拒否が誤った root で走る）。→ `--repo-root` 必須化＋SKILL :595 の call site に付与。
- [B-2 Minor] SKILL :389 の impact-supplement 行が `<config maxImpactedDocs, default 200>` 等のプレースホルダのままで、直前で束縛した `MAX_IMPACTED_DOCS`/`DOC_GLOBS_JSON`/`SEMANTIC_MIN_SCORE` を使っていない（モデルが config を再読する余地）。
- [B-3 Minor] SKILL seal-run 分岐（:432-434）「Any other non-zero exit → release」に exit 7 の停止規約が明示されていない（Guardrails の一般規約に依存）。分岐内に「exit 7／token → 停止規約」を明記。
- [B-4 Minor] `HARNESS_CONFIG_JSON` の getter が `--default '{}'` で「`harness` キー欠落」と「空 object」を区別できない（SKILL は欠落時 `HARNESS_STATE=unset` を要求）。`--default null` に。
- 妥当と確認: 通常 open の `O_EXCL` 先行＋既存 lock 無条件 exit 4、隔離は lock 保持下、旧述語はキー欠落時のみ、`--taint-observed` の非所有 4 ケース無書き込み、子 exit 7 → config_taint、history 書き戻しで `phase4Runs` 保存、trim（5＋source）、parser 上限 6、退化、flip 4 キー、carry-forward 実在 file のみ・文字種制限、shell 7 本の 1 回読み、engine-shas 0.16.0 の実 sha。

**change-reviewer（Opus、read-only）によるテスト/docs 検分**: 判定「差し戻し」。Major-1 ADOPTION 3c の部分コピー手順が未改訂（新段落と自己矛盾）／Major-2 probe の standalone 契約（不正・欠落 config → exit 2）が PLAN 外で変更され docs が旧記述／Major-3 CT-5 の列挙項目 7 点が未テスト（保持 5/上限 6・truncated・round-trip 失敗・境界・unresolvedFileCount・gate の退化・contractVersion/configSha 相違）／Major-4 CT-4c の欠落行（二重障害・非 object・非 bool・`--release` マージ・flock 保持）／Major-5 CT-3b の 4 ケース目／Major-6 CT-3 の gate 子差し替えと SKILL 順序契約。Minor 7 点。CT-1/CT-2/CT-2b/CT-4/CT-4d は判別可能性ありと確認。

**レビューラウンド 1 判定: 差し戻し**（`prompts/12-impl-sol-r2.md`、resume・effort medium）。boss 裁定: Major-2 の fail-closed（exit 2）は承認し、文書側を実装に合わせる（PLAN S3 の補足として記録）。

### 実装ラウンド 2（resume、nohup、`prompts/12-impl-sol-r2.md`）— 完了報告 `12-impl-r2.md`

worker: A-1〜A-4・B-1・B-2・C-1〜C-7 を全対応（新規 `tests/test_v016_phase4_contracts.py`（7 件）、`tests/test_v016_docs_contracts.py`、`test_wp12_contracts.py` に回復状態 15 件追加）。副次修正: history parser の warning が `validate_min_passes` の warning で上書きされる欠陥（decide-verdict.py:1121）。713 tests OK。

**boss 追認（2026-08-31）**: `git add -A` 後に再実行 → `Ran 713 tests in 316.694s / OK`（`boss-full-tests-r2.log`）、`test_v016_contracts -v` → 16 tests OK、`call sites 22／exempt 3／getters 13／scripts 21／observers 19`、`対象 21 本を検査`（`boss-ct-r2.log`）。py_compile/bash -n OK。grep 確認: A-1（`--repo-root` 必須＋SKILL 付与）、A-2（`"$MAX_IMPACTED_DOCS"`/`"$DOC_GLOBS"` 使用）、A-3（seal-run 分岐に exit 7 除外と `--observed-by seal-run.py`）、A-4（`--default null`）、B-1（SKILL :95-97、ADOPTION en/ja の v0.16.0 段落に「直接起動 probe の不正/欠落 config は exit 2、不一致は exit 7」）、B-2（3c は `cp -R` 全 tree のみ）。新テストの assert を精読: 7 run 保持（≤6・source 残存・carry sha 不変）、501 件 truncated、退化で隔離なし、round-trip 失敗で record なし、500×512 境界と 513 KiB/1 MiB 超の退化、unresolvedFileCount=2、flip の contract/config 相違 → 0。→ 完了条件 1〜8 充足。

**レビューラウンド 2 判定: 差し戻し（codex exec review の指摘による）**

### 最終 `codex exec review --uncommitted -m gpt-5.6-sol -c model_reasoning_effort=high`（session `01a0538b-14b9-7ed2-a5a3-6a6ce105435a`、`13-codex-review-log.txt`）

P2 × 2（boss 採用）: (1) shell 消費者が config JSON 全体を `python3 -c` の単一引数で渡し、大きな有効 config で `Argument list too long` → 未検査のまま `not-installed` に黙って退化（7 本）。(2) gate の `config_signature` を `load_sealed_config` 読取後の別 stat で取得するため、隙間の改変を最終確認が見逃す。→ R3（`prompts/14-impl-sol-r3.md`、resume・medium）: stdin 渡し＋失敗時 exit 2、同一 fd の fstat から signature を返す。

### 実装ラウンド 3（resume、nohup、`prompts/14-impl-sol-r3.md`）— 完了報告 `14-impl-r3.md`

worker: R3-1（7 本の shell を stdin 渡し＋parse 失敗は exit 2、codegraph は NUL 区切りのため一時ファイル経由、300 KiB 超 config の 7 本正常動作テスト）、R3-2（`load_sealed_config(..., with_signature=True)` が同一 fd の fstat から `(st_ino, st_size, st_mtime_ns)` を返し、fd と `lstat(path)` の inode 不一致は `SealedConfigMismatch`；gate の別 stat を廃止；読取直後の別 inode 差し替えで REFUSED/taint を検査）。716 tests OK。

**boss 追認（2026-08-31）**: diff 精読（sealed_config.py／decide-verdict.py／7 shell）で指摘どおりを確認、`state_signature` の tuple 形式と一致。`python3 -m unittest discover -s tests` → `Ran 716 tests in 306.562s / OK`（`boss-full-tests-r3.log`）、`test_v016_contracts -v` → 17 OK、`call sites 22／exempt 3／getters 13／scripts 21／observers 19`、`対象 21 本を検査`（`boss-ct-r3.log`）。py_compile/bash -n OK、shell の `json.load(open` 0 件、`sealed_config.py` 呼び出しは各 1 回。

**レビューラウンド 3 判定: 承認**（PLAN §6 完了条件 1〜8 を boss 実測で充足）。

## 手順 7: route-close（2026-08-31）

| 項目 | 記録 |
|---|---|
| 対象タスク | docaudit v0.16.0 — #63 sealed-config verify-on-read ＋ #59 Phase-4 flip 計測／carry-forward（PLAN v8） |
| 記録時点の HEAD | `7c97ded5b1be9f9ce3a847f8cf1e02e791915289`（branch `fix/v0.16.0-issues-63-59`、PR #68） |
| 確定した変更ファイル | 59 files（+3848/−452）。新規 6: `skills/audit/scripts/sealed_config.py`、`tests/test_sealed_config.py`、`tests/test_v016_contracts.py`、`tests/test_v016_docs_contracts.py`、`tests/test_v016_history_common.py`、`tests/test_v016_phase4_contracts.py`。変更: SKILL.md、scripts 20 本（Python 13・shell 7）、`references/config-schema.md`・`engine-shas.json`、`.claude-plugin/plugin.json`、`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`、`README.md`、既存テスト 24 本＋`wp12_helpers.py`。tasks/route/** は別 commit |
| audit verdict | **N/A**: この repo には `.claude/doc-audit.json` が無く `/docaudit:audit` は動作しない。代替: 公開挙動・設定・手順に対応する既存ドキュメント（ADOPTION en/ja・README・config-schema・SKILL）の整合を CT-7／`test_v016_docs_contracts.py`（ファイルごとの token 表）と change-reviewer の per-file grep で確認 |
| SSoT 更新 | **0 ファイル**（`AGENTS.md`／`PROJECT.md`／`CLAUDE.md` は本 repo に存在しない。durable な規約は SKILL.md Guardrails と ADOPTION に記載済み） |
| 検査系成果物の実数 | CT-1: `call sites 22／exempt 3／getters 13／scripts 21／observers 19`（PLAN §9.5 と一致）／CT-2: `対象 21 本を検査`／フルスイート `Ran 716 tests / OK`（基線 655） |
| 残る手順（ユーザー依頼） | PR #68 のマージ（self-merge は不可）→ boss が handoff: tag `docaudit--v0.16.0`、GitHub Release、`~/.claude/skills/docaudit/` 全 tree 同期、#63／#59 close。follow-up: dir-framework の `harness.engineVersion`（現 0.15.0）更新と harness refresh、#66 方式 B の別 route |
| 教訓 | 長時間 codex は `nohup … &` で切り離す（Bash 10 分で kill）／worker は PLAN 内矛盾で正しく停止する（3 回）／`codex exec review --uncommitted` が boss 精読の見逃し 2 件（ARG_MAX・signature 窓）を拾った／**不備**: codex worker 向けプロンプト（08〜14）に、グローバル CLAUDE.md が全委譲に要求する凝縮版行動規範（プロンプト注入・設定書き込み拒否の規律を含む）を貼付していなかった（Opus/change-reviewer 向けには貼付済み）。実害は無かったが、本 route のプロンプトを次回のテンプレートにする際は必ず末尾に付けること |

## Route-close addendum — handoff 完了（2026-08-31）

- PR #68 をユーザーがマージ → main = merge commit `d77ad97c76fbbb0fd359d2544368fa164e784a10`。boss が main で再実測: `Ran 716 tests / OK`、CT-1 `call sites 22／exempt 3／getters 13／scripts 21／observers 19`、CT-2 `対象 21 本を検査`（`boss-main-tests.log`／`boss-main-ct.log`）。
- `echo y | release-handoff.sh d77ad97… 68`（v0.15.1 版から派生、`release-handoff.sh`、ログ `handoff-run.log`）exit 0: detached でフルスイート `Ran 716 / OK` → tag `docaudit--v0.16.0` = `d77ad97`（local/remote 一致を boss が実測）→ GitHub Release https://github.com/akira993/doc-audit-harness/releases/tag/docaudit--v0.16.0（title「docaudit v0.16.0 — sealed-config verify-on-read + Phase-4 flip counter」、非 draft）→ #63・#59 を completed で close → `~/.claude/skills/docaudit/` を tag の archive から rsync 同期（plugin.json 0.16.0、`sealed_config.py` 存在を boss が確認）。
- open Issue: #66（方式 B、別 route）。follow-up: dir-framework の `harness.engineVersion` 0.15.0 → 0.16.0 と `/docaudit:init --harness --refresh`（旧 stamp は plugin engine fallback＋WARN になる）。
