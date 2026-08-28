調査は完了しました。ファイルは一切変更していません。以下の「実測」は現行 HEAD `dfdb8a94e81251944cdc68fedc12217f995eb0eb` の読取り・実行結果、「推奨」は実装計画上の判断です。

## Issue #58 — 絶対パス CFG

結論：主張は実測どおりであり、`SKILL.md` は絶対パスを渡すのに `import-audit-scope.py` だけが拒否しています。推奨は、共有のパス検査を緩めず、当該スクリプトの CLI 入力だけを安全に相対化することです。

- `validate_repo_path` は絶対パスを即時拒否し、`.`・`..`、途中のリンク、実体解決後のリポジトリ外も拒否します。`must_exist=False` は「存在・通常ファイル」の確認だけを外します。実装は [docaudit_paths.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:37)。
- この共有関数には 26 呼出しがあります。主な利用先は `codex-dispatch.py:83`、`decide-verdict.py:211,367-368,489,494,623,627,630`、`fix-scope.py:93`、`import-audit-scope.py:133,235,322`、`open-run.py:152,180`、`start-run.py:94,121,152,162`、`write-template.py:97` です。共有関数自体を変更すると安全境界が広がります。
- `safe_path` は CLI の config/scope を `validate_repo_path(..., must_exist=False)` に渡しています。[import-audit-scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:320)。
- `CFG` は絶対パスとして束縛されます。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:13)

`--config "$CFG"` の主な消費者は以下です。

| SKILL 行 | 実行先 | 絶対パス |
|---:|---|---|
| 26 | `import-audit-scope.py` | 拒否 |
| 73, 408 | `mdq-index.sh` | 受理 |
| 137 | `ax-probe.sh` | 受理 |
| 149 | `codex-probe.sh` | 受理 |
| 174, 193, 211 | 3 graph probe | 受理 |
| 238 | `set-config-key.py` | 受理 |
| 261, 274, 498 | `generic-layers.py` | 受理 |
| 297, 319, 337, 343, 356, 362, 368 | Phase 1〜3 scripts | 受理 |
| 539 | `codex-review-plan.py` | 受理 |
| 629 | `decide-verdict.py` | 受理後、内部で相対化して検査 |

根拠は各スクリプトの `open(args.config)` 等で、例として [mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:29)、[ax-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:23)、[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:606)です。対象プロジェクトへコピーされた `scripts/check-docs.py` の受理可否だけは未確認です。

既存テストは、一時リポジトリで subprocess の JSON と終了番号を検査する構造です。[test_import_audit_scope.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py:57)

- 相対の存在しない config/scope は成功・`absent`。[同](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py:606)
- リポジトリ内絶対パスも現在は拒否する契約。[同](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py:612)
- リンクは拒否。[同](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py:618)
- 外部の絶対パス、途中に `..` を含む CLI 引数のテストは未確認です。

推奨案は、`--config` に限り「実体ルート配下の絶対パス」を相対化して既存検査へ通す方法です。外部絶対パス、`..`、リンク、リポジトリ外への解決は引き続き拒否し、`auditScope.path` の保存形式は相対パスのままにします。`SKILL.md` を相対パスに変える案は、他の消費者との不整合と実行場所依存を増やすため非推奨です。

## Issue #56 — 残り 4 seam の absent-key 意味論

結論：主張どおり、現状の `indexing`・`webExtract`・`codexReview` はキー不在と不正値を実質「既定で有効」に丸め、`contextMode` も型検査のない手順です。3 seam と同じ key-gated 化をするなら、probe だけでなく状態表示・後段判定・文書を一緒に直す必要があります。

### 現状の実測

書込みを行わないファイル記述子と、対象バイナリのない限定 `PATH` で実測しました。各ケースの終了番号は `0` です。

| 入力 | mdq | ax | codex |
|---|---|---|---|
| キー不在 `{}` / キー `{}` | `not-installed`、既定 bin | 同左 | 同左 |
| `enabled:false` | `disabled-by-config` | 同左 | 同左 |
| `enabled:"false"` | 有効扱い → `not-installed` | 同左 | 同左 |
| キーが `[]` | 空 object と同様 | 同左 | 同左 |
| `bin:42` | `"42"` を bin として採用 | 同左 | 同左 |
| 壊れた JSON | 既定へ丸める | 同左 | 同左 |
| `bin:""` | 未実測。静的には既定へ戻る | 同左 | 同左 |

