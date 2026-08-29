# 調査結果

ファイルは変更していません。以下は現行 HEAD の読み取り結果です。

## 1. 現行実装

### `ax-probe.sh`

設定判定は `skills/audit/scripts/ax-probe.sh:23-46`、出力分岐は `:50-66` です。

| 入力 | 判定箇所 | emit JSON | exit |
|---|---:|---|---:|
| キー不在 | `:31-35` | `{ "axAvailable": false/true, "axBin": "<bin>", "axVersion": null/"<version>", "reason": "not-installed"/"ok" }` | 0 |
| `{}` | `:31-35` | キー不在と同じ。`enabled` は暗黙に有効 | 0 |
| `enabled:false` | `:35` | `{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"disabled-by-config"}` | 0 |
| enabled 非 boolean | `:34`, `:42-44` | `{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"invalid-config"}` | 0 |
| キー非 object | `:32-34`, `:42-44` | 同上 | 0 |
| bin 不正 | `:37-40`, `:42-44` | 同上 | 0 |
| bin 未導入 | `:59-61` | `{"axAvailable":false,"axBin":"<bin>","axVersion":null,"reason":"not-installed"}` | 0 |
| bin 実行可能 | `:64-66` | `{"axAvailable":true,"axBin":"<bin>","axVersion":"<version>","reason":"ok"}` | 0 |

現行コードは `state="enabled"` で開始し、`webExtract` が存在する場合だけ検査します（`skills/audit/scripts/ax-probe.sh:25-36`）。したがってキー不在は `not-configured` ではありません。

未知引数だけは `skills/audit/scripts/ax-probe.sh:19` で exit 2 です。通常の probe 分岐は常に exit 0 です（`:9`, `:50-67`）。

### `codex-probe.sh`

設定判定は `skills/audit/scripts/codex-probe.sh:24-47`、呼び出し元情報は `:51-59`、JSON生成は `:61-68`、分岐は `:70-90` です。

| 入力 | 判定箇所 | emit JSON の全フィールド | exit |
|---|---:|---|---:|
| キー不在 | `:26-37` | `codexReviewAvailable`、`codexReviewBin`、`codexReviewVersion`、`probeCommands`、`reason`、`callerCodexHome`、`callerCodexHomeSource`、`callerAuthFile` | 0 |
| `{}` | `:32-37` | キー不在と同じ。暗黙に有効 | 0 |
| `enabled:false` | `:36`, `:74-76` | `codexReviewAvailable:false`、`codexReviewBin:"codex"`、`codexReviewVersion:null`、`probeCommands:[]`、`reason:"disabled-by-config"`、呼び出し元3フィールド | 0 |
| enabled 非 boolean | `:35`, `:43-44`, `:70-72` | `codexReviewAvailable:false`、`codexReviewBin:"codex"`、`codexReviewVersion:null`、`probeCommands:[]`、`reason:"invalid-config"`、呼び出し元3フィールド | 0 |
| キー非 object | `:33-35`, `:43-44` | 上記 `invalid-config` と同じ | 0 |
| bin 不正 | `:37-42`, `:43-44` | 上記 `invalid-config` と同じ | 0 |
| bin 未導入 | `:79-81` | `codexReviewAvailable:false`、指定 bin、version `null`、commands `[]`、`reason:"not-installed"`、呼び出し元3フィールド | 0 |
| `exec --help` 失敗 | `:84-88` | 指定 bin、取得した version、commands `[ "<bin> --version", "<bin> exec --help" ]`、`reason:"probe-exec-failed"`、呼び出し元3フィールド | 0 |
| 成功 | `:84-90` | 指定 bin、version、commands、`reason:"ok"`、呼び出し元3フィールド、available `true` | 0 |

JSON の全フィールドは `skills/audit/scripts/codex-probe.sh:62-67` の `json.dumps` に定義されています。未知引数は `:20` で exit 2、それ以外は通常 exit 0 です。

## 2. 参照パターン

key-gated 化済み probe は、最初にキーの存在を確認し、キー不在なら tool の bin 検査・インストール確認・実行を行いません。

- codegraph: `skills/audit/scripts/codegraph-probe.sh:28-35`

  > `if "symbolGraph" not in config: print("not-configured", default); raise SystemExit`

