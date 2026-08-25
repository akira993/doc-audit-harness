# REVIEW — Issues #33 / #34 / #35 → v0.11.0

boss: Fable ／ 日付: 2026-08-25

## codex セッション記録

| 用途 | モデル / effort | session ID |
|---|---|---|
| 事前調査（read-only） | Luna medium | 01a0369a-8679-7ff0-b448-00746a050d1d |
| 計画批判（read-only, 手順3） | Sol high | 01a0369f-ed50-73b2-b407-2ec7ff938e34 |
| 実装（手順4, workspace-write, 段階 A〜C を同一セッションで） | Terra high | 01a036da-adaa-7e62-9521-4d5bab086f0e |

## ユーザー合意事項（インタビュー確定）

- 対象 Issue: #33 / #34 / #35（#28 は据え置き。設計提案として open 維持）
- バージョン: **v0.11.0（minor）** — ユーザー原文は「パッチ」だったが、新 config キー追加＋挙動変更のため
  インタビューで minor に合意変更
- #33 severity: 解決しない具体的ファイルパスは WARN→**FAIL** 昇格（ディレクトリ形状は WARN 維持）

## 計画批判ラウンド

### ラウンド 1（Sol high）— 承認不可

4 BLOCKER / 8 MAJOR / 2 MINOR（全文: `OUT-critique-r1.md`）。boss 裁定（全 14 件採用、うち 2 件は方式変更で対応）:

- R1-1,2（bare path 偽陽性 BLOCKER）→ 抽出を正規表現方式（`[A-Za-z0-9_.\-/]+` で `/` 含む連続）に変更し、
  **bare は WARN に留める**（FAIL 昇格は構文明示の backtick/link のみ）。indented code もハーベスタ内でマスク
- R1-3（file/dir 判定 BLOCKER）→ 拡張子 `[A-Za-z][A-Za-z0-9]{0,7}` 要求に精緻化。`docs/LICENSE` 型が
  WARN に留まるのは文書化する既知の限界として受容
- R1-4,7（impact-supplement / start-run 再混入 BLOCKER/MAJOR）→ 変更範囲に両ファイル追加
- R1-5（--paths 矛盾）→ 明示 --paths は非除外（列挙時のみ除外）
- R1-6（パターン過広）→ 新設除外箇所は日付認識 regex。正本 glob は据え置き、差は契約テストで固定
- R1-8（`..` 境界）→ looks_like_repo_path に `..` 拒否追加
- R1-9,10,11,12,13,14 → PLAN rev.2 §5.3〜5.6 に反映（3 SHA、refresh テスト、契約テスト、不正型仕様、
  counts 検証、ADOPTION.ja.md:237 追加）

→ PLAN rev.2 へ改訂、ラウンド 2 へ。

### ラウンド 2（Sol high, resume）— 承認不可

4 BLOCKER / 6 MAJOR / 5 MINOR（全文: `OUT-critique-r2.md`）。boss 裁定（全 15 件採用）:

- R2-1（bare=WARN は合意未達）× R1-1（bare=FAIL は偽陽性）→ **折衷の決定論ルール**: 具体ファイルは
  原則 FAIL、ただし同一行に bare 候補 2 つ以上の行（コマンド形）は WARN 降格。残余リスク
  （1 候補の裸コマンド）は文書化
- R2-2（backtick FAIL 昇格が fenced/indented code を誤爆）→ existence 層全体をコードマスク後の
  テキストに変更
- R2-3,6（日付 regex がテンプレートを網羅せず / `[_NN]` 未定義）→ テンプレート全体からの regex 導出に変更
- R2-5（正本 glob と新設 regex の二本立ては `doc_audit_policy.md` を「corpus 会員だが変更監査不能」に
  する）→ **方針転換: マッチャを全経路で統一**。change-set-sha.py の正本自体を regex 化（過剰除外の根治）。
  change-set-sha / decide-verdict / sibling-scan を変更範囲に追加（マッチャ統一に必要な変更のみ）
