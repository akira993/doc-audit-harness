あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-code-review-followup`、main `ef995f0` 起点、engine v0.14.0 未 tag）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md`（最新 rev）を実装せよ。PLAN-cr1.md 全文を最初に読み、§0 A1〜A5・B6・C7〜C9・D10、§6 DoD、§7、§8 に従う。前提知識として `PLAN.md`（rev.8）§0-5/§0-6 と `REVIEW.md` 末尾（code-review 所見と Sol CR1-R1〜R5 の対応表）も読むこと。
不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。**`tasks/**`・`.claude/**` は読むだけで変更しない。** 既存ファイルの上書き・新規作成は本プロンプトで包括承認する（再確認不要）。単独で作業し、collab／サブエージェントは使わない。git commit は行わない。

## 実装項目（PLAN-cr1 §0 を正とする。要点のみ）
- **A1** SKILL.md の harness 辞退 reopen 段落（:267-276 付近）: `open-run.py` の終了値・成功 JSON 確認 → 失敗は既存 exit-4/6 で停止 → 成功時のみ `RUNID`/`RUN_DIR`/`EVIDENCE` を束縛 → その直後に §0-A1 の固定文（verbatim。3 分岐の確認ゲート、`never reuse an earlier answer`、`if that gate evaluation permits the audit to continue, then continue with Phase 0.5 exactly once`）。契約テストは 5 要素の相対順を 1 本で固定（open-run 呼び出し → 停止文 → 束縛文 → 固定文（ちょうど 1 回）→ Phase 0.5 見出し）。
- **A2** :121 を `When the gate does not fire, or is skipped because PHASE3_BACKEND_CONFIG is codex, bind MDQ_DEGRADE="n/a".` に。:122 の記録文を `Whether the gate fired, did not fire, or was skipped because PHASE3_BACKEND_CONFIG is codex, always record the resulting MDQ_DEGRADE:` に（無条件記録）。:100 の mdq-health 失敗時に固定 JSON `{"files":0,"chunks":0,"searchSmoke":false,"healthy":false,"status":"probe-error"}` を `MDQ_HEALTH_PROBE_JSON` に束縛して記録する文。
- **A3** :153 の CM 合成説明: available:false → `contextModeHealthy` 常に `null`、available:true で `CM_HEALTHY` 未束縛 → `false`／`status:"probe-error"`（固定文）。`test_probe_record.py` に正規化後 2 形の write→read→`rebind.context-mode` 完全一致。
- **A4** unknown 7 行を `⚠ <name>: state unknown (probe record unavailable) [non-blocking]` に、codex 接尾辞を `(caller info unavailable)` に（SKILL 全体でちょうど 1 回 — 共通規則文には literal を書かない）。SKILL 再開段落の固定文・`docs/ADOPTION.md`／`ADOPTION.ja.md` §7 ④（**その 1 句のみ置換、周辺文言不変**: en `state unknown after resume` → `state unknown (probe record unavailable)`（前後の `print` は s なしのまま）、ja `「state unknown after resume」` → `「state unknown (probe record unavailable)」`）・`test_v014_contracts.py`（:28 の期待も `and print "state unknown (probe record unavailable)"`）を同時更新。旧文言は grep 0。SKILL に 1 文「A `⚠ probe-record: <seam> not recorded` warning earlier in the run explains a later unknown line; do not substitute conversation values.」。
- **A5** :757 `When CODEX_REVIEW_AVAILABLE=true, append` → `When rebind.codex-review.available is true, append`（診断文も同様）。
- **B6** Phase-5 状態行節の冒頭に共通規則文（§0-B6 verbatim、`(caller info unavailable)` の literal を含めない）。**表の並べ替えは行わない**（現行順序は既に正しい）。契約テストで現行順序を assert: 6 表は unknown 枝が先頭・`invalid-config` 枝がその後かつ他の枝より前、codex-review は invalid-config → reviewState=null → 4-way。`test_v0132_contracts.py` の `6-state`/`8-state` ラベルには触れない。
- **C7** `test_probe_record.py` に display の U+0085/U+2028/U+2029/`\n` 1 行性回帰テスト（`probe-record.py` は変更しない）。
- **C8** `codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh`: `bin` に ASCII 制御文字（U+0000–U+001F, U+007F）→ `invalid-config`。`enabled:false` 先勝ちを維持し、disabled 分岐の不正 bin（空・非文字列・制御文字）は出力 bin を既定名に。既存 `emit` 前の判定のみ変更（キー集合・reason 集合不変）。`config-schema.md` の**表の 3 行（:37/:38/:39）のみ**に §0-C8 の文言。`## codegraph`／`## graphify`／`## CocoIndex` 節の `Its probe reasons are` 以降には追記しない（`test_v0132_contracts.py:248` が固定、編集禁止ファイル）。テスト（各 probe）: enabled 33 文字全走査、disabled 33 文字全走査（`disabled-by-config`＋既定 bin＋sentinel 不起動）、内部スペース入りディレクトリの実行ファイル正例、全 reason 分岐のキー集合完全一致。
- **C9** :193 を §0-C9 の新文言に（`test_v014_contracts.py:90` も更新）。
- **D10** `tests/test_{mdq_index,ax_probe,codex_probe,probe_record}.py` の `mkdtemp` を `TemporaryDirectory`（`with`/`addCleanup`）に統一（識別子 `mkdtemp` 0 件）。`test_codex_probe.py` の `test_output_key_sets_per_branch` エイリアス重複を 1 本に。

## 完了条件（PLAN-cr1 §6 (1)〜(8)。固定テスト名と `Ran N` を報告）
（PLAN-cr1 §6 を verbatim で適用。特に: (1) 契約テスト群、(2) display 1 行性、(3) enabled 33＋disabled 33＋空白パス正例＋全分岐キー集合、(4) `mkdtemp` 0、(5) フルスイート rc=0・skip 0、(6) 禁止ファイル差分なし、(7) scope-check、(8) ADOPTION 単一置換 bytes 一致。）

## 変更範囲（PLAN-cr1 §7）
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`（§7 ④ の 1 句のみ）、
`tests/{test_probe_record.py,test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py}`。
**禁止**: 上記以外（特に `probe-record.py`、`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`、`decide-verdict.py`、`start-run.py`、`write-evidence.py`、`open-run.py`、`mdq-health.py`、`.claude-plugin/plugin.json`、`engine-shas.json`、`tests/test_v013_contracts.py`／`test_v0132_contracts.py`／`test_v0131_docs_contracts.py`（変更が必要になったら報告）、`tasks/**`、`.claude/**`）。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 検証コマンド一式（PLAN-cr1 §8 を verbatim で実行。`<boss commit>` は `git log --oneline -1 -- tasks/route/2026-08-28-issues-56-60/allowlist.txt` の sha）。すべての exit code と要点を報告。

## 報告形式
Markdown で: (1) 変更ファイルと要点、(2) DoD 番号ごとの固定テスト名と `Ran N`、(3) 検証コマンドの結果（失敗は出力ごと）、(4) PLAN との乖離・許可外変更が必要だった点・未実施（無ければ「無し」）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
