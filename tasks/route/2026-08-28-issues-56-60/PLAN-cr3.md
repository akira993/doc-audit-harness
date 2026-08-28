# PLAN-cr3 — 3 回目 `/code-review xhigh`（途中終了）の CONFIRMED 所見 1 件の修正（rev.1, 2026-08-29）

## 0. 決定事項
ユーザーの 3 回目 `/code-review xhigh`（PR #62、HEAD `af5c09e`）はセッション上限（429）で途中終了したが、検証サブエージェント 1 本が完了し CONFIRMED 所見 V9 を残した。所見要旨:
- cr2 で 6 probe の JSON emit 9 か所（`codegraph-probe.sh:52-54`、`graphify-probe.sh:57-58`、`cocoindex-probe.sh:62-63`、`mdq-index.sh:64/97/103`、`ax-probe.sh:60/66`、`codex-probe.sh:66`）に `ensure_ascii=False` が入った。PLAN-cr2 §B5 が要求したのは `sys.stdout.buffer.write(... .encode("utf-8"))` の伝送のみで、`ensure_ascii=False` は要求外（boss の cr2 検収で「無害」と誤判定）。
- (a) 目的だった `PYTHONIOENCODING=ascii` 耐性は既定 `ensure_ascii=True` で満たせる（JSON は純 ASCII）。merge-base の破損は graph の `STATE BIN` 行伝送であり JSON emit ではない。
- (b) bin に U+0085/U+2028/U+2029（validation を通る）を含むと生バイトで出力され、6 テストファイルが固定する「stdout は 1 行（`splitlines()==1`）」契約が破れる（現行テストはこの 3 文字を probe に投入していないため検出不能）。実消費者（`$(...)` → `probe-record.py`）は今日は壊れない。
- (c) **回帰**: `CODEX_HOME` に非 UTF-8 バイト（surrogateescape で `\udcff`）があると `codex-probe.sh` の emit が `.encode("utf-8")` で失敗 → stdout 空・exit 0（`emit_json` 後の `exit 0` が失敗を隠す）→ probe-record が拒否 → Phase 5 で codex-review が unknown。merge-base は `\udcff` をエスケープした正常行を出していた。
- 修正案（検証済み）: 9 か所を `ensure_ascii=True`（既定）に戻し `sys.stdout.buffer.write` は維持 → 6 probe テスト 97 件は無変更で green、surrogate も正常行。

### 修正
1. **6 probe の JSON emit 9 か所から `ensure_ascii=False` を除去**（既定 True）。`sys.stdout.buffer.write((json.dumps(...)+"\n").encode("utf-8"))` の形は維持（ASCII のみなので `.encode` は失敗しない）。
2. **回帰テスト**（6 probe テストに各 1 本 `test_json_emit_is_ascii_one_line`）: bin `"to ol-none"`（validation 通過・not-installed）で stdout が (i) `splitlines()==1`、(ii) bytes が純 ASCII（`stdout.isascii()`）、(iii) JSON round-trip で bin が完全一致。codex はさらに `CODEX_HOME` に `b"/tmp/h\xffome"`（surrogateescape）を与えて stdout が空でなく 1 行の妥当 JSON（`callerCodexHome` が round-trip）であること。
3. `test_probe_record.py`／`SKILL.md`／docs は変更しない（`display()` の ASCII エスケープ決定は正しく、今回はそれと同じ根拠を emit にも適用するだけ）。

## 6. 完了条件
- (1) `grep -c 'ensure_ascii=False' skills/audit/scripts/*.sh` が 0。
- (2) 6 probe テストに `test_json_emit_is_ascii_one_line`（TestCase メソッド、`-v` ログで `... ok` 各 1 回）。codex 版は非 UTF-8 `CODEX_HOME` ケースを含む。
- (3) フルスイート rc=0・skip 0・expected failure 0（`Ran N` ≥ 603＋6）。`bash -n` 6 probe。
- (4) `04a0624` および `79938a5` の全 `test_*` 名が残存（PLAN-cr2 §8 の AST 片を基準 `79938a5` で実行）。
- (5) 禁止ファイル `git diff --quiet ef995f0 -- probe-record.py decide-verdict.py start-run.py write-evidence.py open-run.py mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py docs`（docs も今回は不変）。
- (6) `BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<同> python3 scope-check.py` clean（allowlist は cr3 用: 6 probe＋6 probe テスト）。

## 7. 変更範囲
**許可**: `skills/audit/scripts/{mdq-index.sh,ax-probe.sh,codex-probe.sh,codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`tests/{test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py}`。**禁止**: 上記以外。許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ。

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr3-full.log 2>&1; rc=$?; tail -3 /tmp/cr3-full.log; test $rc -eq 0 || exit 1; test "$(grep -c ' \.\.\. skipped' /tmp/cr3-full.log)" -eq 0 || exit 1; test "$(grep -cE '\.\.\. (expected failure|unexpected success)$' /tmp/cr3-full.log)" -eq 0 || exit 1
test "$(grep -c 'ensure_ascii=False' skills/audit/scripts/*.sh | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh || exit 1
for m in test_mdq_index test_ax_probe test_codex_probe test_codegraph_probe test_graphify_probe test_cocoindex_probe; do test "$(grep -cE "^test_json_emit_is_ascii_one_line \(tests\.$m\.[A-Za-z0-9_]+\.test_json_emit_is_ascii_one_line\)( .*)?$" /tmp/cr3-full.log)" -ge 1 || { echo "missing $m"; exit 1; }; done
git diff --quiet ef995f0 -- skills/audit/scripts/probe-record.py skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin skills/audit/references/engine-shas.json tests/test_v013_contracts.py tests/test_v0132_contracts.py tests/test_v0131_docs_contracts.py && git diff --quiet 79938a5 -- docs skills/audit/SKILL.md skills/audit/references tests/test_v014_contracts.py tests/test_probe_record.py && echo forbidden-clean || exit 1
BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<boss commit> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py || exit 1
```
