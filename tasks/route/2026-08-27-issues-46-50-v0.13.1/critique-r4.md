あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

PLAN.md を rev.4 に改訂した（同 path）。R3 指摘 11 件への対応を番号対応で自己申告する。対応済み事項の再指摘ではなく、rev.4 で新たに
生じた矛盾・取りこぼし・判別不能な DoD のみを指摘せよ。これは 4 往復目（上限 5）である。

# R3 指摘との対応（自己申告）

- R3-1（high）SKILL.md 停止分岐は runtime 変更 → **採用**。§0-6: 停止分岐を v0.13.1 から除外し、現挙動（seal exit 2 → 未 seal → gate が
  `manifest is not sealed` で REFUSED、`decide-verdict.py:693-695`）を正確に文書化。別 Issue 候補として最終報告に載せる。DoD (1b) は削除。
- R3-2（high）(i) の逆対応 → **採用**。DoD (8): severity 1 語 1 行＋「それ以外」の 9 行表、第 2 列先頭を固定コードスパン トークン
  （`non-blocking`／`blocking`／`REFUSED`、en/ja 共通）にし、(i) は行単位で写像を作って Python 側集合と完全一致。
- R3-3（medium）(1b) の判別不能 → **採用**（(1b) 自体を削除、R3-1 に従う）。
- R3-4（medium）(a) の余分な許可例 → **採用**。§0-6: 3 文書に固定マーカー 1 文（en `Accepted \`digestExclude\` prefixes:`／ja
  `\`digestExclude\` で受理されるプレフィックス:`、各文書 1 回）。(a) はマーカー文から文末までのバッククォート値集合を `EXPECTED` と完全一致させ、
  抽出した全値を `normalize()` に通す。
- R3-5（medium）(d) の取り違え → **採用**。audit 行（3）／init 行（5）を別々に完全一致。
- R3-6（medium）(f) → **一部採用**。`codexReview == {"enabled": true, "bin": "codex", "required": false}` で既存 2 キーも固定。`models` の
  dict 完全一致は維持（example は boss 管理の固定成果物で `sensitiveTokens` を載せない方針。緩和は不要と判断）。
- R3-7（medium）severity 表の配置矛盾 → **採用**。§8 の現行説明（`ADOPTION.md:446-448`／`.ja.md:419-421`）を表で置換、§7 には置かない。
- R3-8（medium）(h) 付録総数 → **採用**。tree 行（`├`/`└`、root 行除く）を各 51 件で固定。
- R3-9（medium）detached 検証の手順接続 → **採用**。§8 に `git worktree add --detach` → `tests.test_release_handoff`（18 件）→ `worktree remove`
  を追加（フルスイートは通常 checkout で実施、detached は handoff test に縮小 — Sol の縮小案を採用）。
- R3-10（low）`PRECLOSED` の保証 → **採用**。非空かつ `ISSUES` の真部分集合を assert。
- R3-11（low）REFUSED 到達箇所 → **採用**。`decide-verdict.py:693-695` に訂正。

# 今回の観点

1. R3-1 の帰結として、#47 の文書契約（現挙動の正確な記述）に事実誤認が残っていないか。特に「gate が REFUSED にする」経路は、SKILL.md の
   現手順で実際に gate まで到達し得るか（`read-manifest.py` が未 seal manifest を通す点は R2-1 で確認済み）。
2. DoD (8) の表仕様（9 行・固定トークン・en/ja 共通トークン）が ADOPTION の既存文体・表記と衝突しないか。(i) の行単位解析が正しい表でも
   壊れる条件（セル内の追加コードスパン等）はないか。
3. (a) の固定マーカー方式: config-schema.md は表形式（`digestExclude` 行のセル内）にマーカー文を置くことになるが、セル内の `.`（文末）の扱いと、
   ADOPTION 側の散文とで抽出規則が一貫するか。
4. rev.4 で新たに生じた矛盾。落とすべき・縮小すべき検査。

# 出力形式

指摘は番号付き（R4-1, …）。各指摘に重大度・根拠（file:line または実行結果）・推奨 1 つ。新しい実質的な指摘が無ければ「収束（実装開始可）」と
明記し、残るのが worker 指示で吸収できる細部のみならその旨を列挙して締める。
