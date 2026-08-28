# PLAN-cr1 — PR #61 merge 後の `/code-review` 指摘 10 件の修正（rev.2, 2026-08-28 — Sol CR1-R1 反映）

## 0. 決定事項
ユーザー指示: 「Code-Review で問題があれば、修正計画→Sol レビューを回し、最後に Opus 全体レビュー後、実装、コミット、その後にまた私が Code-Review を打ちます。」
PR #61 は `ef995f0` で merge 済み・**tag 未作成**。修正は branch `fix/v0.14.0-code-review-followup`（main `ef995f0` 起点）、**版は 0.14.0 のまま**。fix PR の merge 後に `release-handoff.sh <最終 merge sha> <fix PR 番号>`。
code-review 所見 10 件（high、CONFIRMED 6・PLAUSIBLE 4、最高 medium）を根本原因で整理。**Phase 5 の情報源は `rebind` のみ、判定不能は常に `unknown`**（Sol CR1-1 — 会話変数へのフォールバックは新設しない）。

### A. フレッシュ run で unknown 行が出る根本原因を塞ぐ（所見 #1・#2・#3・#4・#6）
1. **harness 辞退で run を再取得した後は Phase 0 を丸ごと再実行する（#1、Sol CR1-2）**: SKILL.md:274-275 の「replace `RUNID`, `RUN_DIR`, and `EVIDENCE` from its stdout before continuing」の直後に固定文
   `Then re-run Phase 0 from its first step on the new run (every probe and every probe-record.py call, so the new run directory holds its own phase0-probes.json); Phase 0.5 is not repeated.` を追加。probe は冪等（mdq index は増分）。会話変数からの再記録は採らない（turn-ending checkpoint 後に保証されるのは `RUNID`＋`EVIDENCE` のみ）。
2. **`MDQ_DEGRADE` の未束縛（#2）**: SKILL.md:103 の codex backend 分岐を含め、ゲートが発火しない・評価されない全経路で `MDQ_DEGRADE="n/a"` を束縛する: :121 を `When the gate does not fire, or is skipped because PHASE3_BACKEND_CONFIG is codex, bind MDQ_DEGRADE="n/a".` に改める。
   `mdq-health.py` が JSON を返せなかった場合（:100）は固定 JSON `{"files":0,"chunks":0,"searchSmoke":false,"healthy":false,"status":"probe-error"}` を `MDQ_HEALTH_PROBE_JSON` に束縛して記録する（固定文）。
3. **contextMode 合成の正規化（#3、Sol CR1-3 — validator は変えない）**: SKILL.md:153 の合成説明を「`CM_AVAILABLE` が false のとき `contextModeHealthy` は**常に** `null`（`CM_HEALTHY` が束縛済みでも捨てる）。`CM_AVAILABLE` が true で `CM_HEALTHY` が未束縛のときは `contextModeHealthy:false`・`status:"probe-error"` に正規化する」に改める（固定文。表示分岐 3 本と一致）。
4. **codexReviewState の書き込み失敗（#4）**: 情報源は `rebind` のみを維持。SKILL.md Phase 5 に 1 文「A `⚠ probe-record: <seam> not recorded` warning earlier in the run explains a subsequent "state unknown after resume" line on a run that was never resumed; do not substitute conversation values.」を置き、fail-open 警告行を**報告本文に必ず残す**（現行は `echo` のみ → 状態行の直前に転記する規約を追加）。`state unknown after resume` の文言・§7 は変えない。
5. **接尾辞の gating（#6）**: SKILL.md:757 の「When `CODEX_REVIEW_AVAILABLE=true`, append」→「When `rebind.codex-review.available` is true, append」（診断文も同様）。

### B. 状態行の優先順位（#5）
6. Phase-5 の状態行節の冒頭に共通規則 1 文「Within each status-line table the first matching bullet wins; each `invalid-config` bullet is listed first for that reason.」を置き、mdq／context-mode／ax の `invalid-config` 枝が各表の**先頭**にあることを契約テストで順序 assert（現行 CM/AX は末尾に追加されている — 先頭へ移動）。

