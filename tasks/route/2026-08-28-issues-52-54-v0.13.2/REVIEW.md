# REVIEW — Issues #52〜#54 → docaudit v0.13.2（2026-08-28）

## ベースライン（boss 実測、HEAD `2032e21`）
- `python3 -m unittest discover -s tests -t .` → Ran 495 tests in 139s, **FAILED (failures=1)**:
  `test_import_audit_scope.test_real_dir_framework_scope_has_24_rules_and_46_equivalence_paths`（外部 repo 結合の固定値 46 ≠ 48。PLAN §0-12 で S1 に吸収）。
- codex 準備: `CODEX_HOME=~/.codex-doc-audit-harness`、`auth.json` あり（2026-08-25）。

## 計画批判（Sol、`gpt-5.6-sol` `high` `read-only`）
- 批判セッション ID: `01a0456e-9d7b-7bf3-8afa-5377b2ac031c`（R1 起動 2026-08-28、`critique-r1.md` → `critique-r1-answer.md`）

### R1（`critique-r1-answer.md`、12 件: high 6／medium 5／low 1）→ PLAN rev.2
| # | 指摘 | 裁定 |
|---|---|---|
| 1 | パッチ版は互換性契約に反する（minor へ） | **不採用**: ユーザー明示指示「パッチ」を維持。最終報告で反論を併記（§0-1） |
| 2 | `*.md` 既定は root の AGENTS.md/CLAUDE.md を fix 対象にする | **部分採用**: 既定は揃え、`CLAUDE.md`/`AGENTS.md` を basename 組込み deny に追加（§0-2） |
| 3 | 不正設定を not-configured に畳むのは誤り・`bool("false")` | 採用: `invalid-config` を分離、`enabled` は JSON boolean 必須（§0-4 表 8 行） |
| 4 | 3 seam の判別基準が実装と不一致・移行問題 | 採用: 基準を書き直し、§7 に移行注記、残り 4 seam は別 Issue 候補 |
| 5 | `.gitignore` 自動復元は危険 | **部分採用**: 復元を削除。`settings.yml` マーカーを主対策、変化の検出のみ（書き込み無し）を安全網として残す（§0-5） |
| 6 | run 解放が不完全（read-manifest 分岐・必須引数欠落） | 採用: 3 分岐すべてに SKILL.md:52 の完全コマンド（§0-3a） |
| 7 | read-manifest の非 object で traceback | 採用: dict＋sealed を一体検査、`[]`/`null` もテスト（§0-3b） |
| 8 | 状態行の catch-all で新枝が隠れる | 採用: reason 優先の排他表＋集合一致テスト（§0-4） |
| 9 | §0-12 の導出値は KeyError・外部依存残る | 採用: repo 内 fixture 化（`tests/data/dir-framework-scope/`）。ただし「今回から外す」は不採用 — main が red のままでは handoff のフルスイートが落ちる（§0-12） |
| 10 | 全 *.py 走査は誤検出／0 件検査 | 採用: 既知 consumer 7 ファイル限定・件数固定（§0-2、DoD 3） |
| 11 | 誤実装でも通る DoD | 採用: 判定表 8 行×3 の全件テスト、集合一致、件数は正確に +Δ |
| 12 | ja refresh 行の形式 | 採用: 行単位の完全文言を §0-6 に明記 |

### R2（`critique-r2-answer.md`、13 件: high 2／medium 9／low 2）→ PLAN rev.3
全件採用。1 basename deny を casefold 化／2 組込み deny の列挙 4 か所を更新対象に／3 判定表 6〜8 行は probe 単体の防御と明記（通常経路では
到達不能。boss 実測: open-run.py は config を hash するだけで解析しない）／4 `bin` 非文字列・`minScore` 非数値も `invalid-config`（表 9・10 行）／
5 判別基準の「verdict に影響しない」を「probe 利用不能自体は FAIL 根拠にならない」に訂正／6 `*_REASON` 3 変数の束縛を契約化／7 gitignore 状態行から
原因断定と checkout 案内を削除／8 AST 検査 N=11 と内訳を固定／9 状態行・§7 の対応表検査／10 `command -v` 非実行を契約から外す／11 件数 +Δ を
固定テスト名の網羅に置換／12 期待順序を sorted に／13 fixture 作成順と由来 sha（`d681869…0982d`）を固定。