理由は 3 script とも `try/except` で例外を握りつぶし、`bool(...)` と `str(...)` で丸めるためです。

- mdq: [mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:26)
- ax: [ax-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:23)
- codex: [codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:24)

出力形は次のとおりです。

- mdq は disable 時 `{mdqAvailable,reason}`、未導入時はこれに `bin`、索引成功時は `dbDir`、失敗時は `rc` を追加します。[mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:46)
- ax は常に `{axAvailable,axBin,axVersion,reason}`。[ax-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:43)
- codex は常に `{codexReviewAvailable,codexReviewBin,codexReviewVersion,probeCommands,reason}`。[codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:44)

`mdq-index.sh` は probe 専用ではなく、利用可能なら `mdq index` を実行して `.mdq/` を作る索引作成も兼ねます。[mdq-index.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:77) その後の `mdq-health.py` は検索可否を診断する read-only の補助です。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:86)

### v0.13.2 の 3 seam との差

v0.13.2 の `docGraph`・`semanticSearch`・`symbolGraph` は、キー不在を `not-configured`、非 object・非 boolean `enabled`・空/非文字列 `bin`・壊れた config を `invalid-config` とします。

- graphify: [graphify-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:31)
- cocoindex: [cocoindex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:34)
- codegraph: [codegraph-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:28)
- 決定表の元: [前回 PLAN §4](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:33)

`contextMode` は設定を読む出荷スクリプトが存在せず、`SKILL.md` の `json.load(...).get("contextMode", {}).get("enabled", True)` だけです。non-object では例外になり得ます。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:115)

probe だけを厳格化した場合の不整合は次です。

- mdq の Phase-0 確認ゲートと Phase-5 表示に `invalid-config` 分岐がない。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:95) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:668)
- ax は Phase-5 で `AX_AVAILABLE` しか表示に使わず、reason を束縛しない。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:680)
- codex は reason を束縛して表示できる一方、`start-run.py`・`codex-review-plan.py`・`decide-verdict.py` は `required` 以外の型を厳格にしない。[start-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:247) [codex-review-plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:23) [decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:710)
- `plan-dispatch.py`、`codex-dispatch.py`、`inventory.py`、`scaffold.py`、`set-config-key.py` に、4 key の直接読取りは見つかりませんでした。

テストは全て各ファイル固有の `run_script()` で、一律 helper は未確認です。[test_mdq_index.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_mdq_index.py:26) [test_ax_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_ax_probe.py:25) [test_codex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py:26)  
v0.13.2 契約テストは実行表でなく、reason 集合・状態表示・JSON 束縛文言を固定します。[test_v0132_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:224)

文書・init の変更対象は、schema の 4 seam 行 [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:33)、英語 Adoption の [ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:99)、日本語版の [ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:97)、init の提案規約 [init SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:121) です。

## Issue #57 — probe 結果の run dir 永続化

結論：主張は実測どおりです。Phase 0 の結果は現在プロセス内の変数だけで、再開規約が復元を要求するのは `RUNID` と `EVIDENCE` だけです。Phase 5 表示を再開後も同じ状態にするには、run dir への保存と再束縛が必要です。

Phase 0 の束縛は一様ではありません。

- mdq は `MDQ_AVAILABLE/BIN`、health と確認ゲートの変数を直接束縛。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:73)
- context-mode は出荷スクリプトなしで直接判定。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:115)
- ax も JSON 変数なしで直接 probe。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:136)
- codex、symbol/doc/semantic graph は `*_PROBE_JSON` を束縛し、各 availability/bin/reason を取り出す。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:149) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:174) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:193) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:211)

Phase 5 は mdq の複数変数、context-mode の複数変数、ax の availability、codex の state/reason、3 graph の reason を参照します。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:668) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:684) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:698)

`open-run.py` は lock を作ってから run dir を作り、初期 `EVIDENCE` を返します。[open-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:194) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:210) つまり probe 時点には両方あります。既存の run dir 書込みは、preflight、impact、dispatch、manifest、returns、phase4、report template です。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:298) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:578)

