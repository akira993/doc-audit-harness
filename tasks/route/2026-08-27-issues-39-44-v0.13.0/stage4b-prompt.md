# S4b 実装依頼 — #42 codex-review strict mode（judgement table / gate / probe / SKILL Phase 4-5 / 設計 spec）（PLAN rev.8 §4 S4b、§6 #42、§10 #42）

あなたは実装者（worker）。boss（Fable）が計画とレビューを担当する。計画の正本は
`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（rev.8、Opus 承認済み）。本依頼の範囲は **S4b のみ**。封印連鎖（S4a）は
完了済みの前提。handoff・#41 docs は S5。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。

包括承認（boss）: 読み取り・テスト実行・許可パス内の編集は事前承認済み。個別確認を求めずに完了まで進めよ。**git 操作
（checkout/add/commit）は sandbox の制約で失敗するため行わない — boss が行う。** 許可パス外・`git push`・`rm -rf`・パッケージ
導入は禁止（必要なら報告のみ）。**ネットワークやモデル呼び出しを伴う `codex exec` の実行は禁止**（テストは偽 bin で行う）。

## 0. 事前準備
1. 現在のブランチが `feat/v0.13.0-issues-39-44`（S1〜S4a のコミットが載っている）であることを確認。`git status --short` が空。
2. フルスイートを実行し着手前の件数と結果を記録。
3. 現行契約を読む: `codex-probe.sh`（`:28-37` config 読み、`:44-51` `enabled:false` → `reason:disabled-by-config`、`:55` `--version`）、
   `SKILL.md:139-148`（Phase 0 probe 束縛）、`:474-512`（Phase 4 手順 3。`:477` 無条件 full skip、`:485` baseline 検査、`:499` 実呼出し、
   `:503-507` execution-failed）、`:514-521`（phase4 evidence）、`:617-619`（Phase 5 codex 行）、`decide-verdict.py:198-224,629,785-790`、
   `start-run.py:190-191`（`phase4_required`）、`write-evidence.py:38-50`（phase4 は `findings` 配列のみ検査 — **変更禁止**）、
   `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md:192,345-356,386-394`。

## 1. 新規 `skills/audit/scripts/codex-review-plan.py`（決定論的判定表）
- 引数: `--mode incremental|full`、`--config PATH`、`--available true|false`、`--available-reason <str>`（既定 `not-installed`）、
  `--baseline-ok true|false`。stdout に JSON `{action: "run"|"skip"|"not-active", state, promptVariant: "diff"|"full"|null, reason}`。
- `state` の値域（**gate と同一定数**。共有モジュール定数 `CODEX_REVIEW_STATES = ("completed", "execution-failed", "ref-invalid",
  "skipped-full-run", "not-active")` を `docaudit_cache.py` 等の共有モジュールに置き、本スクリプトと `decide-verdict.py` が同じ
  定数を import する）。
- 規則（4 軸: available × mode × required × baseline-ok。`enabled` は軸に含めない — probe が `enabled:false` を `available:false,
  reason:disabled-by-config` に畳むため。判定表は `--config` から `codexReview.required` のみを読む）:
  - `available:false` → `action:not-active, state:not-active, reason:<--available-reason>`（required の値にかかわらず。required なら
    gate が REFUSED する）。
  - `available:true, mode:full, required:true` → `action:run, state:null（実行後に orchestrator が completed/execution-failed を
    記録）, promptVariant:full`。
  - `available:true, mode:full, required:false` → `action:skip, state:skipped-full-run`。
  - `available:true, mode:incremental, baseline-ok:true` → `action:run, promptVariant:diff`。
  - `available:true, mode:incremental, baseline-ok:false` → `action:skip, state:ref-invalid`（run しない）。
- `required` の型異常（非 bool）は本スクリプトでは `reason` に記録して `run`/`skip` の判定は上記どおり（REFUSED は gate の責務）。
- `tests/test_codex_review_plan.py`: **16 行の真理値表**（`subTest`）で action/state/promptVariant を固定。`enabled:false` の config を
  `available:true` で渡した場合の挙動は「到達不能」としてテストしない（コメントで明記）。

## 2. `decide-verdict.py`（gate）
- config `codexReview.required`（既定 false）を読む。**evidence の `required` は読まない**。
- phase4 evidence（`phase4.json`）に `codexReview` が**存在する**場合は required に関係なく厳格検証: object／`state` が文字列かつ
  `CODEX_REVIEW_STATES` の要素。違反は REFUSED（reason `codexReview evidence invalid: <detail>`）。不在は後方互換（従来挙動）。
- REFUSED 条件: `required` が非 bool → `codexReview.required must be boolean`；`codexReview.enabled == false` かつ `required == true`
  → `codexReview.required conflicts with enabled:false`；`required == true` かつ（phase4 evidence 不在、`codexReview` 不在、または
  `state != "completed"`）→ `codex-review required but state=<state|missing>`。REFUSED は既存契約どおり history・anchor 非更新、
  last-run は理由つき更新。
- `required == false` で `state ∈ {execution-failed, ref-invalid}` → `warnings[]` に `codex-review did not run (<state>) — verdict
  excludes the adversarial layer`。
- **表示分離**: 内部 verdict は 3 値のまま。report の `{{GATE_VERDICT}}` 描画のみ、verdict が CONSISTENT かつ degrade（`required:false`
  で `state ∈ {execution-failed, ref-invalid}`）のとき `CONSISTENT (codex-review did not run: <state>)`。stdout JSON の `verdict`・
  last-run・anchor は素の `CONSISTENT`。stdout JSON に `codexReview: {state, required, degraded}`（evidence 不在時は `state: null`）。
- report token 集合（8 種）は増やさない。EVIDENCE のキー集合は変えない。`write-evidence.py` は変更しない。

## 3. `start-run.py`
- `phase4_required` に `or bool(config.get("codexReview", {}).get("required") is True)` を追加（mode 無関係）。`required` の型異常は
  ここでは無視（gate が REFUSED）。

## 4. `codex-probe.sh`
- `--version` に加え、同じ `$BIN` で `exec --help` を実行（ネットワーク不使用・モデル非起動）。失敗時 `codexReviewAvailable:false,
  reason:probe-exec-failed`。probe JSON に `probeCommands: ["<bin> --version", "<bin> exec --help"]`（実行した順で。設定キーでは
  ない）を追加。`tests/test_codex_probe.py` の偽 bin を `exec --help` にも応答させ、`probe-exec-failed` と `probeCommands[]` を固定。

## 5. `skills/audit/SKILL.md`
- Phase 0（`:139-148`）: probe JSON の `reason` を `CODEX_REVIEW_REASON` に bind。「probe は CLI 存在と `exec` サブコマンド到達の確認で
  あり、Phase 4 の実呼び出し形状（sandbox/permission/wrapper 引数）は検証しない。wrapper が必要な環境は `codexReview.bin` に wrapper を
  指定し、確実性が要るなら `codexReview.required:true`（最初の baseline 確立後に有効化を推奨）」を明記。
- Phase 4 手順 3（`:474-512`）を判定表経由に書き換える: `python3 "$SD/scripts/codex-review-plan.py" --mode "$MODE" --config "$CFG"
  --available "$CODEX_REVIEW_AVAILABLE" --available-reason "$CODEX_REVIEW_REASON" --baseline-ok "<git rev-parse --verify の結果>"` を
  先に実行し、`action=run` のときだけ `codex exec` を起動（`promptVariant=diff` は現行プロンプト、`full` は「`manifest.head` で
  識別され `worktreeDigest` で封印された現在の worktree（未 commit・未追跡を含む）における impacted 全文書 vs code」を対象とする
  変種。`-s read-only`・`--output-schema` は同一）。`action=skip`/`not-active` はその `state` を `CODEX_REVIEW_STATE` に bind。
  model 選択・retry・`CODEX_REVIEW_STATE` 記録は run 経路で共有。`:477` の無条件 full skip と `:485` の baseline 検査は判定表に
  吸収する（重複記述を残さない）。
- Phase 4 evidence（`:514-521`）: payload に `codexReview: {state: "$CODEX_REVIEW_STATE"}` を含める（`required` は含めない）。
- Phase 5（`:617-619`）: codex 行を **4 状態**に分離 — `not-active` → `💡 codex-review: not active (<reason>)`／`skipped-full-run` →
  `💡 codex-review: skipped (full run without codexReview.required)`／`completed` → `✓ codex-review: completed (findings included in
  verdict when present)`／`execution-failed`・`ref-invalid` → `⚠ codex-review: did not run (<state>) — findings not folded
  [non-blocking unless codexReview.required]`。
- #41 の 3 観点（他文書・`.env*`/`.envrc`/src コメントとの矛盾、`X.md §N` 型参照の実在、手順の前提条件）を diff／full 両変種の
  プロンプト構成指示に追加（S5 の docs と対になる）。

## 6. 設計 spec と config-schema
- `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md` の末尾に「v0.13.0 改訂」節を追記（4 状態・
  `codexReview.required` による REFUSED・判定表スクリプト経由・full＋required の実行・probe の保証範囲）。既存本文は書き換えず、
  改訂節から該当行（`:192,345-356,386-394`）を参照して上書き関係を明示。
- `skills/audit/references/config-schema.md`: 設定キー表に `codexReview.required`（bool、既定 false）の行；`## Codex review (Phase 0/4)`
  節に `probeCommands` の記述と 4 状態。

