# S2 実装依頼 — docaudit v0.13.2: 版バンプ・engine-shas・ADOPTION §7 段落・契約テスト再照準・release-handoff

あなたは実装担当（worker）。boss（Claude）が確定した計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（rev.8）に従って **S2 のみ** を実装する。
S1a・S1b（#52〜#54 の本体）は反映・commit 済みの tree が前提。PLAN.md を最初に全文読むこと（§0-6・§0-7・§0-8 と DoD (16)〜(19) が仕様の正）。

## 事前承認（boss）
PLAN.md §7「許可（S2）」に列挙された既存ファイルの上書きと、新規ファイル（`release-handoff.sh`、`stage2-report.md`）の作成を **包括的に承認済み**である。この範囲内の上書きについて個別確認のために停止してはならない。許可外ファイルの変更が必要になった場合のみ、修正せず報告せよ。

## S2 の範囲
1. 版バンプ 5 面: `.claude-plugin/plugin.json` の `version` → `0.13.2`、`docs/ADOPTION.md:224`／`docs/ADOPTION.ja.md:206` の `claude plugin list` 行 → `Version 0.13.2`、
   refresh 段落（en `ADOPTION.md:284`／ja `.ja.md:264-265`）を PLAN §0-6 の **行単位の完全文言**に。`skills/audit/references/engine-shas.json` に `0.13.2` entry
   （`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run` で `stampVersion` と hash を確認。テンプレート不変なら 0.13.1 と同一 hash）。
2. ADOPTION §7 に `**v0.13.2 behavior changes:**`／`**v0.13.2 の挙動変更:**` 段落（`v0.12.0` 段落の直後、同型）。en は PLAN DoD (17) の固定文 ①〜⑤ をこの文言で
   （文書慣習どおりハードラップ・コードスパン付きでよい。契約テストは空白正規化＋バッククォート除去後に `assertIn`）、ja も DoD (17) の固定文 5 つをこの文言で。
   契約テスト `test_v0132_behavior_changes_paragraph` を `tests/test_v0132_contracts.py` に追記（検査方法は DoD (17) のとおり）。
3. 既存契約テストの再照準: `tests/test_v013_contracts.py` test_i の集合 `{"0.13.2"}`、test_j の allowlist（refresh 行 regex を新文言に。en/ja）、
   `tests/test_v0131_docs_contracts.py` test_g の target 集合に `"0.13.1"`、`tests/test_scaffold.py` の `0.13.1` → `0.13.2`（:214-218, :242-246, :312）。
4. `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` を前版 `tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh` と同型で作成:
   `TAG_NEW="docaudit--v0.13.2"`、`RELEASE_TITLE="docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)"`、notes は
   `Ships issues #52, #53, and #54.` と「Absent docGraph/semanticSearch/symbolGraph keys now report not-configured; CocoIndex initialization requires .cocoindex_code/settings.yml;
   fix-scope docGlobs default aligned; seal failures stop the run.」を含め（必須語 `#52` `#53` `#54` `not-configured` `settings.yml`）、Issue close ループは `52 53 54`、
   close コメントは `Shipped in docaudit v0.13.2 (PR #$PR_NUMBER, tag docaudit--v0.13.2).`。`bash -n` 通過。
   `tests/test_release_handoff.py` を新 script に再照準（HANDOFF パス、TAG、TITLE、ISSUES `range(52, 55)`、PRECLOSED、REQUIRED_BODY、Issue 番号を参照する全箇所）。
5. 報告に `Ran N tests` の実数（`python3 -m unittest -v tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff tests.test_v0132_contracts`）を添える。

## 注意
- `.gitignore` が `tasks/` を無視するため新 script は未追跡でよい（boss が `git add -f` する）。`git` への書き込みは行わない。CHANGELOG は作らない。`README.md` は触らない（badge 自動追従）。
- `tests/test_release_handoff.py` は 454 行あり v0.13.1 固有値が本体にも散在する（`:424` tag refspec、`:436,:457` Issue close 件数、`:442,:449` Issue 番号など）。`grep -n '0\.13\.1\|46\|47\|48\|49\|50' tests/test_release_handoff.py` で全箇所を洗い出してから再照準し、洗い出し結果（件数）を報告に書く。
- Terra の sandbox では 30 秒超のフルスイートが完走しないことがある。フルは boss が実行する。
- 対象外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。`?? .claude/` は対象外。

## 報告（最後に `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage2-report.md` へ書き出す）
1. 変更ファイル一覧と要旨。2. PLAN DoD (16)〜(19)・(21)・(22) の各項目について実行コマンドと実測結果（engine-shas の hash 一致/不一致を明記）。3. テストコマンドと `Ran N tests` 実数。
4. 未対応・判断に迷った点・対象外ファイルの変更が必要と判断した点。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認

---
# 以下、PLAN.md の完了条件・変更範囲・検証コマンド一式（原文。S2 に該当する項目に従う）
