S4a の実装は完了し、最終フルスイート 465 件はすべて成功しました（保留 2 件は S4b/S5 対象）。コミットと作業枝への git 操作は行っていません。

主な結果:

- `read-manifest.py` を追加し、manifest を一度だけ読み、同じ bytes で SHA 照合と解析を行うようにしました。
- `start-run.py` で `impactSha`、7 種の provenance、`auditScopeSha` を検査・封印します。
- `decide-verdict.py` に impact/provenance/auditScope の拒否条件と flip 2 集計、指定 warning を追加しました。
- `codex-dispatch.py` は `--evidence` 必須となり、封印済み manifest の provenance だけを使用します。SHA 不一致時は子処理 0 回を確認済みです。
- `check-verdicts.py` は provenance 不一致を診断し、終了コード 0 を維持します。
- `seal-run.py` は manifest 全体を既にハッシュしていたため、変更不要でした。
- `SKILL.md` は Phase 3〜5 の manifest 由来値を `SEALED_MANIFEST` から再取得します。`runClass` も封印後の値へ統一しました。
- EVIDENCE のキー集合と report token 8 種は変更していません。

統合・否定試験:

- regression 文書が resolve → supplement → plan → start → seal → evidence → gate を通り、非 cached dispatch として `CONSISTENT` に到達しました。
- provenance 改変、manifest 改変、`unknown` provenance、audit-scope 改変をそれぞれ指定理由で拒否しました。
- flip は `1/1`、changeSet のみ相違で `1/0`、content 相違で `0/0` を実プロセスで確認しました。
- 実装を一時的に無効化する確認では、manifest 改変検知、impact 改変検知、flip 集計の各試験がそれぞれ失敗しました。直後に復元し、すべて再成功しています。

途中で検出・修正した失敗:

- 既存 fixture に provenance がなく、`start-run: invalid impact provenance: docs/a.md=None` で 1 件失敗しました。新契約どおり `mapped` を追加しました。
- 最初の全体試験で既存の手順書固定文言が欠落し、`test_phase3_codex_backend_is_documented_as_sealed_and_fail_closed` が失敗しました。要求される次の 2 文言を、封印後再取得と矛盾しない説明で復元しました。
  - `Use only sealed manifest.phase3Backend`
  - `Phase-3 backend: <manifest.phase3Backend>`
- 並行編集途中に `test_anchor_change_is_removed_and_refused` が一度 `AssertionError: 3 != 0` となりましたが、単独・対象一式・最終全体試験では再現していません。
- 既存の `ResourceWarning` は着手前・完了後とも出ていますが、試験結果には影響していません。

検証結果:

- 指定対象試験: 164 件成功、2 件保留。
- 最終フルスイート: 465 件成功、2 件保留、124.504 秒。
- `git diff --check`: 成功。
- 一時無効化した行が残っていないことも確認済みです。

### 変更ファイル一覧（`git diff --stat`）

```text
 skills/audit/SKILL.md                  |  92 +++++++++++++---------
 skills/audit/scripts/check-verdicts.py |  11 ++-
 skills/audit/scripts/codex-dispatch.py |  41 ++++++----
 skills/audit/scripts/decide-verdict.py |  88 +++++++++++++++++++++-
 skills/audit/scripts/start-run.py      |  64 +++++++++++++++-
 tests/test_check_verdicts.py           |  19 ++++-
 tests/test_codex_dispatch.py           |  36 ++++++++-
 tests/test_decide_verdict.py           | 134 +++++++++++++++++++++++++++++++++
 tests/test_start_run.py                | 134 ++++++++++++++++++++++++++++++++-
 tests/test_v013_contracts.py           |  73 +++++++++++++++++-
 tests/test_wp12_contracts.py           | 122 ++++++++++++++++++++++++++++++
 11 files changed, 749 insertions(+), 65 deletions(-)
```

未追跡の新規ファイルは stat に含まれません。

- [read-manifest.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/read-manifest.py): 47 行
- [test_read_manifest.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_read_manifest.py): 113 行

着手前から存在する未追跡 `.claude/` は変更対象外として保持しています。

### テスト件数（前後）

- 着手前: 441 件成功、3 件保留。
- 完了後: 465 件成功、2 件保留。
- 増加: 24 件。既存の保留 1 件も有効化しました。

### 許可外変更の必要有無

ありません。変更はすべて許可パス内です。`tasks/`、`docs/`、禁止された各処理、`.claude/` は変更していません。

### §8 (B) の cap 値と理由

`maxImpactedDocs: 3` のままです。rev.8 の正本どおり、候補 6 件から優先順 `mapped ≥ regression ≥ heuristic` により、結果は mapped 2件＋regression 1件＋heuristic 0件となります。regression 1件と heuristic 2件が上限で落ち、`truncated=true` を確認しました。