あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ
作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

## 対象
`tasks/route/2026-08-28-issues-56-60/PLAN.md`（rev.1）。docaudit プラグイン（engine v0.13.2、HEAD dfdb8a9）の open Issue #56（第 1 段）・#57・#58・#59・#60 を v0.14.0 で解消する計画。
事前調査の事実は `tasks/route/2026-08-28-issues-56-60/investigate-report.md`、前版の計画は `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（判定表・Opus B5 キー集合不変・reason 排他表の出所）。
Issue 本文は `gh issue view 56..60` で読める（read-only）。

## 依頼
PLAN の各決定（§0-1〜§0-9）と DoD（§6）を、実コード（`skills/audit/SKILL.md`、`skills/audit/scripts/*`、`tests/*`、`docs/ADOPTION*.md`、`skills/audit/references/*`）に照らして検証し、
次の観点で指摘せよ。各指摘には根拠（file:line または実行結果）と推奨 1 つを付け、番号 R1-N を振る。指摘が無い観点は「無し」と明記。

1. バグ・回帰: 計画どおり実装すると壊れる既存契約（既存テスト名・SKILL の固定文言・gate の REFUSED 条件・EVIDENCE 連鎖）。特に
   - #58 の相対化が `validate_repo_path` の中間 symlink 拒否・`..` 拒否を迂回しないか
   - #56 で `invalid-config` を加えたときの mdq 確認ゲート／`codex-review-plan.py`／`decide-verdict.py` の `required` 経路の整合
   - #57 の `probe-record.py` が EVIDENCE／gate／report-only 契約・run lock 規約に抵触しないか（`$RUN_DIR` の所有・symlink・原子性）
   - #59 の ledger が gate を弱めないか（抑止できるのは non-blocking のみ、blocking は毎 run 再検証、resolved 削除の安全性）、key 正規化の衝突・不一致、diff variant での妥当性、
     `.claude/state` への書き込みが Guardrails の脅威モデル（後続 run への汚染持ち越し）に新しい経路を開かないか
   - #60 のキー追加が既存の JSON 消費者（SKILL の python -c 束縛・テスト・`codex-review-plan.py`）を壊さないか、`$HOME` 未設定・`CODEX_HOME` 空文字列の扱い
2. セキュリティ: ledger／probe record への path/title 注入（プロンプトへ verbatim で入る文字列の扱い）、symlink、`.claude/state` 外への書き込み経路。
3. 互換性: 既存 config（キー省略・`enabled:"false"` 文字列等）を持つ利用者が黙って機能を失う／REFUSED になる経路の網羅（ADOPTION §7 の 5 文で足りるか）。
4. テスト不足: DoD (1)〜(20) のうち「正しい実装でも誤った実装でも通る」検査、対象 0 件で合格し続ける検査、固定文言が実装と乖離しても通る検査。
5. 計画自体の欠陥 vs worker 指示で吸収できる細部 を区分して列挙し、最後に「PLAN を直すべき点」を優先順で 5 件以内にまとめよ。

出力は日本語 Markdown。推測は推測と明記し、実測できるものは実測せよ（read-only サンドボックス。一時ファイルは書けないので静的検証で可）。
