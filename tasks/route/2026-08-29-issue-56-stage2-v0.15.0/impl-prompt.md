# 実装依頼 — docaudit v0.15.0: Issue #56 第2段（webExtract / codexReview の key-gate 化）

あなたは実装 worker である。branch `fix/v0.15.0-issue-56-stage2`（作成済み・checkout 済み、base: main `4c9df5b`）で作業せよ。

## 仕様（必読）

`tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md`（**rev.8**）を全文精読し、**§5（成果物）の項目 1〜18 をそのまま実装**せよ。PLAN は Sol 5 往復＋Opus 3 ラウンドの批判を経て確定しており、記載の設計判断（例: rescope 裁定 §0、resume 再 probe 規則、走査単位、行番号）を worker 判断で変更してはならない。曖昧・矛盾・実装不能を発見した場合は、その項目を実装せず報告せよ。

補足情報:
- TOCTOU 追跡 Issue は **#63** として起票済み（PLAN §9 の「番号」はこれ）。release-handoff.sh の前提条件検証と test_release_handoff.py の新 Issue 前提条件テストは #63 を対象にせよ。
- ADOPTION §7 の v0.15.0 固定文（en 4 文・ja 4 文）は PLAN §5.2-8 の文字列を**一字一句そのまま**使い、契約テストの期待値も同一文字列にせよ。
- 参照実装: `skills/audit/scripts/graphify-probe.sh`（key-gated probe の判定順序）、`tests/test_v0132_contracts.py`（契約テストの型）、`tasks/route/2026-08-28-issues-56-60/release-handoff.sh`（handoff 雛形）。
- commit は Conventional Commits で、意味のある単位（engine/docs/tests 等）に分割してよい。

## 完了条件（PLAN §6 — 機械判定。verbatim）

1. フルスイート green: `python3 -m unittest discover -s tests` が OK・skip 0。ベースライン **609 tests**
   以上、増分内訳を報告に実数記録。
2. 判定表の実数: ax probe **≥ 23 ID**・codex probe **≥ 23 ID**（absent/empty/省略・値欠落・不存在・壊れ/
   disabled/invalid×2/bin 系/not-installed/ok）、呼出し回数固定 **≥ 6**、probe-record **≥ 12**
   （受理 2・mutation 拒否 7・未知フィールド拒否 1・上書き正負 2）、codex-review-plan **既存 16 行維持＋
   追加 ≥ 7**（not-configured 2・旧 record 迂回 1・full-mode 一体 4）、ASCII/1 行 **≥ 2**、
   resume 再 probe 配線 **≥ 2 本**、probe-record 上書きは既存 upsert 不変＋置換/保持の正テスト ≥ 2、
   handoff は test_release_handoff.py の既存 method 全数維持（v0.15 再ターゲット）＋追加 ≥ 5
   （#59 負契約 2・notes directive 1・新 Issue #63 前提条件 正負 2）。各テストは対象スクリプトを
   実起動して stdout/exit code を比較（常時 PASS の偽陽性検査は差し戻し対象）。
3. 残骸 grep ゲート: 最小単位（表行／リスト項目／散文段落）走査で allowlist（§7 歴史ブロック 2 段落
   literal）外 0 件、走査件数 > 0 かつ代表 path 3 件を含むこと、実数出力。indexing/contextMode/mdq の
   保持テキスト 5 箇所（PLAN 参照）が発火しないことを負テストで固定。
4. 版整合: release surface `{"0.15.0"}`、test_scaffold green（engine-shas 0.15.0 実測 SHA）。
5. スコープ検査: `git diff --name-only main...HEAD` が下記許可一覧の部分集合。
6. （boss 側工程のため worker 対象外: 最終 codex exec review）

## 変更範囲（PLAN §7 — verbatim）

**許可（この一覧のみ）**:
- `skills/audit/scripts/ax-probe.sh`, `skills/audit/scripts/codex-probe.sh`,
  `skills/audit/scripts/probe-record.py`, `skills/audit/scripts/codex-review-plan.py`
- `skills/audit/SKILL.md`, `skills/audit/references/config-schema.md`, `skills/init/SKILL.md`
- `docs/ADOPTION.md`, `docs/ADOPTION.ja.md`, `README.md`, `.claude-plugin/plugin.json`,
  `skills/audit/references/engine-shas.json`
- `tests/test_ax_probe.py`, `tests/test_codex_probe.py`, `tests/test_probe_record.py`,
  `tests/test_codex_review_plan.py`, `tests/test_v015_contracts.py`（新規）,
  `tests/test_release_handoff.py`（in-place 再ターゲット）, `tests/test_v014_contracts.py`,
  `tests/test_v0132_contracts.py`, `tests/test_v013_contracts.py`, `tests/test_scaffold.py`
- `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/**`

**禁止**: 上記以外の全ファイル。特に `decide-verdict.py`・`start-run.py`・`open-run.py`・
`workflow-template.js`・graph 系 3 probe・`mdq-index.sh`・config-schema.md :33-34。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**
また `tests/test_v014_contracts.py:225`（`probe-record.py also receives --evidence …`）は変更禁止。

## 検証コマンド一式（PLAN §8 — verbatim。全て実行し結果を報告に含めよ）

```
python3 -m unittest discover -s tests

python3 -m unittest tests.test_ax_probe tests.test_codex_probe tests.test_probe_record \
  tests.test_codex_review_plan tests.test_v015_contracts tests.test_release_handoff \
  tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_scaffold -v

# 残骸スイープ＝機械ゲートの直接実行
python3 -m unittest tests.test_v015_contracts -v

git diff --name-only main...HEAD
```

## 報告形式

最終報告に含めよ: (1) 実装した PLAN 項目の対応表（項目番号→commit）、(2) 完了条件 1〜5 の実測値
（テスト総数・各判定表の実 ID 数・grep ゲートの走査実数）、(3) フルスイートの最終出力の要約（Ran N tests, OK）、
(4) 実装しなかった／できなかった項目とその理由、(5) 変更ファイル一覧。

以下は行動規範。全て命令。

- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
