# PLAN-cr2 — PR #62 の `/code-review xhigh` 指摘 15 件の修正（rev.7, 2026-08-28 — Sol cr2-R1〜R5・Opus O1〜O3/N1〜N2 反映。実装承認）

## 0. 決定事項
ユーザー手順（継続）: 修正計画 → Sol → Opus → 実装 → commit → ユーザーが再 code-review。対象 branch は PR #62 の `fix/v0.14.0-code-review-followup`（同 PR に追加 commit）。版 0.14.0 据え置き、tag は最終 merge 後。
所見 15 件（CONFIRMED/PLAUSIBLE、テストは 585 green のまま見逃す欠陥）。boss の反省: cr1 検収でテスト差分（#2・#3・#9）を精読しなかった → 本 PLAN では**テスト差分の全行精読**を boss の DoD に加える。

### A. SKILL.md（#1・#5・#7・#8・#14）
1. **#1 `CM_PROBE_JSON` の形の復元**: :154 を「synthesize `CM_PROBE_JSON` as exactly `{"contextModeAvailable":<CM_AVAILABLE>,"contextModeHealthy":<bool or null>,"status":"<CM_STATUS>"}` (JSON boolean/null values, not quoted text): when `CM_AVAILABLE` is false, `contextModeHealthy` is always `null`; when `CM_AVAILABLE` is true and `CM_HEALTHY` is unbound, normalize to `contextModeHealthy:false` and `status:"probe-error"`; otherwise use the bound values.」に（3 キー名を明示）。契約テストはこの 3 キー名の literal を Phase 0 節で assert。
2. **#5/#7 codex-review 行の状態分離**: `rebind.codex-review` の (state, reviewState) 組み合わせで枝を固定:
   | state（probe 記録） | reviewState | 行 | 接尾辞 |
   |---|---|---|---|
   | complete, reason=invalid-config | 任意 | `⚠ codex-review: doc-audit.json codexReview is invalid — …`（既存） | なし |
   | complete | null | `⚠ codex-review: review state not recorded [non-blocking]`（新設 — probe 記録はあるが Phase-4 state 記録が無い） | caller 接尾辞（記録値）を付ける |
   | unknown | null | `⚠ codex-review: state unknown (probe record unavailable) [non-blocking]` | なし |
   | complete | 非 null | 既存 4-way（`not-active` は `(<rebind.codex-review.reason>)`） | `available` true のとき caller 接尾辞 |
   | unknown | 非 null | 既存 4-way。`not-active` は `(reason unavailable)` と表示 | reviewState ∈ {completed, execution-failed} のときのみ ` (caller info unavailable)`（codex が実行を試みた枝のみ。`ref-invalid` は実行前 skip — Sol CR2-1。`not-active`/`skipped-full-run`/`phase4-not-required`/`ref-invalid` には付けない） |
   共通規則文は「codex-review: invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way」に更新。ADOPTION は変更不要（§7 ④ は unknown 文言の一般形のまま）。**SKILL には表 5 行の左辺条件（`state`／`reviewState`／`reason` の組）をそのまま箇条書きの条件句として書き、契約テストは 5 条件句の literal と順序を完全一致で固定**（Sol CR2-2 — モデル実行はテストできないため、条件句の文言を固定する）。
3. **#8 `Fix mdq first` 分岐**: :124 の無条件記録文に例外 1 句「（except on the gate's "Fix mdq first" branch, which releases the run and ends the audit before anything is recorded）」。
4. **#14 優先順位段落の位置**: mdq 表の導入文とその箇条書きの間から外し、`PROBE_REBIND` 段落（:651 付近）の直後に**独立段落**として置く（空行で区切る）。出現回数 1 は維持。

