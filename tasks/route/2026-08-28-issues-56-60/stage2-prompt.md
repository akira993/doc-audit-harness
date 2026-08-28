あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-issues-56-60`）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN.md`（rev.8）の **Stage S2**（版 bump・ADOPTION §7・engine-shas・release handoff・契約テスト再標的）を実装せよ。S1a／S1b は commit 済み（`git log` で確認）。
PLAN.md 全文を最初に読み、§0-1・§0-10 と §6 の (12)(13)(14)(15)(16)、§7、§8 に従う。不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。
**PLAN.md・REVIEW.md・allowlist.txt・baseline-hashes.txt・59-design-note.md・scope-check.py は読むだけで変更しない。** 既存ファイルの上書き・新規作成は本プロンプトで包括承認する（再確認不要）。単独で作業し、collab／サブエージェントは使わない。git commit は行わない。

## S2 の内容（PLAN §0-10 を正とする）
1. 版 `0.14.0`: `.claude-plugin/plugin.json`；`docs/ADOPTION.md`（`claude plugin list` 表示行 `Version 0.14.0`、refresh 段落を `Existing unmodified stamped 0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.13.1, or 0.13.2 templates can be updated directly to 0.14.0 with`）；`docs/ADOPTION.ja.md`（同、`0.10.1、0.11.0、0.12.0、0.13.0、0.13.1、または 0.13.2 テンプレートは、… 0.14.0 へ`）。
2. `skills/audit/references/engine-shas.json` に `0.14.0` entry（テンプレート不変のため `0.13.2` と同値の 3 hash。`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run` の `stampVersion` が `0.14.0` になることを確認）。
3. テスト再標的: `tests/test_scaffold.py:214,217,218,242,245,246,312`／`tests/test_v013_contracts.py:201` の `0.13.2` → `0.14.0`；**`tests/test_v013_contracts.py:210,215`（test_j の refresh 許可 regex en/ja）の版列挙を新文言に更新**。
4. ADOPTION §7: `docs/ADOPTION.md` の `**v0.13.2 behavior changes:**` 段落の直後に `**v0.14.0 behavior changes:**` 段落（1 段落、ハードラップ・コードスパン可）、`docs/ADOPTION.ja.md` に `**v0.14.0 の挙動変更:**` 段落。en は次の固定文 6 つをこの文言で含む:
   ① `indexing / contextMode / webExtract / codexReview keys now require a JSON boolean enabled; unless enabled is false, a non-boolean enabled, a non-object key (including null), or — for indexing / webExtract / codexReview — a non-string, empty, or NUL-containing bin reports invalid-config and never runs the tool (an absent key still defaults to enabled; a non-string bin is no longer coerced; an unreadable config still stops the audit before Phase 0 as before)`
   ② `an invalid indexing key fires the Phase-0 mdq confirmation gate like not-installed`
   ③ `codexReview.required:true combined with an invalid codexReview key is now REFUSED instead of silently running codex`
   ④ `Phase-0 probe results are persisted to $RUN_DIR/phase0-probes.json (display-only, never a verdict input); Phase-5 status lines are rendered from that record on fresh and resumed runs and print "state unknown after resume" when it is missing or unreadable`
   ⑤ `the codex probe reports the caller's CODEX_HOME and whether auth.json exists there (display-only; a wrapper's own environment is not observed)`
   ⑥ `import-audit-scope.py accepts an absolute --config/--scope path under the repository root (POSIX paths only)`
   ja は同順の肯定形 6 文（自然な日本語で起草。boss が検分する）。契約テスト `tests/test_v014_contracts.py::test_v014_behavior_changes_paragraph`（段落を `re.split(r"\n\s*\n", text)` で割り `" ".join(p.split())` で正規化・バッククォート除去後 `assertIn`。en 6 文・ja 6 文）。
