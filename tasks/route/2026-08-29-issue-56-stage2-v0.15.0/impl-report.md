PLAN §5の項目1〜18はすべて実装され、629件の全検査に成功しました。ただし `.git` が読み取り専用のためコミットだけ作成できず、完了条件5の正式な `main...HEAD` 検査は未達です。

## 項目→コミット対応

コミット時に `.git/index.lock` を作成できず、ハッシュはありません。

| PLAN項目 | 予定コミット | 状態 |
|---|---|---|
| 1〜4 | `feat(audit): key gate ax and codex integrations` | 実装済み・未commit |
| 5〜8 | `docs(audit): document key-gated optional integrations` | 実装済み・未commit |
| 9〜10 | `chore(release): prepare docaudit v0.15.0` | 実装済み・未commit |
| 11〜16 | `test(audit): enforce v0.15 key-gate contracts` | 実装済み・未commit |
| 17 | `chore(release): add v0.15 release handoff` | 実装済み・未commit |
| 18 | `test(release): retarget v0.15 handoff contracts` | 実装済み・未commit |

エラーは以下です。

```text
fatal: Unable to create '.git/index.lock': Operation not permitted
```

## 完了条件の実測値

1. 全検査

   - `Ran 629 tests in 194.007s`
   - `OK`
   - skip 0
   - 基準609件から20件増
   - 内訳: probe-record +5、planner +3、v0.15契約 +7、release-handoff +5

2. 判定表

   - ax probe: 27 ID
   - codex probe: 27 ID
   - 呼出回数固定: 6必須分岐以上
   - probe-record: 12 ID（受理2、mutation拒否7、未知項目拒否1、上書き正負2）
   - codex-review-plan: 既存16行＋追加7 ID
   - ASCII・1行出力: 2 probe
   - resume再probe: 2本
   - release-handoff: 既存18 method＋追加5＝23 method

3. 残骸検査

   - 101ファイル
   - 2,789走査単位
   - 検出0
   - 代表3パス、保持テキスト5パスの負検査とも成功

4. 版整合

   - release surface: `{"0.15.0"}`
   - scaffold: 20件成功
   - engine SHA:
     - check-docs: `a5c1efbcbe1bdbece74cb188228fd676d4c6c0446a42f27d6514afe40c5f1ab8`
     - doc-lint: `ebc5944f8739b4b0ff9740f442fe05225c6df300f6fcb471ba20120f30366727`
     - engine: `fbef5b46ff06271e740424eb6fc1c73171c6e461e057c8d4d70690dabb8c23a3`

5. 範囲検査

   - 実差分24ファイルは全て許可一覧内
   - 禁止された `test_v014_contracts.py:225` とschema 33〜34行は変更前後のSHA一致
   - 既存の未追跡 `.claude/` は未変更
   - `git diff --name-only main...HEAD` はコミット不能により空出力。このため正式な完了条件5は未達

指定された関連検査も `Ran 127 tests in 36.629s, OK`、残骸検査単独も `Ran 7 tests, OK` でした。

途中でprobe-recordの検証順序による1件の失敗がありましたが修正後に全検査成功しています。全検査では既存の許可外ファイル `tests/test_generic_layers.py` 由来の `ResourceWarning` も出ましたが、検査失敗ではないため変更していません。

未実装のPLAN項目はありません。作業記録は [REVIEW.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/REVIEW.md) に記録済みです。

変更ファイルは以下の24件です。

- 実行部分: `ax-probe.sh`、`codex-probe.sh`、`probe-record.py`、`codex-review-plan.py`
- 文書・版情報: `skills/audit/SKILL.md`、`config-schema.md`、`skills/init/SKILL.md`、`ADOPTION.md`、`ADOPTION.ja.md`、`README.md`、`plugin.json`、`engine-shas.json`
- 検査: `test_ax_probe.py`、`test_codex_probe.py`、`test_probe_record.py`、`test_codex_review_plan.py`、`test_v015_contracts.py`、`test_release_handoff.py`、`test_v014_contracts.py`、`test_v0132_contracts.py`、`test_v013_contracts.py`、`test_scaffold.py`
- 作業記録・出荷手順: `REVIEW.md`、`release-handoff.sh`