### B. probe の `bin` 検査（#4・#10・#11・#13 — 6 probe 共通契約）
5. **`bin` の有効条件を 6 probe で統一**: 文字列・非空・**前後に空白なし（`bin == bin.strip()`）・空白のみでない**・ASCII 制御文字（U+0000–U+001F, U+007F）を含まない・**UTF-8 にエンコード可能**（#11: lone surrogate — `json.loads('"\\ud800"')` は受理するため実設定から到達可）。違反は `invalid-config`。`enabled:false` 先勝ち。**disabled 時の出力値は既存 3 形を維持**（Sol CR2-4 再対応）: mdq は `bin` キー無し（`mdq-index.sh:55`）／ax・codex は `enabled:false` を bin 読取りより先に判定するため妥当なカスタム値でも既定名（`ax-probe.sh:35`、`codex-probe.sh:36`）／graph 3 probe は妥当なカスタム値を保持し、不正なときだけ既定名（`codegraph-probe.sh:40`）。検証条件だけを共通化し、出力形は変えない。DoD に「`enabled:false`＋妥当カスタム bin」の期待を 3 形で固定。内部スペースは許容。
   **#10（先頭 `-`）は bin の禁止ではなく `command -v -- "$BIN"` で解決**（Sol CR2-9 実測: `command -v -- -v` → rc 1。6 probe の `command -v` に `--` を付ける。`-dir/tool` のような値は引き続き有効）。
   **非 ASCII の実行パス（Sol CR2-6）**: 伝送出力は `sys.stdout.buffer.write((line+"\n").encode("utf-8"))` で UTF-8 バイトを直接書き（`print` を使わない — `PYTHONIOENCODING=ascii` 下で `é`／日本語パスが落ちる）、CLI 3 probe の base64 復号側も `sys.stdout.buffer` へ書く。6 probe すべてに `PYTHONIOENCODING=ascii` 環境での非 ASCII パス正例（stub が起動し `<seam>Bin` 完全一致）を追加。
   - graph 3 probe: python 判定で `bin_name` を 1 回束縛し `valid = …` を 1 つ計算して enabled/disabled 両分岐で使う（#13）。**出力行は文字列を組み立てて `.encode("utf-8")` を try 内で検証してから `sys.stdout.buffer` へ 1 回だけ書く**（部分出力後の except を防ぐ）。
   - CLI 3 probe（`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`）: 判定 python に同じ条件を追加（base64 伝送は不変）。**graph と同じ境界値表を適用**（Sol CR2-5）: 判定表 ID に `bin_ws_lead`（`" codegraph"`）・`bin_ws_trail`（`"codegraph "`）・`bin_ws_both`・`bin_ws_nbsp`（`"\u00a0codegraph"` — `str.strip()` は Unicode 空白も除くため拒否対象）・`bin_wsonly`（`"   "`）・`bin_surrogate`（`"\ud800"`）を追加（**26 ID**。Sol CR2-32）。33 制御文字は**文字列の途中**（`"to"+chr(c)+"ol"`）に配置＋ 33 制御文字 × enabled/disabled の全走査（invalid/disabled は sentinel 不起動）＋ 内部スペース正例・非 ASCII 正例（stub 起動 1 回・値完全一致）。**既存 `test_codex_probe.py:233` の改行入り bin 正例は、引用符・バックスラッシュ・内部スペースのみの正例に置き換え、改行は sentinel 付き負例へ移す**（Sol CR2-8 — 削除・弱体化ではなく移行）。
   - `config-schema.md`: 6 seam の行の `bin` 条件を統一文「a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config`」（Sol CR2-25 — U+0080–U+009F は拒否しない）（表の行のみ。`Its probe reasons are` 以降には触れない。Sol CR2-3／CR2-7）。disabled 時の出力は seam ごとに既存記述のまま（mdq: `bin` 無し／ax・codex: 既定名／graph: 妥当なら保持、不正なら既定名 — graph 3 行にはこの句を含める）。
6. **ADOPTION §7（#6）**: ① の句 `a non-string, empty, or NUL-containing bin` を `a non-string, empty, whitespace-only, whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable bin` に（ja: `文字列でない、空、NUL を含む` → `文字列でない、空、空白のみ、前後に空白がある、ASCII 制御文字（U+0000–U+001F または U+007F）を含む、または UTF-8 に符号化できない`。Sol CR2-20／CR2-25）、**⑦ を段落末尾に追加**（en は先頭に半角スペース 1 つを付けて連結: ` the symbolGraph / docGraph / semanticSearch probes now apply the same bin validation: a newly rejected bin reports invalid-config before the tool lookup, and with enabled:false an invalid bin is displayed as the default name.`、ja は区切り無しで連結: `symbolGraph / docGraph / semanticSearch の probe も同じ bin 検証を適用します。新たに拒否される bin はツール探索の前に invalid-config を報告し、enabled:false のときは不正な bin を既定名で表示します。` — 旧 reason を断定しない。Sol CR2-34 — 言語別の区切りは §8 の生成コードと同一。Sol CR2-19）。`test_v014_behavior_changes_paragraph` を en 7・ja 7 に。
   **段落全体の完全一致検査（Sol CR2-10）**: §8 の python 片で、`git show ef995f0:docs/ADOPTION*.md` の §7 v0.14.0 段落に対し「cr1 の unknown 句置換＋上記 ① 句置換＋末尾に ⑦ 文（en は先頭スペース付き、ja は区切り無し）を追加」を施した期待段落と、実ファイルの同段落が完全一致し、かつ段落外の差分が 0 行であることを検査。

### C. テストの修復と強化（#2・#3・#9・#15）
7. **#2 `test_mdq_index.setUp`**: `write(docs/a.md)` を `setUp` 内に戻す（`tmpdir()` は独立 helper のまま）。回帰防止: `setUp` 後に `os.path.exists(docs/a.md)` を assert するテスト 1 本。
8. **#3 `test_graphify_probe`**: `test_disabled_by_config` に `assertFalse(out["gitignoreOk"])` を戻す。**既存メソッド名は改名・削除しない**（DoD (8)(c) が `04a0624` の名前包含を要求）: 既存の `test_control_character_bins_are_rejected_or_normalized_when_disabled` は迷子 assert を除くだけで温存し、`test_bin_boundary_table` は**新規追加**（Opus O1）。**cr1 §D10 の「codex エイリアス統合」要求は撤回**し `test_output_key_sets_per_branch`／`test_caller_keys_present_in_every_branch` の両方を温存（Opus O2、DoD (8)(c) 優先。見送り一覧に記録）。
9. **#9 制御文字テストの sentinel**（graph 3 probe。CLI 3 probe は B5 の境界値表に含む）: 3 graph probe の制御文字/空白/surrogate テストは `_assert_unavailable(..., log)` 相当で **sentinel 不起動**を assert（enabled/disabled 両方）。**先頭 `-` の bin は負例ではない**（Sol CR2-37）: `dash_name` は enabled では stub 起動の正例、disabled では不起動（既存契約）。**内部スペース入りディレクトリの正例**（`bin` = `<tmp>/dir with space/<tool>` の stub、起動され `<seam>Bin` が完全一致）を 3 probe に追加。**cr1 DoD (3) で未実装のまま見逃された「全 reason 分岐の JSON キー集合完全一致」テスト（`test_output_key_sets_per_branch` 同型）も 3 graph probe に追加**（boss 精読で判明）。対象 reason 集合は PLAN で固定（Sol CR2-36）: codegraph `{ok, not-installed, disabled-by-config, index-failed, not-configured, invalid-config}`／graphify `{ok, not-installed, disabled-by-config, update-failed, not-configured, invalid-config}`／cocoindex `{ok, not-installed, disabled-by-config, not-initialized, index-failed, not-configured, invalid-config, gitignore-modified}`（`probe-record.py` の `GRAPH` 集合と同一）。テストは各 reason を実際に生成し、生成 reason 集合の完全一致と各分岐のキー集合（codegraph/cocoindex 3 キー、graphify 4 キー）を assert。
10. **#15 wrap 依存 assert**: `test_cr1_reopen_gate_and_status_order_contracts` の固定 JSON 検査を `normalize_paragraphs()` 経由に。
11. **#12 `scope-check.py`**（boss 工具、boss が修正）: `BASE_COMMIT` 未指定を error にする（default 撤廃）。

## 1. 目的
PR #62 の code-review 15 件を解消し、cr1 で入れた表示経路・probe 判定の穴（形の欠落、状態の矛盾、空白/dash/surrogate bin、テスト fixture の破損）を塞ぐ。verdict ロジック不変。

## 2. 入力・参照資料
`/code-review xhigh`（PR #62）所見、PLAN-cr1 rev.7、`SKILL.md`（:100-160, :640-800）、6 probe、`probe-record.py`（不変）、`config-schema.md`、`docs/ADOPTION*.md`、対象テスト。

## 3. 担当（boss） / 4. 実行者（worker）
boss Fable。worker: 単一 Stage Terra `medium`。差し戻しは resume。**boss はテスト差分を全行精読する。**

## 5. 成果物
`SKILL.md`（A1〜A4）、6 probe（B5）、`config-schema.md`（B5）、ADOPTION en/ja（B6）、テスト（`test_v014_contracts`、3 graph probe テスト、3 CLI probe テスト、`test_mdq_index` 修復）。`probe-record.py` 不変。`scope-check.py` は boss。

## 6. 完了条件（DoD、すべて非 0 終了で判定）
- (1) `test_v014_contracts.py`: A1 の 3 キー名 literal、A2 の表 5 行の固定文（`review state not recorded`、`(reason unavailable)`、接尾辞条件の文）と順序（invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way）、A3 の例外句、A4 の段落位置（`PROBE_REBIND` 段落の直後・mdq 表の導入文とその箇条書きの間に無い・count==1）、B6 の §7 en 7 文・ja 7 文。
- (2) 6 probe の境界値テスト（同一の表、graph は全 reason 分岐のキー集合テストも）: CLI 3 ファイルの判定表 ID は**正確な集合** `{既存 20 ID} ∪ {bin_ws_lead, bin_ws_trail, bin_ws_both, bin_ws_nbsp, bin_wsonly, bin_surrogate}`（26）を各ファイルで完全一致（Sol CR2-18／CR2-32）；**分担（Opus O3）**: 26 ID は既存 `test_config_decision_table_v014` を拡張して持ち、CLI の `test_bin_boundary_table` は 33 制御文字（途中配置）× enabled/disabled のみ；graph 3 probe には判定表が無いので `test_bin_boundary_table` に空白 5 種＋surrogate × enabled/disabled も含める。**33 文字全走査は 6 probe すべてで実施**（Opus N1 の実測 +20〜40 秒を許容）；graph 3 probe の `test_bin_boundary_table` も同じ空白 5 種＋surrogate＋33 制御文字（途中配置）；6 probe とも 33 制御文字（途中配置）× enabled/disabled ＋ **空白 5 種 `{bin_ws_lead, bin_ws_trail, bin_ws_both, bin_ws_nbsp, bin_wsonly}` ＋ `bin_surrogate`**（JSON テキスト `"\\ud800"` で投入）× enabled/disabled は **sentinel 不起動**（Sol CR2-38）（invalid-config／disabled-by-config の出力は seam の既存形: mdq は `bin` 無し、ax・codex は既定名、graph は既定名）；`enabled:false`＋妥当カスタム bin → mdq `bin` 無し／ax・codex 既定名／graph カスタム値保持；正例 4 種（内部スペース入りパス／非 ASCII パス（`PYTHONIOENCODING=ascii` 環境）／引用符・バックスラッシュ入り／**PATH 上の `-x` という名前の stub**（Sol CR2-15））は **stub が起動し値が完全一致**（起動回数: codex は `--version`＋`exec --help` の 2 回を引数列完全一致、他 5 本は 1 回 — Sol CR2-14）。出力キーは seam 別: mdq `bin`／ax `axBin`／codex `codexReviewBin`／graph `symbolGraphBin`・`docGraphBin`・`semanticSearchBin`（Sol CR2-21）。`test_codex_probe.py:233` の改行正例は移行済み（改行は負例）。
- (3) `test_mdq_index.py`: `setUp` が `docs/a.md` を作る assert、`tmpdir()` 内に到達不能文が無い（`python3 -m pyflakes` 相当は不要 — boss が精読）。`test_graphify_probe.py::test_disabled_by_config` に `gitignoreOk` assert。
- (4) フルスイート rc=0・skip 0（`Ran N`）。`bash -n` 6 probe。
- (5) 禁止ファイル `git diff --quiet ef995f0 -- probe-record.py decide-verdict.py start-run.py write-evidence.py open-run.py mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py`。
- (6) `BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<同> python3 scope-check.py`（allowlist は cr2 用。保護 root の列挙は root 自身と全ディレクトリ項目も `lstat` で種類・mode・link 先を比較し、通常ファイルは `st_nlink == 1` を必須 — Sol CR2-33／CR2-40、boss が scope-check.py と baseline を更新）。
- (7) ADOPTION 差分行がすべて §7 v0.14.0 段落行（§8 の python 片）。
- (8) **機械検査（Sol CR2-12／CR2-16／CR2-17）**: §8 の AST 片で、(a) 変更テストファイルに「無条件 `return` の後の文」が 0 件、(b) **ファイル別**必須メソッド名: `test_mdq_index.py` ⊇ {test_setup_creates_corpus, test_output_key_sets_per_branch, test_bin_boundary_table, test_bin_positive_paths}；`test_ax_probe.py`／`test_codex_probe.py` ⊇ {test_output_key_sets_per_branch, test_bin_boundary_table, test_bin_positive_paths}；`test_codegraph_probe.py`／`test_graphify_probe.py`／`test_cocoindex_probe.py` ⊇ {test_disabled_by_config, test_output_key_sets_per_branch, test_bin_boundary_table, test_bin_positive_paths}；`test_v014_contracts.py` ⊇ {test_cr2_codex_state_table_and_cm_shape, test_cr2_config_schema_bin_rows}（後者が DoD (9) の schema 6 行検査 — Sol CR2-35）、(c) **各対象ファイルの cr1 実装時点 `04a0624` の `test_*` 名集合が実装後も包含される**（Sol CR2-22 — cr1 で追加した回帰テストも保護。C10 の `test_cr1_reopen_gate_and_status_order_contracts` は改名せず修正）。(d) 名前の検査は **`unittest.TestCase` 派生クラスのメソッドのみ**を対象にし、フルスイート `-v` ログで **`names(04a0624) ∪ REQ` の全テスト**について「`<name> (<module>.<Class>.<name>)` で始まり行末が `... ok` の行がちょうど 1 回」を確認し、ログに `expected failure`／`unexpected success` が 0 件（Sol CR2-23／CR2-29／CR2-30）。(e) 6 probe テストの `test_bin_positive_paths` は正例 ID 集合 `{space_path, non_ascii_path, quote_backslash, dash_name}` を、`test_bin_boundary_table` は制御文字集合 `set(range(32)) | {127}` を **テスト内で完全一致 assert**（Sol CR2-24）。(f) sentinel は **既定名の stub（`mdq`／`ax`／`codex`／`codegraph`／`graphify`／`ccc`）に加え、各負例の `bin` 値そのもの（パスとして解決可能なもの）と空白除去後の名前も marker 付き stub として PATH に置き**、invalid/disabled の全負例（`enabled:false`＋妥当カスタム bin を含む）で **全 marker 不変**を確認（Sol CR2-28／CR2-31）。加えて **boss** が変更テストの diff を全行精読。`test_probe_record.py:221` の兄弟 symlink は `addCleanup(os.unlink, link)`（CR2-13）。
- (9) `config-schema.md` の 6 seam 行: `test_v014_contracts.py` が各行に境界条件句（`ASCII-control-character (U+0000–U+001F or U+007F)`・`whitespace-only or whitespace-padded`・`non-UTF-8-encodable`）と seam 別 disabled 句（mdq `omits bin`／ax・codex `default name`／graph `keeps a valid custom bin`）を完全一致で固定（Sol CR2-26）。
- (10) A1 の合成指示: §8 で SKILL の **Phase 0 節（`## Phase 0` 見出しから `## Phase 0.5` 見出しまで）** を抽出し、A1 の合成指示文全体（`synthesize \`CM_PROBE_JSON\` as exactly \`{"contextModeAvailable":<CM_AVAILABLE>,"contextModeHealthy":<bool or null>,"status":"<CM_STATUS>"}\`` から `otherwise use the bound values.` まで）が**ちょうど 1 回**完全一致で存在し、SKILL 全体でも `{"contextModeAvailable":` の出現が 1 回（Sol CR2-11）。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{mdq-index.sh,ax-probe.sh,codex-probe.sh,codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`（§7 v0.14.0 段落のみ）、
`tests/{test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py,test_probe_record.py}`。
**禁止**: 上記以外（`probe-record.py`、engine、`test_v013/v0132/v0131`、`tasks/**`、`.claude/**`）。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ。**

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr2-full.log 2>&1; rc=$?; tail -3 /tmp/cr2-full.log; test $rc -eq 0 || exit 1; test "$(grep -c ' \.\.\. skipped' /tmp/cr2-full.log)" -eq 0 || exit 1
python3 -m unittest -v tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_codegraph_probe tests.test_graphify_probe tests.test_cocoindex_probe tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_probe_record || exit 1
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh || exit 1
python3 - <<'PY' || exit 1
import re,sys,ast,subprocess
skill=open('skills/audit/SKILL.md',encoding='utf-8').read()
p0=skill[skill.index('## Phase 0 '):skill.index('## Phase 0.5')]
sent='synthesize `CM_PROBE_JSON` as exactly `{"contextModeAvailable":<CM_AVAILABLE>,"contextModeHealthy":<bool or null>,"status":"<CM_STATUS>"}` (JSON boolean/null values, not quoted text): when `CM_AVAILABLE` is false, `contextModeHealthy` is always `null`; when `CM_AVAILABLE` is true and `CM_HEALTHY` is unbound, normalize to `contextModeHealthy:false` and `status:"probe-error"`; otherwise use the bound values.'
bad=[]
if p0.count(sent)!=1: bad.append('CM synthesis sentence count in Phase 0 = %d'%p0.count(sent))
if skill.count('{"contextModeAvailable":')!=1: bad.append('CM literal count in SKILL != 1')
REQ={'tests/test_mdq_index.py':{'test_setup_creates_corpus','test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_ax_probe.py':{'test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_codex_probe.py':{'test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_codegraph_probe.py':{'test_disabled_by_config','test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_graphify_probe.py':{'test_disabled_by_config','test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_cocoindex_probe.py':{'test_disabled_by_config','test_output_key_sets_per_branch','test_bin_boundary_table','test_bin_positive_paths'},
     'tests/test_v014_contracts.py':{'test_cr2_codex_state_table_and_cm_shape','test_cr2_config_schema_bin_rows'},
     'tests/test_probe_record.py':set()}
def names(src):
    out=set()
    for cls in ast.walk(ast.parse(src)):
        if isinstance(cls,ast.ClassDef) and any(getattr(b,'attr',getattr(b,'id',''))=='TestCase' for b in cls.bases):
            out|={n.name for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    return out
def blocks(node):
    for field in ('body','orelse','finalbody','handlers'):
        v=getattr(node,field,None)
        if isinstance(v,list) and v and isinstance(v[0],ast.stmt): yield v
        if isinstance(v,list):
            for h in v:
                if isinstance(h,ast.ExceptHandler): yield h.body
for f,req in REQ.items():
    src=open(f,encoding='utf-8').read(); tree=ast.parse(src)
    for node in ast.walk(tree):
        for blk in blocks(node):
            for st in blk[:-1]:
                if isinstance(st,(ast.Return,ast.Raise,ast.Continue,ast.Break)): bad.append(f'{f}:{st.lineno} unreachable statement after {type(st).__name__}')
    have=names(src)
    for r in sorted(req-have): bad.append(f'{f}: missing {r}')
    base=subprocess.run(['git','show','04a0624:'+f],capture_output=True,text=True,check=True).stdout
    for r in sorted(names(base)-have): bad.append(f'{f}: existing test removed: {r}')
log=open('/tmp/cr2-full.log',encoding='utf-8',errors='replace').read()
if re.search(r'\.\.\. (expected failure|unexpected success)$',log,re.M): bad.append('expected failure / unexpected success result present in -v log')
for f,req in REQ.items():
    mod='tests.'+f.split('/')[-1][:-3]
    base=subprocess.run(['git','show','04a0624:'+f],capture_output=True,text=True,check=True).stdout
    for r in sorted(names(base)|req):
        n=len(re.findall(r'^'+re.escape(r)+r' \('+re.escape(mod)+r'\.[A-Za-z0-9_]+\.'+re.escape(r)+r'\)(?:\n[^\n]*)? \.\.\. ok$',log,re.M))
        if n!=1: bad.append(f'{mod}.{r}: ... ok lines = {n}')
print('\n'.join(bad) or 'tests-ast-clean'); sys.exit(1 if bad else 0)
PY
git diff --quiet ef995f0 -- skills/audit/scripts/probe-record.py skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin skills/audit/references/engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py && echo forbidden-clean || exit 1
BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<boss commit> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py || exit 1
python3 - <<'PY' || exit 1
import subprocess,sys,re
R={'docs/ADOPTION.md':('**v0.14.0 behavior changes:**',[('state unknown after resume','state unknown (probe record unavailable)'),('a non-string, empty, or NUL-containing bin','a non-string, empty, whitespace-only, whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable bin')],' the symbolGraph / docGraph / semanticSearch probes now apply the same bin validation: a newly rejected bin reports invalid-config before the tool lookup, and with enabled:false an invalid bin is displayed as the default name.'),  # en: 先頭スペース
   'docs/ADOPTION.ja.md':('**v0.14.0 の挙動変更:**',[('state unknown after resume','state unknown (probe record unavailable)'),('文字列でない、空、NUL を含む','文字列でない、空、空白のみ、前後に空白がある、ASCII 制御文字（U+0000–U+001F または U+007F）を含む、または UTF-8 に符号化できない')],'symbolGraph / docGraph / semanticSearch の probe も同じ bin 検証を適用します。新たに拒否される bin はツール探索の前に invalid-config を報告し、enabled:false のときは不正な bin を既定名で表示します。')}  # ja: 区切り無し
def para(text,marker):
    ps=re.split(r'\n\s*\n',text); c=[p for p in ps if p.startswith(marker)]; assert len(c)==1,(marker,len(c)); return c[0]
bad=[]
for f,(marker,subs,tail) in R.items():
    base=subprocess.run(['git','show','ef995f0:'+f],capture_output=True,text=True,check=True).stdout
    cur=open(f,encoding='utf-8').read()
    exp=para(base,marker)
    for a,b in subs:
        assert exp.count(a)==1,(f,a); exp=exp.replace(a,b)
    exp=exp.rstrip()+tail
    if para(cur,marker).rstrip()!=exp: bad.append(f+': §7 paragraph differs from expectation')
    if base.replace(para(base,marker),'')!=cur.replace(para(cur,marker),''): bad.append(f+': changes outside the §7 paragraph')
print('\n'.join(bad) or 'adoption-paragraph-clean'); sys.exit(1 if bad else 0)
PY
```
