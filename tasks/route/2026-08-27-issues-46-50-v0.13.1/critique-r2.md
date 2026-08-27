あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

PLAN.md を rev.2 に改訂した（`tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`）。前回指摘（R1、14 件）への対応を番号対応で自己申告する。
対応済み事項の再指摘ではなく、rev.2 で新たに生じた矛盾・取りこぼし・判別不能な DoD を指摘せよ。

# 前回指摘との対応（自己申告）

1. （high）#47 の「REFUSED」断定 → **採用**。§0-6／§6 (1)／§9: 「tree-digest 拒否 → seal-run exit 2 → Phase 3 冒頭で監査停止、verdict なし」に統一。REFUSED とは書かない。
2. （high）example.json の `auditScope` → **採用**。§0-7／§6 (15)(23f): JSON 本体に `auditScope` を入れず `_note` のみ。契約テスト (f) は `auditScope` 不在を assert。
3. （high）handoff 試験の本体固定値 → **採用**。§2／§6 (25)／§11: `:424` refspec・`:436/:457` 件数・`:442/:449` Issue 番号を定数 `TAG`/`ISSUES` 由来に書き換える変更を明示的に許可。
4. （high）fix-scope の差分検査 → **採用**。§6 (16)／§8: `git diff --numstat` が `1 0` かつ追加行 `#` 始まり、`git diff --name-only -- skills/audit/scripts` が fix-scope.py のみ。
5. （medium）#49-1 の evidence 不正条件 (c) → **採用**。§6 (7) に (c) を追加、参照を `decide-verdict.py:786-795` に訂正。
6. （medium）ja refresh 行の更新先未検査 → **採用**。§6 (22)／(23g): 契約テスト (g) が en/ja の refresh 段落を複数行結合し、旧版集合と更新先 `0.13.1`（plugin.json と一致）を検査。
7. （medium）DoD の判別不能 → **採用**。(3) は Phase 5 節を切り出して判定、(c) は付録フェンス内限定・完全一致、(f) は新キー必須、(8) は契約テスト (i) で集合完全一致。
8. （medium）en/ja パリティの見出し生カウント → **採用**。§6 (17)／(23h): コードフェンス外の見出しレベル列・§5 キー列・付録 path 列の一致を契約テストで検査。
9. （medium）#48-6 の `bin` 注記範囲 → **採用**。§0-3: config-schema.md の詳細節（:216-220、:260-270）も対象に追加。
10. （medium）#50-5 の ADOPTION en/ja `docGlobs` 行 → **採用**。§0-2／§6 (16)。
11. （low）新 handoff の `0.13.0` 残存 → **採用**。§6 (24)／§8: `grep -c '0\.13\.0'` が 0。
12. （medium）`git add -f` の単位と commit 順 → **採用**。§0-11／§6 (27)／§12: 新 script は S2 テスト再照準と同一 commit にファイル名明示で追跡、記録は最後にファイル列挙（`*-session.log` 除外）。
13. （low）参照誤り → **採用**。§0-6（`.claude/worktrees/*` は拒否される旨を明記し worker に文書へ反映させる）、§2（`:786-798`）。
14. （low）契約テスト (e) → **採用**。(e) を落とし、(g)(h)(i) を追加して計 8 本（§6 (23)、N ≥ 495）。

# 今回の観点

- rev.2 で追加した契約テスト (a)(c)(f)(g)(h)(i) の仕様に、対象 0 件で PASS する穴、または正しい実装で FAIL する過剰仕様がないか
  （例: (c) の basename 集合に `__pycache__`／`docaudit_cache.py`・`docaudit_paths.py` のような helper が付録に載る必要があるか、
  (h) の見出しレベル列は ja の `###` 増減で壊れないか、(i) の集合抽出が `decide-verdict.py` の該当行変更で壊れる脆さは許容範囲か）。
- §0-6 の文書契約（seal exit 2 → Phase 3 冒頭停止）が SKILL.md の実手順と一致するか（seal 失敗時の指示が本当に「停止」か）。
- §0-7 の example.json 追加キー（`regressionRecheck`、`codexReview.required`、`phase3Backend`、`models.light`）が `start-run.py` 等の
  config 検証で拒否されないか、既定値相当で挙動が変わらないか。
- §12 の commit 順・`git add -f` の運用に残る穴（detached checkout でのテスト実行時に参照される path）。
- 落とすべき成果物・縮小すべき検査があれば根拠つきで。

# 出力形式

指摘は番号付き（R2-1, R2-2, …）。各指摘に重大度・根拠（file:line または実行結果）・推奨 1 つ。
新しい実質的な指摘が無ければ「収束（実装開始可）」と明記し、残るのが worker 指示で吸収できる細部のみならその旨を列挙して締める。
