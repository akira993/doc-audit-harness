# PLAN-cr2 — PR #62 の `/code-review xhigh` 指摘 15 件の修正（rev.1, 2026-08-28）

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
   | unknown | 非 null | 既存 4-way。`not-active` は `(reason unavailable)` と表示 | reviewState ∈ {completed, execution-failed, ref-invalid} のときのみ ` (caller info unavailable)`（codex が実行を試みた枝のみ。`not-active`/`skipped-full-run`/`phase4-not-required` には付けない） |
   共通規則文は「codex-review: invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way」に更新。ADOPTION は変更不要（§7 ④ は unknown 文言の一般形のまま）。
3. **#8 `Fix mdq first` 分岐**: :124 の無条件記録文に例外 1 句「（except on the gate's "Fix mdq first" branch, which releases the run and ends the audit before anything is recorded）」。
4. **#14 優先順位段落の位置**: mdq 表の導入文とその箇条書きの間から外し、`PROBE_REBIND` 段落（:651 付近）の直後に**独立段落**として置く（空行で区切る）。出現回数 1 は維持。

### B. probe の `bin` 検査（#4・#10・#11・#13 — 6 probe 共通契約）
5. **`bin` の有効条件を 6 probe で統一**: 文字列・非空・**前後に空白なし（`bin == bin.strip()`）・空白のみでない**・ASCII 制御文字（U+0000–U+001F, U+007F）を含まない・**先頭が `-` でない**（#10: `command -v -v` が成功扱いになる）・UTF-8 にエンコード可能（#11: lone surrogate）。違反は `invalid-config`（`enabled:false` 先勝ち → disabled 分岐では出力 bin を既定名に）。内部スペースは許容。
   - graph 3 probe: python 判定で `bin_name` を 1 回束縛し `valid = …` を 1 つ計算して enabled/disabled 両分岐で使う（#13）。**出力行は文字列を組み立てて `.encode("utf-8")` を try 内で検証してから 1 回だけ print**（部分出力後の except を防ぐ）。
   - CLI 3 probe（`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`）: 判定 python に同じ条件を追加（base64 伝送は不変）。判定表 ID に `bin_ws`（`" codegraph "`）・`bin_wsonly`（`"   "`）・`bin_dash`（`"-v"`）を追加（23 ID）。
   - `config-schema.md`: 6 seam の行の `bin` 条件を統一文「a non-string, empty, whitespace-only or whitespace-padded, control-character, or leading-`-` `bin` reports `invalid-config`; with `enabled:false` the output falls back to the default name」（表の行のみ。`Its probe reasons are` 以降には触れない）。
6. **ADOPTION §7（#6）**: ① の `bin` 句を「a non-string, empty, whitespace-padded, control-character, or leading-dash bin」に、**⑦ を追加**（en `the symbolGraph / docGraph / semanticSearch probes now apply the same bin validation (invalid-config instead of not-installed; with enabled:false the displayed bin falls back to the default)`、ja 対応文）。`test_v014_behavior_changes_paragraph` を en 7・ja 7 に。cr1 の「単一置換 bytes 比較」は撤廃し、`git diff ef995f0 -- docs/ADOPTION*.md` の変更行がすべて §7 v0.14.0 段落内（`**v0.14.0 behavior changes:**`／`**v0.14.0 の挙動変更:**` を含む行）であることを検査。

### C. テストの修復と強化（#2・#3・#9・#15）
7. **#2 `test_mdq_index.setUp`**: `write(docs/a.md)` を `setUp` 内に戻す（`tmpdir()` は独立 helper のまま）。回帰防止: `setUp` 後に `os.path.exists(docs/a.md)` を assert するテスト 1 本。
8. **#3 `test_graphify_probe`**: `test_disabled_by_config` に `assertFalse(out["gitignoreOk"])` を戻し、制御文字テストは独立メソッドに（末尾の迷子 assert を除去）。
9. **#9 制御文字テストの sentinel**: 3 graph probe の制御文字/空白/dash テストは `_assert_unavailable(..., log)` 相当で **sentinel 不起動**を assert（enabled/disabled 両方）。**内部スペース入りディレクトリの正例**（`bin` = `<tmp>/dir with space/<tool>` の stub、起動され `<seam>Bin` が完全一致）を 3 probe に追加。
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
- (2) 6 probe の判定表テスト: CLI 3 probe は 23 ID（`bin_ws`/`bin_wsonly`/`bin_dash` 追加、`len(CASES)==23`）、graph 3 probe は 33 制御文字 ×2 ＋ `bin_ws`/`bin_wsonly`/`bin_dash`/`bin_surrogate`（`"\ud800"` は JSON テキスト `"\\ud800"` で投入）×2 ＋ 内部スペース正例 ＋ 全分岐キー集合、**すべて sentinel 不起動を assert**。
- (3) `test_mdq_index.py`: `setUp` が `docs/a.md` を作る assert、`tmpdir()` 内に到達不能文が無い（`python3 -m pyflakes` 相当は不要 — boss が精読）。`test_graphify_probe.py::test_disabled_by_config` に `gitignoreOk` assert。
- (4) フルスイート rc=0・skip 0（`Ran N`）。`bash -n` 6 probe。
- (5) 禁止ファイル `git diff --quiet ef995f0 -- probe-record.py decide-verdict.py start-run.py write-evidence.py open-run.py mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py`。
- (6) `BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<同> python3 scope-check.py`（allowlist は cr2 用）。
- (7) ADOPTION 差分行がすべて §7 v0.14.0 段落行（§8 の python 片）。
- (8) **boss**: 変更テストファイル全行の diff 精読（fixture・assert の迷子・到達不能文が無いこと）。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{mdq-index.sh,ax-probe.sh,codex-probe.sh,codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`（§7 v0.14.0 段落のみ）、
`tests/{test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py,test_probe_record.py}`。
**禁止**: 上記以外（`probe-record.py`、engine、`test_v013/v0132/v0131`、`tasks/**`、`.claude/**`）。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ。**

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr2-full.log 2>&1; rc=$?; tail -3 /tmp/cr2-full.log; test $rc -eq 0 || exit 1; test "$(grep -c ' \.\.\. skipped' /tmp/cr2-full.log)" -eq 0 || exit 1
python3 -m unittest -v tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_codegraph_probe tests.test_graphify_probe tests.test_cocoindex_probe tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_probe_record || exit 1
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh || exit 1
test "$(grep -c 'contextModeAvailable' skills/audit/SKILL.md)" -ge 1 || exit 1
git diff --quiet ef995f0 -- skills/audit/scripts/probe-record.py skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin skills/audit/references/engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py && echo forbidden-clean || exit 1
BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<boss commit> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py || exit 1
python3 - <<'PY' || exit 1
import subprocess,sys
bad=[]
for f,marker in (('docs/ADOPTION.md','**v0.14.0 behavior changes:**'),('docs/ADOPTION.ja.md','**v0.14.0 の挙動変更:**')):
    d=subprocess.run(['git','diff','ef995f0','--',f],capture_output=True,text=True,check=True).stdout
    lines=[l for l in d.splitlines() if l[:1] in '+-' and not l.startswith(('+++','---'))]
    for l in lines:
        if marker not in l: bad.append(f+': '+l[:80])
print('\n'.join(bad) or 'adoption-scope-clean'); sys.exit(1 if bad else 0)
PY
```