### C. 文字列伝送の安全性と可読性（#7・#8・#9）
7. **#7（ensure_ascii）は不採用**（Sol CR1-4: `ensure_ascii=False` は U+0085/U+2028/U+2029 で 1 行性を破る。現行 ASCII エスケープは安全側）。`probe-record.py::display` に U+0085/U+2028/U+2029 を含む値でも 1 行であることのテストを追加（現行実装で通る＝回帰防止）。最終報告で「表示は ASCII エスケープ」を明記。
8. **graph 3 probe の `bin` 検査（#8、Sol CR1-5）**: `codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh` の python 判定で、`bin` が **NUL または C0 制御文字（`\x00`–`\x1f`、`\x7f`）を含む**場合を `invalid-config` にする（`read -r STATE BIN` の行指向伝送で改行・タブが切断される経路を config 側で閉じる。空白を含むパスは従来どおり許容 — `read` の最終変数は行末まで取る）。検査は既存 `emit` の前に限定（キー集合・reason 集合不変）。
   `config-schema.md` の `symbolGraph`/`docGraph`/`semanticSearch` 行に「非文字列・空・制御文字を含む `bin` は `invalid-config`」。テスト: 各 probe に `bin_nul`・`bin_newline`・`bin_tab` の 3 ケース（`invalid-config`、外部 tool 不起動）。
   **全 reason 分岐でのキー集合検査（Sol CR1-11）**: 3 graph probe テストに「全分岐（ok／not-installed／disabled-by-config／invalid-config／not-configured／各 failed 系）の JSON キー集合が固定集合と完全一致」を追加（`test_output_key_sets_per_branch` 同型）。
9. **SKILL.md:193 の宙吊り参照（#9）**: `Rows 6–8 are defenses for direct probe invocation; an unreadable config stops before Phase 0.` → `An unreadable, non-object, or absent config makes the probe report invalid-config only when the probe is invoked directly; in a normal audit such a config stops before Phase 0.`（`test_v014_contracts.py:90` の固定文を同時更新）。

### D. #10（三重化・性能）— **本 follow-up では共有ヘルパー化しない**（Sol CR1-6〜8: 完全同値の証明が無く共通障害を増やす。別 refactor route に分離し最終報告に載せる）。テスト衛生のみ採用:
10. `tests/test_{mdq_index,ax_probe,codex_probe,probe_record}.py` の裸 `tempfile.mkdtemp()` を `tempfile.TemporaryDirectory()`（`with` または `addCleanup`）に統一し、**`grep -c 'mkdtemp()'` が 4 ファイル合計 0** を機械判定（Sol CR1-12）。`test_codex_probe.py::test_output_key_sets_per_branch` のエイリアス重複は 1 本に統合（S1a の DoD 名 `test_output_key_sets_per_branch` を残す）。

### 見送り（記録のみ、最終報告に列挙）
#10 の共有ヘルパー化（golden 差分実行器を伴う専用 refactor）、#7 の非 ASCII 可読化、review 末尾の low 7 項目。

## 1. 目的
merge 済み v0.14.0 の Phase-5 表示経路が「再開していない通常 run で unknown になる」原因（記録の消失・未束縛・合成不整合）を塞ぎ、状態行の優先順位・graph probe の `bin` 伝送・文言・テスト衛生を整える。verdict ロジックは不変。表示の情報源は `rebind` のみ（変更なし）。

## 2. 入力・参照資料
`/code-review 61` 所見、`critique-cr1-r1-answer.md`、PLAN.md rev.8 §0-5/§0-6、`skills/audit/SKILL.md`（:100-121, :149-154, :193, :267-276, :645, :720-765）、`probe-record.py`、6 probe、`config-schema.md`、対象テスト。

## 3. 担当（boss）
Fable。計画・レビュー・検証再実行・PR 作成。実装は書かない。

## 4. 実行者（worker）
単一 Stage: Terra `medium`。差し戻しは resume。