`.claude/state` は digest 除外として許可されています。[tree-digest.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/tree-digest.py:25) `seal-run.py` は manifest の除外一覧をそのまま digest 計算へ渡します。[seal-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:63)

再開規約は `RUNID` と完全な `EVIDENCE` を表示・正確に復元し、できなければ gate を呼ばず release するものです。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:41) 再開時の Phase-0 状態復元を文字列で固定するテストは未確認です。近接する codex 状態テストは [test_v013_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:58)、3 graph の状態表示テストは [test_v0132_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:250) です。

`write-evidence.py` は原子的書込みと `EVIDENCE` hash 差替えを提供しますが、名前は `preflight`・`returns`・`phase4` に限定されています。[write-evidence.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/write-evidence.py:53)  
推奨は新たな別系統 writer より、この helper に probe record 用の名前・schema・`EVIDENCE` hash を追加することです。これは推奨であり、未実装です。「`.claude/state` 以外への書込み禁止」という完全一致の文言は未確認ですが、record を `RUN_DIR` に置くことは既存 ledger と digest 除外に整合します。

## Issue #59 — Codex full review の既往所見 ledger

結論：再現性の問題は構造上あり、過去の Phase-4 Codex 所見を後続 run が読む保存場所は確認できません。既知所見 ledger は新設が必要で、blocking 判定は決定論的 gate 側に置くのが整合的です。

前提の一部を訂正します。`codex-dispatch.py` は Phase 3 の文書別 dispatcher であり、Phase 4 full review の実行器ではありません。[codex-dispatch.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:1)

実際の Phase-4 経路は次です。

1. `codex-review-plan.py` が action/state/promptVariant/reason を決定。[codex-review-plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:14)
2. `SKILL.md` が prompt を `$RUN_DIR/codex-review-prompt.txt` に作成し、Codex を直接起動して `$RUN_DIR/codex-review-result.json` に書かせます。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:545) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:559)
3. findings を Phase-4 collection に畳み、`phase4.json` として `write-evidence.py` に渡します。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:571) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:578)
4. gate が `phase4.json` と codex state を検査し、severity から verdict を導きます。[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:772) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:894)

Codex result の schema は `findings[]` の `{severity,title,file}` で、severity は `critical/high/medium/low` です。[codex-review-output.schema.json](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/codex-review-output.schema.json:5)  
`critical/high` は blocking、`medium/low` は非 blocking へ正規化されます。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:571) gate 側も `FAIL/HIGH/CRITICAL` を blocking とします。[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:262)

`verdictFlipsUnchangedContent` は Phase-3 verdict history 専用です。history の entry にあるのは runid/path/contentSha/changeSetSha/contractVersion/verdict/backend/時刻で、Codex findings はありません。[docaudit_cache.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:13) gate が Phase-3 verdict additions から flip を数えます。[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:219) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:925)

`.claude/state` の既存永続物は history、last-run、anchor と run ledger であり、過去 run の Codex findings が後続 run 用に残る箇所は未確認です。current run の `phase4.json`・`codex-review-result.json` は run dir 内だけです。従って ledger 新設が必要です。

「同一所見が 2 回連続したときのみ blocking」は、推奨として `decide-verdict.py` の Phase-4 findings を `findings_fail` に渡す直前へ置くべきです。[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:894)  
これは推論です。ledger は title/file/severity だけでなく、同一性を決める正規化 key と、sealed content/digest 等を設計しなければ、偶然同名の所見を誤って連続扱いする危険があります。

既存テストは以下です。

- Phase-3 dispatcher の prompt 内容と fake Codex 出力を検査。[test_codex_dispatch.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_dispatch.py:236)
- plan の 16 行真理値表。[test_codex_review_plan.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:17)
- Phase-4 HIGH が `NEEDS_FIX`、severity 欠落は `REFUSED`。[test_decide_verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py:640)
- flip count の Phase-3 契約。[test_decide_verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py:905)

