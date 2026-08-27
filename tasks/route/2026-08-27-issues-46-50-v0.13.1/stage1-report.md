S1 の文書・references・example 修正は完了し、既存 487 テストと S1 の全検証項目が期待どおりの結果になった。

## Issue 所見別の実装結果

- #46-1 — 変更 `README.md:89,94`。実装側の根拠 `skills/init/SKILL.md:4`。DoD (6)。
- #46-2 — 変更 `README.md:25`。実装側の根拠 `skills/audit/scripts/start-run.py:30-32`、`skills/audit/scripts/decide-verdict.py:713-718`。DoD (6)。
- #46-3 — 変更 `README.md:67-69`。実装側の根拠 `skills/audit/SKILL.md:664-705` および Counts の実在キーを作る `skills/audit/scripts/decide-verdict.py:957-960`。DoD (6)。
- #46-4 — 変更 `README.md:67-69`（代表例から `/code-review ⚠` を除外）。実装側の根拠 `skills/audit/SKILL.md:673-675`。DoD (6)。
- #46-5 — 変更 `README.md:75`。実装側の根拠 `docs/ADOPTION.md:425,486`（互換性影響は §8 配下）および `PLAN.md:16-18` の確定裁定。DoD (6)。
- #46-6 — 変更 `README.md:38`。実装側の根拠 `docs/ADOPTION.md:205-208`。DoD (6)。
- #46-7 — 変更 `docs/PROMPTS.md:228-241`、`docs/PROMPTS.ja.md:228-241`。実装側の根拠 `skills/init/SKILL.md:4`。DoD (6)。
- #47-1 — 変更 `skills/audit/references/config-schema.md:29`、`docs/ADOPTION.md:332`、`docs/ADOPTION.ja.md:313`。実装側の根拠 `skills/audit/scripts/tree-digest.py:20-28`、`skills/audit/scripts/seal-run.py:63-70`。DoD (1)。
- #47-2 — 変更は #47-1 と同じ 3 行で `.claude/worktrees` を追加。実装側の根拠 `skills/audit/scripts/tree-digest.py:25-27`、`skills/audit/scripts/start-run.py:18-21`。DoD (1)。
- #48-1 — 変更 `skills/audit/SKILL.md:246`。実装側の根拠 `skills/audit/scripts/generic-layers.py:582`。DoD (2)。
- #48-2 — 変更 `skills/audit/SKILL.md:683-687`。実装側の根拠 `skills/audit/scripts/graphify-probe.sh:81`。DoD (3)。
- #48-3 — 変更 `skills/audit/SKILL.md:153`。実装側の根拠 `skills/audit/scripts/codex-review-plan.py:18`。DoD (4)。
- #48-4 — 変更 `skills/audit/SKILL.md:515-518`。実装側の根拠 `skills/audit/scripts/codex-review-plan.py:35-40`。DoD (5)。
- #48-5 — 変更 `skills/audit/SKILL.md:614-618`。実装側の根拠 `skills/audit/scripts/decide-verdict.py:961-963,975-979,1028`。DoD (5)。
- #48-6 — 変更 `skills/audit/SKILL.md:140-142,178-180`、`skills/audit/references/config-schema.md:35,37,216-218,260-263`。実装側の根拠 `skills/audit/references/workflow-template.js:122-139`。DoD (5)。
- #48-7 — 変更 `skills/audit/SKILL.md:241-247`（未使用の束縛文を削除）。実装側の根拠は repo 全体の `HARNESS_ACTIVE` 参照が 0 件であること。DoD (5)。
- #48-8 — 変更 `skills/audit/SKILL.md:130-131`。実装側の根拠 `skills/audit/SKILL.md:121-127` の中央分岐。DoD (5)。
- #48-9 — 変更 `skills/audit/SKILL.md:666`。実装側の根拠 `skills/audit/SKILL.md:489-500` の実在 step 3。DoD (5)。
- #49-1 — 変更 `docs/ADOPTION.md:136-138`、`docs/ADOPTION.ja.md:120-122`、`skills/audit/references/config-schema.md:250-253`。実装側の根拠 `skills/audit/scripts/decide-verdict.py:713-718,786-798`。DoD (7)。
- #49-2 — 変更 `docs/ADOPTION.md:467-479`、`docs/ADOPTION.ja.md:439-451`。実装側の根拠 `skills/audit/scripts/decide-verdict.py:30,270-279`。DoD (8)。
- #49-3 — 変更 `docs/ADOPTION.md:631-661`、`docs/ADOPTION.ja.md:593-623`。実装側の根拠 `skills/audit/scripts/` 36 ファイルと `skills/audit/references/` 6 ファイルの実体一覧。DoD (9)。
- #49-4 — 変更 `docs/ADOPTION.md:304,322-325`、`docs/ADOPTION.ja.md:285,303-306`。実装側の根拠 `skills/audit/references/config-schema.md:12-13,22`。DoD (10)。
- #49-5 — 変更 `docs/ADOPTION.ja.md:95,328`。実装側の根拠は同文書の既存「である体」と PLAN §9 の確定仕様。DoD (11)。
- #50-1 — 変更 `skills/audit/references/default-heuristics.md:15-16`。実装側の根拠 `skills/audit/scripts/resolve-impact.py:255-257`。DoD (12)。
- #50-2 — 変更 `skills/audit/references/config-schema.md:37-39`。実装側の根拠 `skills/audit/scripts/codegraph-probe.sh:36-37`、`skills/audit/scripts/graphify-probe.sh:39-40`、`skills/audit/scripts/cocoindex-probe.sh:40-41`。DoD (13)。
- #50-3 — 変更 `skills/audit/references/config-schema.md:28`、`docs/ADOPTION.md:330`、`docs/ADOPTION.ja.md:311`。実装側の根拠 `skills/audit/scripts/classify-run.py:33`。DoD (14)。
- #50-4 — 変更 `docs/examples/doc-audit.example.json:2,9-12`。実装側の根拠 `skills/audit/scripts/start-run.py:141-160`、`skills/audit/scripts/classify-run.py:33-37`。DoD (15)。
- #50-5 — 変更 `skills/audit/scripts/fix-scope.py:87`、`skills/audit/references/config-schema.md:10`、`docs/ADOPTION.md:310`、`docs/ADOPTION.ja.md:291`。実装側の根拠 `skills/audit/scripts/fix-scope.py:88`。DoD (16)。