## 5. 成果物
`SKILL.md`（A1〜A5・B6・C9）、`config-schema.md`（C8）、3 graph probe（C8）、テスト（`test_probe_record`（C7 回帰）、3 graph probe テスト（C8＋キー集合全分岐）、`test_v014_contracts`（固定文・順序）、4 テストの `mkdtemp` 置換、`test_codex_probe` エイリアス統合）。`probe-record.py` は変更しない。

## 6. 完了条件（DoD）— すべて非 0 終了で判定
- (1) `test_v014_contracts.py`: A1 固定文（reopen 後の Phase 0 再実行）、A2 の `or is skipped because PHASE3_BACKEND_CONFIG is codex` と mdq-health 固定 JSON、A3 の正規化文（`always null`／`false`・`probe-error`）、A4 の 1 文、A5 の `rebind.codex-review.available`（旧 `CODEX_REVIEW_AVAILABLE=true`, append は grep 0）、B6 の規則文＋mdq/CM/AX の `invalid-config` 枝が各表の先頭（順序 assert）、C9 新文言（旧 `Rows 6` は grep 0）。
- (2) `test_probe_record.py`: display が U+0085/U+2028/U+2029/`\n` を含む値で 1 行（`"\n" not in`・`splitlines()==1`）。固定 ID 集合更新。
- (3) 3 graph probe テスト: `bin_nul`/`bin_newline`/`bin_tab` → `invalid-config`＋sentinel 不起動、全 reason 分岐のキー集合完全一致。`test_v0132_contracts` green（reason 集合不変）。
- (4) `test "$(grep -c 'mkdtemp()' tests/test_mdq_index.py tests/test_ax_probe.py tests/test_codex_probe.py tests/test_probe_record.py | awk -F: '{s+=$2} END{print s}')" -eq 0`。
- (5) フルスイート: `python3 -m unittest discover -s tests -t . -v > /tmp/cr1-full.log 2>&1; rc=$?; tail -3 /tmp/cr1-full.log; test $rc -eq 0 && test "$(grep -c ' \.\.\. skipped' /tmp/cr1-full.log)" -eq 0`（`Ran N` 報告）。`bash -n` 6 probe。
- (6) 禁止ファイル: `git diff --quiet ef995f0 -- <§7 禁止一覧>`。
- (7) スコープ検査: `SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<同> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py`（allowlist は cr1 用に更新済み。tracked＋未追跡を許可集合と比較、保護 root の hash 一致、exit 1 で違反）。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、
`tests/{test_probe_record.py,test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py}`。
**禁止**: 上記以外（特に `probe-record.py`、3 CLI probe、`decide-verdict.py`、`start-run.py`、`write-evidence.py`、`open-run.py`、`mdq-health.py`、`.claude-plugin/plugin.json`、`engine-shas.json`、`docs/**`、`tasks/**`、`.claude/**`）。
**標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr1-full.log 2>&1; rc=$?; tail -3 /tmp/cr1-full.log; test $rc -eq 0 || exit 1; test "$(grep -c ' \.\.\. skipped' /tmp/cr1-full.log)" -eq 0 || exit 1
python3 -m unittest -v tests.test_probe_record tests.test_codegraph_probe tests.test_graphify_probe tests.test_cocoindex_probe tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe || exit 1
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh || exit 1
test "$(grep -c 'Rows 6\|When `CODEX_REVIEW_AVAILABLE=true`, append' skills/audit/SKILL.md)" -eq 0 || exit 1
test "$(grep -c 'mkdtemp()' tests/test_mdq_index.py tests/test_ax_probe.py tests/test_codex_probe.py tests/test_probe_record.py | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
git diff --quiet ef995f0 -- skills/audit/scripts/probe-record.py skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/docaudit_paths.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/init/SKILL.md agents tests/data docs .claude-plugin skills/audit/references/engine-shas.json && echo forbidden-clean || exit 1
SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<boss commit> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py || exit 1
```
