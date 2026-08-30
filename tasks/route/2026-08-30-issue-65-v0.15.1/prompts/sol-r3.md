あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド3: PLAN rev.3 の再批判

`tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md` を rev.3 に改訂した（rev.2 は `PLAN.rev2.md`）。前回指摘との対応（自己申告）:

1. （HIGH `CODEGRAPH_DIR` 同値性）→ 規則の複製精度に依存する設計をやめ、**probe が解決した `DIRNAME` を `CODEGRAPH_DIR` として codegraph に明示エクスポート**する（§5.1 前処理）。解決済み値は codegraph 側の trim・妥当性検査で不変なので同じディレクトリを見ることが構成的に保証される。trim は JS `String.prototype.trim()` と同じ明示文字クラス（Python `str.strip()` 禁止、理由付き）。N12 を無効 9 入力／有効 7 入力の表に拡張（`foo..bar`、`a\b`、NBSP、BOM、`\x1c` 先頭＝JS は剥がさない、大文字、Unicode、`.codegraph` 明示）。
2. （HIGH FIFO 一般化）→ N5b（db が FIFO）・N9b（dir が FIFO）を追加。
3. （HIGH 件数矛盾）→ probe 20→≥33（N1〜N14 で新規 ≥13）、handoff 実測 24→≥26、全体 ≥647。N14 相当の既存 method 拡張は「改修 2」として明示例外。
4. （HIGH パイプで失敗が exit 0）→ §5.7 に単一 `gate.py`（G1〜G10、明示比較・実数表示・`GATE PASS/FAIL`）を新設し、A2 として **変更前ツリーで FAIL することを boss が実測**する（常に PASS する検査でない証明）。
5. （HIGH A8 の変更集合）→ G8: `git diff --name-only -z base...HEAD` ∪ `git status --porcelain=v2 -z --untracked-files=all`、rename/copy 両端、ignored は含めない（force-add 済みは tracked として現れる。理由を明記）、tempfile。
6. （HIGH fake が cwd/env 未記録）→ fake は JSON 行 `{argv,cwd,CODEGRAPH_DIR}` を記録し、全ケースで呼び出し回数・argv・cwd（realpath）・`CODEGRAPH_DIR` を完全一致判定。テストは継承 `CODEGRAPH_DIR` を除去。
7. （HIGH #66 挙動不変の契約）→ test_v015_contracts に回帰契約（`CODE_REVIEW_STATE=not-model-invocable` ≥3 箇所、`disable-model-invocation` ≥1、Phase-4 手順 3 の分岐文 2 種）。
8. （MEDIUM 旧意味残骸）→ G4 の残骸リストに「ユーザー実行のみ」「user-invocation-only」を追加し、5 語の出現数を表示（変更前実測（`grep -o` 集計）: not model-invocable 7・user-invocation-only 3・モデルから起動できない 2・モデルからは起動 2・ユーザー実行のみ 1 → 合計 15 出現／13 行）。
9. （MEDIUM 実行属性）→ G6: index mode 100755 ＋ X_OK。
10. （MEDIUM stderr 注入）→ `printf '%q'` で 1 行エスケープ（N14 で 1 行性を検査）。
11. （MEDIUM 不実行の証明）→ A3: 記録してから実物へ exec するラッパーを PATH 先頭に置き、db ディレクトリ・ケースで呼び出し 0 回を確認。
12. （MEDIUM force-add 範囲）→ 追跡ファイルを名指し（§5.6・§7）、`*-log.txt`・`PLAN.rev*.md` は追跡外（G10 で検査）。

## 依頼

rev.3 を読み直し、**新規の**指摘のみ（対応不十分は番号で）。特に:
- 「解決済み `DIRNAME` を明示エクスポート」の設計に穴はないか（codegraph が `CODEGRAPH_DIR` 以外の経路で dir を決めるケース、`init`/`sync` 以外の副作用、値が `.codegraph` に落ちたとき codegraph の警告が出ないことの是非、probe が env を上書きすることが verifier 側の `codegraph impact/node` 呼び出し（別プロセス・別 env）とずれる可能性）。
- gate.py の G1〜G10 に「常に PASS」または「正しい状態で FAIL」する定義がないか。G8 で ignored を除外する判断の穴。G3 の「改名先が存在」判定の弱さ。
- N1〜N14 の設計で fake の JSON 記録方式では判定できないものはないか。
- 上限 5 往復のうち 3 回目である。残る指摘は「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分して示せ。

出力形式は前回と同じ（番号／重大度／根拠／推奨 1 つ、末尾に HIGH 一覧と「実装に進めてよいか」の 1 行）。
