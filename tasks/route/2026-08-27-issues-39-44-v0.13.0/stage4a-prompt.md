# S4a 実装依頼 — 封印連鎖（read-manifest / provenance / auditScopeSha / flip 集計）（PLAN rev.8 §4 S4a、§6「封印連鎖」「#39 gate」）

あなたは実装者（worker）。boss（Fable）が計画とレビューを担当する。計画の正本は
`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（rev.8、Opus 承認済み）。本依頼の範囲は **S4a のみ**。#42（`codexReview.required`・
`codex-review-plan.py`・probe・Phase 4/5 の codex 分岐）は S4b、handoff は S5 で行う。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。

包括承認（boss）: 読み取り・テスト実行・許可パス内の編集は事前承認済み。個別確認を求めずに完了まで進めよ。**git 操作
（checkout/add/commit）は sandbox の制約で失敗するため行わない — boss が行う。** 許可パス外・`git push`・`rm -rf`・パッケージ
導入は禁止（必要なら報告のみ）。

## 0. 事前準備
1. 現在のブランチが `feat/v0.13.0-issues-39-44`（S1〜S3 のコミットが載っている）であることを `git log --oneline -8` で確認。
   `git status --short` が空（`.claude/` を除く）であること。
2. フルスイートを実行し着手前の件数と結果を記録。
3. 現行契約を読む: `start-run.py`（`:162` config sha 再照合、`:171-174` partition、`:201-210` manifest）、`seal-run.py:34,70-74`、
   `decide-verdict.py`（`:24-25` REQUIRED_EXPECT、`:252-275` validate_evidence、`:629` config、`:724-725`、`:785-790`、`:817-826` history
   追記、`:832` anchor、`:875` last-run）、`codex-dispatch.py:47,67-73`、`check-verdicts.py:23,96,106,174,216`、`plan-dispatch.py`
   （S2 で `impactSha` を dispatch.json に記録済み）、`docaudit_cache.py:11-19,68-83`、`SKILL.md` Phase 2〜4（`:337` 封印前 parse、
   `:359` seal-run、`:373` codex-dispatch 行、`:379`、`:389` workflow 起動、`:421` tree-digest 再確認、`:428` phase4Required）。

## 1. 新規 `skills/audit/scripts/read-manifest.py`
- 引数 `--run-dir`、`--evidence <EVIDENCE JSON 文字列>`。manifest.json を**一度だけ bytes で読み**、sha256 を `EVIDENCE.manifest`
  （`sha256:<hex>`）と照合し、一致すれば**同じ bytes** を `json.loads` して stdout に JSON を出力（exit 0）。不一致・不在・
  EVIDENCE 不正は stderr に理由、stdout は空、exit 非 0。
- 同じ読取関数（bytes 一度読み→hash→parse）をモジュール関数として公開し、`codex-dispatch.py` から import して使う
  （`docaudit_cache.py` 等と同じ「同ディレクトリ import」方式に合わせる）。
- `tests/test_read_manifest.py`: 正常／sha 不一致（manifest 改変）／manifest 不在／EVIDENCE 不正／hash 後に置換される競合を
  模したケース（同一 bytes で解析していることの固定 — 例: 読取関数に注入可能な `opener` を持たせ、2 回目の open が呼ばれないことを
  assert）。

## 2. `start-run.py`
- `--dispatch-json` の dispatch.json から `impactSha` を読み、`--impact-json` の impact.json の**生 bytes** sha256 と照合。不一致は
  error（非 0、`impact.json changed after plan-dispatch`）。`impactSha` が無い dispatch.json（旧版）は error（v0.13.0 では必須）。
- manifest に `provenance: {path: prov}` を転記（impact.json の `impacted[]` から）。契約: keys == impacted 集合（過不足は error）、
  値 ∈ `{mapped, heuristic, both, full, graphify, semantic, regression}`（他は error）。
- config に `auditScope` があれば、`auditScope.path` の実 bytes の sha256 を `auditScope.sha256` と照合（不一致は error
  `audit-scope drift`）、manifest に `auditScopeSha: "sha256:<hex>"` を封印。無ければ `auditScopeSha: null`。
  `auditScope` の型異常（PLAN §9 検査順序 (2) と同じ契約）は error。
- 既存の `impacted`（path 文字列配列）の形状は変えない。

## 3. `seal-run.py`
- `provenance` と `auditScopeSha` が封印対象 bytes に含まれること（manifest 全体を hash する現行実装ならそのままでよい）を確認し、
  必要な最小変更のみ。

## 4. `decide-verdict.py`（gate）
- REFUSED 条件を追加（既存の manifest sha 検査の**後**、verdict 合成の**前**）:
  (a) run-dir の impact.json の sha256 == dispatch.json の `impactSha`（dispatch.json は EVIDENCE で sha 固定済み）。
  (b) manifest.provenance == impact.json の `{path: provenance}`（完全一致）。
  (c) manifest.provenance の型（object、keys == manifest.impacted 集合、値 ∈ enum 7 値）。
  (d) manifest.auditScopeSha が非 null なら、**状態確定直前**（history/anchor/last-run 書き込みの直前の barrier 内）で config
      `auditScope.path` の実 bytes と再照合。
  各違反は固定 reason 文字列（例: `impact sha mismatch`、`provenance mismatch`、`provenance enum violation: <path>=<value>`、
  `audit-scope changed after seal`）で REFUSED。
- **flip 集計**（PLAN §10 #39、boss 再裁定後の定義）: history 追記の直前に、dispatch された各 path（cached は除く）について
  history 内の**最後の entry**が `contentSha`・`contractVersion`・`backend` すべて一致かつ `verdict` 不一致なら flip。
  `counts.verdictFlipsUnchangedContent` = flip 件数、`counts.verdictFlipsUnchangedContentSameChangeSet` = flip のうち `changeSetSha` も
  一致した件数。`changeSetSha` は数え上げ条件に**含めない**。N>0 のとき `warnings[]` に:
  `verdict instability: N document(s) changed verdict with unchanged content since the previous run (M with an unchanged change set)
  — single-pass verification samples the defect pool; "fix these N and re-run" is not guaranteed to converge (see ADOPTION)`。
  stdout JSON と report の warnings 経路（既存の `⚠ … [non-blocking]`）に乗せる。
- report token 集合（8 種）は増やさない。EVIDENCE のキー集合は変えない。

## 5. `codex-dispatch.py`
- `--evidence <EVIDENCE JSON>` を**必須**にし、read-manifest の共通関数で manifest を読む（sha 不一致は子プロセス 0 回で非 0）。
- provenance は `manifest.provenance` からのみ読む（`impact.json` の `load_provenance` は削除）。プロンプト文言の `regression` は
  S2 で追加済み — 確認。

## 6. `check-verdicts.py`
- `manifestMismatch` 診断に「manifest.provenance と impact.json の provenance の不一致」を追加。**exit 0 の契約は維持**
  （診断専用。直接読取のままでよい — 意図的除外）。

## 7. `skills/audit/SKILL.md`
- Phase 2 末尾の manifest 生 parse（`:337`）に「封印前の値。Phase 2 内でのみ使用する」を明記。
- Phase 3 冒頭（seal-run `:359` の直後）に `python3 "$SD/scripts/read-manifest.py" --run-dir "$RUN_DIR" --evidence "$EVIDENCE"` を
  置き、その stdout を `SEALED_MANIFEST` として bind。**封印後に使う manifest 値はすべて** `SEALED_MANIFEST` から再束縛する:
  Phase 3 backend 選択（`phase3Backend`）、workflow 起動行（`:389`）の `impacted`（DISPATCH entries の provenance は
  `SEALED_MANIFEST.provenance` から組む）、codex-dispatch 行（`:373`）の `--timeout-seconds`（`phase3CodexTimeoutSeconds`）と
  `--evidence "$EVIDENCE"` の追加、tree-digest 再確認（`:421`）の `--exclude`（`digestExclude[]`）、Phase 4 gate（`:428`）の
  `phase4Required`。Phase 2 の変数名（例: `PHASE3_BACKEND` 等 — 実際の名前は SKILL を読んで特定）は封印後に再利用しない。
  `preflightRequired` は Phase 0.5（封印前）専用のため対象外と明記。
- Phase 5: gate stdout の `counts.verdictFlipsUnchangedContent`/`…SameChangeSet` を報告の counts 行に含める（既存の counts 行の
  形式に従う）。

## 8. 統合試験 2 本（実プロセス。`tests/wp12_helpers.py` の既存ヘルパを再利用）
工程: resolve-impact → impact-supplement（graphify/cocoindex なしでよい）→ plan-dispatch → start-run → seal-run → write-evidence
（returns／phase4）→ decide-verdict。
- (A) `regressionRecheck.enabled:true`、history に最後が FAIL の文書 1 件（変更集合と無関係）: impacted に `regression` として入り、
  dispatch（cached でない）に含まれ、manifest.provenance == impact.json provenance、gate が partition・provenance 検査を通過して
  CONSISTENT/NEEDS_FIX に到達。
- (B) mapped 2・regression 2・heuristic 2 を用意し `maxImpactedDocs: 3`: impacted は mapped 2＋regression 1、**heuristic は 0 件、
  regression 1 件が cap で落ちる**（PLAN §6 の期待値「regression 1 件が cap で落ち heuristic 1 件が残る」は mapped ≥ regression ≥
  heuristic の順序で cap=3 なら heuristic は残らない — **期待値の矛盾を発見したら報告し、順序を満たす cap 値（例: cap=4 で
  mapped 2＋regression 2、heuristic 0；cap=5 で heuristic 1 が残る）に調整してよい。調整した値と理由を報告に明記**）、
  `truncated=true`、gate 到達。
- 否定試験: plan-dispatch 後に impact.json の provenance だけ改変 → start-run error／seal 後に manifest を改変 → read-manifest 非 0・
  codex-dispatch が子プロセス 0 回で非 0／**全 SHA（manifest・dispatch・impactSha・EVIDENCE）を再計算して整合させ provenance だけ
  `unknown` にした sealed fixture** → gate が enum 専用 reason で REFUSED／`--check` 相当の状態で seal 前に scope を改変 → gate が
  `audit-scope changed after seal` で REFUSED（`auditScope` metadata つき config で）。
- flip 集計 3 ケース: (i) 4 フィールド一致・verdict 相違 → 1／1、(ii) `changeSetSha` のみ相違 → 1／0、(iii) `contentSha` 相違 → 0／0。

## 9. 契約テスト `tests/test_v013_contracts.py`
(f) を有効化: Phase 3 workflow 起動行・codex-dispatch 行の `--timeout-seconds`・tree-digest 再確認の `--exclude`・Phase 4 の
`phase4Required` 参照が**すべて** `SEALED_MANIFEST`（read-manifest 出力変数）由来で、Phase 2 の変数名ではないこと；codex-dispatch
呼出し行に `--evidence "$EVIDENCE"`。行単位で検査し、説明文中の語では通らないこと。

## 10. 完了条件
- フルスイート全 green（件数前後を報告）。§8 の統合・否定試験と flip 3 ケースが実プロセスで対象コードを経由すること（主要 3 件に
  ついて実装 revert で赤になることを確認し方法を報告）。

## 11. 変更範囲
**許可**: `skills/audit/scripts/{read-manifest.py(新規), start-run.py, seal-run.py, decide-verdict.py, codex-dispatch.py, check-verdicts.py}`、
`skills/audit/SKILL.md`（Phase 2〜5 の該当箇所）、`tests/`（`test_read_manifest.py` 新規、`test_start_run.py`・`test_decide_verdict.py`・
`test_wp12_contracts.py`・`test_check_verdicts.py`・`test_codex_dispatch.py`・`test_v013_contracts.py`・`wp12_helpers.py`）。
**禁止**: `open-run.py`・`write-evidence.py`・`write-verdict.py`・`tree-digest.py`・`plan-dispatch.py`・`resolve-impact.py`・
`codex-probe.sh`・`docs/`・`tasks/`・`.claude/`。EVIDENCE のキー集合・report token 集合。既存 assert の変更は PLAN §11 の意図的
差分（manifest `provenance`/`auditScopeSha`、dispatch `impactSha`、gate stdout 追加キー、codex-dispatch の `--evidence` 必須化）のみ。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 12. 検証コマンド一式
```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_decide_verdict tests.test_start_run tests.test_check_verdicts tests.test_codex_dispatch tests.test_read_manifest tests.test_wp12_contracts tests.test_v013_contracts -v
```

## 13. 報告
結論先行・完全な文で。各主張はツール結果と突合し、未検証は未検証と明言。テスト失敗は出力ごと報告。末尾に「変更ファイル一覧
（`git diff --stat`）」「テスト件数（前後）」「許可外変更の必要有無」「§8 (B) の cap 値と理由」。コミットはしない。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