#39 は、前回 FAIL で内容不変の文書を再検証対象に戻し、Phase-3 verdict flip を数える対策でした。[v0.13.0 PLAN](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:26) 後の修正で、現在 content hash が過去 FAIL entry と一致することを条件にしました。[final-review-fixes.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/final-review-fixes.md:3)  
Phase-3 cache の原子的保存・hash 資格判定は再利用候補ですが、Codex findings の履歴 schema と「2 回連続」の gate policy は現行 cache にはありません。よって完全な再利用は不可です。

## Issue #60 — Codex probe の実効認証状態

結論：主張は実測どおりで、現行 probe は binary・version・`exec --help` だけを確認し、実効 `CODEX_HOME` や認証ファイルは見ません。認証ファイルの存在だけを読む probe を追加する案は妥当ですが、wrapper と環境継承を含む契約を明示する必要があります。

`codex-probe.sh` の全体動作は次です。

- `enabled` の既定は true、bin の既定は `codex`。[codex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:24)
- disabled → `disabled-by-config`、未発見 → `not-installed`。[同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:44)
- `--version` と `exec --help` のみを実行。[同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:54)
- 全通常経路で JSON を出し終了番号 `0`。[同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:61)

この環境での実測は、`codex` は `/opt/homebrew/bin/codex`、version は `0.149.0`、`CODEX_HOME` は明示設定済み、そこに `auth.json` は存在します。内容は読みませんでした。`codex --help` は config の既定として `~/.codex/config.toml` を表示しますが、`auth.json` の既定位置は表示しません。したがって「環境変数未設定時の auth の既定が `~/.codex/auth.json`」はこの調査では未確認です。公式 OpenAI Docs の検索でも、その一点を裏付ける公式ページは取得できませんでした。

Phase-3 の `codex-dispatch.py` は `Popen(..., cwd=...)` に `env` を渡さないため、親プロセスの環境をそのまま継承します。[codex-dispatch.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:166) bin は `--codex-bin` をそのまま command の先頭に置きます。[同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:169)  
Phase 4 は Python dispatcher を使わず、`SKILL.md` が `$CODEX_REVIEW_BIN exec ...` を直接指示します。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:559) wrapper 推奨の文書は [config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:230) と [ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:122) にあります。

実装計画では、`${CODEX_HOME:-$HOME/.codex}/auth.json` の存在だけを読み、内容を読まない probe を候補にできます。ただしこれは推奨です。wrapper が独自の認証方法・独自環境を使う場合に誤って `not-authenticated` としない仕様が必要です。

Phase-5 status 行は 5 内部状態を 4 表示へまとめています。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:684) 近接テストは probe 自体の [test_codex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_probe.py:42) と、status state の [test_v013_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:58) です。

`execution-failed` は optional なら degraded warning、`required:true` なら `completed` 以外を `REFUSED` にします。[decide-verdict.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:786) [同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:797) `required:true` と `enabled:false` の組合せも `REFUSED` です。[同](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:717)

## 共通

- 全テストを指定コマンドで実行しました。結果は **551 件、0.558 秒、errors=565、skip は表示なし**です。失敗原因はコード検証ではなく、読み取り専用環境に一時ディレクトリがなく、ほぼ全テストが `tempfile` 作成時に失敗したことです。したがって green/red の機能判定は未実測です。
- plugin version は `0.13.2`。[plugin.json](/Users/akiratakahashi/Projects/doc-audit-harness/.claude-plugin/plugin.json:3)
- `engine-shas.json` は [こちら](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/engine-shas.json:32) に `0.13.2` entry があります。版を上げる場合は、変更後の harness template hash を同ファイルに追加し、`scaffold.py --harness --dry-run` と scaffold tests で確認する手順が前回計画にあります。[前回 PLAN](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:105)
- version bump で最低限更新対象となる文字列は、plugin manifest、英日 Adoption の `claude plugin list` 表示、更新可能な template version 列挙、`engine-shas.json`、関連契約テスト、release handoff script とその test です。[前回 PLAN](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:105)
- `test_release_handoff.py` は handoff path、tag、release title、Issue 集合、Release 本文必須語を固定します。[test_release_handoff.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:14) 実 handoff は version、tag、title、notes、Issue close、同期検査を固定しています。[release-handoff.sh](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh:2)
- ADOPTION §7 の直近版の書式は、英語では一つの太字段落です。[ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:255) 日本語版は対応する一つの太字段落です。[ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:235)