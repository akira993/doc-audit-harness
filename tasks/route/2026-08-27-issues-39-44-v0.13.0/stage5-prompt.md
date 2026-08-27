# S5 実装依頼 — #41 docs／ADOPTION・PROMPTS・config-schema 最終整合／release-handoff.sh（単段縮約）＋試験（PLAN rev.8 §4 S5、§10 #41、§12）

あなたは実装者（worker）。boss（Fable）が計画とレビューを担当する。計画の正本は
`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（rev.8、Opus 承認済み）。本依頼の範囲は **S5 のみ**（S1〜S4b は完了・コミット済み）。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。

包括承認（boss）: 読み取り・テスト実行・許可パス内の編集は事前承認済み。個別確認を求めずに完了まで進めよ。**git 操作
（checkout/add/commit）は sandbox の制約で失敗するため行わない — boss が行う。** 許可パス外・`git push`・`rm -rf`・パッケージ
導入・`gh` の書き込み系コマンド（release/issue/pr）は禁止。

## 0. 事前準備
1. ブランチ `feat/v0.13.0-issues-39-44` で `git log --oneline main..HEAD` を確認。`git status --short` が空（`.claude/` を除く）。
2. フルスイートを実行し着手前の件数を記録。
3. 読む: `tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh`（228 行、二段: v0.11.0 遡及 + v0.12.0）、
   `tests/test_release_handoff.py`（435 行、`HANDOFF` 定数 `:14-16`、`DOCAUDIT_SKILLS_DIR` `:268`）、`docs/ADOPTION.md`／`.ja.md`、
   `docs/PROMPTS.md`／`.ja.md`、`skills/audit/references/config-schema.md`、`skills/audit/SKILL.md` Phase 4（S4b で 3 観点追加済み）。

## 1. #41 — docs
- `docs/ADOPTION.md` と `docs/ADOPTION.ja.md`（対訳を揃える）に「Phase 3 の構造的盲点」節を追加: (1) 複数文書間の矛盾
  （例: ガイドが `.dev.vars` と書き、`.env.example`・src が `.env.local` と言う）、(2) docGlobs 外（src コメント・dotfile・生成物
  ヘッダ）の `X.md §N` 型参照、(3) 手順の実行可能性（前提となる dev server 等）。文言は「**Phase 3 単独ではこれらを保証しない**。
  Phase 4 の code/security review・codex review（incremental、または full＋`codexReview.required`）・gate の sibling scan が横断的な
  補完層」— 「唯一」という断言はしない。
- 同節に S4b で追加した codex review プロンプトの 3 観点への参照を 1 文。
- `docs/PROMPTS.md`／`.ja.md`: Phase 4 のプロンプト複写があれば 3 観点を同期（S4b の SKILL 文言と一致させる）。

## 2. ADOPTION・PROMPTS・config-schema の最終整合（S2〜S4b の変更を docs に反映しきる）
- ADOPTION en/ja: `regressionRecheck`（opt-in、`counts.regression`、provenance `regression` の意味）／飽和 WARN と
  `heuristics.saturationWarnRatio`・`excludeDocPathTokens`／`counts.verdictFlipsUnchangedContent`・`…SameChangeSet` の読み方（「文書内容が
  不変でもコード側の変更で verdict が正当に変わり得る。同一 change set の件数 M が純粋なブレの下限」）／「単発検証の限界・欠陥クラス
  単位で横断掃除」／`codexReview.required`（REFUSED、baseline 確立後に有効化、probe の保証範囲、full＋required は review 実行）／
  audit-scope（正本・生成物・drift 停止・復旧・`--accept-config` 不要・run 中は lock）／**互換性影響一覧**（PLAN §10 末尾を利用者
  向けに: gate の REFUSED 条件追加、manifest `provenance`/`auditScopeSha`・dispatch `impactSha`、版跨ぎの in-flight run は
  `--break-lock`、Phase 3/4 の read-manifest 経由、codex-dispatch `--evidence`、Phase 5 codex 行 4 状態、check-docs 3 修正）。
  S2/S3/S4b が既に書いた段落は重複させず統合する。
- `config-schema.md`: 5 キー（`auditScope`、`heuristics.saturationWarnRatio`、`heuristics.excludeDocPathTokens`、
  `regressionRecheck.enabled`、`codexReview.required`）と impactMap 項目 `source` が表にあること、`## Codex review` 節に
  `probeCommands` と 4 状態があることを確認し、欠けていれば補う。