### R3（`critique-r3-answer.md`、14 件: high 1／medium 9／low 4）→ PLAN rev.4
| # | 指摘 | 裁定 |
|---|---|---|
| 1 | `*_REASON` が中断後に復元できない | **不採用**: 既存 `*_AVAILABLE` と同一の寿命・再開規約（SKILL.md:49）で本変更で悪化しない既往制約。別 Issue 候補「Phase-0 probe 結果の run-dir 永続化」 |
| 2 | reason 束縛の検査が名前出現のみ | 採用: `["reason"]` からの完全な式を 3 組検査（DoD 10b） |
| 3 | 状態数と対応表の不完全 | 採用: doc 6-state(7 msg)/symbol 6/semantic 8、記号＋固定句＋排他 |
| 4 | `enabled:false`×不正 bin の優先順位 | 採用: 評価順序を固定、複合テスト |
| 5 | minScore NaN/Inf | 採用: `math.isfinite` |
| 6 | 型境界テスト不足 | 採用: subTest 表（bin `[]`/`""`、minScore `"0.4"`/`true`/NaN/Inf、enabled `"false"`/`1`、`--config` 省略）計 31 件 |
| 7 | schema の「runtime reads only enabled and bin」矛盾 | 採用: 文言更新＋契約テスト |
| 8 | gitignore 変化×index 失敗 | 採用: 変化を優先、stub テスト |
| 9 | symlink 案内 | 採用: readlink の一句 |
| 10 | `command -v` の自己矛盾 | 採用: 表見出しから削除 |
| 11 | fixture 3 点の由来固定 | 採用: paths `b1a1356…d91d`・config `9723e28…599c`（boss 実測、Sol 値と一致） |
| 12 | §7 が逆説明でも通る | 採用: 肯定形固定文 5 つ（en 文言固定、ja は同順・同コードスパン） |
| 13 | 固定テスト名の未列挙 | 採用: 全 method 名を PLAN に列挙 |
| 14 | deny 文書 4→5 か所 | 採用 |

### R4（`critique-r4-answer.md`、9 件: medium 7／low 2）→ PLAN rev.5
全件採用（設計上の新規論点なし。PLAN 内の整合と DoD の締め付け）: 1 状態数 6/6/8 に統一＋見出し数値を契約化／2 件数 32 に統一／3 semanticSearch の
`enabled:false`×`minScore` 不正の複合テスト／4 subTest 必須入力を列挙（key `true`/`"x"`/`[]`/`null`、bin `[]`/`1`/`null`/`""`、minScore
`"0.4"`/`true`/`null`/NaN/±Infinity）／5 config に stub を置けないケースは既定名 stub を PATH 先頭に／6 `→` 右辺のみ検査／7 ja §7 も肯定形 5 文を文言固定／
8 symlink 案内を「実体の内容を確認」に／9 「4 か所」の残骸を削除。

### R5（`critique-r5-answer.md`、1 件 low）→ **実装承認**（PLAN rev.6）
1 `ok` の検査を文脈付きパターン（`✓ <seam>: active (`／`⚠ doc-graph: active but`）に — 採用（DoD 10）。Sol 5 往復合計 49 件（R1 12／R2 13／R3 14／R4 9／R5 1）。

