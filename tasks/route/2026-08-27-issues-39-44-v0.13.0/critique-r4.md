あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド 4

`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md` を rev.4 に更新した。R3 の 18 指摘との対応を自己申告する。
対応済み事項の再指摘は不要。rev.4 を読み直し、**新たに生じた矛盾・取りこぼし・判別不能な検査**だけを指摘せよ。
新規指摘が無ければ「新規指摘なし」と明記せよ。R4 で新規指摘が残る場合は、各指摘を「計画自体の欠陥」と
「worker 指示で吸収できる細部」に区分し、後者は実装プロンプトへ転記できる 1〜2 行の指示文にせよ。

## R3 指摘との対応（自己申告）

1. impact 束縛: plan-dispatch が supplement 後 impact.json の sha256 を `impactSha` として dispatch.json と EVIDENCE に記録。start-run は照合してから manifest に provenance を転記（§10 #39、§6）。
2. verdict 接続: decide-verdict に REFUSED 条件 (a) impact.json sha == dispatch.impactSha、(b) manifest.provenance == impact.json provenance、(c) 型・enum。check-verdicts は不一致で非 0 exit（§6）。
3. provenance 型契約: keys == impacted 集合、値 ∈ `{mapped, heuristic, both, full, graphify, semantic, regression}`、違反は start-run error／gate REFUSED。双方 `"unknown"` の改変試験を追加（§6）。
4. full プロンプト: 対象を「manifest.head で識別され worktreeDigest で封印された現在の worktree（未 commit・未追跡を含む）」と明記（§10 #42）。
5. required/full 試験: orchestrator（SKILL）は非スクリプトのため shim 統合試験は不可能。SKILL 文言契約に縮小 — full+required 分岐が skipped-full-run 分岐と別行で存在し、既存 review 群の後に codex を置く記述（§6 #42）。
6. importer lock: O_EXCL＋fd 排他 flock 保持＋解放時 inode 一致確認。flock 保持中に open-run の `--break-lock` が拒否されることを実プロセス試験（§9、§6 (v)）。
7. lock path: run-base の包含・全 symlink 構成要素を検証（symlink 化した `.claude/state` で exit 1）（§9、§6 (v)）。
8. 初回 init: Step 3 承認後に draft config を書き、その sha を `CONFIG_SHA` として直ちに同一の `--write` 経路（§9 配線）。
9. DOTALL 撤回: 改行名は fail-closed 拒否 — importer は CR/LF を含む tracked path を error、`compute-baseline.sh` は変更集合に CR/LF path があれば非 0 停止（許可パスに最小変更で追加）。3 つの `glob_to_regex` 複製は変更しない（§9、§10 #39 末尾、§7）。
10. `--doc-glob` 反復引数。カンマを含む 1 glob の試験（§9、§6 (vi)）。
11. 契約試験は S1 で骨格を作り各 Stage が自担当 assert を追加（§4、§6）。
12. 導出元検査: (c) `--scope "$AUDIT_SCOPE_PATH"` と bind 行の `auditScope.path` 参照、(d) `--expect-*-sha "$CONFIG_SHA"/"$SCOPE_SHA"` と bind 行の `configSha/scopeSha` 参照、(f) workflow 起動行の `impacted` が `manifest.provenance` 参照（§6）。
13. 統合試験を (A) regression 残存・(B) cap 落ちの 2 本に分離（§6）。
14. 版残存検査は出荷物 path 集合（skills/ agents/ docs/ .claude-plugin/ README.md tests/）に限定、tasks/ は対象外（§6 (j)、§12）。
15. Issue close: 集合 `{39..44}` 各 1 回を検査（§12）。
16. 再開表: tag push 後／Release 作成後／Issue close 3 件目後で 1 回失敗 → 再実行で 1/1/6/1 に収束（§12）。
17. 同期先 preflight（symlink・包含・書込可能性）を tag 前へ移動、期待 0/0/0/0（§12 (x)(xi)）。
18. multiset 比較＋重複 auto 項目 1 件削除の drift 試験（§9、§6 (vi)）。

## 今回特に見てほしい点

- (a) 封印連鎖の順序: resolve → supplement → plan-dispatch（impactSha）→ start-run（照合・転記）→ seal-run。supplement が
  plan-dispatch の**後**に走る余地は SKILL Phase 2 の現行記述にあるか。EVIDENCE への `impactSha` 追加が open-run の seed と
  decide-verdict の `--expect-json` 検査（必須/任意フィールド集合）と衝突しないか。
- (b) importer の flock と open-run の flock: open-run は lock 取得時に flock を取るか（`open-run.py:191-209`）。取らない
  なら「flock 保持中は --break-lock 拒否」は成立するか（`--break-lock` 側は flock を試みる `:87-111`）。
- (c) compute-baseline.sh の CR/LF 拒否が、full mode の `git ls-files`/`git status` 系出力（`-z` でない）に対して実装可能か。
- (d) 実装コストの妥当性: rev.4 は当初計画から大きく膨らんだ。**落とす・縮小して差し支えない成果物**があれば根拠つきで
  挙げよ（例: 再開表、Phase 5 status 行、`counts.heuristicSaturation` の表示丸め）。

出力形式は前回と同じ。
