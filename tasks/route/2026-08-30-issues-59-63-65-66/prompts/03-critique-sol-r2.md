あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

ラウンド2。`tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` を v2 に改訂した（全面書き換え。再読せよ）。前回指摘との対応（自己申告）:

- R1-1（SKILL 本文の暗黙参照）→ 対応: S1 に `--get DOTTED.KEY [--default]` を追加し、SKILL 本文の config 値参照 7 箇所（§9.2: phase3Backend / maxImpactedDocs・docGlobs・minScore / docAuditCommands / boundaryCommand / reviewCommands / codexReview.model・timeoutMs / reportPath）と一行読み 3 箇所を `sealed_config.py --get` に置換。Guardrails で Read・`json.load(open)` による config 読みを禁止。CT-1(d) で `doc-audit.json` を含む行が禁止文以外に無いことを検査。
- R1-2（harness 複製・Phase 4 docAuditCommands・engine-shas）→ 対応: verify-before-read を撤回し、project 側 harness 複製（scripts/check-docs.py と docAuditCommands の各コマンド）は「攻撃者が差し替え可能な実行ファイルであり所見は設定と同じ信頼クラス。検証は防御にならない」として脅威境界外に明示（§1、§9.3）。`generic-layers.py` は `--expect-config-sha` 任意（harness 複製は sha 無しで動く）とし、engine-shas.json の 0.16.0 entry は変更後の実 sha（S13）。
- R1-3（pre-check→open の差し替え）→ 対応: S4 で open-run に `--expect-config-sha`（`import-audit-scope.py --check` の `configSha`）を必須化し、封印バイト列と不一致なら exit 2 `config-changed-before-open`。anchorPath 突合も維持。
- R1-4（gate 内子プロセス）→ 対応: S2 で gate が子 `change-set-sha.py` の exit 7 を明示判定して `config_taint=True`。CT-3 に gate 実行中の差し替えケース追加。
- R1-5（復元後 exit 6 不発火）→ 対応: taint record に `configAcceptanceRequired:true` を付与（S5）、open-run は marker がある限り sha 一致でも exit 6（S4）。record に runid/reportStatus を含め、書き込み成功後にのみ release。既存 gate 内 mismatch 経路も同形式に統一。
- R1-6（history mismatch の funnel）→ 対応: `--taint-observed {config,history} --observed-by` に一般化（S5）。history は既存の隔離規約（`.tainted-<runid>`、`history-changed`、acceptance marker なし）。
- R1-7（cross-turn の CONFIG_SHA）→ 対応: `CONFIG_SHA` は checkpoint 値ではなく EVIDENCE.config からの導出値と定義し、各 turn 開始・各フェーズの最初の消費者呼び出し前に再導出（S6）。checkpoint 契約（RUNID＋EVIDENCE）は不変。
- R1-8（phase4Runs の構造検査・file 正規化）→ 対応: `docaudit_paths` に共通正規化（`./` 除去、`:line` 除去、`\`→`/`、絶対・`..`・制御文字は `<unresolved>` sentinel＋warning）、`docaudit_cache.parse_phase4_runs` に厳格 parser（件数・型・列挙・title 長・制御文字・findings ≤ 50・record ≤ 64 KiB）、不正は history corrupt 経路（S8/S9）。gate と codex-review-plan の両方が同じ parser を使う。
- R1-9（比較キー）→ 対応: record に `configSha`（EVIDENCE.config）を保存し、比較は `worktreeDigest × contractVersion × configSha` の 3 一致（S10）。
- R1-10（保持）→ 対応: `phase4Runs` は full＋completed の run のみ保存、最新 20（S9）。
- R1-11（必須化の呼び出し側）→ 対応: `set-config-key.py` と `generic-layers.py` のみ任意フラグ（列挙固定）、`fix-scope.py` は `--config` を渡すモードのみ必須。`skills/init/**` は無改修のまま禁止範囲に据え置き。CT-1(a) で「任意フラグ script は 2 本」を registry で固定。
- R1-12（配布・混在・downgrade）→ 対応: ADOPTION 3c の部分コピー手順を「v0.16.0 以降は全 tree 同期＋in-flight run 無し必須」に改訂、downgrade で `phase4Runs` 消失を文書化、混在版は exit 2 で停止することを明記（S7、§10）。dir-framework が 0.15.0 である点は follow-up に記録。
- R1-13（テストの判別可能性）→ 対応: CT-1 を registry（固定集合との等値）＋固定値 assert（N=27/M=3/K=19）＋shell の sealed 読み「ちょうど 1 回」検査に、CT-2 を全 19 本の「一致→成功／不一致→exit 7」対に、CT-3 を復元後 exit 6 と gate 内子プロセスに、CT-5 を不正 phase4Runs・3 キー相違・正規化・保持に、CT-6 を history 隔離と次 run cold start に拡張。mdq-index.sh / compute-baseline.sh は読み 1 回化（S3）。

再批判を求める。特に:
1. v2 で新設した機構同士の組み合わせ矛盾（例: `configAcceptanceRequired` marker と `open-run --release`／`--break-lock`／harness decline 再 open の相互作用、`--taint-observed` が lock を持たない状態で呼ばれた場合、`--expect-config-sha "$PRECHECK_CONFIG_SHA"` と audit-scope `absent`/`not-imported` 状態の整合）。
2. `sealed_config.py --get` を SKILL 本文の 7 箇所に置換する設計で、モデルが依然として config を「読んでしまう」余地（CT-1(d) で捕まらない参照の仕方）。
3. `<unresolved>` sentinel と REFUSED の線引き、`parse_phase4_runs` の corrupt 扱いが正当な history を誤って隔離する経路。
4. 固定値 N=27/M=3/K=19 の数え方が §9 の表と実コードで整合するか（あなたが数え直せ）。
5. 落とすべき成果物・足りない成果物。

出力形式は前回同様（`[R2-n] 深刻度 要約` → 根拠 file:line → 推奨 1 つ）。対応済み事項の再指摘は不要。新しい実質的指摘が無ければ「収束」と明記せよ。
