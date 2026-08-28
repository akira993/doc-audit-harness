boss 差し戻し（テスト diff の精読で PLAN-cr2 §6 DoD (2) の未達 5 点と SKILL の 1 点）。機械検査（603 OK・AST・-v ログ・ADOPTION 段落・scope）は boss 側で全て clean を確認済み。以下を修正し、単独作業・commit なしで報告せよ。

1. **graph 3 probe の `test_output_key_sets_per_branch`（PLAN §0-C9 / DoD (2)）**: 現状は absent／disabled／null の 3 分岐しか生成していない。PLAN が固定した reason 集合を**実際に生成**し、生成した reason の集合が固定集合と完全一致すること、各分岐の JSON キー集合が固定集合（codegraph/cocoindex 3 キー、graphify 4 キー）であることを assert せよ:
   - codegraph `{ok, not-installed, disabled-by-config, index-failed, not-configured, invalid-config}`
   - graphify `{ok, not-installed, disabled-by-config, update-failed, not-configured, invalid-config}`
   - cocoindex `{ok, not-installed, disabled-by-config, not-initialized, index-failed, not-configured, invalid-config, gitignore-modified}`
   生成方法は既存テストの fixture（stub の rc、`.cocoindex_code/settings.yml`、`.gitignore` 改変 stub 等）を再利用する。
2. **`test_bin_positive_paths` の起動 assert（6 probe）**: 正例ごとに stub の呼び出し記録（ARGLOG 等）を読み、**起動回数が codex は 2 回（`--version`、`exec --help` の引数列を完全一致）、他 5 本は 1 回**であることを assert する（現状は mdq が ARGLOG を書くだけで未検証、graph 3 本と ax/codex は記録すら無い）。加えて `dash_name` は **PATH 上に置いた `-x` という名前の stub を `bin:"-x"`（相対名）で指定**する（`command -v -- "$BIN"` の修正を識別するため。絶対パス `…/-x` では旧実装でも通る）。
3. **`enabled:false`＋妥当カスタム bin の 3 形（DoD (2)）**: 6 probe テストに 1 ケースずつ追加 — `{"enabled":false,"bin":"<valid custom name>"}` に対し mdq は `bin` キー無し、ax・codex は既定名、graph 3 本はカスタム値保持（かつ stub 不起動）。
4. **sentinel の網羅（PLAN §6 (8)(f)、Sol CR2-31）**: `test_bin_boundary_table` の負例では、既定名 stub に加えて **各負例の bin 値そのもの（パスとして解決可能なもの）と空白除去後の名前**も marker 付き stub として PATH に置き、全 marker が不変であることを確認せよ（現状は既定名のみ）。graph 3 本の `_default_stub` の `tempfile.mkdtemp()` は `TemporaryDirectory`＋`addCleanup` に置換してよい（必須ではない）。
5. **SKILL.md の共通規則文**: 現在 `Within each status-line table the first matching bullet wins; for codex-review use invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way.` に短縮され、6 表の順序記述が落ちている。次の文に置換せよ（1 回のみ、`PROBE_REBIND` 段落直後の独立段落）:
   `Within each status-line table the first matching bullet wins: the whole-record unknown bullet (when the table has one) comes first, the invalid-config bullet second, then the remaining states; for codex-review use invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way.`
   `test_v014_contracts.py` の `rule` 期待値を同じ文に更新。
6. 実施後: PLAN-cr2 §8 の全コマンド（フルスイート → `/tmp/cr2-full.log`、AST/-v ログ片、ADOPTION 段落片、`BASE_COMMIT=ef995f0 SCOPE_COMMIT=0cec02a BOSS_COMMIT=0ec2401 python3 tasks/route/2026-08-28-issues-56-60/scope-check.py`）を実行し、`Ran N`・各片の出力を報告。PLAN との乖離は「無し」か具体的に。
