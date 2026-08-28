あなたは読み取り専用の調査担当である。ファイルを一切変更せず、以下の 5 つの GitHub Issue（docaudit プラグイン、engine v0.13.2、HEAD dfdb8a9）について、実装計画を書くために必要な事実を file:line つきで報告せよ。推測と実測を区別し、未確認は「未確認」と明記せよ。報告は日本語、Markdown、Issue ごとに見出しを分ける。

前提知識: `skills/audit/SKILL.md` が監査オーケストレータの指示書（Phase 0 probe → Phase 1〜3 → Phase 4 codex full review → Phase 5 report）。`skills/audit/scripts/*.sh|*.py` が決定論エンジン。`tests/test_*.py` が unittest 契約テスト。`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`・`skills/audit/references/config-schema.md`（存在すれば）が公開文書。`skills/init/SKILL.md` が init 側。前回タスクの計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md` §4 に v0.13.2 で 3 seam（docGraph/semanticSearch/symbolGraph）へ入れた key-gated 判定表がある（同型の変更を残り seam に適用するのが #56 の第 1 段）。

## Issue #58 — audit SKILL.md が CFG を絶対パスで束縛するが import-audit-scope.py --check は repo 相対しか受けない
確認済み: `SKILL.md:13` `CFG="${CLAUDE_PROJECT_DIR}/.claude/doc-audit.json"`、`SKILL.md:26` が `--config "$CFG"` を渡す、`import-audit-scope.py:320 safe_path` → `validate_repo_path` が拒否。
調べること:
1. `validate_repo_path` の実装（file:line）と、絶対パスを repo-root 配下なら相対へ正規化して受理する変更の影響範囲（同関数の他の呼び出し元すべて。`must_exist` の扱い、symlink・`..`・repo 外絶対パスの扱い）。
2. SKILL.md 内で `$CFG` を他スクリプトに渡している箇所すべて（`--config "$CFG"` の grep）と、それらのスクリプトが絶対パスを受理しているか（受理していれば #58 は import-audit-scope.py 側の不整合）。
3. `tests/test_import_audit_scope.py` の既存テスト構造（絶対パス／repo 外／`..` に関するテストの有無）。
4. 対応候補 2 つ（スクリプト側で正規化受理 vs SKILL.md を相対パス指示に変更）のどちらが他の呼び出しと整合するか、根拠つきで推奨 1 つ。

## Issue #56 — 残り 4 seam（indexing/contextMode/webExtract/codexReview）の absent-key 意味論の統一（第 1 段: enabled の JSON boolean 必須化・invalid-config）
調べること:
1. `mdq-index.sh`、`ax-probe.sh`、`codex-probe.sh` それぞれの config 読み取り部（file:line）: キー不在・`{}`・`enabled:false`・`enabled` 非 boolean・キー非 object・`bin` 不正・config 不正の各入力で現状どうなるか（実際に一時 config を作って実行して確認してよい。読み取り専用サンドボックスで書けない場合は「未実測」と書く）。出力 JSON のキー集合と exit code も。
2. v0.13.2 で 3 probe に入れた実装（`graphify-probe.sh`/`cocoindex-probe.sh`/`codegraph-probe.sh` の該当部 file:line）と、同型に揃える際に 3 つの残り probe で異なる点（mdq-index.sh は probe ではなく索引作成を兼ねるか？ `mdq-health.py` の役割は？ `contextMode` は config を読むスクリプトが存在するか、SKILL.md のみか）。
3. `contextMode` の判定箇所（`SKILL.md` 内 file:line）と、config の `contextMode` キーを読んでいるかどうか。
4. 各 seam の `enabled`/`bin` を読む **他の** 消費者（SKILL.md の Phase 0 段落、`plan-dispatch.py`、`codex-review-plan.py`、`codex-dispatch.py`、`inventory.py`、`scaffold.py`、`set-config-key.py` 等）を grep で列挙し、probe だけ厳格化すると不整合になる箇所を挙げる。
5. 既存テスト `tests/test_mdq_index.py`・`tests/test_ax_probe.py`・`tests/test_codex_probe.py`・`tests/test_v0132_contracts.py` の構造（3 probe の判定表テストがどう書かれているか、同型で書ける helper があるか）。
6. 文書側: `config-schema.md`・`ADOPTION.md`・`ADOPTION.ja.md`・`skills/init/SKILL.md` で 4 seam の `enabled` 型・conditional-force 記述がある行（file:line）。

## Issue #57 — Phase-0 probe 結果を run dir に永続化し、再開後に Phase-5 状態行を再束縛する
調べること:
1. Phase 0 の各 probe 呼び出し行（`*_PROBE_JSON=` の束縛、SKILL.md file:line、7 seam すべて + mdq）と、Phase 5 状態行が参照する変数の一覧（`*_AVAILABLE`/`*_BIN`/`*_REASON`）。
2. `RUN_DIR` の定義箇所と、run dir 内に既に書いているファイル（`preflight-allowed.json` 等）の書き込み手順の書き方（SKILL.md の該当行、どのスクリプトが書くか、run lock の保持タイミング）。probe を実行する時点で run lock／run dir が既に存在するか（Phase 0 と run open の順序）。
3. `tree-digest.py`／`seal-run.py` の digest 除外規則に `.claude/state` が含まれること（file:line）。
4. 再開規約 `SKILL.md:44-56` の本文と、それを固定する契約テスト（`tests/test_v013_contracts.py` 等で `RUNID`/`EVIDENCE` 文言を assert しているテスト名）。
5. Phase 5 状態行の文言テンプレート（`SKILL.md` の該当ブロック file:line）と、それを固定するテスト。
6. probe 結果を JSON ファイルへ書く手段として既存の小スクリプト（`write-evidence.py` 等）が流用できるか、それとも新規 `write-probe-record.py` のようなものが必要か。report-only 契約（`.claude/state` 以外への書き込み禁止）の文言箇所。

## Issue #59 — Phase-4 codex full review が既往所見を毎回別サンプリングし verdict が再現しない（既知所見 ledger）
調べること:
1. Phase 4 の流れ: `codex-review-plan.py` → `codex-dispatch.py` → verdict への合流（`decide-verdict.py`／`write-verdict.py`／`check-verdicts.py`）の各 file:line。プロンプトがどこで組み立てられ（テンプレート文字列の場所）、codex の出力（findings）がどの形式でどこに保存されるか（run dir 内のファイル名、JSON schema）。
2. `verdictFlipsUnchangedContent` カウンタの実装箇所と、それが Phase-3 のみを対象にしている根拠（file:line）。
3. 過去 run の findings を参照できる状態置き場: `.claude/state` 配下の既存ファイル（anchor、cache、`docaudit_cache.py`）の構造と、過去 run の codex findings がどこかに残っているか（残っていなければ ledger 新設が必要）。
4. codex findings の severity（critical/high/medium/low）判定と blocking 条件（file:line）。「同一所見が 2 ラウンド連続で出た場合のみ blocking」を実装するならどこに入るか。
5. 既存テスト `tests/test_codex_dispatch.py`・`tests/test_codex_review_plan.py`・`tests/test_decide_verdict.py` の構造（プロンプト内容を assert しているテスト、findings の fixture 形式）。
6. `#39` 対策（Phase-3 の安定化）が何をしたかの要約（git log / PLAN 参照。file:line）。ledger を Phase-4 に入れるとき同じ機構（cache）が再利用できるか。