- graphify: `skills/audit/scripts/graphify-probe.sh:31-39`

  > `if "docGraph" not in config: print("not-configured", default); raise SystemExit`

- cocoindex: `skills/audit/scripts/cocoindex-probe.sh:34-41`

  > `if "semanticSearch" not in config: print("not-configured", default); raise SystemExit`

その後に object、enabled、bin を検査します。graphify の順序は `skills/audit/scripts/graphify-probe.sh:40-51`、codegraph は `:36-47`、cocoindex は `:42-51` です。tool の存在確認は、それぞれ graphify `:65-68`、codegraph `:61-64`、cocoindex `:65-68` の後です。

emit される reason の正確な値は次のとおりです。

- codegraph: `ok`, `not-installed`, `disabled-by-config`, `index-failed`, `not-configured`, `invalid-config`（`skills/audit/scripts/codegraph-probe.sh:52-83`）
- graphify: `ok`, `not-installed`, `disabled-by-config`, `update-failed`, `not-configured`, `invalid-config`（`skills/audit/scripts/graphify-probe.sh:56-91`）
- cocoindex: `ok`, `not-installed`, `disabled-by-config`, `not-initialized`, `index-failed`, `not-configured`, `invalid-config`, `gitignore-modified`（`skills/audit/scripts/cocoindex-probe.sh:55-121`）

## 3. `skills/audit/SKILL.md`

### reason enum

現行 enum は以下です。

- ax: `ok` / `not-installed` / `disabled-by-config` / `invalid-config`（`skills/audit/SKILL.md:157-163`）
- codex: `ok` / `not-installed` / `disabled-by-config` / `probe-exec-failed` / `invalid-config`（`skills/audit/SKILL.md:172-182`）

両方に `not-configured` を追加する必要があります。

### Phase 0

ax の probe、parse、bind、record は `skills/audit/SKILL.md:157-170` です。

> `AX_PROBE_JSON=... ax-probe.sh ...`  
> `{axAvailable, axBin, axVersion, reason}` を parse する（`:161-163`）

codex の probe、parse、bind、record は `skills/audit/SKILL.md:172-196` です。

> `{codexReviewAvailable, codexReviewBin, codexReviewVersion, probeCommands, reason}` を parse する（`:175-182`）

変更後は、キー不在時に両 probe が `not-configured` と `available:false` を返すため、Phase 0 の手順自体は維持できます。enum と状態表示を更新する必要があります。

### Phase 4 の codex 実行条件

Phase 4 全体の実行条件は、sealed manifest の `SEALED_PHASE4_REQUIRED` です（`skills/audit/SKILL.md:523-527`）。

codex review の実行可否は、次の plan 呼び出しに集約されています（`skills/audit/SKILL.md:571-581`）。

> `codex-review-plan.py ... --available "$CODEX_REVIEW_AVAILABLE" --available-reason "$CODEX_REVIEW_REASON"`

`action=skip` または `action=not-active` の場合は `CODEX_REVIEW_STATE` を設定し、`codex exec` を起動しません（`:577-581`）。実際の起動は `action=run` の場合だけです（`:583-600`）。

`codex-review-plan.py` は `available:false` のとき reason をそのまま返します（`skills/audit/scripts/codex-review-plan.py:32-34`）。したがって `not-configured` 自体で壊れる実装はなく、Phase-5 の表示追加が必要です。

### Phase 5 の優先順位と全分岐

全体の優先順位規則は `skills/audit/SKILL.md:643-654` です。

> whole-record unknown → invalid-config → 残りの状態  
> codex-review は invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way

ax の現行分岐は `skills/audit/SKILL.md:744-748` です。

- unknown → ⚠ state unknown
- invalid-config → ⚠ invalid
- available false → 💡 not active
- available true → ✓ active

`AX_REASON=not-configured` を追加し、「not configured。キーが無いため tool を起動していない。`/docaudit:init` で有効化」という専用 💡 行にする必要があります。通常の `AX_AVAILABLE=false` より前に置く必要があります。

codex の現行分岐は `skills/audit/SKILL.md:750-764` です。

- invalid-config → ⚠ invalid（`:754`）
- review state 未記録 → ⚠（`:755-756`）
- review state あり → 4-way（`:757-759`）
- `not-active` は現在 `<rebind.codex-review.reason>` を表示（`:757`）

