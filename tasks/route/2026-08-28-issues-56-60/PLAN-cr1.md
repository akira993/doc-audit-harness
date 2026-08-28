# PLAN-cr1 — PR #61 merge 後の `/code-review` 指摘 10 件の修正（rev.1, 2026-08-28）

## 0. 決定事項
ユーザー指示: 「Code-Review で問題があれば、修正計画→Sol レビューを回し、最後に Opus 全体レビュー後、実装、コミット、その後にまた私が Code-Review を打ちます。」
PR #61 は `ef995f0` で merge 済み・**tag 未作成**。修正は branch `fix/v0.14.0-code-review-followup`（main `ef995f0` 起点）で行い、**版は 0.14.0 のまま**（未 release）。fix PR の merge 後に `release-handoff.sh <最終 merge sha> <fix PR 番号>` で tag/Release/close/同期を行う（handoff の PR 番号引数は fix PR）。
code-review 所見（`/code-review 61`、high、CONFIRMED 6・PLAUSIBLE 4、最高 medium）を根本原因 4 群に整理する。

### A. 「Phase 5 は `rebind` のみ」× 「記録は fail-open」の不整合（所見 #1・#2・#3・#4・#6 — 根本原因）
1. **フレッシュ run のフォールバック規則（#1・#4 の直接対策）**: SKILL.md Phase 5 と再開段落を「`rebind` は権威。ただし**再開していない run**（同一会話に Phase 0/4 の変数がまだ束縛されている）で `rebind` の行が `unknown`／`reviewState` が null のときは、会話変数から通常行を描画し、`⚠ probe-record: <seam> fallback to conversation values [non-blocking]` を 1 行添える。`state unknown after resume` 行は**再開後のみ**」に改める。
   固定文（再開段落に置換）: `Phase-5 status lines are rendered from probe-record.py --read (its "rebind" map is authoritative). On a resumed run, a line marked unknown prints its "state unknown after resume" form. On a run that was never resumed, an unknown line or a null reviewState falls back to the conversation's Phase-0/4 variables and adds "⚠ probe-record: <seam> fallback to conversation values [non-blocking]"; CODEX_REVIEW_STATE is rebound from rebind.codex-review.reviewState when non-null. A failed read is treated the same way. None of this changes the verdict.`
2. **harness 辞退で run を再取得した後の再記録（#1 の根本）**: SKILL.md:274-275 の「replace `RUNID`, `RUN_DIR`, `EVIDENCE`」の直後に「re-record every Phase-0 seam already probed（`MDQ_PROBE_JSON`／`MDQ_HEALTH_PROBE_JSON`／`{"degrade":…}`／`CM_PROBE_JSON`／`AX_PROBE_JSON`／`CODEX_PROBE_JSON`／3 graph）into the new run dir with the same record commands」を追加（固定文 1 文＋契約テスト）。
3. **`MDQ_DEGRADE` の未束縛（#2）**: SKILL.md:103 の「except when `PHASE3_BACKEND_CONFIG` is `codex`」分岐と、ゲート不発火の全経路で `MDQ_DEGRADE="n/a"` を束縛するよう :121 の文を「When the gate does not fire **or is skipped**, bind `MDQ_DEGRADE="n/a"`」に改める。`mdq-health.py` が JSON を返せなかった場合（:100 「treat as probe-error」）は `MDQ_HEALTH_PROBE_JSON='{"files":0,"chunks":0,"searchSmoke":false,"healthy":false,"status":"probe-error"}'` を束縛して記録する（固定文）。
4. **contextMode validator の緩和（#3）**: `probe-record.py` の `contextMode` 分岐を「`contextModeAvailable:bool`、`contextModeHealthy:bool|null`（available の真偽によらず）、`status:str`（available:true → `{ok,degraded,probe-error}`、false → `{disabled-by-config,not-installed,probe-error,invalid-config}`）」に緩める。`rebind.context-mode.healthy` は記録値そのまま。SKILL.md:153 の合成説明に「`CM_HEALTHY` が未束縛なら `null`」を明記。テスト: `{available:false, healthy:false, status:probe-error}` と `{available:true, healthy:null, status:probe-error}` を受理。
5. **接尾辞の gating（#6）**: SKILL.md:757 の「When `CODEX_REVIEW_AVAILABLE=true`, append」を「When `rebind.codex-review.available` is true, append」に改める（診断文も同様）。

### B. 状態行の優先順位（#5）
6. Phase-5 の mdq／context-mode／ax ブロック冒頭に共通規則 1 文「Within each status-line table, **the first matching bullet wins**; the `invalid-config` bullet is listed first for that reason.」を置き、CM/AX の `invalid-config` 枝が各表の**先頭**にあることを契約テストで順序 assert（mdq は S1a で順序済み）。

