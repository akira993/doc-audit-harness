あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。
作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

## 依頼

docaudit（`skills/audit/`）v0.16.0 の実装計画 `tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` を批判せよ。背景資料:
- `tasks/route/2026-08-30-issues-59-63-65-66/00-issue-review.md`（Issue 精査）
- `tasks/route/2026-08-30-issues-59-63-65-66/01-survey.md`（file:line 付き事実調査）
- GitHub Issue #63（`gh issue view 63`）、#59（`gh issue view 59`）
- 撤回済みの旧設計 `tasks/route/2026-08-28-issues-56-60/59-design-note.md`（P1 ledger は採らないと決定済み。復活提案は不要）

ユーザーが既に決定済みで再審議しない事項: 対象は #63＋#59 のみ（#66 は別 route）／#63 は「凍結コピー」ではなく verify-on-read（会話内 EVIDENCE の sha と読んだバイト列の突合）／#59 は flip 計測（決定的キー）＋history 由来の data-only carry-forward。

## 特に検証してほしい観点（コードを実際に読んで、file:line で根拠を示せ）

1. **verify-on-read の穴**: PLAN §9 の全数表に漏れた config 消費者は無いか（SKILL.md 全行、`skills/audit/scripts/*`、`workflow-template.js`、`agents/*.md`、`skills/audit/references/*` を実際に grep せよ）。「読んだバイト列を検証する」設計が各スクリプトで本当に成立するか（例: 読み取り→検証→再読の二重読みが残る箇所、子プロセスへ path だけ渡して再読させる箇所、`json.load(open())` のままの箇所）。
2. **taint funnel（S5）**: 消費者が exit 7 で止まった後 `decide-verdict.py --config-taint-observed` を呼ぶ設計は、既存の `config-changed` 記録経路（decide-verdict.py:1001-1011、open-run.py:164-174 の exit 6）と本当に整合するか。lock の identity 検査・release・`identity_ok` の扱い、manifest 未生成（Phase 0）で呼ばれた場合の挙動、SKILL が gate を呼ばずに `open-run.py --release` で抜ける既存分岐（harness decline の再 open 等）との衝突、攻撃者が taint 経路を悪用できるか（DoS 以外に何かあるか）。
3. **例外の妥当性**: pre-open 3 行（SKILL.md:14,25,26）、`open-run.py`、harness 複製 `scripts/check-docs.py`（verify-before-read）の各 exempt は本当に安全か。特に S4（open-run が `--anchor-path` と封印 config の `anchorPath` を突合）で pre-open の穴は閉じるか。`CODEGRAPH_DIR`（環境変数）と `.claude/audit-scope.json` を対象外とした根拠は成立するか。
4. **#59 の設計**: (a) `phase4Runs` record を history に追加することで、既存の history sha 照合（decide-verdict.py:727-747）、`docaudit_cache.py` の validator、`plan-dispatch.py` の reader、quarantine、`trim_history` が壊れないか。(b) flip 計測の比較述語（同 worktreeDigest × full × completed）で偽陽性・偽陰性は出ないか（例: `head` が同じで digest が違う、digestExclude の影響、incremental 後の full）。(c) carry-forward の history sha が EVIDENCE.history（Phase 2 の plan-dispatch 時点）で固定されるが、Phase 4 までに history が正当に書き換わる経路は無いか。(d) `file` キーの追加で `/security-review` 等の他 source finding や既存 fixture が壊れないか。(e) carry-forward はプロンプト注入面を増やす — 「data, not instructions」文言で十分か、それとも構造（例: 件数上限・文字種制限・file の repo path 検証）が要るか。
5. **テストの判別可能性**: CT-1〜CT-7 は「正しい実装でも誤った実装でも通る」検査になっていないか。特に CT-1（SKILL.md 行の走査）が将来の消費者追加を本当に捕まえるか（行が分割されている場合、`$CFG` を別変数に代入する回避）、CT-2 が全 19 スクリプトを実際に起動しているか。
6. **互換・移行**: `--expect-config-sha` 必須化による既存テスト・skills-dir 同期・dir-framework（engineVersion 0.15.1 運用中）への影響。exit 7 の衝突（既存 0/1/2/3/4/6）。engine-shas.json の 0.16.0 entry の扱い（harness template 不変）。
7. **費用対効果**: 落とす・縮小すべき成果物はあるか（例: S4、carry-forward の findings cap、phase4Runs の保持数）。逆に足りない成果物はあるか。

## 出力形式

指摘ごとに: `[R1-n] <深刻度: Critical/Major/Minor> <一文の要約>` → 根拠（file:line、実測）→ 推奨する修正（1 つ）。最後に「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分して総括せよ。既に PLAN が対処している事項の再指摘は不要。