## Issue #60 — codex probe が binary 有無しか検査せず、実効 CODEX_HOME/auth が不可視
調べること:
1. `codex-probe.sh` の全体（検査内容、出力 JSON キー集合、exit code）。
2. `codex-dispatch.py` が codex を起動する箇所（subprocess の env の扱い、`bin` の解決方法、wrapper 推奨の注記）。
3. `CODEX_HOME` の既定値（codex CLI の仕様: 環境変数未設定時は `~/.codex`。`codex --help` や実機で確認できれば実測）。`auth.json` の存在確認をどう probe に加えるか（`${CODEX_HOME:-$HOME/.codex}/auth.json` の存在。読み取りはしない）。
4. Phase-5 codex-review 状態行のテンプレート（SKILL.md file:line）と、それを固定するテスト（`tests/test_codex_probe.py`／`test_v0132_contracts.py` 等）。
5. 文書側: `config-schema.md`・`ADOPTION.md`・`ADOPTION.ja.md` で `codexReview` の `bin`/wrapper/env に触れている行（file:line）。
6. Phase 4 が `execution-failed` → `required:true` で REFUSED になる分岐（file:line）。

## 共通
- テストの実行方法（`python3 -m unittest discover -s tests -t .`）で現状の件数・skip 数・所要時間を報告（実行できれば）。
- `.claude-plugin/plugin.json` の version と、版 bump 時に更新が必要な文字列の一覧（`tests/test_release_handoff.py` と前回 `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` を参照。engine-shas.json の場所と更新手順も）。
- `docs/ADOPTION.md` §7（behavior changes）の直近版の書き方（v0.13.2 段落の file:line）。

行動規範（全て命令）:
- **結論先行**: 各 Issue の冒頭 1 文で「主張は実測どおりか／推奨は何か」に答える。完全な文で書く
- **進捗の実証**: 各主張を file:line または実行結果で裏付ける。未検証は未検証と明言
- **スコープ規律**: 修正案の提示は求められた範囲まで。実装しない・ファイルを変更しない
- **ターン終了規律**: 全 5 Issue と共通項目を報告し切ってから終える
