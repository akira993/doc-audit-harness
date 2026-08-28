あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-issues-56-60`、engine v0.13.2）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN.md`（rev.7）の **Stage S1a** を実装せよ。PLAN.md 全文を最初に読み、§0-4（#58）・§0-5（#56 第 1 段）・§0-7（#59 最小案）・§0-8（#60）と §6 の該当 DoD、§7、§8 に従う。
不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。**PLAN.md・REVIEW.md・allowlist.txt・baseline-hashes.txt・59-design-note.md・scope-check.py は読むだけで変更しない。**

## S1a の範囲（PLAN §0-9）
1. **#58**（§0-4）: `skills/audit/scripts/import-audit-scope.py` の `safe_path` と `main()` のみ。`docaudit_paths.py` は変更しない。テスト `test_absolute_path_cases_v014`（20 ID、明示 symlink fixture、`len(CASES)==20`＋ID 集合 assert）。
2. **#56 第 1 段**（§0-5）: `mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh` の config 読み取りを判定表（行 1〜10、20 ID: `absent, empty, disabled, en_str, en_int, en_null, key_null, key_true, key_str, key_list, cfg_omitted, cfg_empty, cfg_missing, cfg_broken, top_list, top_null, bin_int, bin_empty, bin_nul, compound`）に合わせる。
   評価順序・出力形（既存分岐のキー集合不変、`invalid-config` は not-installed 形、`bin` は既定名、全分岐 exit 0・JSON 1 行）は §0-5 のとおり。`--config ""` は `invalid-config`（`CONFIG=""` を未指定の印に使わず、指定有無を別フラグで持つ）。
   SKILL.md: `CM_ENABLED` の 3 値式（§0-5 の式を verbatim で掲載）、mdq 確認ゲート（:95）に `invalid-config` を追加、Phase 0 で `MDQ_REASON`／`AX_REASON` を束縛、Phase-5 に `invalid-config` 枝 3 本（固定文言、mdq 枝は `MDQ_AVAILABLE` false の 💡 行より**前**）、
   reason 列挙 **mdq 散文（:80-81）・ax（:138）・codex（:151）の 3 か所のみ**に `invalid-config`（graph 3 seam の列挙は不変）、probe 段落に「行 6〜8 は probe 単体呼び出し時の防御。読めない config は Phase 0 前に停止する」の 1 句。
   `config-schema.md:33-36` の 4 行を §0-5 の文言で更新。`test_codex_review_plan.py::test_invalid_config_reason_passes_through`（完全一致 JSON）、`test_decide_verdict.py::test_required_with_not_active_state_is_refused`（engine 変更なし。既存同等テストがあればその名前を報告し新設不要）、
   `test_v0132_contracts.py::test_probe_reason_enumerations_match_fixed_sets` の ax/codex 集合更新、`tests/test_v014_contracts.py`（新規）に DoD (5)(6) の契約テスト（`test_cm_enabled_expression_decision_table` は SKILL からコードスパンを抽出し 13 ID `absent, empty, disabled, en_str, en_int, en_null, key_null, key_true, key_str, key_list, cfg_broken, top_list, top_null` で実行）。
3. **#59 最小案**（§0-7）: SKILL.md Phase 4 の codex review 段落末尾と ADOPTION en/ja の codex 段落に固定文の運用注記。契約テスト `test_codex_review_convergence_note`（段落正規化 `" ".join(p.split())` でバッククォート除去後 `assertIn`）。
4. **#60**（§0-8）: `codex-probe.sh` の出力に全 5 分岐で `callerCodexHome`／`callerCodexHomeSource`／`callerAuthFile`。JSON 出力全体を `python3 -c` の `json.dumps` で生成（`tr -d` sanitizer 廃止。`bin`・version も含む）。availability は変えない。
   SKILL.md: Phase-5 codex 行の `CODEX_REVIEW_AVAILABLE=true` 全枝に caller 接尾辞（3 値は `rebind` から — S1b が `probe-record.py --read` を供給する。S1a では文言だけ書く）、`execution-failed`＋`absent` の診断文、Phase 4 実行行直後の env 注記 1 文。**SKILL に表示用の python -c 式（`callerCodexHome"]` を含む式）を置かない。**
   `config-schema.md:228-236`・`ADOPTION.md:122-126`／ja 対応段落に wrapper と caller 表示の限界。テスト: `test_caller_codex_home_and_auth_file`（7 ID、最小 env ＝ `{"PATH": os.environ["PATH"]}`＋ケース別 HOME/CODEX_HOME）、`test_caller_keys_present_in_every_branch`（5 分岐、probe-exec-failed は `exec --help` が非 0 の偽 bin）、`test_json_escaping_of_bin_and_home`、契約テスト DoD (9)。

