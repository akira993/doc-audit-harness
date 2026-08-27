あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。
作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

# 対象

`tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`（docaudit v0.13.1 — Issues #46〜#50 の docs-only 整合パッチ計画）。
Issue 本文は `tasks/route/2026-08-27-issues-46-50-v0.13.1/issues-46-50.md`。リポジトリは HEAD `3a6068b`（v0.13.0 出荷直後）、作業ツリー clean。

# レビューの前提（boss が確定済み。再審議不要、ただし前提そのものが誤りなら指摘せよ）

- 版は 0.13.1、runtime 挙動は変えない（docs-only）。`fix-scope.py` はコメント 1 行のみ。
- リリースは PR → merge commit → `release-handoff.sh`（前版 `tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh` の派生）。
- テストは `python3 -m unittest discover -s tests -t .`（現状 487 件 OK）。lint／型チェックは存在しない。

# 特に検証してほしい点（実物のファイル・行を読んで根拠を付けること）

1. **Issue の所見が現 HEAD で本当に成立するか**（file:line が動いていないか。特に #47 の `tree-digest.py` の拒否条件と許可プレフィックス、
   #48 の `codex-review-plan.py --available` の choices、#49 の `decide-verdict.py` の REFUSED 条件、#50 の `resolve-impact.py` の content hash 条件）。
   所見が誤りなら PLAN の対応 DoD は無効なので指摘せよ。
2. **版バンプの結合漏れ**: `tests/test_v013_contracts.py` test_i / test_j、`tests/test_scaffold.py`、`scaffold.py` の engine-shas 検査、
   `engine-shas.json`。PLAN §6 (20)〜(22) と §11 で拾えていない「0.13.0 → 0.13.1 で赤になるテスト・スクリプト」が他にないか
   （`grep -rn '0\.13\.0' --include='*.py' --include='*.json' --include='*.md' --include='*.sh'` で全数確認せよ）。
3. **handoff script の再照準**: `tests/test_release_handoff.py` が定数以外で v0.13.0 固有の文字列・分岐に依存していないか。
   新 script を `tasks/route/...` に置き `git add -f` で追跡する運用（test が script path を固定）の落とし穴。
4. **DoD の判別可能性**: PLAN §6 の各条件が「正しい修正でも誤った修正でも通る」検査になっていないか。契約テスト (a)〜(f) の設計で
   偽陽性（対象 0 件で PASS）になり得るもの。
5. **en/ja パリティ**: ADOPTION の見出し数・表行数・付録の同時更新で漏れやすい箇所。`test_j` の許容リストが ja 側にもあるか。
6. **スコープ**: docs-only と言いつつ runtime を変える提案が紛れていないか。逆に、docs だけ直すと実装との矛盾が残る箇所
   （#50-5 の `fix-scope.py` 既定値、#48-6 の `bin` 上書き）は「文書化で足りる」と言えるか。
7. 費用対効果が低く、落とす・縮小すべき成果物（契約テストの本数、handoff script の再作成、PROMPTS の新節）はあるか。

# 出力形式

- 冒頭にメタ認知の自己申告（1〜2 行）。
- 指摘は番号付き。各指摘に **重大度（high/medium/low）・根拠（file:line または実行結果）・推奨 1 つ**。
- 最後に「PLAN 自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分した要約。
- 指摘が無い観点は「問題なし（確認した根拠）」と明記。