- R2-4（impact-supplement CLI 契約）→ `--config` 追加＋SKILL.md 呼び出し更新
- R2-7（明示 --paths レポートの発リンク欠落で偽 orphan）→ semantic scan = 除外済み列挙 ∪ 明示 paths
- R2-8（ASCII 限定の誤抽出）→ Unicode \w ベース＋URL 事前マスク＋非 ASCII フォールバック解決
- R2-9（symlink 越境）→ realpath 封じ込め（越境トークンはスキップ）
- R2-10〜15 → 契約テスト全実装適用・opt-in 4 経路・indented 判定明文化・正例/件数/行番号の厳密テスト・
  pass 集計修正・refresh fixture の SHA 事前 assert・ADOPTION 層説明更新

→ PLAN rev.3 へ改訂（実装者も Terra high に引き上げ）、ラウンド 3 へ。

### ラウンド 3（Sol high, resume）— 承認不可

4 BLOCKER / 6 MAJOR / 5 MINOR（全文: `OUT-critique-r3.md`）。boss 裁定 — **設計単純化への方針転換**:

- R3-1,2,3（降格則は回避可能・1 候補コマンド偽陽性は高頻度・Unicode 融合）→ 3 ラウンドの結論として
  「散文収穫に blocking 権限は与えられない」と裁定。**bare は常に WARN**（検出網）、FAIL 昇格は
  link/backtick のみ。降格則・Unicode 抽出・フォールバック解決を削除（R3-7,13 も構造的に解消）。
  ユーザー合意（Q3）は backtick token の昇格であり整合（bare の severity は Issue #33 も未指定）
- R3-4（blockquote/リスト内 fence）→ fence 判定にマーカー剥がしの簡易拡張（過剰マスク側に倒す）
- R3-5,6（URL マスク境界・percent-decode）→ パス文字クラス停止・`//` 拒否・decode 解決を採用
- R3-8（opt-in と sealed 契約の矛盾）→ **マッチャ統一と除外有効条件を分離**: 機構除外
  （changed[]/sibling-scan）は無条件、corpus 除外（4 経路）のみ opt-in 対象
- R3-9〜15 → --config 任意化＋no-op 互換・正本妥当性条件無変更・生成側 suffix 契約明文化・`[0-9]`・
  shell 経由統合テスト・版残置ゲートを配布物パス限定

→ PLAN rev.4 へ改訂、ラウンド 4 へ。

### ラウンド 4（Sol high, resume）— 承認不可（ただし中核設計は受容）

2 BLOCKER / 5 MAJOR / 4 MINOR（全文: `OUT-critique-r4.md`）。Sol は bare=WARN 裁定・opt-in 分離・
suffix 整合・compute-baseline 据え置き・3 SHA を明示的に受容。boss 裁定:

- R4-1（仕様×テストの自己矛盾）→ backtick 非 ASCII は FAIL に統一（テスト期待値を修正）
- R4-2（`%00` で監査停止）→ decode 後の NUL/制御文字/`..` 再検証＋例外時トークンスキップ＋回帰試験
- R4-3（FAIL 判定の基底未定義）→ 正規化パイプライン（suffix 除去→locator→decode）を確定
- R4-4（入れ子 fence）→ マーカー剥がしを反復化＋`数字)` 対応
- R4-5（レポート書き込み×並行監査 sealed 指紋の競合）→ **スコープ外**（既存挙動・本変更と独立）。
  follow-up Issue を起票して対応（リリースフェーズ）
- R4-6（`[_NN]` 無しの衝突出力先が無い＋厳密化の互換性回帰）→ suffix を常時許容（R2-6 の明示的上書き）
  ＋生成契約「`[_NN]` 無しでも `_02` を日付直後に挿入」
- R4-7〜11 → scope/完了条件へ suffix 契約追加・opt-in 不正型×4 経路・URL 文字クラス拡張・文言整合・
  残置ゲートのホワイトリスト化＋ADOPTION.md:254 追加

**bare=WARN の位置づけ（R4-10 の指摘に対応）**: Q3 ユーザー合意「具体的ファイルパスの FAIL 昇格」の
適用先を構文明示（link/backtick）に限定する**明示的上書き決定**として記録する。最終報告でユーザーに
明示する。

→ PLAN rev.5 へ改訂、ラウンド 5（上限）へ。

### ラウンド 5（Sol high, resume・最終）— 承認不可 → boss 裁定で rev.6 確定

2 BLOCKER / 3 MAJOR / 1 INFO（全文: `OUT-critique-r5.md`）。R4-5 スコープ外裁定は Sol 受容（INFO）。
残指摘は全て**機械的に確定できる仕様文修正**（設計判断の余地なし）:

- R5-1: suffix は `[_NN]` の記述位置維持・無い場合のみ日付直後挿入（既存有効設定の互換維持）
- R5-2: 版残置の完了条件・検証コマンドを §5.5 ホワイトリストに整合
- R5-3: placeholder→regex の 4 段変換規則を明示（`[_NN]` をリテラル扱いしない）
- R5-4: マーカー剥がしの固定上限（8 回）撤廃（各反復が文字を消費するため自然停止）
- R5-5: 例外捕捉経路の直接試験（生 NUL／mock 例外注入）

批判ループは上限 5 往復に到達。R5 全件を rev.6 に反映し、**rev.6 を実装フェーズの拘束仕様として
boss 承認で確定**（Sol の R5 指摘に対する裁定はすべて Sol の提案どおりの採用であり、争点は残っていない）。

## 実装レビューラウンド

実装は 3 段階分割（advisor 助言採用）: A=generic-layers 本体＋テスト／B=マッチャ統一（6 スクリプト）＋
契約テスト／C=scaffold・engine-shas・版 bump・docs。同一 Terra high セッションを resume で継続。

### 実装ラウンド 1（段階 A）— 差し戻し 2 件

worker 報告: generic-layers.py +314/-38、テスト 24 件追加（58 件 green）、既存テスト期待値変更 0 件。
全体テストの失敗 10 件はすべて engine-shas stale（段階 C で解消予定・想定どおり）。

boss 全行 diff レビュー結果:
- 仕様適合を確認: マスク（fence 反復剥がし・indented・URL/リンク/inline マスク）・正規化パイプライン・
  percent-decode 安全検証・realpath 封じ込め・file/dir 判定・bare=WARN・layerGlobs（semantic の
  発リンク維持含む）・レポートマッチャ（suffix 位置規則 R5-1/R5-3 準拠）・counts/pass 整合・
  config WARN の dedup
- **差し戻し 1**: frontMatterOverrides が `glob`（単一文字列）実装 — PLAN §5.2 の `globs`（配列）と不一致
- **差し戻し 2**: `_token_base` が locator 分割を常に優先し、コロンを含む実在ファイル名が偽 finding に
  なる回帰（旧実装はフルトークン存在確認が先）
- 申し送り: 段階 A の report_pattern 妥当性条件（`.endswith(".md")` 等）は段階 B の契約テストで
  正本と完全一致させる

→ 修正指示＋段階 B を resume で発行（実装ラウンド 2 へ）。

### 実装ラウンド 2（段階 A 修正＋段階 B）— 承認

worker 報告: 差し戻し 2 件修正（frontMatterOverrides→globs 配列・フルトークン先行解決）、マッチャ統一
6 スクリプト＋SKILL.md 呼び出し更新＋契約テスト（5 実装＋decide-verdict の同一判定をケース表で固定）。
対象 134 件 green、全体は engine-shas stale 10 件のみ（段階 C 解消予定）。

boss 全行 diff レビュー結果（差し戻しなし）:
- change-set-sha: 正本の妥当性条件は無変更のまま regex 化・機構除外は opt-in 非依存 ✓
- sibling-scan regex 受け・start-run `is not True` ゲート・resolve-impact full/heuristic 除外
  （mapped 無変更）・impact-supplement 任意 --config＋no-op 契約維持 ✓（`$CFG` は SKILL.md:13 で定義済み）
- `_resolve_path_token` はフルトークン→locator 基底の順で解決、FAIL 判定は最後に試行した基底
  （decode 後）に適用 — R4-3 準拠 ✓
- 既存テスト期待値変更 3 件はすべて PLAN §5.6 の意図的差分と対応（machineryExcludedCount 8→9・
  policy.md の changed[] 復帰・sibling-scan の regex 化）✓

→ 段階 C（scaffold・engine-shas・版 bump・docs）を resume で発行（実装ラウンド 3 へ）。

### 実装ラウンド 3（段階 C）— 承認