## Opus 全体敵対レビュー（change-reviewer、read-only）
### O1（rev.5 対象、ブロッキング 7／非ブロッキング 8）→ PLAN rev.7
| # | 指摘 | 裁定 |
|---|---|---|
| B1 | conditional-force／auto-used 記述 13 行の一掃漏れ | 採用: 対象を列挙、契約テスト追加（§0-4） |
| B2 | `active` 固定句の衝突 | rev.6（Sol R5-1）で対応済み |
| B3 | §7 固定文検査がハードラップ・コードスパンと矛盾 | 採用: 空白正規化＋バッククォート除去（DoD 17） |
| B4 | cocoindex 非起動検査が vacuous | 採用: fixture に settings.yml 必須（DoD 8） |
| B5 | 新分岐の JSON 形状未規定 | 採用: 同一キー集合・既定名 Bin・gitignoreOk 常在・exit 0（§0-4） |
| B6 | `*_PROBE_JSON` 捕捉行 | 採用: 呼び出し行 3 本の変更と契約検査（§0-4、DoD 10b） |
| B7 | テスト前提（実在ファイル・case-twin） | 採用（DoD 2） |
| N1/N3/N4/N5/N6 | 残存記述 4 か所・行番号・`?? .claude/`・SEALED_MANIFEST 行・親 git root の限界 | 採用（DoD 14/5/22、§0-5 記録） |
| N2 | 内訳固定は保守負債 | 採用: 総数 11＋ファイル集合のみ assert |
| N7 | `.gitignore` 検出の削除 | **不採用**（boss 裁定、§0-5 に理由） |
| N8 | S1 の事前分割 | 採用: S1a（#52+#53+fixture）→ S1b（#54）（§0-9） |
### O2（rev.7 対象、ブロッキング残 1／細部 5）→ PLAN rev.8 — **実装承認**（条件全反映）
R2 B1 契約テストを段落単位＋空白正規化に／R1 テスト名を DoD 20 の網羅リストへ／R3 `docs/claude.md` に統一／R4 `{}` ケースの PATH stub＋cocoindex は settings.yml／
R5 件数表記／R6 §5 の Stage 別記。Opus 2 往復合計 21 件（O1 15／O2 6）。

## 実装（手順 4〜6）
- ブランチ `fix/v0.13.2-issues-52-54`（HEAD `2032e21` から）。
- S1a 実装セッション ID: `01a045a7-8a6c-7b00-9092-01d31eb800cc`（Terra `high`、`stage1a-prompt.md` → `stage1a-answer.md`／`stage1a-report.md`）

### S1a（Terra `high`、#52＋#53＋fixture）
- 経過: 初回は安全ルールで上書き承認待ち停止 → `stage1a-approve.md` で包括承認 resume → フルスイート待機中に外部停止（killed）→ `stage1a-continue.md` で resume し完了。
- boss レビュー: diff 全行を読了（runtime 2・SKILL.md・config-schema・ADOPTION en/ja・テスト 3・fixture 3）。PLAN §0-2/§0-3/§0-12 と一致。指摘なし。
- boss 追認: `python3 -m unittest discover -s tests -t .` → **Ran 505 tests, OK, skip 0**（ベースライン 495 − 置換 0 ＋ read-manifest 4 ＋ 契約 6）。
  `py_compile` OK、`grep -c 'get("docGlobs", \[\])'` = 0、fail-closed 残存 0、fixture sha 3 点一致（`d681…`/`9723…`/`b1a1…`）。worker 報告（105 件成功）と乖離なし。
- 判定: **承認**。commit（fixture は `git add -f`）。
- S1b 実装セッション ID: `01a045b2-a40f-7ca1-b000-55c3108d3815`（Terra `high`、`stage1b-prompt.md` → `stage1b-answer.md`／`stage1b-report.md`）