## 3. `release-handoff.sh`（単段・v0.12.0 の縮約）— `tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh`
前回スクリプトをコピーし、次を変更（構造・関数・fail-closed 検査はできる限り保つ）:
- v0.11.0 遡及段（`TAG_OLD` とその tag/Release/検証）を**削除**。`TAG_NEW="docaudit--v0.13.0"`、Release title は**完全一致**で
  `docaudit v0.13.0 — audit-scope import, regression recheck, strict codex review`、body 必須要素: 承認 SHA（完全）・`#39`〜`#44`・
  `codexReview.required`（baseline 確立後に有効化）・`--break-lock`（版跨ぎ in-flight run）。Issue close は `{39,40,41,42,43,44}` を
  「Shipped in docaudit v0.13.0 (PR #<n>, tag docaudit--v0.13.0)」で冪等 close。
- 順序: 引数検証（SHA 40 hex・PR 数値）→ fetch → branch==main・HEAD==origin/main==SHA・tracked clean → **同期先 preflight**
  （`DOCAUDIT_SKILLS_DIR` override は維持。既定 `~/.claude/skills/docaudit`。正規化した同期先が `DOCAUDIT_SKILLS_ROOT`（既定
  `~/.claude/skills`）配下・非 symlink・書込可能。違反は tag 前に停止）→ 対象 SHA で unittest → tag（既存は SHA 一致検証）→
  **単一 refspec push** `git push origin refs/tags/docaudit--v0.13.0:refs/tags/docaudit--v0.13.0` → Release（既存なら非 draft・
  非 prerelease・title 完全一致・body 必須要素を検証、違反は停止）→ Issue close → 同期確認（`y` のみ続行、EOF は中止）→ 同期
  （archive 方式・hide/protect filter・`rsync --delete`・diff 検証・`generic-layers.py --help` smoke は前回のまま）。
- Release notes は上記必須要素＋PLAN §10「互換性影響一覧」の要約を含める。

## 4. `tests/test_release_handoff.py`（縮約＋追加 4 点）
- `HANDOFF` を新スクリプトへ向ける。v0.11.0 遡及固有の分岐（`OLD_SHA`、`docaudit--v0.11.0`）を削除し、`docaudit--v0.12.0` を
  `docaudit--v0.13.0`、`0.12.0` を `0.13.0` に置換（本ファイルに `0.12.0` を残さない — 契約テスト (j) の許容リスト外）。既存の
  安全条件（SHA 引数・fetch・tag 不一致・再開・symlink・完全成功・不正 Release）は単段版として維持。
- 追加 4 点: (1) 全成功・再開ケースで tag → approved SHA、Release の tagName/title（完全一致）/body 必須要素を assert、
  (2) ローカルに無関係 tag（例 `scratch-tag`）を置いても push の refspec が対象 tag のみ（偽 git が受けた引数で assert）、
  (3) Issue close の対象集合が `{39,40,41,42,43,44}` で各 1 回（偽 gh の呼出し記録で assert）、(4) 同期先 preflight 失敗（symlink／
  `DOCAUDIT_SKILLS_ROOT` 外）で tag/Release/close/rsync の呼出しが 0 回。
- 偽 `git`/`gh`/`rsync` の PATH shim は前回方式を踏襲。

## 5. 契約テスト `tests/test_v013_contracts.py`
- (j) の `skipTest` を外して有効化（出荷物 path 集合内の `0.12.0` 残存が許容リストのみ）。(h) の残りがあれば有効化。
- (g)/(h) 等、S2〜S4b で有効化済みの項目がすべて green であることを確認。skip が残っていないこと（`skipped=0`）。

## 6. `pr-body.md`
`tasks/route/2026-08-27-issues-39-44-v0.13.0/pr-body.md` を作成: タイトル `docaudit v0.13.0 — Issues #39〜#44`、各 Issue の対応
要約（1〜3 行）、互換性影響一覧、テスト件数（前後）、handoff の使い方（`release-handoff.sh <merge-sha> <pr>`）、末尾に
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`。

## 7. 完了条件
- フルスイート全 green・**skip 0**。件数を報告。`git ls-files | grep -v '^tasks/' | xargs grep -n '0\.12\.0'` が許容リストのみ。
- handoff 試験の追加 4 点と縮約後の既存分岐が対象スクリプトを経由すること（`HANDOFF` が新スクリプトを指すことを含む）。

## 8. 変更範囲
**許可**: `docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`docs/PROMPTS.md`、`docs/PROMPTS.ja.md`、`skills/audit/references/config-schema.md`、
`skills/audit/references/default-heuristics.md`、`tests/test_release_handoff.py`、`tests/test_v013_contracts.py`、
`tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh`（新規）、同 `pr-body.md`（新規）。
**禁止**: `skills/audit/scripts/`・`skills/audit/SKILL.md`・`skills/init/SKILL.md`・`agents/`（S2〜S4b で確定済み。矛盾を見つけたら
修正せず報告）、前回タスクフォルダ `tasks/route/2026-08-25-*/`（読むだけ）、`.gitignore`、`.claude/`。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 9. 検証コマンド一式
```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_release_handoff tests.test_v013_contracts -v
git ls-files | grep -v '^tasks/' | xargs grep -n '0\.12\.0'
```

## 10. 報告
結論先行・完全な文で。各主張はツール結果と突合し、未検証は未検証と明言。テスト失敗は出力ごと報告。末尾に「変更ファイル一覧」
「テスト件数（前後、skip 数）」「許可外変更の必要有無」「S2〜S4b の成果物と docs の矛盾（あれば）」。コミットはしない。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
