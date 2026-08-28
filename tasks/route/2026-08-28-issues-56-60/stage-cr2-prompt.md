あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-code-review-followup`、PR #62、cr1 実装 `04a0624` の上に追加 commit する）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md`（最新 rev）を実装せよ。PLAN-cr2.md 全文を最初に読み、§0 A1〜A4・B5〜B6・C7〜C10、§6 DoD (1)〜(10)、§7、§8 に従う。前提として `PLAN-cr1.md`（rev.7）と `REVIEW.md` 末尾（code-review 15 件と Sol cr2-R1〜R5・Opus の対応表）も読むこと。
不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。**`tasks/**`・`.claude/**` は読むだけで変更しない。** 既存ファイルの上書き・新規作成は本プロンプトで包括承認する（再確認不要）。単独で作業し、collab／サブエージェントは使わない。git commit は行わない。
**特に重要**: cr1 で worker 実装がテストの fixture を壊した（`setUp` の到達不能文、迷子 assert、DoD のテストを名前だけ作って中身を省略）。本 Stage では §8 の AST 検査・`-v` ログ検査・期待段落検査が**すべて機械的に通る**ことを自分で確認してから報告せよ。

## 実装項目（PLAN-cr2 §0 を正とする）
- **A1** SKILL.md:154 の CM 合成指示を §0-A1 の文（verbatim、3 キー明示）に置換。
- **A2** Phase-5 codex-review 表を §0-A2 の 5 行の条件句で書き直す（invalid-config → `review state not recorded`（state=complete かつ reviewState=null、caller 接尾辞あり）→ `state unknown (probe record unavailable)`（state=unknown かつ reviewState=null、接尾辞なし）→ 4-way（state=complete: `not-active` は `(<rebind.codex-review.reason>)`、`available` true で caller 接尾辞）→ 4-way（state=unknown: `not-active` は `(reason unavailable)`、reviewState ∈ {completed, execution-failed} のときのみ ` (caller info unavailable)`）。共通規則文の codex 部分を「invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way」に。
- **A3** :124 の無条件記録文に `Fix mdq first` 分岐の例外句。
- **A4** 優先順位段落を mdq 表の導入文と箇条書きの間から外し、`PROBE_REBIND` 段落直後の独立段落へ（count 1 維持）。
- **B5** 6 probe（`mdq-index.sh`/`ax-probe.sh`/`codex-probe.sh`/`codegraph-probe.sh`/`graphify-probe.sh`/`cocoindex-probe.sh`）: `bin` 検証条件を統一（文字列・非空・`bin == bin.strip()`・空白のみ不可・ASCII 制御文字 U+0000–U+001F/U+007F 不可・UTF-8 エンコード可）。違反は `invalid-config`。`enabled:false` 先勝ちで **disabled 時の出力は既存 3 形を維持**（mdq: `bin` 無し／ax・codex: 既定名／graph: 妥当なら保持・不正なら既定名）。6 probe の `command -v "$BIN"` を `command -v -- "$BIN"` に。伝送出力は `sys.stdout.buffer.write(...)` で UTF-8 直書き（graph は行を組み立て `.encode("utf-8")` を try 内で検証してから 1 回だけ書く。CLI の base64 復号側も buffer へ）。graph 3 probe は `bin_name` を 1 回束縛し `valid` を 1 つ計算して両分岐で使う。
   `config-schema.md`: 6 seam の**表の行のみ**を §0-B5 の統一文（`ASCII-control-character (U+0000–U+001F or U+007F)` を含む）に更新し、disabled 出力の seam 別句を graph 3 行に含める。`Its probe reasons are` 以降には触れない。