`not-configured` は既存の `not-active` でも表示可能ですが、key-gated の他 seam と揃えるなら、invalid-config の次に専用の 💡 `not configured` 分岐を追加するのが必要です。追加しない場合でも、少なくとも 4-way の `<reason>` に `not-configured` が現れることを仕様として明記する必要があります。

### resume/rebind

Phase-5 は probe-record の rebind を唯一の情報源にします（`skills/audit/SKILL.md:643-654`）。resume 後の Phase 4 も rebind から availability、reason、bin を復元できます（`:68`）。

ax の rebind は `reason` を保持します（`skills/audit/scripts/probe-record.py:276-279`）。

codex の rebind は `available`、`reason`、`bin`、caller 情報を保持します（`skills/audit/scripts/probe-record.py:279-290`）。

したがって `not-configured` は rebind 構造を変更せず、reason enum と Phase-5 表示だけを追加すれば扱えます。

## 4. `probe-record.py`

ax の許容 reason は現在次の5行相当で固定されています（`skills/audit/scripts/probe-record.py:105-112`）。

> `{"ok", "not-installed", "disabled-by-config", "invalid-config"}`

codex の許容 reason は `skills/audit/scripts/probe-record.py:113-128` です。

> `{"ok", "not-installed", "disabled-by-config", "probe-exec-failed", "invalid-config"}`

両方の集合に `not-configured` を追加する必要があります。

rebind 側はすでに reason をそのまま保持しており、追加変更は不要です（`skills/audit/scripts/probe-record.py:276-290`）。

## 5. 下流の消費者

### 変更不要

`workflow-template.js` は ax の reason を読まず、availability の真偽値だけを受け取ります（`skills/audit/references/workflow-template.js:90-95`）。

> `const axAvailable = a.axAvailable === true || a.axAvailable === 'true'`

ax の note は available が true の場合だけ追加されます（`skills/audit/references/workflow-template.js:122-128`）。`not-configured` では false なので壊れません。

`codex-review-plan.py` は `--available-reason` をそのまま result reason に渡します（`skills/audit/scripts/codex-review-plan.py:18-20`, `:32-34`）。reason の固定集合検査はありません。

`start-run.py` は `codexReview.required` のみを見ています（`skills/audit/scripts/start-run.py:247-252`）。`not-configured` の導入で変更は不要です。

`decide-verdict.py` も codex の設定では `required` と `enabled:false` の整合性を検査するだけです（`skills/audit/scripts/decide-verdict.py:710-718`）。probe reason は読みません。

`import-audit-scope.py`、`plan-dispatch.py`、`codex-dispatch.py`、`inventory.py`、`set-config-key.py` に対象 reason の直接読取りは確認できません。未確認ではなく、横断検索で該当なしでした。

### 変更が必要

実質的な reason 消費者は `skills/audit/SKILL.md` の Phase-5 表示です。

- ax: `skills/audit/SKILL.md:744-748`
- codex: `skills/audit/SKILL.md:750-759`

ここに `not-configured` の 💡 分岐を追加します。

## 6. `skills/init/SKILL.md`

### 現行の提案・OMIT 文言

ax は現在、未検出時も「既定で動く」と説明しています（`skills/init/SKILL.md:131-135`）。

> `If ax was NOT detected, OMIT the key — the audit already runs without external-URL corroboration by default`

codex も同じです（`skills/init/SKILL.md:136-142`）。

> `If codex was NOT detected, OMIT the key — the audit already runs without the Codex review by default`

この2箇所を、次の形へ変更する必要があります。

> `OMIT the key; absent key ⇒ the audit reports not-configured and never runs the tool.`

見本は symbolGraph の `skills/init/SKILL.md:143-148`、docGraph の `:149-155` です。

### Step 1 の検出説明

ax/codex の検出と config 提案自体は `skills/init/SKILL.md:41-45` にあります。検出された場合は従来どおり key を提案し、未検出の場合だけ OMIT 文言を変更します。

## 7. `config-schema.md`

webExtract の schema 行は `skills/audit/references/config-schema.md:35` です。

> `An absent key remains enabled by default (intentional asymmetry).`

codexReview の schema 行は `skills/audit/references/config-schema.md:36` です。

> `An absent key remains enabled by default (intentional asymmetry)`

