あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

## 対象
`tasks/route/2026-08-31-issue-66/PLAN.md`（Issue #66 方式 B: /code-review 自律実行、docaudit v0.17.0）。

## 前提資料（すべて読み込むこと）
- `tasks/route/2026-08-31-issue-66/00-preflight-verification.md` — 実機検証（この事実は再検証不要の前提として扱う）
- `tasks/route/2026-08-31-issue-66/01-survey-out.md` — 現状インベントリ（file:line 付き）
- 現行実装: `skills/audit/SKILL.md`（特に :51-67, :556, :580-602, :657-663, :813-816）、`skills/audit/scripts/codex-review-plan.py`、`skills/audit/scripts/decide-verdict.py`、`skills/audit/scripts/sealed_config.py`、`tests/test_v016_contracts.py`（CT registry）、`tests/test_v015_contracts.py:197-230`
- 前 route の registry 契約: `tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` §9

## 確定済み事項（再審議しない）
- 方式 B（`reviewCommands.code` 単一窓口・新キー `codeReview{...}` は作らない）はユーザー決定。
- `permissions.ask` を推奨構成にしない（実測不成立）。
- verify-on-read／taint funnel／registry 計数という v0.16.0 の機構自体。

## 特に検査してほしい層
1. S1 決定表の完全性（config の異常値で表のどの行にも落ちない入力は無いか。`reviewCommands` 自体が非 object、`code` が null、unicode 空白、`/code-review  high` の二重空白等）。
2. S3 の gate enforcement と既存 phase4 検証（codexReview eligibility、write-evidence.py）との整合。EVIDENCE round-trip・history phase4Runs への影響。
3. 互換性: 既存 adopter（reviewCommands.code 設定済み・required 無し）が v0.17.0 に上げた瞬間に何が変わるか。REFUSED に落ちる正当な既存 config は無いか。旧 SKILL 文言を固定している全テストの棚卸し漏れ。
4. cross-turn 規則 (g) の書き換えで、resume 時の「会話内に可視の所見のみ fold」が偽装可能でないか（#63 の脅威モデル: repo 書き込み者、および会話内 prompt injection）。
5. sealed-config registry 計数（23/3/13/22/20）の算術。getter 13 不変という主張の正否（SKILL:556 の REVIEW_COMMANDS_JSON getter は S2 後も使われるのか、死に getter にならないか）。
6. severity ラベル無し所見を WARN 扱いにする既定の欠陥（blocking にすべき実測ケースは無いか。逆に code-review の出力に PLAN が想定しない severity 語彙が入る場合）。
7. テスト計画の判別可能性（誤実装でも通る検査になっていないか）。

## 報告形式
指摘は番号付きで、各指摘に: 重大度（Critical/Major/Minor）／根拠（file:line または PLAN の節）／推奨修正 1 つ。最後に「PLAN 自体の欠陥」と「worker 指示で吸収できる細部」の区分表。
