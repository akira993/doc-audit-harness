# PLAN — Issue #66 方式 B: `/code-review` の自律実行と verdict 統合（docaudit v0.17.0）

版: v8（Opus ラウンド 2 の V7-1〜V7-5 反映、2026-08-31）。

## 1. 目的

上流 Claude Code（≥2.1.246、実測 2.1.251）で `/code-review` がモデル起動可能になったため、docaudit の
Phase 4 で `reviewCommands.code` を**単一窓口**として自律実行し、所見を verdict に畳み込む（方式 B、
ユーザー決定済み）。旧契約（「監査自身は起動しない」「AskUserQuestion で一度だけ提案」
「`CODE_REVIEW_STATE=not-model-invocable`」）を全面置換する。fail-closed を維持し、「設定された
レビュー層が黙ってスキップされて CONSISTENT」を構造的に不可能にする。

**設計原則（v0.16.0 から継承、逸脱禁止）**
- 決定は script の決定表で行い、SKILL.md の散文で再決定しない。
- config を読む新規消費者は sealed-config 契約（verify-on-read・exit 7・taint funnel・registry 計数）に完全参加。
- **REFUSED を出すのは gate（decide-verdict.py）だけ**。planner の refuse はレビュー起動の抑止のみで、
  監査は通常どおり gate まで進み、gate が封印 config から独立に同じ判定を導出して正式な REFUSED
  （報告書・履歴・lock 解放を伴う）を出す。
- 強制（required）は gate が封印 config から直接導出。モデルの EVIDENCE 自己申告を根拠にしない。
- ターンを跨いだ「完了」を信用しない: resume 後の `ran` は禁止。
- 実測に無い挙動を文書化しない（`permissions.ask` は推奨しない — 実測不成立）。

**裁定済みの意図的非対称（ユーザー裁定・advisor 追認。再審議しない）**: 不正な
`reviewCommands.code`（P2/P4/P5/P7・required 矛盾）は **required の値に関わらず全 run REFUSED**。
codexReview の invalid-config（⚠ WARN で継続）とは意図的に非対称である。理由: (i) static な設定ミスは
adopter が一度直せば恒久解消するのに対し、runtime の not-run は環境起因で一過性がある — 制御可能性が
異なるものに同じ罰を与える必要はない。(ii) `required` 既定 false の世界で「⚠ 表示＋CONSISTENT 継続」は
#66 の発端症状（設定済みレイヤが 15 run 誰にも気づかれずスキップされ続けた）の再演になる。
(iii) v0.16.0 で probe の invalid-config を exit 0 から exit 2 に強めた本プロジェクト自身の軌跡と一致。
既存 adopter 実測（2026-08-31、9 プロジェクト）: `ultra` 0 件・P7 該当は sunrise-web の
`/code-review xhigh` 1 件のみ（現行でも正規レベルでない潜在誤設定。1 行修正で移行可能）。

## 2. 入力・参照資料

- Issue #66 本文（方式 A の JSON 例は不採用。拒否強度はユーザー裁定で Issue どおり REFUSED）。
- `tasks/route/2026-08-31-issue-66/00-preflight-verification.md` — 実機検証。**前提事実の正本**。
- `tasks/route/2026-08-31-issue-66/01-survey-out.md` — 現状インベントリ。
- `tasks/route/2026-08-31-issue-66/02〜06-critique-r*-out.md` — Sol 批判 5 ラウンド。
- Opus 全体レビュー（REVIEW.md の Opus ラウンド記録）。

### 実測で確定した前提（再検証不要）

| 事実 | 出所 |
|---|---|
| モデルは Skill ツールで code-review を起動できる（headless/interactive、flag 不要） | preflight |
| headless: 同期 tool_result（`Skill "code-review" completed (forked execution).`）で所見返却 | preflight |
| interactive: background agent → 同一ターン内で完了待ち可能・完了後に所見が可視 | preflight |
| 所見レイアウトは揺れる（bullet／`file:line —` 行／fenced JSON）。severity ラベルは無い | preflight |
| `deny: ["Skill(code-review *)"]` → `Error: Skill execution blocked by permission rules` | preflight |
| project settings の `skillOverrides: user-invocable-only` → `Error: Skill code-review is disabled for model invocation in skillOverrides settings` | preflight |
| `ask` は headless 素通り・interactive(auto mode) プロンプト無し → 承認ゲート不成立 | preflight |
| `ultra` は待たない・`--fix` は checkpoint 外編集 | 上流 docs |

