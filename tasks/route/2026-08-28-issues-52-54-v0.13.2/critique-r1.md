あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ
作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

# 対象
docaudit（Claude Code plugin、このリポジトリ）の次版 v0.13.2 の実装計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md` を批判せよ。
対象 Issue の本文は `tasks/route/2026-08-28-issues-52-54-v0.13.2/issues-52-54.md`。前版の記録は `tasks/route/2026-08-27-issues-46-50-v0.13.1/`（PLAN.md、REVIEW.md）。

# 必ず実物で確認してから指摘すること（文書の記述＝正と思い込まない）
- `skills/audit/scripts/{fix-scope.py,read-manifest.py,seal-run.py,codex-dispatch.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh,decide-verdict.py}`
- `skills/audit/SKILL.md`（Phase 0 の probe 3 段落 :174-215、Phase 3 の seal/read-manifest 手順 :363-373、run 解放 :66-70、Phase-5 状態行 :678-694）
- `skills/init/SKILL.md:147-163`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`
- テスト: `tests/test_{graphify,cocoindex,codegraph}_probe.py`、`tests/test_read_manifest.py`、`tests/test_v013_contracts.py`（test_i/test_j）、
  `tests/test_v0131_docs_contracts.py`（test_g）、`tests/test_scaffold.py`、`tests/test_release_handoff.py`、`tests/test_import_audit_scope.py:657-684`、
  `tests/test_wp12_contracts.py`（fix-scope）
- cocoindex 実機ソース（読み取り可）: `~/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py`（:80-128, :297-321, :636-646）、
  `settings.py:333-345`。PLAN §0-5 の原因分析はこれに基づく。

# 特に検分してほしい点
1. §0-4 判定表（キー不在／config 不正／非 object → `not-configured`、`{}` → 有効）の互換性影響。既存利用者の config で壊れるものはあるか。
   3 seam に限定し `indexing`/`contextMode`/`webExtract`/`codexReview` を据え置く判別基準は妥当か。
2. §0-5 の `.gitignore` ガード: 「復元」と「報告のみ」のどちらが正しいか、根拠つきで立場を示せ。復元の競合・失敗時の扱い、`.gitignore` が
   symlink の場合、`git` 管理外 repo の場合。`settings.yml` マーカーだけで十分で、ガードは過剰か。
3. §0-3 `read-manifest.py` の sealed 検査が既存呼び出し元（SKILL.md:372、codex-dispatch.py）と Phase 2 raw parse を壊さないか。
   SKILL.md の停止分岐の文言が、既存の exit 5 分岐・run 解放規約（:66-70）・codex backend の fail-closed 記述と矛盾しないか。
4. §0-2 `docGlobs` 既定の変更で、`fix-scope.py` 経由の pre-flight fix が新たに許可する path の安全性（組込み deny と `protectedGlobs` で十分か）。
5. Phase-5 状態行の `not-configured` 独立枝（畳まない案）の是非。
6. 版バンプ・契約テストの取りこぼし（test_i/test_j/test_g/test_scaffold/test_release_handoff の v0.13.1 固有値、engine-shas の max semver）。
7. DoD の各項目が「正しい実装でも誤った実装でも通る検査」になっていないか。対象 0 件で合格し続ける検査はないか。
8. §0-12（外部 repo 結合テストの導出値化）の妥当性。
9. 計画から落とす・縮小すべき成果物はあるか（費用対効果）。

# 出力
指摘は番号つきで、各指摘に (a) 根拠となるファイル・行・実測、(b) 深刻度（high/medium/low）、(c) 推奨 1 つ。最後に「計画自体の欠陥（PLAN を直してから実装）」と
「worker 指示で吸収できる細部」に区分して総括せよ。
