あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド 2

`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md` を rev.2 に更新した。前回（R1）の 23 指摘との対応を
自己申告する。対応済み事項の再指摘は不要。rev.2 を読み直し、**新たに生じた矛盾・取りこぼし・判別不能な検査**
だけを指摘せよ。

## 前回指摘との対応（自己申告）

1. flip 集計: `contentSha`・`changeSetSha`・`contractVersion`・`backend` 全一致かつ verdict 不一致のみを数える（§10 #39、DoD に 3 ケース）。
2. required の導出元: config のみ（gate は SHA 固定済み config を読む）。evidence は `codexReview.state` のみ、`required` は読まない（§10 #42）。
3. impacted 0 件: `start-run.py` の `phase4_required` に `mode==incremental and codexReview.required is True` を追加。start-run.py を「この変更と impactSha 追加のみ」の限定で許可パスへ（§7）。
4. drift: Phase 0 で `drift` なら監査を開始せず停止（open-run 前）。`not-imported` は 💡 で継続（§9 配線）。
5. `--check`: scope から auto 項目集合を再生成し config の auto 項目集合・metadata と照合。drift 4 経路（scope 変更／auto 手編集／auto 削除／metadata ありで scope 消失）を DoD に列挙（§9、§6 (vi)）。
6. glob 変換: 構文限定。各 `*` 連続 → `**`、置換後 `**` の直後が `/` になる形（`*/`、`**/`）は拒否、`?`・`[`・先頭 `./`・末尾 `/`・空・裸 catch-all も拒否。許可範囲では両方言の正規表現が同一であることをテストで固定。tracked 集合検査は二次（0 件は error）（§9）。
7. `--write` 境界: `--config`/`--scope` を `validate_repo_path` で検証、lock 存在時は拒否（exit 3）。init は `--check --json` の差分提示 → AskUserQuestion 承認 → `--write`。`--import-audit-scope` フラグ自体は維持（drift 後の再同期の入口が必要なため。承認なしの書き込みは禁止）（§9）。
8. history 二重読み: impact.json に `historySha`、plan-dispatch が自身の読取 SHA と照合し不一致は非 0（§10 #39、plan-dispatch.py をこの変更のみ許可）。
9. provenance 封印: manifest に `impactSha`（impact.json の sha256）を封印、codex-dispatch は照合してから provenance を読む（§10 #39）。manifest の `impacted` 形状（path 文字列）は変えない。
10. 統合試験: 全 provenance で cap 満杯にした resolve → supplement → plan-dispatch → start-run → decide-verdict の実プロセス試験（§6）。
11. required と full: full も REFUSED（例外なし）。docs に「最初の baseline 確立後に有効化」（§10 #42）。`enabled:false`＋`required:true` は REFUSED。
12. REFUSED: 判定値は REFUSED のまま。history・anchor・last-run 非更新を実ファイルで固定（§6）。
13. probe: `exec --help` を追加するが保証範囲を「CLI 存在＋exec サブコマンド到達」に縮小して明記（§10 #42）。
14. 表示分離: 内部 verdict 3 値、表示文字列を別変数、stdout/last-run/anchor を同一テストで固定（§6/§10）。
15. 型契約: 5 キーそれぞれ型検証。heuristics/regressionRecheck の不正値は warning＋既定値、`required` 不正は REFUSED。表形式否定試験（§6）。
16. 飽和 WARN: corpus 下限撤廃。`heuristicOnly > 0` かつ比率 ≥ 閾値（§10 #40）。
17. regressionRecheck: 既定 false。init draft で `true` を提案。history 不在は無音、破損のみ warning（§10 #39）。
18. list 継続: content indent 追跡規則（marker 列＋幅＋後続空白、≥+4 でコード、[ci, ci+4) で継続、< ci で終了、tab=4）。`-`／`10.`／引用内／tab の対テスト（§10 #43、§6）。
19. #41: 「唯一」を撤回し「Phase 3 単独では保証しない。Phase 4 reviews・codex・sibling scan が補完層」に。固定 report 行は不採用（§10 #41）。
20. docGlobs 非対称: 影響先が docGlobs（report 除外後 corpus）に無ければ error（§9 検証）。
21. exit 6: run 間 import は `--accept-config` 不要と明記、run 中は lock で拒否（§9）。
22. handoff 試験: 既存試験を拡張（全面差し替え禁止）、13 分岐で tag/Release/Issue close/rsync 0 回を shim カウント（§12、§6）。
23. 契約検査: `tests/test_v013_contracts.py`（5 キー・7 消費側・argument-hint・Phase 5 codex 3 状態・版一致・0.12.0 履歴行の許容リスト）（§6、§12）。

## 今回特に見てほしい点

- (a) R1 対応同士の組み合わせ矛盾。例: 「drift は監査停止」×「init は既存 config があると停止」×「`--import-audit-scope` は承認必須」で、drift 状態からの復帰経路が実際に閉じているか。「impactSha 封印」×「impact-supplement が impact.json を書き換える」の順序（supplement は seal 前か）。「required は full も REFUSED」×「初回 run は full」の運用。
- (b) 構文限定変換で dir-framework 実物の 24 規則のうち拒否されるものがあるか（`~/Projects/dir-framework/.claude/audit-scope.json`。読めなければ PLAN §2 の説明で判断）。拒否が多いなら設計の実用性が落ちる。
- (c) 新テスト `test_v013_contracts.py` が「正しい実装でも誤った実装でも通る」grep になっていないか。
- (d) worker が S1〜S4 の分割で実装可能か（Stage 間依存: S1 の `historySha` と S3 の `impactSha`、S2 の Phase 0 配線と S3 の Phase 5 行）。

出力形式は前回と同じ（番号・重大度・根拠・推奨 1 つ、最後に「PLAN 欠陥／worker 吸収」の区分）。
新規指摘が無ければ「新規指摘なし」と明記せよ。
