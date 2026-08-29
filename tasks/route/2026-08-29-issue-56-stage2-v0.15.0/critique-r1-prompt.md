あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

## レビュー対象

docaudit engine（この repo、現 HEAD `4c9df5b`）の次版 v0.15.0 の実装計画:
`tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md`

背景資料（すべて読み取り可）:
- 事前調査（全 file:line 引用）: `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/investigate-report.md`
- ユーザー裁定の記録: `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/REVIEW.md`
- Issue #56 本文: `gh issue view 56` 相当の内容は PLAN §1 に要約済み
- 参照実装（key-gated 3 seam）: `skills/audit/scripts/{graphify,codegraph,cocoindex}-probe.sh`
- 変更対象の現物: PLAN §7 の許可一覧のファイル群

## 決定済み事項（再審議不要 — ユーザー裁定）

- webExtract / codexReview の 2 seam を key-gated 化（キー不在＝not-configured・tool 不起動）
- indexing / contextMode は既定有効を維持
- 版は minor 0.15.0、#56 は本 PR で close、#59 は据え置き（対象外）

## 依頼

PLAN.md を上の背景資料・repo の現物と突合し、以下の観点で欠陥を列挙せよ:
1. バグ・回帰: PLAN の指定どおり実装すると壊れる箇所（行番号の誤り・見落とした下流消費者・
   resume/rebind・Phase-4 の実行判定・Phase-5 表示の優先順位・単体呼び出し時の防御との相互作用を含む）
2. 互換性: 既存 config（キー無し・キー有り・enabled:false・required:true）と既存 run の resume に対する影響の取りこぼし
3. テスト不足: 完了条件 §6 の判定表・grep ゲートが「正しい実装でも誤った実装でも通る」偽陽性にならないか、
   歴史契約テストと現行契約テストの分割方針の穴
4. セキュリティ: probe の入力検証・emit の純 ASCII/単一行規約（v0.14.0 の ensure_ascii 教訓）・path 検証への影響
5. 文書整合: 残骸列挙（investigate-report §10）の漏れ、ADOPTION §7 固定文の矛盾

各指摘に: 根拠（file:line の実測引用）・重大度（Critical/High/Medium/Low）・推奨修正 1 つ。
既に PLAN が正しく扱っている点の再説明は不要。指摘が無い観点は「指摘なし」と明記せよ。