## 差し戻し 1 の反映と学び

- severity 表の en/ja 両方で、8 severity の第 1 列をコードスパンへ修正した。catch-all の第 1 列は非コードスパン、第 2 列先頭の固定トークンは維持した。
- README の互換性リンクを ADOPTION §8 へ修正し、Counts を `decide-verdict.py:957-960` に実在する `impacted`、`dispatch`、`verdictFlipsUnchangedContent`、`verdictFlipsUnchangedContentSameChangeSet` だけの JSON 例へ修正した。
- PROMPTS.ja.md §9 の `<task>`、`<constraints>`、実行行を既存節と同じ「〜してください」へ修正した。
- 再発防止ルール: 表の機械契約は表示上の意味だけでなくコードスパンを含む字句形まで確認する。節参照は見出しの実位置を確認する。出力例は生成処理と構築元のキーを直接確認する。日本語の文体は文書単位で既存節に合わせ、ADOPTION の規則を PROMPTS へ横展開しない。

## 検証結果

### S1 該当の §8 コマンド

`python3 -m unittest discover -s tests -t .`

```text
----------------------------------------------------------------------
Ran 487 tests in 142.192s

OK
exit code: 0
```

途中で既存 `tests/test_generic_layers.py` の未 close ファイルに関する `ResourceWarning` が複数表示されたが、失敗・skip はなく、最終結果は上記のとおりである。

`python3 -c 'import json;json.load(open("docs/examples/doc-audit.example.json"))'`

```text
(stdout/stderr なし)
exit code: 0
```

`grep -c '\.claude/state/\*\*' skills/audit/references/config-schema.md docs/ADOPTION.md docs/ADOPTION.ja.md`

```text
skills/audit/references/config-schema.md:0
docs/ADOPTION.md:0
docs/ADOPTION.ja.md:0
exit code: 1
```

表示値は全ファイル 0 である。終了状態 1 は `grep` が一致なしを表す通常動作である。

`grep -n 'generic-layers.py' skills/audit/SKILL.md | grep -vc -- '--config'`

```text
0
exit code: 1
```

