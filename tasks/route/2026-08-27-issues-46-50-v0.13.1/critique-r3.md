あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

PLAN.md を rev.3 に改訂した（同 path）。R2 指摘 11 件への対応を番号対応で自己申告する。対応済み事項の再指摘ではなく、rev.3 で新たに
生じた矛盾・取りこぼし・判別不能な DoD のみを指摘せよ。

# R2 指摘との対応（自己申告）

- R2-1（high）seal exit 2 の停止保証 → **採用**。§0-6 (i): SKILL.md Phase 3 seal 手順に「exit 5 以外の非 0 でも run を解放して停止、
  `read-manifest.py` を呼ばず stderr を報告」の分岐を追加（DoD (1b)、Phase 3 節内・`read-manifest.py` より前の位置で判定）。(ii) 文書契約は
  「seal 失敗 → 監査停止。未 seal の run は gate でも REFUSED にしかならない」に修正（DoD (1)）。
- R2-2（high）契約テスト (c) → **採用**。実体側は `scripts/`・`references/` 直下の通常ファイルのリポジトリ相対 path（42）、文書側は付録
  フェンス内で当該ディレクトリを含む行だけから復元した path。不足・余分を別 assert。
- R2-3（medium）(f) の値検査 → **採用**。4 設定の値を既定値と完全一致（`models.light` の 5 値含む）。schema 表の行キーは S1 で `models` に改める。
- R2-4（medium）handoff 再開テストの算術 → **採用**。DoD (25): `PRECLOSED = {"46","47"}` を定数化し、期待 close 集合・件数を `ISSUES - PRECLOSED` から導出。
- R2-5（medium）(a) の抽出規則 → **採用**。`EXPECTED` 6 値を固定し、各文書のバッククォート抽出との積集合が `EXPECTED` と一致することを assert、
  `normalize()` には `EXPECTED` のみ渡す。負例 2 値の `ValueError` も確認。
- R2-6（medium）(g) の包含 → **採用**。refresh 段落を一意条件（en `templates can be updated directly to`／ja `へ直接更新できる`、ちょうど 1 件）で
  特定し、抽出した版集合が `{0.10.1,0.11.0,0.12.0,0.13.0} ∪ {plugin.json version}` と完全一致。
- R2-7（medium）(h) の同一欠落 → **採用**。`##` 見出し数 15、§5 キー 25 件＋必須 2 キー、付録 path 件数は (c) で固定。
- R2-8（medium）(i) の脆さ → **採用**。Python 側は `ast` で set literal を読み件数 3/5 を assert、文書側は一意ヘッダ
  `| severity | gate effect |`／`| severity | gate への効果 |` の表ちょうど 1 つを §7 に置く（DoD (8)）。
- R2-9（medium）`git ls-files` → **採用**。DoD (27)/§8: `git cat-file -e HEAD:<path>` と `git worktree add <tmp> HEAD` の detached checkout でスイート実行。
- R2-10（medium）fallback 手順 → **採用**。§0-8 に merge → main 切替 → pull → ps 確認 → handoff の完全手順。
- R2-11（low）`grep -c` の終了コード → **採用**。§8 を `! grep -q` に置換。

# 今回の観点

1. §0-6 (i) の SKILL.md 追加分岐は「runtime を変えない docs-only」の範囲と言えるか。既存の exit 5 分岐・`read-manifest.py` 失敗時の停止と
   矛盾しないか。追加位置と文言の DoD (1b) は判別可能か。
2. (a)(c)(f)(g)(h)(i) の固定値（6・42・8・15・25・3/5）が現 HEAD＋PLAN 実施後の実物と一致するか。特に (d) の flag 件数 8
   （init 5＋audit 3）と、(c) の `references/` 6 本（`engine-shas.json`・`workflow-template.js`・schema 2・md 2）。
3. (g) の「段落＝空行区切り」が ADOPTION en/ja の実際の refresh 段落境界と合うか（前後の行が同じ段落に含まれて余計な版番号を拾わないか）。
4. rev.3 で新たに生じた矛盾。落とすべき・縮小すべき検査。

# 出力形式

指摘は番号付き（R3-1, …）。各指摘に重大度・根拠（file:line または実行結果）・推奨 1 つ。新しい実質的な指摘が無ければ「収束（実装開始可）」と
明記し、残るのが worker 指示で吸収できる細部のみならその旨を列挙して締める。
