あなたは docaudit v0.16.0 の実装計画に対する **全体敵対レビュアー**（read-only）。実装も修正もしない。

対象: `tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md`（v5）。背景: 同ディレクトリの `00-issue-review.md`、`01-survey.md`、`02-critique-r1.md`〜`06-critique-r5.md`（GPT-5.6 Sol による 5 往復の逐次批判と boss の対応。REVIEW.md に対応表）。GitHub Issue #63・#59 は `gh issue view` で読める（接続不可なら 00-issue-review の要約で代替）。コードは `skills/audit/`（SKILL.md・scripts/・references/）、テストは `tests/`。

**Sol の指摘の再発見に価値はない。Sol が構造的に見落とす層を狙え。** Sol のラウンド逐次批判は「個別修正の妥当性」を見る構造のため、次の層を落としやすい:

(a) **ラウンド間で入れた修正同士の組み合わせ矛盾**。特に: verify-on-read の必須化 × `--expect-config-sha` 任意フラグ 2 本（set-config-key / generic-layers）× harness 互換表（stamp == 版のみ直接起動）× engine-shas の 0.16.0 entry／acceptance marker × 隔離待ち marker（last_run と lock holder）× `--accept-config` × `--release`／`--break-lock` × decline 再 open（precheck 再実行）／history の 4 reader 真理値表 × Phase 2 での EVIDENCE.history 封印 × Phase 4 の carry-forward × gate の書き戻し／§9.7 eligibility の REFUSED × 旧版 SKILL が書いた evidence × 混在版の扱い。
(b) **タスク目的との整合**: #63 は「TOCTOU を閉じる」、#59 は「サンプリング契約への是正」。対策が負荷の削減でなく付け替えになっていないか。定常状態の維持コスト（SKILL の getter 13 行、22 call site の sha 付与、registry の同期、`sitecustomize` テスト）は将来の変更ごとに何を要求するか。verify-on-read で得られる保証を、脅威境界（§1: plugin engine は信頼、repo 内の実行ファイル・run をまたぐ状態は repo 書き込みクラス）に照らして一文で言い切れるか。
(c) **修正の波及先の取りこぼし**: 規約の複写（README／ADOPTION en・ja／config-schema.md／SKILL Guardrails）、テンプレート（scaffold.py の command/skill テンプレートは不変とした判断は正しいか）、生成物（engine-shas、dir-framework 側 0.15.0 harness）、受入テスト対象外のファイル（skills/init/SKILL.md は禁止範囲だが set-config-key の呼び出しは無改修で成立するか、`docs/examples/doc-audit.example.json`、`docs/PROMPTS*.md`）。
(d) **worker 実行可能性と受入テストの判別可能性**: PLAN の各 S 項目を Sol `high` の worker が一度の委譲で実装できる粒度か（分割すべきか）。CT-1〜CT-7・CT-2b・CT-3b・CT-4b は「正しい実装でも誤った実装でも通る」検査になっていないか（特に sitecustomize 方式が macOS/Python 3.14 で成立するか、`bash` 内蔵 python にも効くか）。
(e) **費用対効果が低く落とす・縮小すべき成果物**: 例: CT-2b、`historyQuarantineFailed` の二重 marker、carry-forward そのもの（#59 の実測では title が揺れるので file 単位の carry-forward の価値は何か）、`--raw` オプション、getter 13 本の粒度。

各指摘に **根拠（ファイル・行・実測。推測は推測と明記）** と **推奨 1 つ** を付け、深刻度（Critical／Major／Minor）を付けよ。最後に「PLAN を直してから実装すべき事項」「worker 指示で吸収できる細部」「ユーザー決定に関わる事項（スコープ縮小・仕様変更）」の 3 区分で総括し、区分が空なら空と書け。指摘が無い観点は「指摘なし」と明記せよ。

- **結論先行**: 報告の最初の一文で「何が見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造は最悪の失敗
- **スコープ規律**: ファイルを変更しない。読むだけ
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない
