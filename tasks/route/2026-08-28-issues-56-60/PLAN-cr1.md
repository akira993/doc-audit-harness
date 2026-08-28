# PLAN-cr1 — PR #61 merge 後の `/code-review` 指摘 10 件の修正（rev.6, 2026-08-28 — Sol CR1-R1〜R5（上限）反映。Opus 全体レビューへ）

## 0. 決定事項
ユーザー指示: 「Code-Review で問題があれば、修正計画→Sol レビューを回し、最後に Opus 全体レビュー後、実装、コミット、その後にまた私が Code-Review を打ちます。」
PR #61 は `ef995f0` で merge 済み・**tag 未作成**。修正は branch `fix/v0.14.0-code-review-followup`（main `ef995f0` 起点）、**版は 0.14.0 のまま**。fix PR の merge 後に `release-handoff.sh <最終 merge sha> <fix PR 番号>`。
code-review 所見 10 件（high、CONFIRMED 6・PLAUSIBLE 4、最高 medium）を根本原因で整理。**Phase 5 の情報源は `rebind` のみ、判定不能は常に `unknown`**（Sol CR1-1 — 会話変数へのフォールバックは新設しない）。

### A. フレッシュ run で unknown 行が出る根本原因を塞ぐ（所見 #1・#2・#3・#4・#6）
1. **harness 辞退で run を再取得した後は Phase 0 を丸ごと再実行する（#1、Sol CR1-2）**: SKILL.md:274-276 の reopen 段落を「`open-run.py` の終了値と成功 JSON を確認し、失敗なら既存の exit-4/6 規則で停止 → 成功時のみ `RUNID`・`RUN_DIR`・`EVIDENCE` を新値で束縛」の順に整え、**その束縛文の直後（失敗停止文より後）**に固定文（Sol CR4-1）
   `Then re-run Phase 0 from its first step on the new run — every probe, every probe-record.py call, and the mdq confirmation gate evaluated exactly as on a first pass against the new probe results: if it fires and AskUserQuestion is available and the user has not asked the run not to pause, ask again; if it fires but questions are unavailable or suppressed, bind MDQ_DEGRADE="non-interactive"; if it does not fire or PHASE3_BACKEND_CONFIG is codex, bind MDQ_DEGRADE="n/a"; never reuse an earlier answer — so the new run directory holds its own phase0-probes.json; if that gate evaluation permits the audit to continue, then continue with Phase 0.5 exactly once (the harness question is not asked again because harness.declined is now recorded).`（CR5-1: `Fix mdq first` 選択時は既存どおり解放・終了）（CR4-2 の 3 分岐） を追加（Sol CR2-1／CR3-1: 既回答は再利用しない — `MDQ_DEGRADE` は EVIDENCE に含まれず復元元が無く、`non-interactive`／`n/a` は承認ではない）。
   契約テスト: harness 段落内で **5 要素の相対順**を 1 本の順序テストで固定（CR5-4）: `open-run.py` 呼び出し → 失敗確認・停止文（`if the reopen fails`）→ 成功時のみの `RUNID`/`RUN_DIR`/`EVIDENCE` 束縛文 → 固定文（ちょうど 1 回）→ Phase 0.5 見出し。probe は冪等（mdq index は増分）。会話変数からの再記録は採らない。
2. **`MDQ_DEGRADE` の未束縛（#2）**: SKILL.md:103 の codex backend 分岐を含め、ゲートが発火しない・評価されない全経路で `MDQ_DEGRADE="n/a"` を束縛する: :121 を `When the gate does not fire, or is skipped because PHASE3_BACKEND_CONFIG is codex, bind MDQ_DEGRADE="n/a".` に改める。
   `mdq-health.py` が JSON を返せなかった場合（:100）は固定 JSON `{"files":0,"chunks":0,"searchSmoke":false,"healthy":false,"status":"probe-error"}` を `MDQ_HEALTH_PROBE_JSON` に束縛して記録する（固定文）。
3. **contextMode 合成の正規化（#3、Sol CR1-3 — validator は変えない）**: SKILL.md:153 の合成説明を「`CM_AVAILABLE` が false のとき `contextModeHealthy` は**常に** `null`（`CM_HEALTHY` が束縛済みでも捨てる）。`CM_AVAILABLE` が true で `CM_HEALTHY` が未束縛のときは `contextModeHealthy:false`・`status:"probe-error"` に正規化する」に改める（固定文。表示分岐 3 本と一致）。テスト（CR2-7）: 正規化後の 2 形 `{false,null,"not-installed"}`／`{true,false,"probe-error"}` を書き込み `rebind.context-mode` を完全一致で assert。
4. **unknown 文言の fresh/resumed 共通化（#4、Sol CR2-2）**: 7 行の unknown 文言を `⚠ <name>: state unknown (probe record unavailable) [non-blocking]` に改める（`after resume` を撤去 — フレッシュ run の書き込み失敗でも事実に合う）。codex の `reviewState` null 行と `(caller info unknown after resume)` 接尾辞も `(caller info unavailable)` に（新接尾辞はちょうど 1 回、旧は 0 回を DoD に — CR3-4）。
   同時更新: SKILL 再開段落の固定文（`"state unknown after resume" form` → `"state unknown (probe record unavailable)" form`）、`docs/ADOPTION.md`／`ADOPTION.ja.md` §7 ④（en `prints "state unknown (probe record unavailable)" when it is missing or unreadable`、ja `記録が無いか読めない場合は「state unknown (probe record unavailable)」と表示されます`）、`test_v014_contracts.py` の固定文（`test_v014_behavior_changes_paragraph`・unknown 文言・再開段落）。情報源は `rebind` のみを維持し、会話変数は使わない。SKILL に 1 文「A `⚠ probe-record: <seam> not recorded` warning earlier in the run explains a later unknown line; do not substitute conversation values.」。
5. **接尾辞の gating（#6）**: SKILL.md:757 の「When `CODEX_REVIEW_AVAILABLE=true`, append」→「When `rebind.codex-review.available` is true, append」（診断文も同様）。

### B. 状態行の優先順位（#5）
6. Phase-5 の状態行節の冒頭に共通規則 1 文「Within each status-line table the first matching bullet wins: the whole-record unknown bullet (when the table has one) comes first, the `invalid-config` bullet second, then the remaining states. The codex-review table has no whole-record unknown bullet: its order is invalid-config → reviewState=null → the four CODEX_REVIEW_STATE branches, and rebind.codex-review.state=unknown only replaces the caller suffix with (caller info unavailable).」を置き、**7 表すべて**で順序を契約テストで assert（Sol CR2-4／CR3-2／CR4-3。mdq／context-mode／ax／graph 3 表: unknown → invalid-config → その他。codex-review: `reason=invalid-config` → `reviewState=null` → 4-way、`state=unknown && reviewState!=null` は 4-way＋`(caller info unavailable)` — S1b R4 の順序と `test_probe_record.py:169` の部分状態を維持。現行 CM/AX は `invalid-config` が末尾、graph 3 表は unknown → not-configured → invalid-config → 並べ替え。S1a の「mdq 枝が `MDQ_AVAILABLE` false より前」・S1b R4 の「invalid-config が `phase4-not-required`/`reviewState=null`/`not-active` より前」は維持）。

### C. 文字列伝送の安全性と可読性（#7・#8・#9）
7. **#7（ensure_ascii）は不採用**（Sol CR1-4: `ensure_ascii=False` は U+0085/U+2028/U+2029 で 1 行性を破る。現行 ASCII エスケープは安全側）。`probe-record.py::display` に U+0085/U+2028/U+2029 を含む値でも 1 行であることのテストを追加（現行実装で通る＝回帰防止）。最終報告で「表示は ASCII エスケープ」を明記。
8. **graph 3 probe の `bin` 検査（#8、Sol CR1-5／CR2-3／CR2-8）**: `codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh` の python 判定で、`bin` が **ASCII 制御文字（U+0000–U+001F、U+007F）を含む**場合を `invalid-config` にする。**評価順序は現行どおり `enabled:false` が先勝ち**: `enabled:false` 分岐では bin が空・非文字列・制御文字入りなら出力の bin を既定名へ正規化して `disabled-by-config`（v0.13.2 判定表と同じ）。検査は既存 `emit` の前に限定（キー集合・reason 集合不変）。内部スペースを含むパスは従来どおり許容。
   `config-schema.md` の `symbolGraph`/`docGraph`/`semanticSearch` 行に「`enabled:false` takes priority and reports `disabled-by-config` (a non-string, empty, or control-character `bin` is then replaced by the default name in the output); otherwise a non-string, empty, or ASCII-control-character (U+0000–U+001F, U+007F) `bin` reports `invalid-config`」（Sol CR3-3 — 実装契約と同文）。
   テスト（3 probe 共通）: 33 文字を全走査する拒否テスト（各 `invalid-config`・sentinel 不起動）、**同じ 33 文字ループを `enabled:false` 複合でも走らせ** `disabled-by-config`＋既定 bin＋sentinel 不起動を完全一致（CR3-5）、内部スペースを含むディレクトリの実行ファイルを `bin` に指定して起動され出力 bin が完全一致する正例。
   **全 reason 分岐でのキー集合検査（Sol CR1-11）**: 3 graph probe テストに「全分岐（ok／not-installed／disabled-by-config／invalid-config／not-configured／各 failed 系）の JSON キー集合が固定集合と完全一致」を追加（`test_output_key_sets_per_branch` 同型）。
9. **SKILL.md:193 の宙吊り参照（#9）**: `Rows 6–8 are defenses for direct probe invocation; an unreadable config stops before Phase 0.` → `An unreadable, non-object, or absent config makes the probe report invalid-config only when the probe is invoked directly; in a normal audit such a config stops before Phase 0.`（`test_v014_contracts.py:90` の固定文を同時更新）。

### D. #10（三重化・性能）— **本 follow-up では共有ヘルパー化しない**（Sol CR1-6〜8: 完全同値の証明が無く共通障害を増やす。別 refactor route に分離し最終報告に載せる）。テスト衛生のみ採用:
10. `tests/test_{mdq_index,ax_probe,codex_probe,probe_record}.py` の裸 `tempfile.mkdtemp()` を `tempfile.TemporaryDirectory()`（`with` または `addCleanup`）に統一し、**識別子 `mkdtemp` が 4 ファイル合計 0** を機械判定（Sol CR1-12／CR2-9）。`test_codex_probe.py::test_output_key_sets_per_branch` のエイリアス重複は 1 本に統合（S1a の DoD 名 `test_output_key_sets_per_branch` を残す）。

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
- (1) `test_v014_contracts.py`: A1 固定文（reopen 後の Phase 0 再実行・`never reuse an earlier answer` を含む、count==1＋位置）、新接尾辞 `(caller info unavailable)` ちょうど 1 回・旧 `caller info unknown after resume` 0 回、A4 の新 unknown 文言 7 行＋§7 ④ en/ja（旧 `state unknown after resume` は SKILL/ADOPTION/テストで grep 0）、A2 の `or is skipped because PHASE3_BACKEND_CONFIG is codex` と mdq-health 固定 JSON、A3 の正規化文（`always null`／`false`・`probe-error`）、A4 の 1 文、A5 の `rebind.codex-review.available`（旧 `CODEX_REVIEW_AVAILABLE=true`, append は grep 0）、B6 の規則文＋順序 assert（**6 表**（mdq／context-mode／ax／symbol-graph／doc-graph／semantic-search）は unknown → invalid-config → その他、**codex-review** は invalid-config → reviewState=null → 4-way で whole-record unknown 枝を持たず、`state=unknown && reviewState!=null` は 4-way＋`(caller info unavailable)` — CR5-2）、C9 新文言（旧 `Rows 6` は grep 0）。
- (2) `test_probe_record.py`: display が U+0085/U+2028/U+2029/`\n` を含む値で 1 行（`"\n" not in`・`splitlines()==1`）。固定 ID 集合更新。
- (3) 3 graph probe テスト: 制御文字 33 文字全走査 → `invalid-config`＋sentinel 不起動（enabled 側 33 件）、**同じ 33 文字を `enabled:false` 複合で 33 件** → `disabled-by-config`＋既定 bin＋sentinel 不起動（CR4-5）、内部スペース入りパスの正例、全 reason 分岐のキー集合完全一致。`test_v0132_contracts` green（reason 集合不変）。
- (4) `test "$(grep -c 'mkdtemp' tests/test_mdq_index.py tests/test_ax_probe.py tests/test_codex_probe.py tests/test_probe_record.py | awk -F: '{s+=$2} END{print s}')" -eq 0`。
- (5) フルスイート: `python3 -m unittest discover -s tests -t . -v > /tmp/cr1-full.log 2>&1; rc=$?; tail -3 /tmp/cr1-full.log; test $rc -eq 0 && test "$(grep -c ' \.\.\. skipped' /tmp/cr1-full.log)" -eq 0`（`Ran N` 報告）。`bash -n` 6 probe。
- (6) 禁止ファイル: `git diff --quiet ef995f0 -- <§7 禁止一覧>`。
- (7) スコープ検査: `BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<同> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py`（CR2-5。allowlist は cr1 用、tracked＋未追跡を許可集合と比較、保護 root の hash 一致、exit 1 で違反）。
- (8) ADOPTION の段落限定（CR3-7／CR4-4）: §8 の python 片で、`git show ef995f0:docs/ADOPTION.md` に対し旧句 `state unknown after resume` → 新句 `state unknown (probe record unavailable)` を**ちょうど 1 回**置換した期待バイト列と実ファイルが完全一致（ja も同様）。差分 0 件・同一行の別改変は失敗。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{codegraph-probe.sh,graphify-probe.sh,cocoindex-probe.sh}`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`（§7 ④ の unknown 文言のみ）、
`tests/{test_probe_record.py,test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codegraph_probe.py,test_graphify_probe.py,test_cocoindex_probe.py,test_v014_contracts.py}`。
**禁止**: 上記以外（特に `probe-record.py`、3 CLI probe、`decide-verdict.py`、`start-run.py`、`write-evidence.py`、`open-run.py`、`mdq-health.py`、`.claude-plugin/plugin.json`、`engine-shas.json`、`docs/**` の §7 ④ 以外、`tasks/**`、`.claude/**`）。
**標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/cr1-full.log 2>&1; rc=$?; tail -3 /tmp/cr1-full.log; test $rc -eq 0 || exit 1; test "$(grep -c ' \.\.\. skipped' /tmp/cr1-full.log)" -eq 0 || exit 1
python3 -m unittest -v tests.test_probe_record tests.test_codegraph_probe tests.test_graphify_probe tests.test_cocoindex_probe tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe || exit 1
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh || exit 1
test "$(grep -c 'Rows 6\|When `CODEX_REVIEW_AVAILABLE=true`, append' skills/audit/SKILL.md)" -eq 0 || exit 1
test "$(grep -c 'mkdtemp' tests/test_mdq_index.py tests/test_ax_probe.py tests/test_codex_probe.py tests/test_probe_record.py | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
test "$(grep -c 'state unknown after resume' skills/audit/SKILL.md docs/ADOPTION.md docs/ADOPTION.ja.md tests/test_v014_contracts.py | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
git diff --quiet ef995f0 -- skills/audit/scripts/probe-record.py skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/docaudit_paths.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/init/SKILL.md agents tests/data .claude-plugin skills/audit/references/engine-shas.json && echo forbidden-clean || exit 1
BASE_COMMIT=ef995f0 SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<boss commit> python3 tasks/route/2026-08-28-issues-56-60/scope-check.py || exit 1
python3 - <<'PY' || exit 1
import subprocess,sys
old=b'state unknown after resume'; new=b'state unknown (probe record unavailable)'
bad=[]
for f in ('docs/ADOPTION.md','docs/ADOPTION.ja.md'):
    base=subprocess.run(['git','show','ef995f0:'+f],capture_output=True,check=True).stdout
    if base.count(old)!=1: bad.append(f+': baseline has %d occurrences'%base.count(old)); continue
    if open(f,'rb').read()!=base.replace(old,new): bad.append(f+': differs from the single-replacement expectation (bytes)')
print('\n'.join(bad) or 'adoption-clean'); sys.exit(1 if bad else 0)
PY
test "$(grep -c 'caller info unknown after resume' skills/audit/SKILL.md tests/test_v014_contracts.py | awk -F: '{s+=$2} END{print s}')" -eq 0 || exit 1
```