### S1b（Terra `high`、#54-1／#54-2）
- boss レビュー R1: diff 全行を読了（3 probe・audit SKILL.md Phase 0/5・config-schema・ADOPTION en/ja・init SKILL・テスト 4 本）。判定表 10 行・評価順序・
  JSON 形状・`*_PROBE_JSON`／`*_REASON` 束縛・状態行 6/6/8・settings.yml マーカー・`.gitignore` 検出（非復元・exit code より優先）はすべて PLAN どおり。
  **差し戻し 1 件**: `skills/init/SKILL.md:36` の mdq（`indexing`）文を「opt-in」に変えていた（mdq の意味論は不変。同段落の CocoIndex 語で段落単位の
  B1 契約テストに掛かった副作用）→ 意味を保つ言い換えを指示（`stage1b-feedback1.md`、resume medium）。
- boss レビュー R2: 差し戻し 1 の修正を確認（`skills/init/SKILL.md:36-37` — mdq は「on by default when installed; `enabled:false` opts out」で意味不変）。
- boss 追認: `python3 -m unittest discover -v -s tests -t .` → **Ran 548 tests, OK, skip 0**（S1a 505 ＋ probe 36 ＋ 契約 7）。DoD (20) の固定テスト名 34 種すべて出現
  （probe 共通名は 3 probe 分）。`bash -n` 3 本 OK、`git diff --check` OK、変更ファイルは許可 12 本のみ。worker 報告（対象 94 件→64 件 OK）と乖離なし。
- 判定: **承認**。commit。

### S2（Terra `medium`、版バンプ・engine-shas・§7・テスト再照準・handoff）
- S2 実装セッション ID: `01a045c5-0a75-7772-b08d-42c1573741ac`（`stage2-prompt.md` → `stage2-answer.md`／`stage2-report.md`）
- boss レビュー R1: diff 全行を読了（plugin.json・engine-shas（0.13.2 = 0.13.1 と同一 hash、boss も `engine-shas-v0132-equals-v0131=True` を worker 報告で確認）・ADOPTION en/ja
  （版行・refresh 段落・§7 5 文）・test_v013/test_v0131/test_scaffold/test_v0132 の再照準と `test_v0132_behavior_changes_paragraph`・release-handoff.sh（v0.13.1 と
  同型、差分は版・題名・Issue・notes・必須語のみ。旧ヘッダのコメント 2 行の脱落は無害）・test_release_handoff.py（旧値 0 件、boss grep でも 0 件））。指摘なし。
- boss 追認: `git add -f release-handoff.sh` 後に `python3 -m unittest discover -v -s tests -t .` → **Ran 549 tests, OK, skip 0**。`scaffold --dry-run` stampVersion 0.13.2、
  `bash -n` handoff OK。worker 報告（70 件 OK）と乖離なし。判定: **承認**。commit。

## 最終レビュー（`codex exec review`、Sol `high`）
- 最終レビューセッション ID: `01a045cc-b758-7101-8884-46999a77a695`（`codex exec review --base main -c model=gpt-5.6-sol -c model_reasoning_effort=high`）
- 結果（`final-review-answer.md`）: **P2 × 1** — `cocoindex-probe.sh:85` の `.gitignore` 指紋が `shasum` 依存で、`shasum` 不在環境では前後とも空になり変更を見逃す
  （README の必要条件は Python 3 のみ）。boss 判定: 妥当（report-only 契約の安全網が無効化される）→ S1b セッションへ差し戻し 2（`stage1b-feedback2.md`、`hashlib` 化＋
  計算失敗時は degrade＋`shasum` 不在テスト）。
- PR #55 作成済み（branch push 済み、merge は最終承認後）。
- 差し戻し 2 の修正を boss がレビュー: `fingerprint_gitignore()` は `hashlib.sha256`、失敗時は `ccc index` 不起動で `index-failed`（新 reason なし）、`grep -c shasum` = 0、
  テスト 2 件追加（`shasum` を exit 127 stub で隠す／`.gitignore` がディレクトリで指紋失敗）。boss 追認: フルスイート **Ran 551 tests, OK, skip 0**、`bash -n` OK。
