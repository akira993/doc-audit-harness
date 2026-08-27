boss レビュー（S2 差し戻し 1）— 欠陥 3 点＋テスト不足。git 操作は不要（boss が行う）。

## A. コード欠陥（`skills/audit/scripts/resolve-impact.py`）

1. **`saturationWarnRatio` の bool 判定順序**: 現状 `if saturation == 0:` が型検査より先にあるため、`false`（Python では `False == 0`）
   が「無効化」として通り、仕様（bool は warning＋既定値 0.5）に反する。**bool 検査を最初に**行い、その後に `== 0`（int/float の 0）
   で無効化、範囲・型違反は warning＋既定値、の順に直せ。
2. **history 破損時の `historySha`**: `history_sha` を `parse_history` 成功後に代入しているため、history が JSON 不正のとき
   `historySha: null` になる。一方 plan-dispatch は同じ bytes の sha を計算するので `null ≠ sha` で **exit 3（history changed）** に
   なり、本来の `historyStatus: corrupt` 経路を潰す。`history_sha` は**生 bytes を読んだ直後**（parse 前）に計算し、parse 失敗時も
   `historySha` に記録せよ（regression 候補は追加しない・warning は従来どおり）。
3. **provenance の優先規則**: PLAN §10 #39「`provenance()` は既存規則（mapped/heuristic/both/full）を優先し、`regression` 単独の
   ときのみ `"regression"`」。現状は `heuristic ∧ regression` を `"regression"` にしている。`heuristic` が含まれる場合は `"heuristic"`
   を返すよう直せ（cap の tier 分けは現状どおり — regression を含む文書は regression tier で可。`mapGapCandidates` は provenance ==
   `heuristic` の文書なので、この修正で heuristic∧regression の文書が候補に戻る）。

## B. テスト不足（`tests/test_resolve_impact.py`・plan-dispatch のテスト）— 依頼書 §6 のとおり全項目を追加せよ

- #40: docCorpus 0 → `heuristicSaturation 0.0`・warning なし・正常終了／synthetic corpus **9 docs 中 9 件** heuristic-only で WARN
  （下限なし）／**丸め前比較**（比率 0.4996 と閾値 0.5 で WARN なし・表示は 0.5）／`excludeDocPathTokens` の true/false 対／cap 超過が
  `warnings[]` に入る／**型検証表**（`subTest`）: `saturationWarnRatio` ∈ {"0.5", true, **false**, -1, 1.5, None, [], 0（無効）, 1（有効・全件で
  WARN）}、`excludeDocPathTokens` ∈ {"true", 1, None}、`regressionRecheck` ∈ {[], "x", {"enabled":"yes"}} の各挙動（warning 文言と
  既定値）。
- #39: 既に mapped の文書は provenance `mapped`（regression にならない）／**heuristic∧regression は `heuristic`**（A-3）／full mode で無効／
  既定（enabled 省略）で無効かつ warning なし／history 不在は無音（`historySha: null`）／history 破損は warning かつ **`historySha` は
  bytes の sha**（A-2）／cap 順序（mapped 2・regression 2・heuristic 2・`maxImpactedDocs: 3` → mapped 2＋regression 1、heuristic 0、
  `truncated=true`、cap warning が `warnings[]` に入る）。
- plan-dispatch（既存の plan-dispatch テストの置き場に従う。無ければ `tests/test_plan_dispatch.py` を新設）: `historySha` 一致で正常／
  改変で exit 3 と stderr 文言／`historySha: null` と history 不在で正常／**history 破損 + `historySha` = その bytes の sha** で
  `historyStatus: corrupt` かつ exit 0（A-2 の回帰）／dispatch.json の `impactSha` が impact.json bytes の sha256（`sha256:` 形式）と
  一致／stdout の EVIDENCE キー集合が変更前と同一（`impactSha` を含まない）。
- `source` 互換: impactMap 項目に `source:"audit-scope"` を付けた config と付けない config で resolve-impact の JSON 出力が完全一致。

## C. 確認事項（報告に含めよ）
- 修正後のフルスイート件数（成功／失敗／skip）と `git status --short`。
- A-1〜A-3 それぞれについて、修正を revert すると対応テストが赤になることを確認した方法。
- 依頼書 §5 の docs/消費側/契約テスト (b)(g)(h) は実装済みとのことだが、`docs/ADOPTION*.md` の「コスト主因は anchor の古さ」段落と
  「欠陥クラス横断掃除」推奨、`skills/init/SKILL.md` の `regressionRecheck` 提案が入っているか、入っていなければ追加。
