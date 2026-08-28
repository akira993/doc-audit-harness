# S1a 実装依頼 — docaudit v0.13.2: Issue #52（fix-scope 既定＋組込み deny）・#53（seal 停止分岐＋read-manifest sealed 検査）・既往 red の fixture 化

あなたは実装担当（worker）。boss（Claude）が確定した計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（rev.7）に従って **S1a のみ** を実装する。
S1b（#54: 3 probe・状態行・conditional-force 一掃・cocoindex 文書）と S2（版バンプ・handoff）は別依頼なので触らない。PLAN.md を最初に全文読むこと（§0 が仕様の正）。
Issue 本文: 同ディレクトリ `issues-52-54.md`。設計判断の根拠は `REVIEW.md` と `critique-r*-answer.md`（再審議しない）。

## S1a の範囲（PLAN §0-2・§0-3・§0-12。固定文言・テスト名は PLAN が正）
1. #52 `skills/audit/scripts/fix-scope.py`: `docGlobs` 既定を `["docs/**/*.md", "*.md"]` に。`DENIED_PARTS` と並ぶ basename deny（`casefold()` 比較で `claude.md`／`agents.md`、
   任意の深さ、docGlobs より優先、理由文字列は既存 deny と同型）。`:87` の fail-closed コメントを撤去。
   文書: `config-schema.md:10`、`docs/ADOPTION.md:310`、`docs/ADOPTION.ja.md:291` の docGlobs 行から fail-closed／全パス拒否の記述を外し「pre-flight fix path も同じ既定」に。
   組込み deny の列挙 5 か所（`config-schema.md:30`・`:157`、`skills/audit/SKILL.md:284`、`ADOPTION.md:333`、`ADOPTION.ja.md:314` — 行番号は目安、内容で特定）に
   `CLAUDE.md`／`AGENTS.md`（case-insensitive／大文字小文字を区別しない）を追加。
2. #53 `skills/audit/SKILL.md` Phase 3: seal 手順に 3 停止分岐（exit 5／`Any other non-zero exit`／`read-manifest.py` 失敗）を記述し、**各分岐に SKILL.md:52 の完全な解放コマンド**
   （`--run-base`・`--repo-root`・`--anchor-path`・`--release --runid "$RUNID"`）を伴わせる。exit 5 の既存メッセージは不変。行頭 `` `SEALED_MANIFEST="$(python3 "$SD/scripts/read-manifest.py" `` の
   行の形は崩さない（`tests/test_v013_contracts.py:101-103` が依存）。
   `skills/audit/scripts/read-manifest.py`: hash 一致後に `isinstance(manifest, dict) and manifest.get("sealed") is True` を一体で検査、不成立は
   `ValueError("manifest is not sealed")` → exit 2・stdout 空。`codex-dispatch.py` は変更しない。
3. §0-12 `tests/data/dir-framework-scope/{audit-scope.json,doc-audit.json,paths.txt}` を PLAN の手順で作成（dir-framework は `git -C ~/Projects/dir-framework show/ls-tree` の読み取りのみ）。
   3 点の sha256 が PLAN の固定値と一致することを自分で確認してから、`tests/test_import_audit_scope.py` の当該テストを fixture 版
   `test_dir_framework_fixture_scope_is_not_imported_with_24_rules_and_48_paths` に置換（`DIR_FRAMEWORK` 定数・skip 条件を削除。空ファイル → JSON 上書きの順）。
4. テスト: `tests/test_read_manifest.py` に 4 件（PLAN DoD 6 の固定名）。**新規** `tests/test_v0132_contracts.py` に `TestFixScopeDefaults`（DoD 2 の 2 件、DoD 3 の 1 件）、
   `test_builtin_deny_documented_in_five_places`（DoD 4）、`test_doc_globs_rows_no_longer_say_fail_closed`（DoD 4）、`test_phase3_three_stop_branches_release_the_run`（DoD 5）。
   各 test の docstring に DoD 番号。S1b の契約テストは書かない（S1b が同ファイルに追記する）。

## 注意
- `.gitignore` が `data/` と `tasks/` を無視するため新 fixture は未追跡のままでよい（boss が `git add -f` する）。`git` への書き込み（add/commit/checkout）は行わない。
- 既存テストを緩めない。`tests/test_wp12_contracts.py` の fix-scope テストが新 deny で影響を受ける場合のみ最小修正し、理由を報告。
- Terra の sandbox では 30 秒超のフルスイートが完走しないことがある。その場合は `python3 -m unittest -v tests.test_v0132_contracts tests.test_read_manifest tests.test_import_audit_scope tests.test_wp12_contracts tests.test_codex_dispatch tests.test_v013_contracts tests.test_v0131_docs_contracts` を実行して結果を報告し、フルは boss が実行する旨を書く。
- 対象外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。
- `git status --short` の未追跡 `?? .claude/` は本タスク以前から存在する worktree コピーで対象外。

## 報告（最後に `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1a-report.md` へ書き出す）
1. 変更ファイル一覧と要旨。2. PLAN DoD (1)〜(7)・(15)・(20)〜(22) の各項目について実行コマンドと実測結果。3. テストコマンドと `Ran N tests` 実数・OK/FAIL。
4. 未対応・判断に迷った点・対象外ファイルの変更が必要と判断した点。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認

---
# 以下、PLAN.md の完了条件・変更範囲・検証コマンド一式（原文。S1a に該当する項目に従う）