この2行を「key-gated」「key が無ければ `not-configured`、tool は実行しない」に変更します。

比較対象の正しい記述は以下です。

- symbolGraph: `skills/audit/references/config-schema.md:37`
- docGraph: `skills/audit/references/config-schema.md:38`

両方とも次の順序です。

> `key-gated Phase-0 ...`  
> `it runs only when this key exists ...`

`indexing` と `contextMode` は既定有効のまま維持するため、`skills/audit/references/config-schema.md:33-34` は変更対象外です。

## 8. テスト

### `test_ax_probe.py`

現在の既定動作テストは `test_default_when_no_webextract_block`（`tests/test_ax_probe.py:121-130`）です。

> `enabled defaults true, bin defaults "ax"`

v0.15.0 では、キー不在を `not-configured`、available false、bin を `ax`、version null とする期待値へ変更する必要があります。

網羅的な v0.14 判定表は `test_config_decision_table_v014`（`tests/test_ax_probe.py:132-187`）です。`absent` と `empty` を現在は有効扱いしています（`:146-161`, `:184-187`）。ここに「absent は not-configured」「empty object は従来どおり enabled」を固定する変更が必要です。

出力フィールド集合のテストは `tests/test_ax_probe.py:189-205`、bin 境界は `:206-230` です。invalid-config、disabled-by-config、not-installed、ok の既存検査は維持します。

### `test_codex_probe.py`

現在の既定動作テストは `test_default_when_no_codexreview_block`（`tests/test_codex_probe.py:140-149`）です。ここも `not-configured` 期待へ変更する必要があります。

網羅的な判定表は `test_config_decision_table_v014`（`tests/test_codex_probe.py:151-206`）です。`absent` と `empty` は `tests/test_codex_probe.py:166-180` で定義され、現在 `absent` も成功または未導入になります。`absent` のみ `not-configured` に変更します。

caller 情報を全分岐で保持するテストは `tests/test_codex_probe.py:208-251`、出力キー集合は `:277-291`、bin 境界は `:293-317` です。not-configured 分岐でも全フィールドを維持することを追加固定すべきです。

### `test_probe_record.py`

probe schema の invalid case は `tests/test_probe_record.py:99-124` です。ax/codex の `not-configured` 正常ケースを追加する必要があります。

rebind の完全性は `tests/test_probe_record.py:136-157`、部分 record と caller 情報は `:159-197` で固定されています。`reason:"not-configured"` を保存し、read 後の rebind に戻せるテストを追加する必要があります。

### `test_v014_contracts.py`

現行 v0.14 契約は ax/codex enum を `not-configured` なしで固定しています（`tests/test_v014_contracts.py:50-70`）。

また、v0.14 文書が「absent key still defaults to enabled」と固定されています（`tests/test_v014_contracts.py:23-48`）。これは v0.14 の歴史契約として残すか、v0.15 契約へ移すかを決める必要があります。現行版を v0.15 に更新する運用なら、文面と期待値を更新します。

schema テストも全4 seam に `An absent key remains enabled by default` を要求しています（`tests/test_v014_contracts.py:135-142`）。webExtract/codexReview については key-gated 期待へ分割変更が必要です。

### `test_v0132_contracts.py`

v0.13.2 の3 seam reason 集合は `tests/test_v0132_contracts.py:224-254`、状態行は `:256-289`、init の `not-configured` 件数は `:300-306` です。

特に init の件数は現在3固定です（`:301-303`）。

> `only the three selected OMIT rules name not-configured`

v0.15.0 では5固定へ更新するか、v0.15 専用契約テストへ切り出す必要があります。

### `test_codex_review_plan.py`

`invalid-config` の reason passthrough は `tests/test_codex_review_plan.py:15-28` で固定されています。`not-configured` も同様に passthrough されるケースを追加すべきです。

16行 truth table は `tests/test_codex_review_plan.py:30-61` にあり、available false なら `not-active` になる仕様です。key-gated 化後も `available:false`, `reason:not-configured` なら `codex exec` を起動しないことを固定する必要があります。

### `test_v013_contracts.py` の版列挙

release surface の現在値は `tests/test_v013_contracts.py:182-201` です。

> `{plugin_version, latest_sha_version, adoption_version, adoption_ja_version, stamp_version} == {"0.14.0"}`

v0.15.0 追加時は期待値を `{"0.15.0"}` に変更します。

