# S2 実装依頼 — #40 飽和可視化＋#39 regression 再検証（resolve-impact / plan-dispatch / impact-supplement）（PLAN rev.8 §4 S2）

あなたは実装者（worker）。boss（Fable）が計画とレビューを担当する。計画の正本は
`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（rev.8、Opus 承認済み）。本依頼の範囲は **S2 のみ**。gate（decide-verdict）・
start-run・seal-run・codex-dispatch・SKILL の manifest 再束縛・#44・#42 は行わない（S3/S4a/S4b）。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。

包括承認（boss）: 読み取り・テスト実行・許可パス内の編集は事前承認済み。個別確認を求めずに完了まで進めよ。**git 操作
（checkout/add/commit）は sandbox の制約で失敗するため行わない — boss が行う。** 許可パス外・`git push`・`rm -rf`・パッケージ
導入は禁止（必要なら報告のみ）。

## 0. 事前準備
1. 現在のブランチが `feat/v0.13.0-issues-39-44`（S1 のコミット `3e2b404`・`dd6ba4a` が載っている）であることを `git log --oneline -3`
   で確認。`git status --short` が空（`.claude/` を除く）であること。
2. `python3 -m unittest discover -s tests -t .` を実行し着手前の件数と結果を記録（S1 完了時点の件数）。

## 1. #40 — `skills/audit/scripts/resolve-impact.py`（PLAN §10 #40）
- `counts.docCorpus = len(doc_files)`（report 除外後の corpus 件数）。
- `counts.heuristicSaturation = round(len(heur_only) / docCorpus, 3)`（pre-cap の heuristic-only 候補数／corpus。docCorpus 0 なら
  `0.0`。**閾値比較は丸め前の比率**で行う）。
- `heuristics.saturationWarnRatio`: bool を除く数値（int/float）を受理、既定 `0.5`、`0` で無効。負数・1 超・文字列・bool・None
  以外の不正型は `warnings[]` に 1 行（`heuristics.saturationWarnRatio invalid (...); using default 0.5`）を出して既定値。
- `heuristicOnly > 0` かつ比率 ≥ 閾値のとき `warnings[]` に:
  `heuristic saturation: <heur>/<corpus> docs (<pct>%) reached only by the token heuristic — impactMap is not carrying the selection;
  promote couplings from mapGapCandidates to impactMap`（corpus 下限なし。9/9 でも出す）。
- `heuristics.excludeDocPathTokens`（bool、既定 false。非 bool は warning＋既定値）: true のとき、docGlobs に一致する変更パスから
  token を生成しない（`tokens_for()` の入力段で除外）。
- cap 超過（`maxImpactedDocs`）の stderr 警告を `warnings[]` にも同文で入れる。
- `regressionRecheck` が非 object、または `regressionRecheck.enabled` が非 bool のときは warning＋既定値（false）。

## 2. #39 — resolve-impact.py の regression 再検証（PLAN §10 #39）
- 新引数 `--history PATH`（任意）。`regressionRecheck.enabled`（既定 **false**）。**incremental のみ**（`--mode full` では無効）。
- 有効時: `docaudit_cache.parse_history` で history を読む。path ごとの**最後の entry**（配列順で最後）が `verdict == "FAIL"` なら
  候補。docGlobs 一致・report 除外・実在（`validate_repo_path` 経由の既存 `exists()`）を満たすものを provenance 集合に
  `regression` として追加。
- `provenance()`: 既存規則（mapped/heuristic/both/full）を優先し、`regression` 単独のときのみ `"regression"` を返す。
- **cap 優先順位 `mapped ≥ regression ≥ heuristic`**（`ordered = mapped_paths + regression_only + heur_only`）。supplement 側は
  `≥ graphify ≥ semantic`（§3）。
- `counts.regression` = 出力 impacted のうち provenance == `regression` の件数。
- history 不在（ファイルなし）は無音（`counts.regression = 0`、warning なし）。history 破損（JSON 不正・`parse_history` 例外）は
  `warnings[]` に 1 行（`regression recheck skipped: history unreadable (<reason>)`）。
- `--history` が与えられ、かつ regressionRecheck 有効のとき、出力 JSON に `historySha`（読んだ history の**生 bytes** の sha256、
  形式 `sha256:<64hex>`。不在は `null`）。無効時は `historySha` を出さない（キー自体を省略）。
- `mapGapCandidates` は従来どおり provenance == `heuristic` のみ（regression は含めない）。

## 3. `skills/audit/scripts/impact-supplement.py`
- docstring（`:5-9`）の優先順位を `mapped ≥ regression ≥ heuristic ≥ graphify ≥ semantic` に更新。既存の impacted は無条件に保持する
  契約はそのまま（regression 項目も displaced されない）。コードの挙動変更は「既存 impacted を保持し残枠にのみ追加」の現行で
  十分か確認し、必要な最小変更のみ。

## 4. `skills/audit/scripts/plan-dispatch.py`
- impact.json に `historySha` があれば、自身が読んだ history bytes の sha256 と照合し、不一致なら stderr に
  `history changed between resolve and dispatch` を出して非 0 終了（exit 3）。history 不在で `historySha` が `null` なら整合とみなす。
- supplement 後の impact.json（`--impact-json` で渡されたファイル）の**生 bytes** の sha256 を `impactSha`（`sha256:<64hex>`）として
  **dispatch.json 内**に記録する。EVIDENCE（stdout の evidence JSON）のキー集合は**変えない**（`impactSha` を EVIDENCE に足さない）。

## 5. SKILL / docs / 消費側（S2 分）
- `skills/audit/SKILL.md` Phase 2: `resolve-impact.py` の**コマンド行**に `--history "$CLAUDE_PROJECT_DIR/.claude/state/docaudit-history.json"`
  を追加。順序記述（`mapped ≥ heuristic ≥ graphify ≥ semantic`、`:322` 付近）を `mapped ≥ regression ≥ heuristic ≥ graphify ≥ semantic`
  に更新。Phase 2 の `counts{...}` 列挙に `docCorpus, heuristicSaturation, regression` を追加。
- provenance `regression` の意味を **7 消費側**に追加（文言: 「前回 FAIL・内容不変の再検証。以前の指摘クラスが実際に解消している
  かを確認する。impactMap-gap 候補ではない」）: `agents/doc-impact-verifier.md:15,36-38`、`agents/doc-impact-verifier-light.md:37-38`、
  `skills/audit/references/workflow-template.js:2,153,160`、`skills/audit/scripts/codex-dispatch.py:92-126`（プロンプト文言のみ。
  読み元の変更は S4a）、`skills/audit/scripts/impact-supplement.py:5-9`、`docs/ADOPTION.md:173`／`docs/ADOPTION.ja.md:158`、
  `docs/PROMPTS.md:64-66`／`docs/PROMPTS.ja.md:63-65`。
- `tests/test_workflow_template.py:361-366`（`test_agent_documents_all_current_provenance_values`）のタプルに `regression` を追加
  （意図的差分、PLAN §11）。
- `skills/audit/references/config-schema.md` の設定キー表に `heuristics.saturationWarnRatio`・`heuristics.excludeDocPathTokens`・
  `regressionRecheck`（`{enabled:bool=false}`）の行を追加（既存 `heuristics` 行の拡張で可）。`default-heuristics.md` を同期。
- `docs/ADOPTION.md`・`.ja.md` §6: 「健全な設定は選択の大半が mapped。heuristic は残差」「コストの主因は anchor の古さ
  （maxImpactedDocs ではない）。実測 92 docs ≈ 3.6M tokens、単一 commit 窓の中央値 ≈ 18 docs」「`regressionRecheck` は opt-in。
  単発検証はブレるため『指摘 N 件を直して再実行すれば CONSISTENT』は保証されない。欠陥クラス単位で横断掃除を推奨」を追記。
  `skills/init/SKILL.md` Step 2 の draft に `regressionRecheck: {enabled: true}` の提案を追加（既存 config には触れない旨も）。
- `tests/test_v013_contracts.py`: S1 の骨格に対し (b)（Phase 2 の `resolve-impact.py` **コマンド行**に `--history …` がある。行単位
  で検査し、説明文中の出現では通らないこと）と (g)（7 消費側の**列挙箇所**＋`test_workflow_template.py` のタプルに `regression`。
  各ファイルの該当行を特定して検査）を有効化。(h) のうち本 Stage の 3 キー行を config-schema 表で検査するテストも有効化
  （残り 2 キー `auditScope`・`codexReview.required` は S3/S4b で追加されるので、それらの assert は skipTest のまま）。

## 6. テスト（`tests/test_resolve_impact.py`・`tests/test_impact_supplement.py`・plan-dispatch のテストは既存の配置に従う）
- #40: `counts.docCorpus`・`counts.heuristicSaturation` の値、**docCorpus 0 → 0.0・warning なし・正常終了**、synthetic corpus 9 docs
  中 9 件 heuristic-only で WARN（下限なし）、丸め前比較（例: 比率 0.4996 と閾値 0.5 で WARN なし、`heuristicSaturation` 表示は 0.5）、
  `excludeDocPathTokens:true` で doc 由来 token が消える（false では出る）、cap 超過が `warnings[]` に入る。型検証表（表形式・
  `subTest`）: `saturationWarnRatio` ∈ {"0.5", true, -1, 1.5, None, [], 0（無効）, 1（有効・全件で WARN）} と `excludeDocPathTokens`
  ∈ {"true", 1, None}、`regressionRecheck` ∈ {[], "x", {"enabled":"yes"}} の各挙動。
- #39: `regressionRecheck.enabled:true`＋`--history` で最後の entry が FAIL の文書が `regression` で impacted に入る／同文書が既に
  mapped なら provenance は `mapped`（regression にならない）／full mode では無効／既定（enabled 省略）で無効かつ warning なし／
  history 不在は無音／history 破損は warning／`historySha` の形式と有効時のみ出力／cap 順序（mapped 2 件・regression 2 件・
  heuristic 2 件・`maxImpactedDocs: 3` → mapped 2＋regression 1、truncated=true）。
- plan-dispatch: `historySha` 一致で正常／不一致で exit 3 と stderr 文言／`null` と history 不在で正常／dispatch.json に `impactSha`
  が supplement 後 impact.json bytes の sha256 と一致／EVIDENCE stdout のキー集合が従来と同一（`impactSha` を含まない）。
- `source` 互換（PLAN §6 (viii) の前倒し）: impactMap 項目に `source:"audit-scope"` を付けた config と付けない config で
  resolve-impact の JSON 出力が完全一致。
- **統合試験 2 本は S4a で作る**（本 Stage では作らない）。ただし本 Stage の変更で `tests/test_wp12_contracts.py` 等の既存
  統合系テストが赤にならないこと。

## 7. 完了条件（PLAN §6 抜粋、S2 分）
- フルスイート全 green。件数を報告（前後）。
- 上記 6 のテストが実際に対象コードを経由すること（主要な 3 件について、実装を revert すると赤になることを確認し方法を報告）。

## 8. 変更範囲（PLAN §7 抜粋）
**許可**: `skills/audit/scripts/resolve-impact.py`、`skills/audit/scripts/impact-supplement.py`、`skills/audit/scripts/plan-dispatch.py`
（`historySha` 照合と `impactSha` 記録のみ）、`skills/audit/scripts/codex-dispatch.py`（**プロンプト文言のみ**）、`skills/audit/SKILL.md`
（Phase 2 の該当行のみ）、`skills/init/SKILL.md`（Step 2 の draft 提案のみ）、`skills/audit/references/{config-schema.md,
default-heuristics.md, workflow-template.js}`、`agents/doc-impact-verifier.md`、`agents/doc-impact-verifier-light.md`、
`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`docs/PROMPTS.md`、`docs/PROMPTS.ja.md`、`tests/`。
**禁止**: `decide-verdict.py`・`start-run.py`・`seal-run.py`・`check-verdicts.py`・`open-run.py`・`write-evidence.py`・
`compute-baseline.sh`・`docaudit_paths.py`・`generic-layers.py`・`tasks/`・`.gitignore`・`.claude/`。EVIDENCE のキー集合。既存 assert
の変更は PLAN §11 の意図的差分（`test_resolve_impact.py` の counts 完全一致 assert の更新、`test_workflow_template.py` のタプル）
のみ。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 9. 検証コマンド一式
```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_resolve_impact tests.test_impact_supplement tests.test_workflow_template tests.test_wp12_contracts tests.test_v013_contracts -v
```

## 10. コミットと報告
- Conventional Commits で論理単位ごと（例: `feat(impact): saturation ratio + excludeDocPathTokens (#40)`、
  `feat(impact): regression recheck provenance + historySha/impactSha (#39)`、`docs: regression provenance + cost guidance`）。
  push はしない。
- 報告は結論先行・完全な文で。各主張はツール結果と突合し、未検証は未検証と明言。テスト失敗は出力ごと報告。末尾に
  「変更ファイル一覧（`git diff --stat <S1 最終 commit>`）」「テスト件数（前後）」「許可外変更の必要有無」。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