5. Release handoff: 前版 `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` を雛形に `tasks/route/2026-08-28-issues-56-60/release-handoff.sh`（新規）を作る。差分は: tag `docaudit--v0.14.0`、Issue close は `57 58 60` のみ、title `docaudit v0.14.0 — invalid-config for all seams, probe persistence, CODEX_HOME visibility`、Release notes に完全一致で
   `Closes #57, #58, #60.` と `Partially addresses #56 (stage 1) and #59 (operational note); both remain open.` を含み、必須語 `#56 #57 #58 #59 #60 invalid-config phase0-probes.json CODEX_HOME` を含む。version 検査は `0.14.0`、skills-dir 同期検査は前版と同じ。`bash -n` 通過。
   `tests/test_release_handoff.py` を新 script に再標的（path・tag・title・Issue 集合・notes の完全一致 2 文・必須語）。**旧定数 `docaudit--v0.13.2`／`2026-08-28-issues-52-54-v0.13.2` をテストファイルに残さない。**
6. `0.13.2` 残存: repo 全体 `git grep -n '0\.13\.2' -- . ':!tasks' ':!tests/test_v0132_contracts.py' ':!tests/data'` の一致が、許可 = `engine-shas.json` の `"0.13.2": {` entry、ADOPTION en/ja の §7 v0.13.2 段落、refresh 段落の列挙（en `0.13.1, or 0.13.2`、ja `0.13.1、または 0.13.2`）のみであること。

## 完了条件（PLAN §6 (12)〜(16)＋共通）
- (12) `python3 -m unittest tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff tests.test_v014_contracts` green。5 面（plugin.json、ADOPTION en/ja の表示行、engine-shas、scaffold stampVersion）が `0.14.0`。
- (13) `test_v014_behavior_changes_paragraph` green（en 6・ja 6）。
- (14) `test_release_handoff.py` green、`grep -c 'docaudit--v0.13.2\|issues-52-54' tests/test_release_handoff.py` = 0、`bash -n release-handoff.sh`、残存 grep が許可外 0 件。
- (15) フルスイート green・skip 0。`Ran N` 実数。
- (16) `bash -n`、`py_compile` 変更 .py。
- (18) 禁止ファイル差分なし。

## 変更範囲（PLAN §7 の S2 分）
**許可**: `.claude-plugin/plugin.json`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`skills/audit/references/engine-shas.json`、`tests/test_scaffold.py`、`tests/test_v013_contracts.py`、`tests/test_release_handoff.py`、`tests/test_v014_contracts.py`、`tasks/route/2026-08-28-issues-56-60/release-handoff.sh`（新）。
**禁止**: 上記以外すべて（`skills/audit/SKILL.md`・scripts・`data/**`・`tests/data/**`・`.claude/**`・`tasks/**` の他ファイル）。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 検証コマンド一式（すべて実行し、要点と exit code を報告）
```
python3 -m unittest discover -s tests -t . -v > /tmp/s2-full.log 2>&1; tail -3 /tmp/s2-full.log; test "$(grep -c ' \.\.\. skipped' /tmp/s2-full.log)" -eq 0 || echo SKIP-FOUND
python3 -m unittest -v tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff tests.test_v014_contracts
bash -n tasks/route/2026-08-28-issues-56-60/release-handoff.sh
python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run | python3 -c 'import json,sys;print(json.load(sys.stdin)["stampVersion"])'
test "$(grep -c 'docaudit--v0.13.2\|issues-52-54' tests/test_release_handoff.py)" -eq 0 || echo OLD-CONSTANTS
git grep -n '0\.13\.2' -- . ':!tasks' ':!tests/test_v0132_contracts.py' ':!tests/data' | grep -v 'engine-shas.json:.*"0.13.2": {\|ADOPTION.*v0.13.2 behavior changes\|ADOPTION.*v0.13.2 の挙動変更\|ADOPTION.*0.13.1, or 0.13.2\|ADOPTION.ja.*0.13.1、または 0.13.2' ; echo "residual-grep-exit=$? (1 が正)"
git diff --quiet HEAD -- skills/audit/SKILL.md skills/audit/scripts skills/init data tests/data && echo forbidden-clean
git status --short
```

## 報告形式
Markdown で: (1) 変更ファイルと要点、(2) DoD ごとの固定テスト名と `Ran N`、(3) 検証コマンドの結果（失敗は出力ごと）、(4) PLAN との乖離・許可外変更が必要だった点・未実施（無ければ「無し」）。ja の §7 段落全文を報告に含める（boss 検分用）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
