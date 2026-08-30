あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド2: PLAN rev.2 の再批判

`tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md` を rev.2 に改訂した（rev.1 は同ディレクトリの `PLAN.rev1.md`）。前回指摘との対応（自己申告）を先に列挙する。boss は各指摘を実物で照合した（codegraph 1.5.0 の `directory.js` 読解、`codegraph.db` をディレクトリにした実機テスト: `init` rc=0・`sync` rc=1、`grep -c` 実数、`git ls-files`）。

## 前回指摘との対応

1. （HIGH 非通常ファイルで偽 ok）→ §5.1 を 7 行の分岐表に置換。通常ファイル→`sync`、不存在→`init`、存在する非通常（ディレクトリ・FIFO 等）→不実行・`index-failed`・stderr。
2. （HIGH `CODEGRAPH_DIR` 無視）→ §5.1 前処理で codegraph 1.5.0 と同じ妥当性規則（trim・空／`.`／`..` 含む／`/`／`\`／絶対パス → 既定）を bash で複製。テスト N10〜N12。
3. （HIGH 親 symlink）→ 分岐表 行1（dir が symlink）・行2（dir が非ディレクトリ）を不実行・`index-failed` に。テスト N8・N9。
4. （HIGH テスト件数矛盾・誤実装が通る）→ 現行 20 を基準に N1〜N14 を列挙（`.gitignore` のみ→init の N2 を含む）、合計 ≥32・既存名称全数維持・fake の log 実体で「呼ばれた／呼ばれていない」を判定・stderr 文言・厳密 3 キー JSON を明記（A2・B1）。
5. （HIGH #66 置換範囲 13 行・gate exit）→ 対象を 13 行（SKILL.md:3 description、ADOPTION.ja.md:11/79 を含む）に訂正、許可範囲に SKILL.md:3 を追加、ゲートは `! grep -rnE ...` の単一コマンド（A4、着手前 13 行ヒットを記録）。
6. （HIGH 版更新の同期漏れ）→ test_scaffold 7 箇所（行番号列挙）・test_v013_contracts:201,210,215 を明示（§5.5）。
7. （MEDIUM refresh 列挙・直前版互換）→ engine-shas の 0.15.1 以外の全キー（0.10.0〜0.15.0）を昇順列挙、0.15.0 stamp→0.15.1 の直接 refresh テストを test_scaffold に追加。
8. （HIGH handoff の追跡・スコープ検査）→ `git add -f` 必須（A6 `git ls-files` = 1）、スコープ検査は `git diff main...HEAD` ＋ `git status --porcelain` の和集合と許可集合の差（A8）。
9. （MEDIUM handoff 残骸・#66 OPEN 条件）→ A7（`v0.15.0|#56|webExtract|codexReview` の出現 0）、#59/#63/#66 の OPEN 事前条件と test_release_handoff の #66 版 method 追加（§5.6）。
10. （MEDIUM v0.15.1 ブロック）→ test_v015_contracts.py を許可範囲に追加し en/ja 完全一致テストを追加（§5.5・A5）。
11. （MEDIUM §6 が機械判定でない）→ §6 を A（機械ゲート 10 項目: コマンド→期待・実数記録）と B（boss 検収 5 項目: 記録項目）に分離。

## 依頼

rev.2 を読み直し、**新規の**指摘のみを挙げよ（対応済み事項の再指摘は不要。対応が不十分な場合はその旨を番号で示せ）。特に:
- 分岐表 §5.1 の順序・網羅性（7 行で全状態を尽くしているか、順序依存の穴はないか）。`CODEGRAPH_DIR` の複製規則が codegraph 1.5.0 と食い違う入力はないか（例: 前後空白、`.codegraph` 自体を指定、大文字小文字、Unicode）。
- N1〜N14 で「正しい実装でも誤った実装でも通る」ものが残っていないか。fake codegraph の設計（log 方式）でこれらが判定可能か。
- A1〜A10 の期待値・コマンドが実際に機械判定として成立するか（A8 の porcelain 解析の穴、A4 の `-E` と `|` の扱い、A1 の下限値の妥当性）。
- §7 の許可範囲の過不足。

出力形式は前回と同じ（番号／重大度／根拠／推奨 1 つ、末尾に「計画自体を直すべき HIGH の一覧」と「実装に進めてよいか」の 1 行）。