表示値 0 は `--config` 欠落行が 0 件であることを示す。終了状態 1 は末段 `grep` の一致なしによる。

`grep -cE '(ます|です)(。|$|が)' docs/ADOPTION.ja.md`

```text
0
exit code: 1
```

表示値 0 は対象表現が 0 件であることを示す。終了状態 1 は `grep` の一致なしによる。

`grep -c -- '--import-audit-scope' README.md docs/PROMPTS.md docs/PROMPTS.ja.md`

```text
README.md:2
docs/PROMPTS.md:1
docs/PROMPTS.ja.md:1
exit code: 0
```

`git diff --numstat -- skills/audit/scripts/fix-scope.py`

```text
1	0	skills/audit/scripts/fix-scope.py
exit code: 0
```

`git diff --name-only -- skills/audit/scripts`

```text
skills/audit/scripts/fix-scope.py
exit code: 0
```

### 補助検証

`python3 -m unittest tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff -v`

```text
Ran 48 tests in 12.196s

OK
exit code: 0
```

`git diff --stat -- skills/audit/scripts`

```text
 skills/audit/scripts/fix-scope.py | 1 +
 1 file changed, 1 insertion(+)
exit code: 0
```

`git diff --check`

```text
(stdout/stderr なし)
exit code: 0
```

追加の構造検査では、コードブロック外の ADOPTION 見出しレベル列が en/ja とも 24 要素で一致し、PROMPTS は en/ja とも `#` 1 個＋`##` 9 個で一致した。§5 のキー列は 26/26 で一致し、付録フェンス内は実体 42 path と en/ja の両方で完全一致した。3 文書の `digestExclude` 固定マーカーは各 1 回・同一物理行で、マーカー以降のコードスパンは指定 6 値だけであり、全値が `tree-digest.normalize()` を通過した。severity 表は各 1 個、9 データ行で、8 severity の第 1 列コードスパンから第 2 列先頭コードスパンへの写像が en/ja とも PLAN の期待集合に完全一致し、catch-all は非コードスパンであった。README の Counts JSON は実在キーだけで構成され、`cached` を含まないことも確認した。example の追加値は PLAN の既定値と完全一致した。

S2 専用の新規契約テスト、版 stamp の scaffold 検査、handoff script 検査は、S1 では対象ファイルが存在または更新していないため実行していない。

## 報告のみ（許可外変更候補）

- `fix-scope.py` 以外の各 runtime と `docGlobs` 省略時既定を揃える案は挙動変更になるため実施していない。別 Issue 候補である。
- `seal-run.py` の exit 5 以外の非 0 に明示的な停止分岐がなく、その後の挙動が backend で非対称な点は、実行手順・状態変更を伴うため実施していない。別 Issue 候補である。

## 未検証・未対応

S1 の未検証・未対応はない。上記 S2 専用項目のみ、この Stage の対象外として未実行である。

## 作業ツリー

### `git status --short`

```text
 M README.md
 M docs/ADOPTION.ja.md
 M docs/ADOPTION.md
 M docs/PROMPTS.ja.md
 M docs/PROMPTS.md
 M docs/examples/doc-audit.example.json
 M skills/audit/SKILL.md
 M skills/audit/references/config-schema.md
 M skills/audit/references/default-heuristics.md
 M skills/audit/scripts/fix-scope.py
?? .claude/
```

`.claude/` は作業開始前から存在する未追跡項目であり、変更していない。`stage1-report.md` は route 記録の ignore 規則によりこの表示には出ないが、指定 path に作成済みである。

### `git diff --stat`

```text
 README.md                                     | 23 ++++++--------
 docs/ADOPTION.ja.md                           | 43 ++++++++++++++++++++++-----
 docs/ADOPTION.md                              | 37 +++++++++++++++++++----
 docs/PROMPTS.ja.md                            | 20 +++++++++++++
 docs/PROMPTS.md                               | 20 +++++++++++++
 docs/examples/doc-audit.example.json          |  7 +++--
 skills/audit/SKILL.md                         | 36 ++++++++++++++--------
 skills/audit/references/config-schema.md      | 26 +++++++++-------
 skills/audit/references/default-heuristics.md |  4 +--
 skills/audit/scripts/fix-scope.py             |  1 +
 10 files changed, 162 insertions(+), 55 deletions(-)
```