refresh 許可 regex の既存箇所は `tests/test_v013_contracts.py:203-225` です。v0.15.0 の behavior-change ブロックを許可対象に追加する必要があります。現在の v0.12.0 許可パターンは `:207-218` にあります。

### `test_release_handoff.py`

現行ファイルは v0.14.0 専用の歴史的テストです。

- module docstring: `tests/test_release_handoff.py:1`
- tag: `:23`
- title: `:24`
- required release body: `:27-32`
- tag/release 検証利用: `:277-287`, `:384-410`

現行 v0.14.0 のリリース引き渡しを保存するなら変更不要です。v0.15.0 用の handoff に置き換える場合は、これら全ての版・タイトル・本文・tag を更新し、対応する handoff script の版文字列も更新します。現行 script は v0.14.0 を固定しています（`tasks/route/2026-08-28-issues-56-60/release-handoff.sh:2`, `:16-17`, `:66-74`, `:155-157`）。

## 9. 版文字列と ADOPTION

### plugin version

`.claude-plugin/plugin.json:1-4` に現在の版があります。

> `"version": "0.14.0"`

v0.15.0 に更新が必要です。

### ADOPTION §7

英語の behavior-change ブロックは次の範囲です。

- v0.12.0: `docs/ADOPTION.md:254-259`
- v0.13.2: `docs/ADOPTION.md:261-269`
- v0.14.0: `docs/ADOPTION.md:271`

v0.14.0 ブロックは一行の長い段落で、webExtract/codexReview の absent key 既定有効を含みます（`docs/ADOPTION.md:271`）。v0.15.0 の新ブロックを追加し、以下を記載する必要があります。

- webExtract/codexReview のキー不在は `not-configured`
- tool は起動しない
- `indexing`/`contextMode` は既定有効のまま
- `enabled:false`、invalid-config、bin 検査は従来どおり

日本語版も同じ構造です。

- v0.12.0: `docs/ADOPTION.ja.md:234-239`
- v0.13.2: `docs/ADOPTION.ja.md:241-245`
- v0.14.0: `docs/ADOPTION.ja.md:247`

v0.15.0 ブロックを `docs/ADOPTION.ja.md:247` の後に追加する必要があります。

本文中の版表示も更新候補です。

- 英語確認例: `docs/ADOPTION.md:231`
- 日本語確認例: `docs/ADOPTION.ja.md:211`
- 英語 refresh 説明: `docs/ADOPTION.md:303-304`
- 日本語 refresh 説明: `docs/ADOPTION.ja.md:277-279`

### `engine-shas.json`

構造は版をキーにし、各版が `check-docs`、`doc-lint`、`check-docs-engine` の SHA を持ちます（`skills/audit/references/engine-shas.json:1-41`）。現行最新版は `0.14.0`（`:37-41`）です。

`scaffold.py` は plugin version を読み、該当版の SHA エントリを要求し、現在の生成元と比較します（`skills/audit/scripts/scaffold.py:164-180`）。生成結果には `stampVersion` を入れます（`:338-343`）。

したがって v0.15.0 では、生成元の本文が変わらない場合でも `engine-shas.json` に `0.15.0` エントリを追加する必要があります。SHA は既存値を再利用できる可能性がありますが、実値は実装後の生成元で再計算が必要です。ここは未確認です。

検証テストは `tests/test_scaffold.py:307-317` です。

> plugin version と engine-shas の版を読み、生成元 SHA と一致させる

refresh の版固定は `tests/test_scaffold.py:201-220`、`:229-248`、plugin version 固定は `:311-316` です。

## 10. その他の残骸

webExtract/codexReview のキー不在既定有効を明記している残骸は次のとおりです。

- `skills/audit/references/config-schema.md:35-36`

  > `An absent key remains enabled by default (intentional asymmetry).`

- `skills/init/SKILL.md:134-135`

  > `the audit already runs without external-URL corroboration by default`

- `skills/init/SKILL.md:140-142`

  > `the audit already runs without the Codex review by default`

- `skills/audit/SKILL.md:224-225`

  > `When ax is absent, webExtract.enabled is false ...`

  これは「ax が absent」の意味が tool 未導入なのか config key 不在なのか曖昧になるため、key-gated 化後は「key が存在し、tool が absent」のように分離が必要です。