## 3. 担当

boss = Fable/Opus（計画・レビューのみ。実装は書かない）。

## 4. 実行者

worker = GPT-5.6（実装: Terra high 起点。批判: Sol high）。

## 5. 成果物

### S1 新規 script `skills/audit/scripts/code-review-plan.py` — 決定表

決定的・字句的。入力: `--config CFG --expect-config-sha SHA`。config は
`sealed_config.load_sealed_config` で読む（registry 完全参加）。出力（stdout JSON 1 個）:
`{"action": "run|legacy|not-active|refuse", "state": "...", "effort": "...|null", "required": bool, "command": "...|null", "reason": "..."}`。
`command` は legacy 時の原文字列。

**優先順位付き完全表（上から順に最初の一致で確定）**

| P | 条件 | action | state | 備考 |
|---|---|---|---|---|
| 1 | `reviewCommands` キー無し | not-active | not-configured | |
| 2 | `reviewCommands` が JSON object でない（null・配列・文字列・数値含む） | refuse | invalid-review-config | reason に型を明記 |
| 3 | `code` キー無し | not-active | not-configured | `security` の有無に関わらず |
| 4 | `code` が文字列でない（null 含む） | refuse | invalid-review-command | |
| 5 | `code` が空文字列または Unicode 空白のみ | refuse | invalid-review-command | |
| 6 | `code` が `^/code-review (low|medium|high)$`（ASCII 単一空白）に完全一致 | run | pending | effort を抽出 |
| 7 | `code` が `/code-review` そのもの、または `/code-review` の直後に任意の Unicode 空白が続く（`ultra`・`xhigh`・`--fix` 含む・二重空白・全角空白・未知レベル・追加トークン） | refuse | invalid-review-command | 公式名前空間の不正形。charset 制約は**この名前空間内のみ** |
| 8 | それ以外すべて（`/code-review-custom`・`/社内レビュー 高` 等。文字集合の制約なし） | legacy | legacy-pending | **契約・挙動とも現行から一切変更しない**（後述）。`legacy-pending` は planner 内部の分類値であり `CODE_REVIEW_STATE` には束縛しない（V7-5） |

**`required`**: 省略時 false。非 boolean → refuse `invalid-review-config`。`required:true` は P6 とのみ
併用可。P1/P3 または P8 と併用 → refuse `invalid-review-config`（設定矛盾）。refuse 行では required は
評価不要。**refuse／not-active 行の planner 出力は常に `required:false` に正規化**。

**refuse の reason は remediation を含む固定形式**（advisor 裁定）: 原文値の引用＋
「`/code-review <low|medium|high>` に修正するか `reviewCommands.code` を外す」＋ADOPTION 該当節への
ポインタ。gate も同一文字列を REFUSED 理由に使う。

**分類の単一実装**: P1〜P8 は副作用のない共通関数
`classify_review_command(config_doc) -> {p, action, state, effort, required, command, reason}` を新規
ライブラリ `skills/audit/scripts/docaudit_review.py` に置き、planner・gate（decide-verdict.py）・
start-run.py の 3 者が封印済み config doc に対して呼ぶ。二重実装禁止。library は parsed dict のみを
受け取り、config I/O・環境変数・`sealed_config` import を持たない（registry 対象外の根拠。S7 で AST 固定）。

sealed-config 契約: sha 不一致 → exit 7 + stderr `sealed-config-mismatch` → SKILL stopping rule →
`decide-verdict.py --taint-observed config --observed-by code-review-plan.py`。OBSERVERS に追加。

### S2 SKILL.md Phase 4 step 3 の書き換え（現行 :580-602）

