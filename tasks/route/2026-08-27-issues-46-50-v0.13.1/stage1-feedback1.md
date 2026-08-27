# S1 差し戻し 1（boss レビュー）

diff 全行を読んだ。DoD (1)(2)(3)(4)(5)(7)(9)(10)(11)(12)(13)(14)(15)(16) は良い（§5 表 26/26、付録 tree 行 51/51、マーカー各 1 回、severity 表ヘッダ各 1 回を boss 側でも実測）。
以下 4 件を修正してから、§8 の S1 検証コマンドを再実行し、`stage1-report.md` を更新せよ（差分箇所だけでなく報告全体を最新化）。

1. **[必須] severity 表の第 1 列をコードスパンにする（en/ja 両方）。** PLAN §6 (23)(i) は「第 1 列のコードスパン語 → 第 2 列先頭のコードスパン トークンの写像」を
   行単位で解析する契約なので、`| PASS |` ではなく `` | `PASS` | `` の形が必要（8 severity 行すべて）。catch-all 行の第 1 列は en `any other value`／
   ja `上記以外の値` のまま（コードスパンにしない）。第 2 列の先頭トークン（`non-blocking`／`blocking`／`REFUSED`）は現状のままでよい。
2. **[必須] README.md:75 の参照節番号。** 版別の互換性影響（`### v0.13.0 compatibility impact` 等）は `docs/ADOPTION.md` の **§8**（Running audits）
   配下にある（:486）。`§7` → `§8` に直す（ADOPTION.md 側は変更しない）。
3. **[必須] PROMPTS.ja.md §9 の文末様式。** 既存節はプロンプト本文・実行行とも「〜してください」（例 :25, :35, :55）。新節だけ「〜すること」になっているので、
   `<task>`・`<constraints>`・末尾の実行行を既存節と同じ「〜してください」に揃える（ADOPTION.ja の「である体」規則は PROMPTS.ja には適用しない）。
4. **[必須] README.md の Usage example の Counts 行。** gate は `{{GATE_COUNTS}}` を JSON（`decide-verdict.py:446` の `safe_json(counts)`）で描画する。
   例示のキーは gate の `counts` に実在するキーだけを使うこと（`decide-verdict.py` で `counts[...]` に入るキー名を確認し、実在しないキー（例: `cached`）は使わない）。
   書式は JSON 風でも `key=value` 列挙でもよいが、キー名は実在のものに限る。修正後、使ったキーの根拠 file:line を報告に書く。

低優先（任意・やるなら 1 行）: ADOPTION §2（en :138／ja :122）の `CODEX_REVIEW_STATES` は実装の定数名。利用者向けには「上記 5 状態のいずれでもない」と
言い換えてよい（言い換えなくても可）。

禁止事項は前回どおり（許可 path 外は報告のみ、テスト不変、版番号を書かない、git commit しない）。