- **B6** ADOPTION en/ja §7 v0.14.0 段落: ① の句置換（en `a non-string, empty, or NUL-containing bin` → `a non-string, empty, whitespace-only, whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable bin`、ja `文字列でない、空、NUL を含む` → `文字列でない、空、空白のみ、前後に空白がある、ASCII 制御文字（U+0000–U+001F または U+007F）を含む、または UTF-8 に符号化できない`）と ⑦ の追加（en は先頭スペース 1 つ付きで段落末尾に連結、ja は区切り無し — §8 の生成コードと同一文）。段落外は変更しない。`test_v014_behavior_changes_paragraph` を en 7・ja 7 に。
- **C7** `test_mdq_index.setUp` に `write(docs/a.md)` を戻し、`test_setup_creates_corpus` を追加。**C8** `test_graphify_probe.test_disabled_by_config` に `assertFalse(out["gitignoreOk"])` を戻し、既存の制御文字テストは迷子 assert を除くだけで温存（**既存メソッド名の改名・削除は一切禁止** — `04a0624` の全テスト名が残ることを §8 が機械判定する。codex のエイリアス `test_output_key_sets_per_branch`／`test_caller_keys_present_in_every_branch` も両方温存）。
- **C9** 6 probe テストに `test_bin_boundary_table`（33 制御文字を途中配置 × enabled/disabled、空白 5 種 `{bin_ws_lead, bin_ws_trail, bin_ws_both, bin_ws_nbsp, bin_wsonly}` ＋ `bin_surrogate` × enabled/disabled、`enabled:false`＋妥当カスタム bin は seam 別 3 形；テスト内で制御文字集合 `set(range(32))|{127}` を完全一致 assert；sentinel は既定名 stub・各負例の bin 値・trim 後名の全 marker が不変）、`test_bin_positive_paths`（正例 ID 集合 `{space_path, non_ascii_path, quote_backslash, dash_name}` を完全一致 assert。非 ASCII は `PYTHONIOENCODING=ascii` 環境。stub 起動: codex は `--version`＋`exec --help` の 2 回を引数列完全一致、他 5 本は 1 回。出力キー: mdq `bin`／ax `axBin`／codex `codexReviewBin`／graph `symbolGraphBin`・`docGraphBin`・`semanticSearchBin`）、graph 3 probe に `test_output_key_sets_per_branch`（PLAN 固定の reason 集合を実際に生成し集合完全一致＋各分岐キー集合）。CLI 3 ファイルの判定表 ID は `{既存 20} ∪ {bin_ws_lead, bin_ws_trail, bin_ws_both, bin_ws_nbsp, bin_wsonly, bin_surrogate}` を完全一致（26。既存 `test_config_decision_table_v014` を拡張。`test_bin_boundary_table` は CLI では 33 制御文字 × enabled/disabled のみ、graph では空白 5 種＋surrogate × enabled/disabled も含む）。33 文字全走査は 6 probe すべて。`test_codex_probe.py:233` の改行入り正例は引用符・バックスラッシュ・内部スペースの正例に置換し、改行は負例へ。
- **C10** `test_cr1_reopen_gate_and_status_order_contracts` の固定 JSON 検査を `normalize_paragraphs()` 経由に（改名しない）。`test_v014_contracts.py` に `test_cr2_codex_state_table_and_cm_shape`（A1 の合成文がちょうど 1 回、A2 の 5 条件句と順序、A3 例外句、A4 段落位置）と `test_cr2_config_schema_bin_rows`（schema 6 行の境界条件句と seam 別 disabled 句）を追加。`test_probe_record.py:221` の兄弟 symlink に `addCleanup(os.unlink, link)`。

## 完了条件・変更範囲・検証コマンド
PLAN-cr2 §6 (1)〜(10)（(8) 機械検査・(9) schema 6 行・(10) CM 合成指示）、§7、§8 を verbatim で適用。`<boss commit>` は `git log --oneline -1 -- tasks/route/2026-08-28-issues-56-60/allowlist.txt` の sha。§8 の各 python 片（CM/AST/-v ログ検査、ADOPTION 期待段落検査）はそのまま実行し、出力（`tests-ast-clean`／`adoption-paragraph-clean`／`scope-clean`）を報告に貼ること。
**禁止**: `probe-record.py`、engine（`decide-verdict.py` 等）、`tests/test_v013_contracts.py`／`test_v0132_contracts.py`／`test_v0131_docs_contracts.py`、`tasks/**`、`.claude/**`。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 報告形式
Markdown で: (1) 変更ファイルと要点、(2) DoD 番号ごとの固定テスト名と `Ran N`、(3) §8 全コマンドの結果（失敗は出力ごと）、(4) PLAN との乖離・許可外変更が必要だった点・未実施（無ければ「無し」）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