1. 既存 getter `REVIEW_COMMANDS_JSON`（:556）は維持し、**`security` コマンド値の供給源**として消費
   （legacy 実行値は planner 出力の `command` に一本化）。
2. `CODE_REVIEW_PLAN="$(python3 "$SD/scripts/code-review-plan.py" --config "$CFG" --expect-config-sha "$CONFIG_SHA")"`
   の呼び出しは Phase 4 の CONFIG_SHA 再束縛・getter 直後、**global Phase 4 分岐より前**。分岐前で
   行うのは**分類と初期状態の束縛のみ**（実コマンド起動は一切しない）:
   - `phase4Required=true` の内側でのみ、action=run → 5. の Skill 起動、action=legacy → **現行の
     project 固有コマンド挙動そのまま**（実行を試み、不可なら skip+WARN。状態・evidence・fold 規則
     とも現行から変更しない）。
   - `phase4Required=false` → P6 は `CODE_REVIEW_STATE=phase4-not-required`（required:true は S3-1 に
     より false と共存しない）。P8 は現行どおり（何も追加しない）。
   - action=refuse/not-active → 起動なし・状態のみ。
3. `action=refuse` → 起動せず、状態束縛して**通常どおり続行**（gate が正式 REFUSED）。
4. `action=not-active` → 現行どおり何もしない。
5. `action=run` → **Skill ツールで起動**: skill=`code-review`、args=**effort のみ**。AskUserQuestion
   offer は廃止。非対話でも起動。
6. **完了確認は同一ターン列内のみ**: 同期 tool_result または background agent の完了通知を**ターンを
   終えずに待つ**。ユーザー入力を跨いだ resume 後に `ran` を束縛することは**禁止** — cross-turn
   checkpoint 表の行 (g) を「code-review 起動後に中断された監査は resume 時
   `CODE_REVIEW_STATE=not-run` とし、会話に残る所見を fold しない」に改める。
7. 会話内状態（`CODE_REVIEW_STATE`）: `ran`／`blocked-by-settings`（エラーに
   `disabled for model invocation in skillOverrides` または `blocked by permission rules` を含む）／
   `not-run`（その他: skill 不存在＝旧 CC・起動失敗・完了未確認・resume 後）／
   `phase4-not-required`／refuse 系（S1 の state）。旧 `not-model-invocable` は全廃。
   ※報告書の状態行の正本は S4 の gate 導出（会話変数は orchestration 用）。
8. **fold 契約（レイアウト非依存）**: 完了結果に可視の所見のみ、`source:"code-review"` を付けて
   Phase-4 findings collection へ。SKILL は severity 欠落・未知値に `UNSPECIFIED` を付す（表示規約）。
   **gate 側の扱いが正本**（S4: source=="code-review" に限り欠落・未知値も blocking として扱い、
   REFUSED にはしない）。
9. `reviewCommands.security` は現行のまま変更しない。
10. **SKILL.md:710-719 の placeholder 契約表に行を追加**（V7-1）:
    `{{GATE_CODE_REVIEW_STATUS}} | 1 | code-review 状態行（gate が S5 の固定文言で描画）`。
11. 現行の `/code-review ultra` 段落・`disable-model-invocation` 分岐・非対話分岐は削除。
    **:598-602 の context-mode 節（CM_AVAILABLE 時の ctx_execute 還元規約）は逐語で保持する**
    （自律起動でも所見は in-band で返るため依然有効。ADOPTION:82/:101・ja:81/:95・
    config-schema.md:207 の既存記述と整合を保つ）。

### S3 code-review 層のライフサイクル

**codexReview の実挙動と対称**（実装事実: `start-run.py:247` は `codexReview.required:true` 自体を
`phase4Required=true` の条件に含める）:

1. **start-run.py**: `phase4Required` の計算に「classify_review_command が P6 かつ `required:true`」を
   追加（codexReview.required と並列。**P6 でも required:false なら影響しない**）。共通分類関数を import。