## 7. テスト
- `tests/test_decide_verdict.py`: `required:true` × `state` ∈ {completed → 通常, execution-failed/ref-invalid/skipped-full-run/
  not-active/欠落 → REFUSED}、`enabled:false`＋`required:true` → REFUSED、`required` 非 bool → REFUSED、`codexReview` evidence の型異常
  （配列、`state` 数値、未知 state）→ required に関係なく REFUSED、不在 → 従来挙動。REFUSED では history・anchor が非更新、
  last-run が理由つき更新（実ファイル）。表示分離: degrade 時に report は修飾、stdout/last-run/anchor は素の値（同一テスト内で
  3 箇所を assert）。
- `tests/test_start_run.py`: `required:true` で impacted 0 件でも `phase4Required:true`（incremental・full とも）。
- `tests/test_codex_probe.py`: `exec --help` 失敗 → `probe-exec-failed`、`probeCommands[]`。
- `tests/test_v013_contracts.py`: (e) を有効化 — Phase 4 evidence 組み立てに `codexReview`/`state`；`codex-review-plan.py` 行に
  `--available "$CODEX_REVIEW_AVAILABLE" --available-reason "$CODEX_REVIEW_REASON"` があり、`CODEX_REVIEW_REASON` の bind 行が probe
  JSON の `reason` を参照；`codex exec` 行が判定表行の後；Phase 5 codex 行が 4 状態。(h) の `codexReview.required` 行と
  `## Codex review` 節の `probeCommands`。

