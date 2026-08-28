# S1b 実装依頼 — docaudit v0.13.2: Issue #54（report-only 監査の Phase-0 probe が worktree に書き込む）

あなたは実装担当（worker）。boss（Claude）が確定した計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（rev.8）に従って **S1b のみ** を実装する。
S1a（#52・#53・fixture）は反映済みの tree が前提（`tests/test_v0132_contracts.py` は既に存在する — **追記**する）。S2（版バンプ・handoff）は別依頼なので触らない。
PLAN.md を最初に全文読むこと（§0-4・§0-5 が仕様の正。判定表・評価順序・JSON 形状・固定文言・テスト名はすべて PLAN の記載に従う）。
Issue 本文: 同ディレクトリ `issues-52-54.md`。設計判断の根拠は `REVIEW.md` と `critique-r*-answer.md`（再審議しない）。

## S1b の範囲
1. #54-1 3 probe（`graphify-probe.sh`／`cocoindex-probe.sh`／`codegraph-probe.sh`）の config 解釈を PLAN §0-4 の判定表（10 行）＋評価順序どおりに実装。
   reason `not-configured`／`invalid-config` を追加。出力 JSON の形状は §0-4「probe JSON の形状」どおり（キー集合不変・既定名 Bin・graphify は常に gitignoreOk・全分岐 exit 0）。
   `enabled` は JSON boolean のみ（Python で `isinstance(v, bool)` を先に判定）。`minScore` は `isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)`。
2. #54-2 `cocoindex-probe.sh`: 初期化済み判定を `-f "$REPO_ROOT/.cocoindex_code/settings.yml"` に。`ccc index` 前後で `.gitignore` の存在有無＋sha256 を比較し、変化していれば
   `semanticSearchAvailable:false, reason:"gitignore-modified"`（**書き戻さない**、exit code より優先、stderr 1 行）。ヘッダコメントを更新（settings.yml マーカー・
   `ccc index` の自動 init 経路（`require_project_root(auto_init=True)` → `.gitignore` 追記）・親 git root anchor の限界）。
3. `skills/audit/SKILL.md`: Phase 0 の 3 probe 段落（:174-215）を `<VAR>_PROBE_JSON="$(bash …)"` 捕捉＋`<VAR>_REASON` 束縛（`["reason"]` からの完全な式）＋reason 列挙の
   更新（`not-configured`・`invalid-config`、cocoindex は `gitignore-modified` も）＋settings.yml マーカーの説明（:211 含む）＋「行 6〜8 は通常経路では probe 前に停止する」の 1 句に。
   Phase 5 の 3 状態行（:678-694）を `*_REASON` による排他表に書き直し（doc-graph 6-state（7 messages）／symbol-graph 6-state／semanticSearch 8-state。新枝の文言は
   PLAN §0-4・§0-5。既存文言はできるだけ保つ。他の状態行は変えない）。
4. `skills/audit/references/config-schema.md`: :37-39 の 3 行と 3 節（:257-320）に reason 追加・key-gated 化（conditional-force 一掃）・:39 の「runtime reads only」を
   「the probe validates enabled/bin/minScore; Phase 2 uses minScore」に・:309 の settings.yml 化。
5. `docs/ADOPTION.md`／`docs/ADOPTION.ja.md`: tool 表（:85-87／:84-86）・seam 段落（:147-172／:131-156）の conditional-force／auto-used 一掃と settings.yml 化、
   状態行要約（:197-198／:179-180）に not configured／未設定・invalid／不正 を追加。**§7 の v0.13.2 段落は S2 なので書かない。**
6. `skills/init/SKILL.md`: :52（`.cocoindex_code/` 存在判定 → settings.yml）、:147-163 の symbolGraph／docGraph／semanticSearch の OMIT 文 3 か所に
   「absent key ⇒ the audit reports `not-configured` and never runs the tool」、:155-158 の「already exists」を settings.yml 基準に。他 seam の OMIT 文は不変。
7. テスト: `tests/test_graphify_probe.py`／`test_codegraph_probe.py` に各 10 件、`tests/test_cocoindex_probe.py` に 10＋2＋1（legacy dir）＋3（gitignore）件、すべて PLAN DoD 8・12・13 の
   固定名・subTest 入力・PATH stub／settings.yml 条件どおり。`tests/test_v0132_contracts.py` に追記: DoD 9 `test_probe_reason_enumerations_match_fixed_sets`、
   DoD 10 `test_phase5_status_lines_map_each_reason_to_one_branch`、DoD 10b `test_phase0_binds_reason_from_each_probe_json`、DoD 11
   `test_init_skill_marks_three_omit_rules_as_not_configured`、DoD 14 `test_settings_yml_marker_documented_in_five_files`、§0-4 B1
   `test_three_seams_no_longer_documented_as_auto_used`、DoD 12 の config-schema:39 文言検査。各 test の docstring に DoD 番号。

## 事前承認（boss）
PLAN.md §7「許可（S1b）」に列挙された既存ファイルの上書きと、新規ファイル（`stage1b-report.md`、テスト追記）の作成を **包括的に承認済み**である。この範囲内の上書きについて個別確認のために停止してはならない。許可外ファイルの変更が必要になった場合のみ、修正せず報告せよ。

## 注意
- `git` への書き込み（add/commit/checkout）は行わない。既存テストを緩めない（cocoindex の ok／index-failed fixture に `settings.yml` を置く変更は可）。
- Terra の sandbox では 30 秒超のフルスイートが完走しないことがある。その場合は `python3 -m unittest -v tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe tests.test_v0132_contracts tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_impact_supplement` を実行して結果を報告し、フルは boss が実行する旨を書く。
- 対象外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。`?? .claude/` は対象外。

## 報告（最後に `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1b-report.md` へ書き出す）
1. 変更ファイル一覧と要旨。2. PLAN DoD (8)〜(14)・(20)〜(22)・§0-4 B1 の各項目について実行コマンドと実測結果。3. テストコマンドと `Ran N tests` 実数・OK/FAIL。
4. 未対応・判断に迷った点・対象外ファイルの変更が必要と判断した点。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認

---
# 以下、PLAN.md の完了条件・変更範囲・検証コマンド一式（原文。S1b に該当する項目に従う）