2. planner の配置と分岐前の扱いは S2-2。
3. gate: `phase4:"none"` sentinel × P6 × `required:true` → REFUSED（codexReview :1027 対称）。
   `"none"` × P6 × required:false → 正常（gate が `phase4-not-required` 状態行を導出）。
4. **`manifest.phase4Required` の厳密型検査**: gate は双方向契約（false ⇔ `"none"` sentinel）の判定
   より前に厳密 JSON boolean を検査。欠落・null・数値・文字列 → REFUSED。

### S4 EVIDENCE / gate の enforcement（decide-verdict.py）

- EVIDENCE.phase4 の `codeReview` キーは **P6（run）の run でのみ書く**:
  `codeReview: {"state": "<ran|blocked-by-settings|not-run>"}`（3 値のみ）。
  **refuse・not-active・P8 legacy の run では `codeReview` キーを書かない**（Opus O-1。gate は封印
  config から独立導出するので evidence 不要）。write-evidence.py に phase4.codeReview の型検査
  （object・state が 3 値 enum）を**追加する**（hedge しない。キー存在が許されるのは P6 のみという
  検査は gate 側=§9.8 の責務）。
- **REFUSED 理由の優先順位（gate はこの順で検査し最初の該当で確定）**:
  (1) `phase4Required` 厳密 boolean → (2) config 分類の refuse（P2/P4/P5/P7・required 矛盾。理由は
  S1 の remediation 込み固定文字列） → (3) sentinel 双方向整合 → (4) codeReview eligibility（§9.8）。
- **refuse の送出位置（V7-2）**: 優先順位 (2)〜(4) の `Refused` は **`report_trusted = identity_ok`
  （decide-verdict.py:968）の確定より後**に送出し、`can_report`（:1300）を成立させて REFUSED 報告書を
  publish する（codexReview の :955-963 の位置に置いてはならない — 報告書が公開されなくなる）。
  (1) は既存の manifest 検証群と同じ扱いでよいが、その経路でも V7-3 の既定値により描画は壊れない。
- **placeholder の全経路定義（V7-3）**: `{{GATE_CODE_REVIEW_STATUS}}` は報告書を描画する**全経路**で
  必ず文字列値を持つ。分類を導出できない REFUSED 経路（(1) の型異常・(3) の sentinel 不整合・既存の
  evidence/digest 系 REFUSED）の既定値は `code-review: n/a (audit refused before classification)`。
  `render_report` の values dict に無条件で含める（KeyError/TypeError クラッシュの遮断）。
- P6 × `required:true` × `state != ran` → REFUSED `code-review-required-not-run`。
- P6 × `required:false` × `state != ran` → **gate の `warnings[]` に警告コード `codeReviewNotRun` を
  追加**し（Opus O-10）、`{{GATE_WARNINGS}}` にも載せる。状態行と二重で黙殺を防ぐ。
- **severity の gate 側正規化（Opus O-4、gate が正本）**: `source=="code-review"` の所見に限り、
  severity 欠落・未知値を blocking として扱う（既存の `Refused("severity is missing")` 経路に落とさ
  ない）。他 source の既存挙動（欠落・未知値 → Refused）は不変。SKILL の `UNSPECIFIED` ラベルは表示
  規約であり gate はそれに依存しない。
- **state×findings の整合検査**: `source=="code-review"` の所見は「封印 config が P6 かつ
  `codeReview.state=="ran"`」の場合のみ許可。それ以外での存在 → REFUSED（偽所見の混入遮断）。
- **報告書の状態行は gate が導出（正本）**: 報告書テンプレートに **`{{GATE_CODE_REVIEW_STATUS}}`
  placeholder を新設（常に厳密 1 回出現。TOKEN_COUNTS に追加、OPTIONAL_TOKENS には入れない）**。
  gate が封印 config・manifest.phase4Required・検証済み evidence から決定的に導出した固定文言
  （S5）で埋める。not-active では `code-review: n/a (not configured)` を、P8 では
  `code-review: project-specific review command (not contract-verified)` を描画（P8 の run/skip WARN
  は現行 SKILL 経路のまま）。出力 JSON にも同値 `codeReviewStatus` を含める。