- `skills/audit/references/config-schema.md:215-225`

  > `With ax on PATH ... Phase 0 detects it.`  
  > `When ax is absent ...`

  key-gated 条件を明記する必要があります。

- `skills/audit/references/config-schema.md:233-240`

  > `With codex on PATH ... Phase 0 runs ...`

  `codexReview` key が存在する場合に限定する記述へ変更が必要です。

- `docs/ADOPTION.md:115-120`

  > `auto-used when installed`

- `docs/ADOPTION.md:124-127`

  > `auto-used when installed`

- `docs/ADOPTION.ja.md:100-105`

  > `導入済みなら自動使用`

- `docs/ADOPTION.ja.md:109-112`

  > `conditional-force（導入済みなら自動使用`

- `docs/ADOPTION.md:271`

  > `(an absent key still defaults to enabled ...)`

- `docs/ADOPTION.ja.md:247`

  > `キーが無い場合は従来どおり有効`

- `tests/test_v014_contracts.py:25-30`

  v0.14.0 behavior paragraph が absent key の既定有効を固定しています。

- `tests/test_v014_contracts.py:137-142`

  webExtract/codexReview も absent key enabled を要求しています。

- `tests/test_ax_probe.py:121-130`

  キー不在を既定有効としてテストしています。

- `tests/test_codex_probe.py:140-149`

  キー不在を既定有効としてテストしています。

`tests/test_v0132_contracts.py:300-306` の「3 seam のみ」という固定は、v0.15.0 では矛盾するため更新対象です。

# 変更が必要なファイル一覧

| ファイル | 変更点 |
|---|---|
| `skills/audit/scripts/ax-probe.sh` | キー不在を `not-configured` とし、tool 検査前に終了 |
| `skills/audit/scripts/codex-probe.sh` | キー不在を `not-configured` とし、Codex 検査前に終了 |
| `skills/audit/SKILL.md` | reason enum、Phase-5 ax/codex の `not-configured` 状態行、key-gated 説明を追加 |
| `skills/audit/scripts/probe-record.py` | ax/codex の reason 許容集合に `not-configured` を追加 |
| `skills/init/SKILL.md` | ax/codex の OMIT 文言を absent key ⇒ `not-configured` に変更 |
| `skills/audit/references/config-schema.md` | webExtract/codexReview の absent-key 既定有効記述を key-gated に変更 |
| `docs/ADOPTION.md` | v0.15.0 behavior changes、版表示、既定有効説明を更新 |
| `docs/ADOPTION.ja.md` | 日本語版の同内容を更新 |
| `.claude-plugin/plugin.json` | version を `0.15.0` に変更 |
| `skills/audit/references/engine-shas.json` | `0.15.0` の生成物 SHA エントリを追加 |
| `tests/test_ax_probe.py` | キー不在、空 object、全フィールド、tool 不起動を v0.15.0 契約へ更新 |
| `tests/test_codex_probe.py` | 同上。caller 情報を含む not-configured 出力を追加固定 |
| `tests/test_probe_record.py` | `not-configured` の schema 保存・rebind テストを追加 |
| `tests/test_codex_review_plan.py` | `not-configured` reason passthrough と未起動を追加固定 |
| `tests/test_v014_contracts.py` | 歴史版として残すか、現行契約へ更新するか要決定 |
| `tests/test_v0132_contracts.py` | init の3 seam 固定を5 seam対応へ更新、またはv0.15契約へ分離 |
| `tests/test_v013_contracts.py` | 最新版期待値を0.15.0へ更新し、refresh許可 regex を追加 |
| `tests/test_scaffold.py` | 最新版・stamp・engine-shas の期待値を0.15.0へ更新 |
| `tests/test_release_handoff.py` | 現行 v0.14.0 歴史テストを保存するなら変更不要。v0.15.0 handoff に再利用する場合のみ版・tag・title・本文を更新 |
| `skills/audit/references/workflow-template.js` | reason を読まないため変更不要 |
| `skills/audit/scripts/codex-review-plan.py` | reason を透過するため、実装変更は不要 |
| `skills/audit/scripts/decide-verdict.py` | probe reason を読まないため、実装変更は不要 |
| `skills/audit/scripts/import-audit-scope.py` | 対象 reason の読取りなし。変更不要 |