あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。
曖昧な両論併記で終わらせず、根拠の上ではっきり立場を表明する。
局所最適ではなく全体最適を、短期的解決ではなく長期的視点を優先する。

# 依頼

以下の計画 `tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md` を批判せよ。対象リポジトリはカレントディレクトリ（docaudit の開発リポジトリ、main HEAD e1c0b19）。読み取り専用で、必要なファイルは自分で開いて実物と突き合わせること（計画中の行番号は 2026-08-30 時点の実測だが、必ず再確認せよ）。

背景の決定記録（ユーザー承認済み。再審議不要）: `tasks/route/2026-08-30-issues-59-63-65-66/00-issue-review.md`。
本計画は 4 Issue のうち **#65 の修正と #66 の文言是正のみ**を v0.15.1 として出すパッケージであり、#63・#59・#66 方式 B の実装は別 route で行う。スコープ拡大の提案は不要（ただし「このパッケージに含めないと #65 の修正自体が不完全／矛盾する」ものは指摘せよ）。

## 特に確かめてほしい点

1. `skills/audit/scripts/codegraph-probe.sh` の新分岐（`.codegraph/codegraph.db` の通常ファイル有無で `sync`/`init`、symlink は実行せず `index-failed`、0 バイトは `sync`）に、既存の 6 状態契約（`ok/not-installed/disabled-by-config/index-failed/not-configured/invalid-config`）や JSON 出力・exit 0 規約を壊す点はないか。`codegraph.db` 以外に codegraph 1.5.0 が「初期化済み」の根拠にする実体（`.gitignore`、WAL/SHM、daemon ファイル）を probe が誤って根拠にすべきケースはあるか。
2. symlink を `index-failed` にする判断は妥当か（`init` に落とすと codegraph が symlink 先を上書きし得る、という理由）。別の安全な扱いがあるか。
3. `tests/test_codegraph_probe.py` の既存 `test_stub_installed_existing_calls_sync`（空ディレクトリ fixture）を改める方針と、新規 6 ケースの設計に、「正しい実装でも誤った実装でも通る」検査が混ざっていないか。fake codegraph の log 実体で subcommand を判定させる方針で十分か。
4. #66 の文言是正（挙動不変・状態トークン `not-model-invocable` 維持）で、文書と実挙動の間に **新たな不整合**が生じる箇所はないか。特に README:14 の「autonomous runs … expected user-invocation-only layer」の置換案と SKILL.md:560-563 の分岐説明の整合。`docs/superpowers/**` を触らない判断の妥当性。
5. 版 bump 0.15.1: `engine-shas.json` に同一 sha の "0.15.1" を追加した場合、`scaffold.py --refresh`（stamp 判定）や `test_v013_contracts`（最新キー判定）で壊れる経路はないか。ADOPTION の refresh 列挙文（0.14.0 が現行文で欠けている）をどう直すべきか。
6. `tests/test_release_handoff.py` の in-place 再ターゲット（#56→#65、#59/#63/#66 が open のままという負契約）で、既存 method の意味が失われるものはないか。release-handoff.sh の複製で v0.15.0 固有のロジック（PRECLOSED 等）が残ると誤動作する箇所はないか。
7. 完了条件（§6）が機械判定可能か。「対象 N 件を検査」の実数記録が欠けている検査はないか。常に PASS する検査はないか。
8. 変更範囲（§7）の許可一覧に、実装上どうしても必要なファイルの漏れはないか（逆に不要に広い許可はないか）。

## 出力形式

指摘ごとに: 番号／重大度（HIGH: 計画自体の欠陥・MEDIUM: worker 指示で吸収できる細部・LOW: 文言）／根拠（ファイル:行、または実測コマンドと出力）／推奨 1 つ。最後に「計画自体を直すべき HIGH の一覧」と「このまま実装に進めてよいか」の立場を 1 行で表明せよ。
