あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

# 対象

`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（docaudit v0.13.0 — GitHub Issues #39〜#44 の一括対応計画）。
このリポジトリ（Claude Code プラグイン docaudit）の現行コードを読み取り専用で参照しながら、計画の欠陥を指摘せよ。

Issue 本文は `gh issue view 39` 〜 `gh issue view 44` で読める（読めなければ PLAN §1/§2 の要約を前提にする）。
#44 の参照実装（`~/Projects/dir-framework/.claude/audit-scope.json` と `scripts/resolve-audit-scope.py`）は
読み取り可能なら参照してよい（書き込み禁止）。

# 特に検分してほしい点

1. **partition 不変条件**: `start-run.py:171-174` / `decide-verdict.py:724-725` は impacted == dispatch ∪ cached を
   強制する。PLAN §10 #39 は再検証文書を resolve-impact.py 段で impacted に入れる設計だが、`impact-supplement.py`
   （graphify/semantic 補完・cap 順序）や `plan-dispatch.py` の cache 判定、sealed manifest、`codex-dispatch.py` の
   provenance 読み取りと矛盾しないか。
2. **#42 の REFUSED 採用**: `codexReview.required:true` で codex 不実行を REFUSED にする案は、REFUSED の既存意味論
   （整合性侵害・anchor 非前進・history 非更新）と衝突しないか。NEEDS_FIX の方が正しいか。full mode との相互作用。
   phase4 evidence に `codexReview` を足すことが `write-evidence.py` / sha 照合 / `findings_fail()` の型検査と衝突しないか。
3. **glob 変換の等価検査**（§9）: fnmatch と docaudit `glob_to_regex` の意味論差（`*`/`**`/`?`/`[`/`**/*`/先頭
   `./`/大文字小文字/`os.sep`）を tracked ファイル集合での等価検査で本当に fail-closed にできるか。将来追加される
   ファイルで初めて食い違う規則を見逃す構造ではないか。
4. **`--write` が doc-audit.json を書く副作用**: config 変更検出（次回 exit 6・`--accept-config`）、`auditScope`
   キー追加が既存 config validator / 契約テストに与える影響、原子書き込みと `.claude/` 保護規則の整合。
5. **#40 既定値**: `saturationWarnRatio` 0.5 / docCorpus ≥ 10 / `excludeDocPathTokens` 既定 false の妥当性。
   `regressionRecheck.enabled` 既定 true は全採用者の impacted 集合を変える — 互換性上の妥当性。
6. **#43 の list 継続段落規則**: 簡易規則が別の過小マスク（本当のインデントコードを検査対象にしてしまう
   → 偽 FAIL）を生まないか。`_LINK_RE` の改行保持置換で `_INLINE_CODE_RE`/`_URL_RE` の順序依存はないか。
7. **テストの判別可能性**: §6 の各 DoD が「正しい実装でも誤った実装でも通る」検査になっていないか。
   対象 0 件で合格し続ける検査が残っていないか。
8. **スコープと費用対効果**: 落とす・縮小すべき成果物（例: Phase 5 status 行追加、init `--import-audit-scope`
   フラグ、handoff テストの再作成）。逆に欠けている成果物（例: `docs/PROMPTS*.md`、`skills/init/SKILL.md` の
   argument-hint、`agents/*-light.md`）。
9. **版・リリース**: 0.13.0 の妥当性、engine-shas 更新手順、`test_release_handoff.py` の差し替え方針。

# 出力形式

- 指摘は番号つき。各指摘に `[BLOCKER]/[MAJOR]/[MINOR]/[INFO]` と、根拠（ファイル:行 または PLAN の節）と、推奨する
  修正 1 つ。
- 既に PLAN が正しく扱っている点の再説明は不要。
- 最後に「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分した一覧を付ける。
