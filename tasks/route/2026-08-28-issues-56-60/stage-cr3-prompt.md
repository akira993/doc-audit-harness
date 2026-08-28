あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-code-review-followup`、PR #62、cr2 実装 `79938a5` の上に追加 commit する）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md`（最新 rev）を実装せよ。PLAN-cr3.md 全文を最初に読み、§0 の修正 1〜3、§6 DoD (1)〜(6)、§7、§8 に従う。
不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。**`tasks/**`・`.claude/**` は読むだけで変更しない。** 既存ファイルの上書きは本プロンプトで包括承認する。単独で作業し、collab／サブエージェントは使わない。git commit は行わない。
**特に重要**: 過去 2 回、worker 実装は「テスト名だけ作って中身が薄い」「fixture を壊す」で差し戻された。§8 の python 片（`tests-clean`／scope-clean）と `Ran N ≥ 609` が**機械的に通る**ことを自分で確認してから報告せよ。既存テストの改名・削除は禁止（`79938a5` の全 TestCase メソッド名が残ることを §8 が判定する）。

## 実装
1. 6 probe（`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`／`codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh`）の JSON emit **9 か所**から `ensure_ascii=False` を除去（既定 `True`）。`sys.stdout.buffer.write((json.dumps(...)+"\n").encode("utf-8"))` の形は維持。graph の `emit()` 内の `line.encode("utf-8");` 検証行は**残す**（削除しない）。`grep -c 'ensure_ascii=False' skills/audit/scripts/*.sh` の合計が 0。
2. 6 probe テストに `test_json_emit_is_ascii_one_line` を追加（TestCase メソッド）。PLAN §0-2 のとおり **9 emit をすべて実行経路で通す**:
   - 各 probe: bin `"to ol-none"`（validation 通過）で not-installed 経路。
   - U+2028 を名前に含む実行可能 stub を PATH に置き、mdq の `indexed`（stub rc 0）と `index-failed`（stub rc 1）、ax の `ok`（stub の `--version` 出力に **U+2028** を含める: `printf 'ax 1.0-\342\200\250x\n'`。`\xff` は使わない — macOS の `tr` が切り落とし判別力が無い）、codex の `ok`（`--version`＋`exec --help` に応答）、codegraph/graphify/cocoindex は not-installed 経路のみで足りる（emit サイトは 1 つ）。
   - 各出力を `subprocess.run(..., capture_output=True)`（**bytes**。CLI 3 本は `run_script` を経由しない）で受け、(i) `raw.isascii()`、(ii) `raw.decode().splitlines()` が 1 行、(iii) `json.loads` で bin（ax は version `ax 1.0-\u2028x` も）が完全一致。
   - codex はさらに `env` に `CODEX_HOME=b"/tmp/h\xffome"`（bytes 値。`subprocess.run(env={...bytes...})` は POSIX で可）を与え、stdout が空でなく 1 行の妥当 JSON、`os.fsencode(out["callerCodexHome"]) == b"/tmp/h\xffome"`。
3. `probe-record.py`・SKILL.md・docs・他テストは変更しない。

## 完了条件・変更範囲・検証
PLAN-cr3 §6 (1)〜(6)、§7、§8 を verbatim で適用（`<boss commit>` は `git log --oneline -1 -- tasks/route/2026-08-28-issues-56-60/allowlist.txt` の sha、`BASE_COMMIT=79938a5`）。§8 の各コマンドの出力（`tests-clean`／`forbidden-clean`／`scope-clean`／`Ran N`）を報告に貼ること。

## 報告形式
Markdown で: (1) 変更ファイルと要点（9 emit の行番号）、(2) 新テスト 6 本が通した emit の一覧、(3) §8 全コマンドの結果、(4) PLAN との乖離（無ければ「無し」）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告
- **スコープ規律**: 要求以上の機能追加・リファクタ禁止。動く最小をやる
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
