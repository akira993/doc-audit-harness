あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

# レビュー対象

`tasks/route/2026-08-25-issues-33-34-35/PLAN.md` を読み、計画を批判せよ。
現況調査は `tasks/route/2026-08-25-issues-33-34-35/OUT-investigate.md` にある（file:line 付き）。
対象コードは実ファイルを直接読んで裏取りしてよい（read-only）。

# 背景（GitHub Issue 要約。ネットワーク不可のため転記）

- **#33**: `generic-layers.py` はリンク `[x](path)`（FAIL）と backtick `` `path` ``（WARN）しか見ない。
  bare path（`- docs/logs/x.md — 説明`）は不可視。ファイル移動後の収束に 4 監査サイクルを要した実害。
  提案: bare path 収穫を追加（`looks_like_repo_path` は無変更で再利用）、解決しない具体的ファイルパスは
  構文を問わず FAIL、ディレクトリ形状・glob は WARN 維持。
- **#34**: `docGlobs` が 3 層すべてで共用。`.claude/**`（Claude Code 専用 frontmatter を持つ）や
  `docs/logs/**`（append-only 履歴）が構造的に満たせない層の WARN を永久に出す（ある repo で 143 WARN 中
  131=92% がこのノイズ）。docGlobs から外すと impact pool と --full corpus からも消えるので不可。
  提案: `layerGlobs`（層別 exclude）+ `frontMatterOverrides`（glob 別 frontmatter fields）。additive。
- **#35**: 監査レポート（`docs/logs/doc_audit_*.md`）が docGlobs に一致し corpus に残留、走るたびに
  ノイズ単調増加。report-pattern 除外は compute-baseline.sh / sibling-scan.py には適用済みだが
  `list_doc_files` と resolve-impact.py には未適用。提案: デフォルト除外 + `auditReportsInCorpus` opt-in。

ユーザー合意済みの決定（覆す場合は根拠を示せ）: 対象 #33/#34/#35 のみ／v0.11.0（minor）／
解決しない具体的ファイルパスは FAIL に昇格。

# 特に検証してほしい点

1. bare path 収穫の偽陽性リスク: 日本語散文・コマンド例・URL 断片で `looks_like_repo_path` を通過して
   しまうケースは本当に十分抑えられるか。約物トリムの仕様は妥当か
2. FAIL 昇格の file/dir ヒューリスティック（basename に `.` の有無 + 末尾 `/`）の穴
3. semantic layerGlobs exclude の「発リンクは referenced に残す」仕様で偽 orphan は防げるか。逆に
   exclude された doc しか参照していない index の扱いに矛盾はないか
4. report-pattern 導出ロジックの self-contained 複製（change-set-sha.py と将来乖離するリスク）と、
   `--paths` 明示指定時も除外する仕様の是非（dispatch 済み doc を黙って落とすことにならないか）
5. resolve-impact.py の heuristic/full 除外で、逆に「レポートに書かれた stale 参照を直したい」ユーザーの
   経路を塞がないか
6. engine-shas.json / scaffold.py / consuming repo の check-docs.py 同期契約を壊す点がないか
7. テスト計画の抜け（境界ケース・後方互換の検証）
8. 版 bump 箇所の抜け

# 出力形式

指摘を severity（BLOCKER / MAJOR / MINOR / INFO）付きの番号リストで。各指摘に根拠（file:line または
再現手順）を付ける。最後に「計画承認可否」の立場を明示する。