worker 報告: v0.11.0 bump（plugin.json・ADOPTION 英日 4 箇所・test_decide_verdict:422）・engine-shas
0.11.0 3 SHA（scaffold.py で算出。check-docs/doc-lint は 0.10.1 と同一＝テンプレート未変更、engine のみ
更新）・config-schema.md 全項目・SKILL.md suffix 契約・ADOPTION 層説明更新・旧前提記述は該当なし・
scaffold refresh テスト（0.10.1 fixture は `git show docaudit--v0.10.1` 由来で SHA 事前 assert 付き）。
全 296 テスト green（boss も自身で再実行して確認）。版残置は許可ホワイトリスト 3 行のみ（boss 確認済み）。

boss diff レビュー: bump・engine-shas・config-schema・SKILL.md・scaffold テストすべて仕様適合。差し戻しなし。

### 最終レビュー（codex exec review --uncommitted, Sol high）→ P2 修正（実装ラウンド 4）— 承認

指摘 2 件: P1=歴史的 fixture が `.gitignore` の `data/` 規則で未追跡（CI で FileNotFoundError）→
コミット時に `git add -f` で boss が対応。P2=`report_pattern()` の docGlobs fallback が空配列のため、
docGlobs 省略＋reportPath 指定の有効 config で除外が不発（実バグ）→ 実装セッション resume（medium）で
5 複製すべてを既定値 `["docs/**/*.md","*.md"]` に統一・契約テスト＋列挙テスト追加・engine SHA 再計算。
全 298 テスト green（boss 再実行で確認）。**boss 最終承認**（PLAN §6 完了条件 1〜7 充足）。

## route-close

- **対象タスク**: Issues #33/#34/#35 対策 + v0.11.0 リリース（/route・PLAN rev.6）
- **記録時点の HEAD**: `e66e2ca795d42a16a2245623f6d84d26de63bc01`（feat/v0.11.0-issues-33-35。
  PR #36 作成・push 済み。**マージ以降は classifier がセルフマージを拒否したためユーザー実行の
  `release-handoff.sh` に委譲** — v0.10.1 と同じ前例）
- **確定した変更ファイル**（git status/diff で確定・52 ファイル +3432/−69、pr-body 追記 1 件）:
  - エンジン/機構 8: generic-layers.py・change-set-sha.py・resolve-impact.py・impact-supplement.py・
    start-run.py・sibling-scan.py・SKILL.md（audit）・scaffold は変更なし（engine-shas.json のみ）
  - 配布参照 2: config-schema.md・engine-shas.json（0.11.0 エントリ 3 SHA）
  - 版/docs 4: .claude-plugin/plugin.json・docs/ADOPTION.md・docs/ADOPTION.ja.md・
    tests/test_decide_verdict.py:422
  - tests 9 ＋新規 test_report_matcher_contract.py・tests/data/generic-layers-v0.10.1.py（force-add）
  - 記録: tasks/route/2026-08-25-issues-33-34-35/（PLAN/REVIEW/prompt/OUT/fixture/handoff）
- **audit verdict**: この repo 自体に `.claude/doc-audit.json` は無い（docaudit 未導入）ため
  /docaudit:audit は実行不能。代替として、変更した公開挙動・設定・手順に対応する既存文書
  （config-schema.md・ADOPTION 英日・SKILL.md）を本リリース内で同時更新し、Sol 批判 5 往復＋
  `codex exec review` で整合を検証した（版残置ゲート合格・旧前提記述の grep 該当なし）
- **SSoT 更新**: AGENTS.md / PROJECT.md は本 repo に存在せず、リポジトリ外の恒久規約変更もなし →
  **0 ファイル更新**（正）
- **follow-up**: Issue #37 起票済み（R4-5: レポート書き込み×並行監査 sealed 指紋の競合・suffix 上書き競合）
- **残手順**（ユーザー実行）: `bash tasks/route/2026-08-25-issues-33-34-35/release-handoff.sh`
  （PR #36 マージ → main で 298 テスト → tag docaudit--v0.11.0 → GitHub Release → #33/#34/#35 close →
  skills-dir 再同期・検証）

## ユーザー合意からの明示的逸脱（最終報告で明示）

- 「解決しない具体的ファイルパスは FAIL 昇格」（Q3 合意）の適用先を**構文明示（link/backtick）に限定**し、
  bare path（散文収穫）は WARN の検出網とした。根拠: Sol 批判 R1/R3 で、散文収穫への blocking 権限は
  コマンド例・日本語直結文で偽陽性 FAIL を量産し実装不能と実証されたため（R4 で Sol も受容）。
  Issue #33 自体は bare の severity を指定していない。