## 8. 完了条件
- フルスイート全 green（件数前後）。§7 の各テストが対象コードを経由すること（主要 3 件の revert 確認と方法を報告）。

## 9. 変更範囲
**許可**: `skills/audit/scripts/{codex-review-plan.py(新規), decide-verdict.py, start-run.py, codex-probe.sh, docaudit_cache.py
（共有定数の追加のみ）}`、`skills/audit/SKILL.md`（Phase 0/4/5 の該当箇所）、`skills/audit/references/config-schema.md`、
`docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md`（改訂節の追記のみ）、`tests/`。
**禁止**: `write-evidence.py`・`open-run.py`・`seal-run.py`・`read-manifest.py`・`codex-dispatch.py`・`docs/ADOPTION*.md`（S5）・
`tasks/`・`.claude/`。EVIDENCE のキー集合・report token 集合。既存 assert の変更は PLAN §11 の意図的差分（gate stdout の
`codexReview`、probe JSON の `probeCommands`）のみ。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ。**

## 10. 検証コマンド一式
```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_decide_verdict tests.test_codex_probe tests.test_start_run tests.test_codex_review_plan tests.test_v013_contracts -v
```

## 11. 報告
結論先行・完全な文で。各主張はツール結果と突合し、未検証は未検証と明言。テスト失敗は出力ごと報告。末尾に「変更ファイル一覧」
「テスト件数（前後）」「許可外変更の必要有無」。コミットはしない。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