- **phase4Runs / flip 計測は現行どおり `source=="codex-review"` のみ**。code-review 所見は verdict に
  効くが history record・flip には入らない（意図的非対象。ADOPTION に明記＋除外の固定テスト）。

### S5 状態行の固定文言（gate が描画。現行 SKILL :813-816 の置換）

- `ran` → `✓ code-review: ran (findings folded into phase4)`
- `blocked-by-settings` → `⚠ code-review: blocked by this repo's own settings (skillOverrides or permission deny) while reviewCommands.code is configured — remove the block or unset reviewCommands.code`
- `not-run` → `⚠ code-review: configured but could not be run or confirmed this session`
- `phase4-not-required` → `💡 code-review: not run — Phase 4 not required for this run (expected)`
- not-active → `code-review: n/a (not configured)`
- P8 legacy → `code-review: project-specific review command (not contract-verified)`
- refuse 系は gate の REFUSED 理由に出る（状態行は refuse でも placeholder を埋める:
  `✗ code-review: invalid configuration (audit refused)`）。
- **見出しリテラル `**code-review status line**` と「codex-review 行の直後」という位置は保持**
  （Opus O-9。test_v014_contracts.py:206-207／test_v015 が分割キーに使用）。

### S6 registry 改訂（v0.17.0 正本 = 本 PLAN §9）

scripts 21→**22**、call sites 22→**23**、observers 19→**20**、getters **13**（不変・REVIEW_COMMANDS_JSON
は security 専用の消費検査を追加）、exempt **3**（不変）。
`skills/audit/references/engine-shas.json` に 0.17.0 エントリ（plugin.json 0.17.0 と同一 commit。
scaffold.py:172-180 の ValueError 回避）。

### S7 テスト

- 新規 `tests/test_docaudit_review.py`: 共通分類関数の **P1〜P8 全行×境界値の表駆動検査**（型異常
  P2/P4・空/空白 P5・token 境界 P7/P8・`xhigh`・Unicode legacy）。「対象 N 件を検査」の実数出力。
  **library 純粋性の AST 検査**（config I/O・環境変数・`sealed_config` import・`open()` 不在）＋隔離
  単体テスト。
- 新規 `tests/test_code_review_plan.py`: planner の S1 全行（一致/不一致 sha 対、exit 7、
  required 正規化、remediation 文字列）。「対象 N 件を検査」の実数出力。
- gate 側（表駆動）: config 分類（P1〜P8 全行）× `codeReview` evidence（欠落・各 enum・未知値・
  型違い・**P8/not-active/refuse でのキー存在 → REFUSED**）× required × `phase4Required`（true/false・
  型異常）× phase4（`"none"`／present）×既存 codexReview evidence 健全。source=="code-review" 偽所見
  の対照（P1/P3・P8・P6×not-run への混入 → REFUSED、P6×ran → 受理）。severity 欠落・未知値の
  gate 側 blocking（source=="code-review" 限定・他 source は従来どおり Refused の対照ケース込み）。
  `codeReviewNotRun` 警告コード。code-review 所見の phase4Runs 不算入。CT-5b 無回帰。
- **`{{GATE_CODE_REVIEW_STATUS}}`**: TOKEN_COUNTS 厳密 1 回・全状態の固定文言・not-active の `n/a`
  描画（reportTemplateInvalid にならないこと）。**テンプレート fixture の棚卸し（V7-1）**:
  `tests/wp12_helpers.py:153-165` の `report_template()`（9 テストファイル・write_template 13 箇所が
  依存）と `tests/test_decide_verdict.py:309-317` に新トークンを追加。**SKILL.md の placeholder 契約表
  （:710-719）と decide-verdict.TOKEN_COUNTS の一致を検査する cross-source テストを新設**（現状この表
  を検査するテストは存在しない）。分類前 REFUSED（phase4Required 型異常）× `reportPath` 有効で報告書
  描画が例外を出さないこと（V7-3）。
