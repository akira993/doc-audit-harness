docaudit v0.17.0（Issue #66 方式 B）の実装を依頼する。正本は `tasks/route/2026-08-31-issue-66/PLAN.md`（v8）。**まず PLAN.md を全文精読せよ**（S1〜S9 が成果物、§9 が registry の正本）。前提資料として同ディレクトリの `00-preflight-verification.md`（実測事実）と `01-survey-out.md`（現状 file:line）も読め。

## 実装順の推奨
1. `skills/audit/scripts/docaudit_review.py`（分類 library、S1 の共通関数）→ `tests/test_docaudit_review.py`
2. `skills/audit/scripts/code-review-plan.py`（planner）→ `tests/test_code_review_plan.py`
3. `start-run.py`（S3-1 のみ）／`write-evidence.py`（型検査のみ）
4. `decide-verdict.py`（S4: 優先順位・eligibility §9.8・warnings・placeholder。**V7-2 の送出位置と V7-3 の既定値を厳守**）
5. SKILL.md（S2・S5。placeholder 契約表・cross-turn 行 (g)・stamp :317/:888）
6. テンプレート fixture（wp12_helpers ほか）と既存テスト棚卸し（S7 の一覧。行番号は現物で再確認）
7. docs（S8）・版数（S9）
8. フルスイート

## 完了条件（PLAN §6。機械判定。§6b は boss 実施につきあなたのスコープ外）
1. `python3 -m unittest discover -s tests` 全緑。`Ran N tests / OK` verbatim（基準 716＋追加分、実数記録）。
2. CT 実数出力 = `call sites 23／exempt 3／getters 13／scripts 22／observers 20`。
3. `tests/test_docaudit_review.py`・`tests/test_code_review_plan.py` が「対象 N 件を検査」を出力（実数記録）。
4. `grep -rn 'not-model-invocable' skills/ README.md docs/` 0 件（tests/ は不在検査コード内のみ許容）。
5. `{{GATE_CODE_REVIEW_STATUS}}` の TOKEN_COUNTS 厳密 1 回検査と全状態文言テスト green。
6. planner 単体: S1 全行が期待 JSON、破損 config で exit 7・stderr `sealed-config-mismatch`。
7. gate: 優先順位 4 段・required REFUSED・eligibility 全数表（§9.8）・偽所見遮断・severity gate 正本・`codeReviewNotRun` 警告・phase4Runs 不算入が独立テストで green。
8. plugin.json = 0.17.0、engine-shas.json 0.17.0 エントリ（同一 commit）。
9. `tests/test_release_handoff.py` に diff 無し。

## 変更範囲（PLAN §7）
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/code-review-plan.py`（新規）、`skills/audit/scripts/docaudit_review.py`（新規）、`skills/audit/scripts/decide-verdict.py`、`skills/audit/scripts/start-run.py`（S3-1 のみ）、`skills/audit/scripts/write-evidence.py`（phase4.codeReview 型検査のみ）、`skills/audit/references/config-schema.md`、`skills/audit/references/engine-shas.json`、`skills/init/SKILL.md`（reviewCommands 行のみ）、`README.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`docs/examples/doc-audit.example.json`、`.claude-plugin/plugin.json`、`tests/`（**ただし `tests/test_release_handoff.py` は変更禁止**）。
**禁止**: 上記以外のすべて。probe 群・sealed_config.py・open-run.py・docaudit_cache.py・docaudit_paths.py・codex-review-plan.py・seal-run.py・probe-record.py。`reviewCommands.security` と P8 legacy の挙動変更。`.gitignore`。git 操作（commit/push は boss）。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 検証コマンド一式（PLAN §8）
```
python3 -m unittest discover -s tests
python3 -m unittest tests.test_v016_contracts -v 2>&1 | tail -20
python3 -m unittest tests.test_docaudit_review tests.test_code_review_plan -v
grep -rn 'not-model-invocable' skills/ README.md docs/ ; test $? -eq 1
git diff --stat && git status --short
git diff -- tests/test_release_handoff.py
```

## 規律
- PLAN の registry（§9.5: 23/3/13/22/20）と実測が食い違ったら、実装を曲げず停止して報告（boss が registry を改訂）。
- PLAN に無い判断が必要になったら停止して報告してよい。PLAN 内で解決済みの事項は再質問しない。
- 単独で作業せよ。collab・他エージェント依頼・承認待ちを使わない。
- 報告形式: 結論先行。S1〜S9 ごとの実施内容と該当 file:line、完了条件 1〜9 の充足を番号対応で、フルスイートの `Ran N tests` / `OK` を verbatim で。

以下は行動規範。全て命令。

- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