### C. 実装の整合・可読性（#7・#8・#9）
7. `probe-record.py::display`: `json.dumps(value[:200], ensure_ascii=False)[1:-1]`（非 ASCII パスを可読に、制御文字は引き続きエスケープ）。テスト: 日本語パスが verbatim、改行は `\n` のまま 1 行。
8. graph 3 probe（`codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh`）の `bin` 検査に `or "\0" in bin_name` を追加（`invalid-config`）。`config-schema.md` の 3 行に NUL 句。各テストに `bin_nul` ケース 1 つ。既存キー集合・reason 集合は不変（`test_v0132_contracts` の完全一致を壊さない）。
9. SKILL.md:193 の「Rows 6–8 are defenses for direct probe invocation」を平文に置換: `An unreadable, non-object, or absent config makes the probe report invalid-config only when it is invoked directly; in a normal audit such a config stops before Phase 0.`（`test_v014_contracts.py:90` の固定文を同時更新）。

### D. 重複と性能（#10）— 縮小して採用
10. 共有ヘルパー `skills/audit/scripts/probe-config.py`（新規）: `--seam <indexing|webExtract|codexReview> --default-bin <name> [--config PATH | --config-omitted]` を受け、判定表（rev.8 §0-5 と同一）を 1 回の python 起動で評価し、stdout に **1 行の JSON** `{"state":"enabled|disabled|invalid","bin":"<name>","roots":[…]}`（`roots` は indexing のみ、`indexing.roots` の文字列要素）を返す。3 probe はこの 1 呼び出しで `CONFIG_STATE`／`BIN`／（mdq は）`ROOTS` を得て、base64 復号・roots 再解析の追加 python 起動を廃止する。判定結果・出力 JSON 形・exit code は現行と完全同一（3 probe の `test_config_decision_table_v014` 20 ID がそのまま green であることが同値性の証明）。
    `bin` の受け渡し: JSON を `python3 -c` 1 回で `state`／`bin`／`roots` を NUL 区切りに展開して `read -r -d ''` で受ける（tab・改行入り bin も保持）。テスト `tests/test_probe_config.py`（新規、20 ID＋roots 3 ケース）。ADOPTION 付録に 1 行追加（`test_v0131_docs_contracts.py` の件数 43→44・行 52→53）。
11. テストの `tempfile.mkdtemp()` 漏れ: 3 probe テストと `test_probe_record.py` で `self.addCleanup(shutil.rmtree, …)` または `TemporaryDirectory` に統一。`test_codex_probe.py::test_output_key_sets_per_branch` のエイリアス重複は解消（1 本に）。テストの三重化（`test_config_decision_table_v014` の本体）は共通 fixture を `tests/probe_table_helpers.py` に切り出して 3 ファイルから参照（ケース表は 1 か所）。

### 見送り（low・記録のみ）
review 本文末尾の low 項目（`RUNID_RE` 等の重複、reason enum の厳格さ、handoff の冗長ネットワーク呼び出し、`emit_json` の位置引数、破損 record が以後の書き込みを止める点、python3 不在時の空出力、CASES テストの自己参照）は本 PR では扱わず、次版候補として最終報告に列挙。

## 1. 目的
merge 済み v0.14.0 の表示経路（Phase 5）が「再開していない通常 run で unknown 表示になる」欠陥を根本から塞ぎ、状態行の優先順位・NUL 検査・可読性・三重化を整える。verdict ロジック（`decide-verdict.py`）は不変。

## 2. 入力・参照資料
`/code-review 61` の所見（本 PLAN §0 に転記）、PLAN.md rev.8 §0-5/§0-6、`skills/audit/SKILL.md`（:100-121, :149-154, :193, :267-276, :645, :720-765）、`probe-record.py`、3 CLI probe、3 graph probe、`config-schema.md`、`tests/test_{probe_record,mdq_index,ax_probe,codex_probe,codegraph_probe,graphify_probe,cocoindex_probe,v014_contracts,v0132_contracts,v0131_docs_contracts}.py`。

## 3. 担当（boss）
Fable。計画・レビュー・検証再実行・PR 作成。実装は書かない。

## 4. 実行者（worker）
単一 Stage: Terra `medium`（`codex exec -m gpt-5.6-terra -s workspace-write -c model_reasoning_effort=medium`）。差し戻しは resume。

## 5. 成果物
`SKILL.md`（A1〜A3・A5・B6・C9）、`probe-record.py`（A4・C7）、`probe-config.py`（新）＋3 CLI probe（D10）、3 graph probe＋`config-schema.md`（C8）、`docs/ADOPTION*.md` 付録（D10）、テスト（`test_probe_record`、`test_probe_config`(新)、`tests/probe_table_helpers.py`(新)、3 CLI probe テスト、3 graph probe テスト、`test_v014_contracts`、`test_v0131_docs_contracts`）。