- EVIDENCE end-to-end は**本番順序**: `start-run → seal-run → write-evidence → decide-verdict`。
- 報告書 e2e: `reportPath` 有効 run で placeholder が正しい固定文言に置換（ran／phase4-not-required／
  not-active／P8／**refuse（報告書が公開され `✗ … (audit refused)` と remediation 込み
  `{{GATE_REASON}}` を含む。V7-2）**の 5 代表＋checkpoint (h) resume 相当の「会話変数なし」条件）。
- planner・gate・start-run が同一分類関数を呼ぶことの検査（import 経路＋結果クロス assert）。
- 無回帰: config/history early-taint 経路、「空 impact＋corrupt history＋`phase4:"none"`」の隔離成功。
- `phase4Required` 厳密 boolean 検査、start-run「required:true で空 diff でも true」「P6+required:false
  では不変」。
- `tests/test_v015_contracts.py`: 旧固定を新契約固定へ全面更新＋旧トークン不在検査。
- `tests/test_v016_contracts.py`: CT 計数 23/3/13/22/20・registry・getter 消費検査・harness stamp
  （**:832** の 0.16.0 → 0.17.0）。
- `tests/test_v016_docs_contracts.py`: 旧意味句不在検査（`offered`×code-review 文脈・
  `not started by the audit`・「監査自身がまだ起動しない」等。SKILL:3 description・ADOPTION 冒頭
  要約 :11/ja 含む）＋新契約トークンの per-file 表。
- **既存テスト棚卸し（実行番号は現物で再確認のこと）**: `test_v0131_docs_contracts.py`（内部ファイル
  数 44→46、ADOPTION en/ja ファイル一覧に docaudit_review.py・code-review-plan.py）、
  `test_scaffold.py` :192/:337 等の 0.16.0、`test_v013_contracts.py` **:206** の engine-shas キー集合、
  `test_v014_contracts.py` **:206-207**（見出しリテラル依存 — S5 で位置保持のため原則無変更で green）。
- `tests/test_release_handoff.py` は**変更禁止**（歴史契約）。

### S8 ドキュメント是正

- `README.md` :9-10, :14-15, :26 — 新契約へ置換。
- `docs/ADOPTION.md` / `.ja.md` — survey §8 の全該当行＋冒頭要約（en:11 相当／ja 対応行）を更新。
  **版数の完全棚卸し（Opus O-6）**: en:236（`Version 0.16.0` 出力例）・en:284（stamp 完全一致の挙動）・
  en:322（更新一覧）と ja:213・ja:257・ja:294 の 0.16.0 → 0.17.0。
  新設節「code-review の自律実行と opt-out」:
  - opt-out は `permissions.deny: ["Skill(code-review *)"]` または `skillOverrides`（実測エラー文字列
    と `blocked-by-settings` 検出を記載）。**`permissions.ask` は推奨しない**（実測根拠つき）。
  - 要求バージョン: 自律実行は CC ≥ 2.1.246。旧環境は `not-run` WARN（required で REFUSED）。
  - **運用コスト 3 点の明記（Opus O-8）**: (i) P6 設定では diff のある監査ごとに code-review が走る
    定常コストと、effort を下げる／deny で opt-out する選択肢。(ii) code-review 所見は code 欠陥でも
    doc audit を NEEDS_FIX にする（severity 無し所見を blocking 扱いするのは意図的）。(iii) codex
    review との二重レビューは意図的な多層化。
  - 再現性: code-review は LLM サンプリング。phase4Runs/flip 計測の対象外。
  - v0.17.0 Behavior changes: 自律起動開始／**非 P6 の `/code-review` 文字列（`ultra`・`xhigh`・
    `--fix`・typo）は全 run REFUSED（breaking。`ultra` は監査外で手動実行は引き続き可能。移行は
    `/code-review <low|medium|high>` への 1 行修正）**／`not-model-invocable` 廃止／`required` 追加
    （**作用は `code` のみ、`security` には効かない**）／P6 設定のプロジェクトでは進行中の v0.16 run
    を resume 不可（fresh run 必須。P1/P3 は影響なし）。
  - v0.15.1 記録の「remains tracked in #66」は過去形＋v0.17.0 参照に修正（歴史段落自体は保存）。
