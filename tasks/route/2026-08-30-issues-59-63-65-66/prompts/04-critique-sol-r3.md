あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

ラウンド3。`tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` を v3 に改訂した（全面書き換え。再読せよ）。前回指摘との対応（自己申告）:

- R2-1（harness の config 読み）→ **方針 B を採用**（boss が advisor に諮った上での決定。ユーザーは boss に委任）。根拠: Phase-4 コマンドの定義ファイル自体（`.claude/commands/check-docs.md`、`.claude/skills/doc-lint/SKILL.md`、`scripts/check-docs.py`）が repo 書き込み者に改変可能で、config 改竄より安価な同効果の経路が常に存在する。stamp 検査は版のみで本文完全性ではない。よってこれらの所見は「repo 書き込みレベルの信頼」で扱い（§1、§9.3）、ADOPTION に信頼クラス段落を明記（S7）。あなたの案 A は doc-lint の FAIL が NEEDS FIX を起こさなくなる製品契約変更で #63 の範囲外（将来オプションとして記録）。ただし Phase 0.5 で SKILL が直接起動する engine 複製（:302）には sha を付け、stamp < 0.16.0 の複製は起動せず plugin の generic-layers.py（sha 付き）で代替＋WARN＋refresh 案内（S6）。この方針そのものの再審議は不要。方針 B の下での整合性・抜けを指摘せよ。
- R2-2（seal-run）→ S2 で pass-through 対象に追加、子 exit 7 を保持、SKILL の release 分岐（:419-423）より前に token 判定（S6）。CT-3 に順序契約検査。
- R2-3（decline 再 open）→ decline 後に `import-audit-scope.py --check` を再実行して `PRECHECK_CONFIG_SHA` 再束縛（S6）。`--accept-config` は lock 取得成功時に一度だけ消費し marker を false に書き換える（S4）。CT-3/CT-4。
- R2-4（隔離失敗）→ 隔離失敗（例外または live 残存）時は release せず exit 3 `history-quarantine-failed`、lock 残存 → 次 open exit 4 → `--break-lock` が明示回復経路。既存 gate 経路にも適用（S5）。CT-5 に先置きディレクトリのケース。
- R2-5（非所有）→ 4 ケース（lock 欠落／holder runid 相違／inode 相違／flock 他保持）で無書き込み exit 3（S5）、observer ID 固定列挙（§9.4、O=22）、CT-3b。
- R2-6（impact-supplement）→ 条件付き必須に変更（S2、§9.1）。
- R2-7（`--get` の型・既定値）→ `--raw` 追加、key ごとの default／mode／束縛変数を §9.2 に表で固定。
- R2-8（plan-dispatch）→ 共通 `parse_history_document` を plan-dispatch・gate・codex-review-plan の 3 者で使用、不正は `historyStatus:"corrupt"`（S9）。
- R2-9（carry-forward の注入面）→ findings を `{file, severity}` のみに縮小（title/source は history にも持たない）、carry-forward は現在の worktree に実在する file だけ（S9/S11）。
- R2-10（unresolved）→ findings／flip 集合／carry-forward から除外し `unresolvedFileCount` で別計上（S8）。
- R2-11（64 KiB）→ title を持たないため record は小さく、予算 8 KiB を worker が計算し固定。gate は書き込み前に同じ parser で round-trip 検証、`blockingFiles` は保存せず導出（S9）。
- R2-12（件数）→ §9 を registry（script／sha 供給／フラグ／読み／正常 exit／mismatch exit／observer ID）に改め、§9.5 で N=22／M=4／G=13／K=21／O=22 を導出。CT-2 は registry の mismatch exit（open-run 2、gate 3、他 7）を使う。
- R2-13（CT-1(d)）→ ファイル名 grep を廃止。getter registry（key→VAR→default→mode）で「VAR の束縛行がちょうど 1 行・他の代入なし」を等値検査（CT-1(c)）。
- R2-14（正規化）→ exact 検証を先、失敗時のみ locator 除去、Windows drive/UNC は OS 非依存に拒否（S8）。
- 細部: `head`／per-finding `source` を record から削除、severity は uppercase 4 値。

再批判を求める。特に:
1. 方針 B の下で、Phase 0.5 の installed 分岐（stamp ≥ 0.16.0 → 複製起動＋sha／< 0.16.0 → plugin engine で代替＋WARN）と Phase 4 の docAuditCommands 実行、`harness.state` の各値（installed/integrated/adjusted/existing-untouched/declined/broken）の組み合わせで矛盾や抜けはないか。
2. acceptance marker × decline 再 open × `--expect-config-sha` × `--break-lock` × `--release` の組み合わせ。
3. §9.5 の件数（N=22／M=4／G=13／K=21／O=22）をあなたが数え直せ。数え方が一意に定まらない項目があれば指摘せよ。
4. `parse_history_document` の corrupt 判定が、旧版（≤0.15）が書いた正当な history や、v0.16.0 gate 自身が書いた record を誤って隔離する経路。
5. 落とすべき・足りない成果物。

出力形式は前回同様（`[R3-n] 深刻度 要約` → 根拠 file:line → 推奨 1 つ）。対応済み事項の再指摘は不要。新しい実質的指摘が無ければ「収束」と明記せよ。