## 6. 完了条件（DoD）
- (1) `test_v014_contracts.py`: 再開段落の新固定文（A1）、reopen 後の再記録文（A2）、`MDQ_DEGRADE="n/a"` の「or is skipped」文と mdq-health フォールバック固定文（A3）、CM 合成の null 注記（A4）、接尾辞 gating が `rebind.codex-review.available`（A5）、「first matching bullet wins」文（B6）と CM/AX の `invalid-config` 枝が表の先頭（順序 assert）、:193 新文言（C9）。旧文言（`Rows 6–8`、`When CODEX_REVIEW_AVAILABLE=true, append`、旧再開段落）が SKILL に残らない（grep 0）。
- (2) `test_probe_record.py`: contextMode 緩和 2 ケース受理＋従来の不正例（status 集合違反）は拒否、display の非 ASCII verbatim＋改行 1 行、固定 ID 集合更新（`len(CASES)` assert）。
- (3) 3 graph probe テストに `bin_nul` → `invalid-config`（キー集合不変）。`test_v0132_contracts` green（reason 集合不変）。
- (4) `tests/test_probe_config.py`（20 ID＋roots 3）green、3 CLI probe の `test_config_decision_table_v014`／`test_output_key_sets_per_branch` が**無変更の期待値で** green（同値性）。3 probe の inline python 判定ブロックが消え `probe-config.py` 呼び出し 1 回になっている（`grep -c 'base64' mdq-index.sh ax-probe.sh codex-probe.sh` = 0）。
- (5) `test_v0131_docs_contracts.py` 44/53、ADOPTION 付録 en/ja に `probe-config.py`。
- (6) テストの `mkdtemp` 漏れ 0（`grep -c 'mkdtemp()' tests/test_{mdq_index,ax_probe,codex_probe,probe_record}.py` の各件数が cleanup 付きのみ — worker が `addCleanup`/`TemporaryDirectory` へ置換した行数を報告）。
- (7) フルスイート green・skip 0（`-v` の ` ... skipped` 0 行）。`Ran N` 報告。`bash -n` 6 probe、`py_compile` 変更 .py。
- (8) 禁止ファイル `git diff --quiet ef995f0 -- decide-verdict.py start-run.py write-evidence.py docaudit_paths.py docaudit_cache.py open-run.py seal-run.py read-manifest.py tree-digest.py mdq-health.py scaffold.py write-template.py skills/init/SKILL.md agents tests/data data`。
- (9) スコープ検査: 変更ファイル集合 ⊆ §7 許可一覧（`git diff --name-only ef995f0 HEAD` ＋ 未追跡）。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{probe-record.py,probe-config.py(新),mdq-index.sh,ax-probe.sh,codex-probe.sh,codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
`tests/{test_probe_record.py,test_probe_config.py(新),probe_table_helpers.py(新),test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py,test_v0131_docs_contracts.py}`。
**禁止**: 上記以外（特に `decide-verdict.py`、`start-run.py`、`write-evidence.py`、`open-run.py`、`mdq-health.py`、`.claude-plugin/plugin.json`（版は据え置き）、`engine-shas.json`、`tasks/**`、`.claude/**`）。
**標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr1-full.log 2>&1; tail -3 /tmp/cr1-full.log; test "$(grep -c ' \.\.\. skipped' /tmp/cr1-full.log)" -eq 0 || exit 1
python3 -m unittest -v tests.test_probe_record tests.test_probe_config tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_codegraph_probe tests.test_graphify_probe tests.test_cocoindex_probe tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_v0131_docs_contracts
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh
python3 -m py_compile skills/audit/scripts/probe-record.py skills/audit/scripts/probe-config.py
test "$(grep -c 'base64' skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
test "$(grep -c 'Rows 6\|When `CODEX_REVIEW_AVAILABLE=true`, append' skills/audit/SKILL.md)" -eq 0 || exit 1
git diff --quiet ef995f0 -- skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/docaudit_paths.py skills/audit/scripts/docaudit_cache.py skills/audit/scripts/open-run.py skills/audit/scripts/seal-run.py skills/audit/scripts/read-manifest.py skills/audit/scripts/tree-digest.py skills/audit/scripts/mdq-health.py skills/audit/scripts/scaffold.py skills/audit/scripts/write-template.py skills/init/SKILL.md agents tests/data .claude-plugin/plugin.json skills/audit/references/engine-shas.json && echo forbidden-clean
{ git diff --name-only ef995f0 HEAD; git status --porcelain=v1 --untracked-files=all | awk '{print $2}'; } | sort -u | grep -v '^tasks/\|^\.claude/'
```