- `skills/audit/SKILL.md:3` description（`offers /code-review`）を新契約に更新。
  **harness stamp は :317 と :888 の 2 箇所**（Opus O-6）を 0.17.0 に。
- `skills/audit/references/config-schema.md` :20 — S1 字句契約・`required`（code のみ作用）・legacy・
  refuse=REFUSED 込みで全面更新。:207 の context-mode 記述は S2-11 により**現状のまま**。
- `docs/examples/doc-audit.example.json` — `"required": false` を追記。
- ADOPTION en/ja の内部ファイル一覧に `docaudit_review.py`・`code-review-plan.py` を追加。
- `skills/init/SKILL.md` :166 — required の言及を追加。

### S9 バージョン・記録

`.claude-plugin/plugin.json` → 0.17.0。engine-shas.json 0.17.0（同一 commit）。REVIEW.md に記録。

## 6. 完了条件（機械判定）

1. `python3 -m unittest discover -s tests` 全緑。`Ran N tests / OK` verbatim（基準 716＋追加分、実数記録）。
2. CT 実数出力 = `call sites 23／exempt 3／getters 13／scripts 22／observers 20`。
3. `tests/test_docaudit_review.py`・`tests/test_code_review_plan.py` が「対象 N 件を検査」を出力（実数記録）。
4. `grep -rn 'not-model-invocable' skills/ README.md docs/` 0 件（tests/ は不在検査コード内のみ許容）。
5. `{{GATE_CODE_REVIEW_STATUS}}` の TOKEN_COUNTS 厳密 1 回検査と全状態文言テスト green。
6. planner 単体: S1 全行が期待 JSON、破損 config で exit 7・stderr `sealed-config-mismatch`。
7. gate: 優先順位 4 段・required REFUSED・eligibility 全数表（§9.8）・偽所見遮断・severity gate 正本・
   `codeReviewNotRun` 警告・phase4Runs 不算入が独立テストで green。
8. plugin.json = 0.17.0、engine-shas.json 0.17.0 エントリ（同一 commit）。
9. `tests/test_release_handoff.py` に diff 無し。

## 6b. 受入条件（boss 実施。worker のスコープ外 — worker プロンプトには §6 のみを貼る）

1. **受入 run**: scratch repo に `reviewCommands.code:"/code-review low"` を設定し、意図的な code 欠陥
   と doc 変更を置いて監査を 1 回完走（headless）。(i) `{{GATE_CODE_REVIEW_STATUS}}` 行、
   (ii) phase4.json の `codeReview.state` と fold 所見、(iii) verdict を REVIEW.md に記録。

## 7. 変更範囲

**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/code-review-plan.py`（新規）、
`skills/audit/scripts/docaudit_review.py`（新規・分類 library）、
`skills/audit/scripts/decide-verdict.py`、`skills/audit/scripts/start-run.py`（S3-1 のみ）、
`skills/audit/scripts/write-evidence.py`（phase4.codeReview 型検査のみ）、
`skills/audit/references/config-schema.md`、`skills/audit/references/engine-shas.json`、
`skills/init/SKILL.md`（reviewCommands 行のみ）、`README.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
`docs/examples/doc-audit.example.json`、`.claude-plugin/plugin.json`、`tests/`
（**ただし `tests/test_release_handoff.py` は変更禁止**）。

**禁止**: 上記以外のすべて。probe 群・sealed_config.py・open-run.py・docaudit_cache.py・
docaudit_paths.py・codex-review-plan.py・seal-run.py・probe-record.py。`reviewCommands.security` と
P8 legacy の挙動変更。`.gitignore`。git 操作（commit/push は boss）。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 8. 検証コマンド一式

```
python3 -m unittest discover -s tests
python3 -m unittest tests.test_v016_contracts -v 2>&1 | tail -20
python3 -m unittest tests.test_docaudit_review tests.test_code_review_plan -v
grep -rn 'not-model-invocable' skills/ README.md docs/ ; test $? -eq 1
git diff --stat && git status --short
git diff -- tests/test_release_handoff.py   # 空であること
```

