読み取り専用の機械的調査。リポジトリ doc-audit-harness の現状インベントリを作成せよ。ファイルの変更は一切禁止。

## 目的
Issue #66（`/code-review` の自律実行化・方式 B: 既存 `reviewCommands.code` を単一窓口として Skill ツールで自律実行し所見を verdict に畳み込む）の PLAN 作成材料。

## 調査項目（各項目とも file:line と該当行の verbatim 引用を付けること）
1. `reviewCommands` に言及する全箇所（skills/ README.md docs/ tests/ .claude-plugin/ を対象。grep -rn）。各箇所を「定義／消費／文書／テスト」に分類し、総数 N を報告。
2. `CODE_REVIEW_STATE` の全出現箇所と、取りうる値の一覧（skills/audit/SKILL.md の状態表・分岐を含む）。
3. skills/audit/SKILL.md の Phase 4 における reviewCommands.code の現行フロー全文（AskUserQuestion での offer、ターン終了、Phase-5 cross-turn state（RUNID/EVIDENCE の書き出しと resume）、fold 規則、`/code-review ultra` の扱い、`disable-model-invocation` 分岐）。該当行範囲を明示し全文引用。
4. `reviewCommands.security`（/security-review）の現行実行方法と fold 経路（code と対称か）。
5. skills/audit/references/config-schema.md の `reviewCommands` と `codexReview` の定義全文（`required` キーの有無、fail-closed の記述）。docs/examples/doc-audit.example.json の該当部。
6. decide-verdict.py・その他 scripts/ に CODE_REVIEW_STATE や reviewCommands を読む箇所があるか（SKILL.md 内だけの契約か、script 側で enforce されるか）。EVIDENCE に code-review 関連キーがあるか。
7. tests/ で `not-model-invocable` `CODE_REVIEW_STATE` `reviewCommands` をアサートするテストの一覧（test 名と何を固定しているか）。docs contract テスト（test_v016_docs_contracts.py 等）が README/ADOPTION の code-review 文言を固定しているか。
8. README.md・docs/ADOPTION.md・docs/ADOPTION.ja.md で code-review に言及する節（見出しと該当行）。"not model-invocable" / "user-invocation-only" 相当の残存記述。
9. Phase 5（fix loop）・verdict 出力テンプレートで code-review 所見がどう表示されるか。

## 報告形式
結論先行の日本語。項目ごとに表または引用ブロック。最後に「PLAN が触る必要がありそうなファイル一覧（推定変更規模つき）」を 1 表で。

以下は行動規範。全て命令。

- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