## 完了条件（PLAN §6 の S1a 分＋共通。固定テスト名を Stage 報告に列挙せよ）
- (1) `test_import_audit_scope.py::test_absolute_path_cases_v014`（20 ID、明示 symlink fixture）。`:618` の既存 symlink 拒否テスト不変。
- (2) `git diff --quiet dfdb8a9 -- skills/audit/scripts/docaudit_paths.py`。
- (3) `test_mdq_index.py`／`test_ax_probe.py`／`test_codex_probe.py` 各 `test_config_decision_table_v014`（20 ID）: `invalid-config` 全ケースで偽 bin の sentinel が書かれない、`cfg_*`／`top_*` は helper を通さず直接、`bin` 値は seam 既定名。各 `test_output_key_sets_per_branch`（mdq 5・ax 4・codex 5）。
- (4) `test_codex_review_plan.py::test_invalid_config_reason_passes_through`（完全一致）、`test_decide_verdict.py::test_required_with_not_active_state_is_refused`（engine 変更なし）。
- (5) `test_v014_contracts.py`: `reason` 列挙 3 か所に `invalid-config`、ゲート文に `invalid-config`、Phase-5 `invalid-config` 行 3 本が各 1 回だけ＋mdq 枝の順序、`test_cm_enabled_expression_decision_table`（13 ID 実行）、`AX_REASON`／`MDQ_REASON` 束縛が Phase 0 節内、probe 段落の防御 1 句。
- (6) `test_config_schema_four_seams_invalid_config`。
- (7) `test_v014_contracts.py::test_codex_review_convergence_note`。
- (8) `test_codex_probe.py::test_caller_codex_home_and_auth_file`（7 ID）、`test_caller_keys_present_in_every_branch`（5 分岐）、`test_json_escaping_of_bin_and_home`。auth 不在でも `codexReviewAvailable:true`。
- (9) `test_v014_contracts.py`: Phase-5 codex 接尾辞が `rebind` の 3 値を使う固定文、診断文、Phase 4 env 注記、`config-schema.md`・ADOPTION en/ja に `CODEX_HOME`＋`wrapper` 段落各 ≥1、SKILL に表示用 python -c 式が無い（`grep -c 'callerCodexHome"\]' skills/audit/SKILL.md` = 0）。
- (15) フルスイート green・skip 0（`-v` 出力に ` ... skipped` 0 行）。`Ran N` の実数を報告。
- (16) `bash -n` 3 probe、`py_compile` 変更 .py。
- (18) 禁止ファイルに差分無し（§8 の `git diff --quiet dfdb8a9 -- …` が真）。
- 既存テストの規約: `tests/test_v013_contracts.py`／`test_v0132_contracts.py`／`test_wp12_contracts.py`／`test_harness_contract.py` が固定する SKILL.md の文言・順序・出現回数を壊さない（壊れたら原因と、PLAN が想定していない場合はその旨を報告。勝手に既存テストを緩めない）。

## 変更範囲（PLAN §7）
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{import-audit-scope.py,mdq-index.sh,ax-probe.sh,codex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
`tests/{test_import_audit_scope.py,test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codex_review_plan.py,test_decide_verdict.py,test_v0132_contracts.py,test_v014_contracts.py(新)}`。
（S1a では `probe-record.py`・`test_probe_record.py`・`engine-shas.json`・`plugin.json`・`test_scaffold.py`・`test_v013_contracts.py`・`test_release_handoff.py` に触れない — S1b/S2 の範囲。）
**禁止**: `skills/audit/scripts/{decide-verdict.py,start-run.py,docaudit_paths.py,write-evidence.py,docaudit_cache.py,mdq-health.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh,scaffold.py,write-template.py,open-run.py,seal-run.py,read-manifest.py,tree-digest.py,codex-dispatch.py,plan-dispatch.py}`、
`skills/audit/references/codex-review-output.schema.json`、`data/**`、`tests/data/**`、`skills/init/SKILL.md`、`agents/**`、`.gitignore`、`.envrc`、`.serena/**`、`docs/superpowers/**`、`.claude/**`、`tasks/**`（ログ以外）。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。** git commit は行わない（boss が行う）。

## 検証コマンド一式（PLAN §8 の S1a 分。すべて実行し、出力の要点と exit code を報告）
```
python3 -m unittest discover -s tests -t . -v > /tmp/s1a-full.log 2>&1; tail -3 /tmp/s1a-full.log; test "$(grep -c ' \.\.\. skipped' /tmp/s1a-full.log)" -eq 0 || echo SKIP-FOUND
python3 -m unittest -v tests.test_import_audit_scope tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_codex_review_plan tests.test_decide_verdict tests.test_v0132_contracts tests.test_v014_contracts
python3 -m unittest -v tests.test_v013_contracts tests.test_wp12_contracts tests.test_harness_contract
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh
python3 -m py_compile skills/audit/scripts/import-audit-scope.py
test "$(grep -c 'callerCodexHome"\]' skills/audit/SKILL.md)" -eq 0 || echo DISPLAY-EXPR-FOUND
git diff --quiet dfdb8a9 -- skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/docaudit_paths.py skills/audit/scripts/write-evidence.py skills/audit/scripts/docaudit_cache.py skills/audit/scripts/mdq-health.py skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/scaffold.py skills/audit/scripts/write-template.py skills/audit/scripts/open-run.py skills/audit/scripts/seal-run.py skills/audit/scripts/read-manifest.py skills/audit/scripts/tree-digest.py skills/audit/scripts/codex-dispatch.py skills/audit/scripts/plan-dispatch.py skills/audit/references/codex-review-output.schema.json skills/init/SKILL.md agents tests/data && echo forbidden-clean
git status --short
```

## 報告形式
最終回答は Markdown で: (1) 変更ファイル一覧と各ファイルの要点、(2) DoD 番号ごとの固定テスト名と `Ran N` 実数、(3) 検証コマンドの結果（失敗があれば出力ごと）、(4) PLAN と乖離した点・許可外変更が必要だった点・未実施の点（無ければ「無し」）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