## 9. Registry（v0.17.0 の単一の真実）

### 9.1 スクリプト消費者（v0.16.0 §9.1 の 21 本 ＋ 下記 = **K=22**）

| # | script | SKILL call site | sha 供給 | フラグ | 読み | 正常 exit | mismatch exit | observer ID |
|---|---|---|---|---|---|---|---|---|
| 22 | `code-review-plan.py`（新規） | Phase 4 の CONFIG_SHA 再束縛・getter 後、global Phase 4 分岐直前（S2-2 の 1 行） | `$CONFIG_SHA` | 必須 | 直接 | 0 | 7 | `code-review-plan.py` |

→ call sites **N=23**。exempt **M=3**（不変）。

### 9.2 getter registry（**G=13**、構成不変）

v0.16.0 §9.2 のまま。`reviewCommands` → `REVIEW_COMMANDS_JSON` の消費先は「**`security` 実行値のみ**。
CT は代入後の消費を検査」。

### 9.4 observers（**O=20**）

v0.16.0 §9.4 の 19 個 ＋ `code-review-plan.py`。

### 9.8 code-review evidence eligibility（gate の全数表）

前提（gate が S4 の優先順位で検査。採番は S4 と同一）: (1) `phase4Required` 厳密 boolean →
(2) config refuse → (3) 双方向契約 `phase4Required=false` ⇔ `phase4` は `"none"` sentinel → (4) 本表。
P6×required:true は start-run により `phase4Required=true` が保証され、`"none"`×P6×required:true は REFUSED。

| config 分類 | phase4Required | `phase4.codeReview` | gate の扱い／状態行 |
|---|---|---|---|
| P1/P3 not-active | true | キー無し | 正常／`n/a (not configured)` |
| P1/P3 not-active | true | キー有り | REFUSED（evidence invalid） |
| P1/P3 not-active | false（`"none"`） | —（phase4 なし） | 正常／`n/a (not configured)` |
| P2/P4/P5/P7 refuse・required 矛盾 | 任意 | 任意（キー有りでも優先順位 (2) が先） | REFUSED（remediation 込み固定理由）／`invalid configuration` |
| P6 run | true | `{state:"ran"}` | 正常・所見 fold 済み／`ran` |
| P6 run | true | `{state:"blocked-by-settings"}`／`{state:"not-run"}` | required:true → REFUSED `code-review-required-not-run`／false → `codeReviewNotRun` 警告＋状態行 |
| P6 run | true | キー無し・enum 外・型違い | REFUSED（evidence invalid。P6 config の v0.16 run resume を含む） |
| P6 run（required:false のみ到達可） | false（`"none"`） | — | 正常／`phase4-not-required` |
| P6 run（required:true） | false（`"none"`） | — | REFUSED（前提） |
| P8 legacy | true | **キー無し（正）** | 正常（現行 legacy 挙動）／`project-specific review command (not contract-verified)` |
| P8 legacy | true | キー有り | REFUSED（evidence invalid。legacy は evidence 契約外） |
| P8 legacy | false（`"none"`） | — | 正常／同上の固定行 |

追加の整合検査（全行）: `source=="code-review"` の所見は「P6 かつ state=="ran"」でのみ許可。それ以外 → REFUSED。

### 9.5 期待値（CT が出力・assert）

call sites **N=23**／exempt **M=3**／getters **G=13**／scripts **K=22**／observers **O=20**。
worker の実測が異なれば、実装を曲げず報告する（boss が registry を改訂）。

## 10. 非対象の明示

- `reviewCommands.security` の挙動・状態体系。
- **P8 legacy の evidence 契約化**（ユーザー裁定で縮小: legacy は現行挙動を一切変更しない。
  evidence に codeReview キーを書かず、gate は存在すれば invalid とするのみ）。
- code-review 所見の phase4Runs/flip 計測（意図的除外）。
- `tests/test_release_handoff.py`（歴史契約）。
- ledger 型の所見持ち越し（#59 で撤回済み）。
- `permissions.ask` の推奨（実測不成立）。