- 最終判定: **承認**（commit・push 済み）。

## route-close（手順 7）
- 対象タスク: Issues #52・#53・#54 → docaudit v0.13.2（パッチ）。
- 記録時点の HEAD: `2b2fcadc55b35513e962fd6f0a81d2e2994476ca`（PR #55 の merge commit ＝ tag `docaudit--v0.13.2`）。tracked 差分 0（`git status --short` は既存の未追跡 `?? .claude/` のみ）。
- 確定した変更ファイル（4 commit: `9792dca` S1a／`8eed115` S1b／`9aec2c6` S2／`b1b77e9` 最終レビュー P2）:
  runtime `skills/audit/scripts/{fix-scope.py,read-manifest.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh}`／
  手順・文書 `skills/audit/SKILL.md`、`skills/init/SKILL.md`、`skills/audit/references/{config-schema.md,engine-shas.json}`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
  `.claude-plugin/plugin.json`／テスト `tests/{test_v0132_contracts.py(新規),test_read_manifest.py,test_import_audit_scope.py,test_graphify_probe.py,test_cocoindex_probe.py,
  test_codegraph_probe.py,test_v013_contracts.py,test_v0131_docs_contracts.py,test_scaffold.py,test_release_handoff.py}`、`tests/data/dir-framework-scope/{audit-scope.json,doc-audit.json,paths.txt}(新規)`／
  `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`(新規)。
- audit verdict: `.claude/doc-audit.json` 未導入のため `/docaudit:audit` は不実行。代替として、変更した公開挙動（docGlobs 既定・組込み deny・key-gated probe・settings.yml マーカー・
  seal 停止分岐）と既存文書（SKILL.md・config-schema.md・ADOPTION en/ja・init SKILL.md）の整合を契約テスト 14 本（`test_v0132_contracts.py`）＋既存契約テスト
  （test_v013/test_v0131/test_wp12）で機械判定 → フルスイート **Ran 551 tests, OK, skip 0**（handoff 内で承認 commit に対して再実行、同値）。
- SSoT 更新: **0 ファイル**（AGENTS.md／PROJECT.md は本 repo に存在しない。規約・仕様の変更は config-schema.md／ADOPTION §7 に記録済み）。
- 検査系成果物の実数: fix-scope docGlobs 既定の AST 走査 **対象 7 ファイル・11 call site**／組込み deny 文書 **5 か所**／settings.yml マーカー文書 **5 ファイル**／
  conditional-force 一掃の検査対象 **4 文書**（段落単位）／Phase-5 状態行 **3 ブロック・20 枝**（6＋7＋8 メッセージ、reason 6/6/8）／probe 判定表テスト **3 probe × 10 ＋ cocoindex 2**
  ＋ cocoindex 固有 6（legacy dir・gitignore 3・指紋 2）／read-manifest 未 seal **4 入力**／fixture **48 path・24 rule・sha 3 点一致**／test_release_handoff の旧値残存 **0 件**。
- リリース実測: tag local/remote `2b2fcad` 一致、Release `docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)`（draft=false）、
  `gh issue list --state open` = 0、`~/.claude/skills/docaudit/.claude-plugin/plugin.json` = 0.13.2、handoff の rsync dry-run 差分 0。
- 別 Issue 候補（未起票、ユーザー判断）: (1) `indexing`/`contextMode`/`webExtract`/`codexReview` のキー不在既定の統一、(2) Phase-0 probe 結果の run-dir 永続化
  （中断後の Phase-5 状態行復元 — Sol R3-1）、(3) dir-framework 側の `graphify-out/` 残骸（884K、利用者側で削除）。
- 版判断の記録: #52/#53 本文と Sol R1-1 は minor（v0.14.0）を提案。ユーザー指示「パッチアップデート」を採り 0.13.2 で出荷（ADOPTION §7 に挙動変更 5 点を明記）。
