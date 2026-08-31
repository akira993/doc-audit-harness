現状は、`reviewCommands.code` は Phase 4 の単一設定窓口として定義されているものの、`/code-review` は自律起動されず、対話時のユーザー提案とターン跨ぎ状態だけが実装されています。Issue #66 の方式 B は未実装です。調査中のファイル変更はなく、`git status --short` も空でした。

## 1. `reviewCommands` 全出現箇所

総数は 11 箇所です。

| 分類 | file:line | verbatim |
|---|---|---|
| 消費 | `skills/audit/SKILL.md:556` | `REVIEW_COMMANDS_JSON="$(python3 "$SD/scripts/sealed_config.py" --config "$CFG" --expect-sha "$CONFIG_SHA" --get reviewCommands --default '{}')"` |
| 消費 | `skills/audit/SKILL.md:580` | `3. Handle \`reviewCommands.code\` (e.g. \`/code-review high\`) on the working diff, then` |
| 消費 | `skills/audit/SKILL.md:581` | `   \`reviewCommands.security\` (e.g. \`/security-review\`). Normalize any` |
| 消費 | `skills/audit/SKILL.md:595` | `   unavailable or failed \`reviewCommands.code\` command (including project-specific` |
| 消費 | `skills/audit/SKILL.md:596` | `   commands) is handled as before: skip and WARN. Then run \`reviewCommands.security\`.` |
| 定義 | `skills/audit/references/config-schema.md:20` | `| \`reviewCommands\` | object | no | {\`code, security\`} review command strings (effort embedded, e.g. \`/code-review high\`) |` |
| 定義 | `docs/examples/doc-audit.example.json:19` | `"reviewCommands": { "code": "/code-review high", "security": "/security-review" },` |
| 文書 | `docs/ADOPTION.md:354` | `| \`reviewCommands\` | object | no | {\`code, security\`} — review command strings with effort embedded (e.g. \`"/code-review high"\`, \`"/security-review"\`) |` |
| 文書 | `docs/ADOPTION.md:646` | `- [ ] \`reviewCommands\` + \`reportPath\` set; report dir exists` |
| 文書 | `docs/ADOPTION.ja.md:326` | `| \`reviewCommands\` | object | いいえ | {\`code, security\`} — effort 込みの review コマンド文字列（例 \`"/code-review high"\`, \`"/security-review"\`） |` |
| 文書 | `docs/ADOPTION.ja.md:599` | `- [ ] \`reviewCommands\` + \`reportPath\` を設定。レポートのディレクトリが存在` |
| 定義 | `skills/init/SKILL.md:166` | `- \`reviewCommands\`: {\`code:"/code-review high", security:"/security-review"\`}.` |
| テスト | `tests/test_v016_contracts.py:63` | `    ("reviewCommands", "REVIEW_COMMANDS_JSON", "{}", False),` |

`.claude-plugin/plugin.json` には `reviewCommands` の出現はありません。

## 2. `CODE_REVIEW_STATE`

出現箇所は 7 行、実質的な値は 2 つです。

| file:line | verbatim |
|---|---|
| `skills/audit/SKILL.md:590` | `` `CODE_REVIEW_STATE=ran` even when findings are empty. If completion cannot be `` |
| `skills/audit/SKILL.md:591` | `` confirmed, do not invent findings and use `CODE_REVIEW_STATE=not-model-invocable`. `` |
| `skills/audit/SKILL.md:594` | `` block, bind `CODE_REVIEW_STATE=not-model-invocable` without WARN. Any other `` |
| `skills/audit/SKILL.md:814` | `- \`CODE_REVIEW_STATE=ran\` → \`✓ code-review: ran (findings folded into phase4)\`` |
| `skills/audit/SKILL.md:815` | `- \`CODE_REVIEW_STATE=not-model-invocable\` → \`💡 code-review: not run — the audit does not start /code-review itself yet ...\`` |
| `tests/test_v015_contracts.py:217` | `"If completion cannot be confirmed, do not invent findings and use \`CODE_REVIEW_STATE=not-model-invocable\`.",` |
| `tests/test_v015_contracts.py:218` | `"If execution reports the specific \`disable-model-invocation\` block, bind \`CODE_REVIEW_STATE=not-model-invocable\` without WARN.",` |

取りうる値:

- `ran`
- `not-model-invocable`

なお、`CODEX_REVIEW_STATE` には別の状態体系があります。`CODE_REVIEW_STATE` と混同されていません。

## 3. Phase 4 の `reviewCommands.code` 現行フロー

該当範囲は `skills/audit/SKILL.md:580-602` です。

> 3. Handle `reviewCommands.code` (e.g. `/code-review high`) on the working diff, then  
> `reviewCommands.security` (e.g. `/security-review`). Normalize any  
> `/security-audit ...` request to `/security-review`. In an interactive session,  
> before the gate and only once, use AskUserQuestion to offer running the configured  
> `/code-review` command. If the user chooses it, end the turn with: “Run  
> `/code-review <configured effort>` and, when complete, enter ‘continue the audit’.” Write  
> the Phase-5 cross-turn state (`RUNID` and complete `EVIDENCE`) before ending.  
> On resume, fold only findings visibly present in the same conversation into  
> the Phase-4 findings collection, normalizing `high`→`HIGH` and `medium`→`MEDIUM`; fold findings only  
> when they are visibly present. If completion of the review is confirmed, bind  
> `CODE_REVIEW_STATE=ran` even when findings are empty. If completion cannot be  
> confirmed, do not invent findings and use `CODE_REVIEW_STATE=not-model-invocable`.  
> In a non-interactive session, do not offer the question and use that expected  
> state directly. If execution reports the specific `disable-model-invocation`  
> block, bind `CODE_REVIEW_STATE=not-model-invocable` without WARN. Any other  
> unavailable or failed `reviewCommands.code` command (including project-specific  
> commands) is handled as before: skip and WARN. Then run `reviewCommands.security`.  
> `/code-review ultra` is non-blocking — never wait on a cloud run; default to the  
> configured effort. When `CM_AVAILABLE` is true and a review exposes its output as  
> capturable text/JSON or a file, do not read that raw output into context: reduce it  
> to its FAIL/WARN findings with `ctx_execute`/`ctx_batch_execute` in the sandbox and  
> fold only the distilled findings into the verdict (non-blocking; degrade to reading  
> the output directly when context-mode is absent).

ターン跨ぎの共通規則は `skills/audit/SKILL.md:51-67` です。

> **Cross-turn checkpoint rule.** At every turn-ending pause, state `RUNID` and the complete,  
> unabridged `EVIDENCE` JSON. On resume, restore both exactly.  
> ...  
> | (g) waiting for `/code-review` | same as (f) |  
> | (h) Phase-4 evidence complete | (g) + phase4 |

要点は次のとおりです。

- 対話実行では AskUserQuestion を一度だけ表示する。
- ユーザーが選ぶとターンを終了する。
- 終了前に `RUNID` と完全な `EVIDENCE` を保持する。
- 再開時は、同じ会話内で目視できる所見だけを取り込む。
- 完了確認済みなら `ran`、確認できなければ `not-model-invocable`。
- 非対話実行では提案せず、`not-model-invocable`。
- `disable-model-invocation` の明示的失敗は警告なし。
- その他の失敗・未使用可能状態は WARN。
- `/code-review ultra` は待機せず、設定済み effort を既定値として扱う。
- context-mode があれば raw 出力ではなく要約所見だけを折り込む。

## 4. `reviewCommands.security` の実行と fold 経路

実行順は `code` → `security` です。

> `skills/audit/SKILL.md:580-582`  
> `3. Handle \`reviewCommands.code\` ... then \`reviewCommands.security\` ...`

> `skills/audit/SKILL.md:595-596`  
> `unavailable or failed \`reviewCommands.code\` command ... is handled as before: skip and WARN. Then run \`reviewCommands.security\`.`

Phase 4 の一般 fold 規則は次のとおりです。

> `skills/audit/SKILL.md:572`  
> `Fold its \`findings[]\` into the verdict: \`severity:"FAIL"\` -> NEEDS FIX, \`severity:"WARN"\` -> report only.`

結論として、所見の格納先は同じ Phase-4 findings collection ですが、実行制御は対称ではありません。

- `code`: AskUserQuestion、ターン終了、resume、`CODE_REVIEW_STATE`、特別な WARN 規則がある。
- `security`: 自律的に続けて実行するだけで、専用状態値やターン跨ぎ規則がない。
- したがって、fold の入れ物は共通ですが、方式 B の変更対象は主に `code` 側です。

## 5. 設定スキーマと例

`skills/audit/references/config-schema.md:20`:

> `| \`reviewCommands\` | object | no | {\`code, security\`} review command strings (effort embedded, e.g. \`/code-review high\`) |`

`skills/audit/references/config-schema.md:36` の `codexReview` 定義全文:

> `| \`codexReview\` | object | no | {\`enabled:bool=true, required:bool=false, bin:string="codex", model?:string, timeoutMs?:number=300000\`} — key-gated Phase-0 \`codex\` preflight: it runs only when this key exists, \`enabled\` is not false, and the tool is installed. An absent key reports \`not-configured\` and never runs the tool. \`enabled\` must be a JSON boolean; \`enabled:false\` takes priority and reports \`disabled-by-config\` with the default name. Otherwise a non-boolean \`enabled\`, a non-object key (including \`null\`), or a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable \`bin\` reports \`invalid-config\` (the tool is not run and a ⚠ status line is printed). When this key exists, \`required:true\` makes a non-completed review REFUSED; it cannot conflict with an absent key. |`

`reviewCommands` には `required` キーはありません。`required` と fail-closed の記述は `codexReview` にだけあります。

例:

> `docs/examples/doc-audit.example.json:9`  
> `"codexReview": { "enabled": true, "bin": "codex", "required": false },`

> `docs/examples/doc-audit.example.json:19`  
> `"reviewCommands": { "code": "/code-review high", "security": "/security-review" },`

## 6. scripts 側の enforce と EVIDENCE

`skills/audit/scripts/` に対して `CODE_REVIEW_STATE` と `reviewCommands` を検索した結果は空です。

つまり、現状は:

- `reviewCommands` の読み取り: `SKILL.md` の sealed getter 契約だけ。
- `CODE_REVIEW_STATE` の設定: `SKILL.md` の会話オーケストレーションだけ。
- scripts 側で `/code-review` の自律実行可否を強制する処理: なし。

EVIDENCE の Phase 4 は一般的な `findings` と `codexReview` を受け取ります。

> `skills/audit/scripts/write-evidence.py:49-50`  
> `elif name == "phase4" and not isinstance(value.get("findings", []), list):`  
> `    raise ValueError("phase4.findings must be an array")`

> `skills/audit/scripts/decide-verdict.py:320-324`  
> `codex = phase4.get("codexReview")`  
> `if not isinstance(codex, dict):`  
> `    raise Refused("codexReview evidence invalid: codexReview must be an object")`  
> `if "state" not in codex or "promptVariant" not in codex or "carryForwardSha" not in codex:`  
> `    raise Refused("codexReview evidence invalid: required keys are missing")`

`phase4.json` に `codeReview` や `CODE_REVIEW_STATE` 専用キーはありません。code-review の所見は通常の `findings[]` に折り込まれる想定です。

## 7. 関連テスト

| test | 固定している内容 |
|---|---|
| `tests/test_v015_contracts.py:214` `test_code_review_behavior_is_unchanged_by_wording_update` | `not-model-invocable`、`disable-model-invocation` 時の WARN なし、非対話時の状態、AskUserQuestion 一度だけ、Phase 5 の期待表示 |
| `tests/test_v015_contracts.py:197` `test_v0151_behavior_change_paragraphs_are_exact` | README ではなく `docs/ADOPTION.md` / `.ja.md` の「自律起動可能という上流文言に修正したが、挙動は不変、#66 で追跡」という段落 |
| `tests/test_v016_contracts.py:112` `test_ct_1_registry_equivalence` | 設定 getter の登録として `reviewCommands → REVIEW_COMMANDS_JSON → {}` を固定 |
| `tests/test_v016_contracts.py:872` `test_ct_5b_complete_phase4_eligibility_table` | `codexReview` の Phase 4 状態と mode/promptVariant の組合せ。`CODE_REVIEW_STATE` ではない |
| `tests/test_v016_contracts.py:921` `test_ct_5_gate_records_and_measures_four_key_flips` | `codex-review` 所見の Phase-4 history、HIGH 所見、flip 計測 |
| `tests/test_v016_docs_contracts.py:14` `test_ct_7_required_tokens_are_present_in_each_named_document` | README/ADOPTION を含む必須語を固定するが、code-review 文言は必須語に含まれない |
| `tests/test_release_handoff.py:34` | `#66 remains open for autonomous /code-review invocation.` をリリース引き継ぎ文言として固定 |

`test_v016_docs_contracts.py` は README/ADOPTION の code-review 文言を固定していません。文言を直接固定しているのは `test_v015_contracts.py:test_v0151_behavior_change_paragraphs_are_exact` です。

今回、テスト実行は行っていません。したがってテスト失敗はありません。

## 8. README / ADOPTION の残存文言

### README.md

見出しは `README.md:1` のみです。

> `README.md:9-10`  
> `delegates the project's existing doc checks, runs \`/security-review\`,`  
> `and offers \`/code-review\` for the user to run (the audit does not start it on its own yet; autonomous invocation is tracked in #66)`

> `README.md:14-15`  
> `The audit does not start \`/code-review\` itself: autonomous runs skip it as expected, while interactive`  
> `runs offer the user one chance to run the configured \`/code-review\` before continuing.`

> `README.md:26`  
> ``- [`/security-review`](https://code.claude.com/docs) — Claude Code built-in; `/code-review` is offered to the user but is not started by the audit yet (tracked in #66).``

### docs/ADOPTION.md

主な節と該当行:

- §1 `Mental model`: `56`
- §2 `Prerequisites`: `80`, `82`
- §2 の context-mode 説明: `101-104`
- §2 の Codex 説明: `124-125`
- v0.15.1 変更記録: `290`
- §5 config reference: `354`
- §10 Hard-won gotchas: `581-582`
- §12 Troubleshooting: `631`
- §13 checklist: `646`

代表的な残存文言:

> `docs/ADOPTION.md:56`  
> `offer \`/code-review\` once in interactive runs because the audit does not start it itself yet (#66).`

> `docs/ADOPTION.md:80`  
> `` `/security-review` runs in the audit, while `/code-review` is offered to the user (not started by the audit yet; #66) ``

> `docs/ADOPTION.md:290`  
> `The \`/code-review\` wording now reflects the upstream capability for Claude to invoke it autonomously; audit behavior is unchanged, and autonomous invocation remains tracked in #66.`

### docs/ADOPTION.ja.md

対応する節と該当行:

- §1 `メンタルモデル`: `55`
- §2 `前提`: `79`, `81`
- context-mode 説明: `95`
- Codex 説明: `109`
- v0.15.1 変更記録: `263`
- §5 config reference: `326`
- §10 実運用で得た落とし穴: `538-540`
- §12 トラブルシューティング: `584`
- §13 checklist: `599`

代表的な残存文言:

> `docs/ADOPTION.ja.md:55`  
> `監査自身がまだ起動しない \`/code-review\` は対話実行で一度だけ提案（#66）。`

> `docs/ADOPTION.ja.md:95`  
> `自律実行では監査自身が \`/code-review\` を起動しないため想定どおり省略する（自律起動は #66 で追跡）。対話実行では一度だけ実行を確認し、完了後に監査を続行できる。`

> `docs/ADOPTION.ja.md:263`  
> `` `/code-review` の記述を、Claude が自律起動できるという上流の現状に合わせて是正したが、監査の挙動は不変で、自律起動は #66 で追跡する。``

リテラルの `not-model-invocable` は README/ADOPTION にはありません。`user-invocation-only` もありません。ただし、「ユーザーに提案」「監査自身は起動しない」「interactive runs offer」という同義の残存記述はあります。

## 9. Phase 5 と verdict 出力

Phase 5 は、Phase-4 findings を gate に渡し、`FAIL/HIGH/CRITICAL` を blocking として扱います。

> `skills/audit/SKILL.md:657-663`  
> `collect every delegated-layer and review finding as`  
> ``{"findings":[...],"codexReview":{...}}``  
> `Use each finding's own severity verbatim (\`FAIL\`/\`HIGH\`/\`CRITICAL\` = blocking; \`WARN\`/\`MEDIUM\`/\`LOW\`/\`INFO\` = non-blocking);`  
> `map review high→\`HIGH\`, medium→\`MEDIUM\`.`

Phase 5 の code-review 表示:

> `skills/audit/SKILL.md:813-816`  
> `**code-review status line** — include exactly one immediately after the codex-review line:`  
> `- \`CODE_REVIEW_STATE=ran\` → \`✓ code-review: ran (findings folded into phase4)\``  
> `- \`CODE_REVIEW_STATE=not-model-invocable\` → \`💡 code-review: not run — the audit does not start /code-review itself yet ... (expected)\``  
> `- Any other unavailable or failed command → the existing ⚠ WARN status for the unavailable review command.`

最終テンプレートには code-review 専用 placeholder はありません。共通 placeholder のみです。

> `skills/audit/SKILL.md:710-718`  
> `{{GATE_VERDICT}}`、`{{GATE_REASON}}`、`{{GATE_COUNTS}}`、`{{GATE_HISTORY_STATUS}}`、`{{GATE_WARNINGS}}`、`{{GATE_SIBLING_SCAN}}`、`{{GATE_ANCHOR_WRITTEN}}`、`{{GATE_REPORT_DATE}}`

判定スクリプトは Phase-4 の全 findings を判定します。

> `skills/audit/scripts/decide-verdict.py:1147-1152`  
> `has_fail = any(record["verdict"] == "FAIL" for record in verdicts.values())`  
> `if phase4 is not None:`  
> `    has_fail = findings_fail(phase4) or has_fail`  
> `verdict = "NEEDS_FIX" if has_fail else "CONSISTENT"`

なお、code-review 固有の `not-model-invocable` は WARN なしで期待表示されますが、実際に所見が `phase4.findings[]` に入れば通常の blocking 規則に従います。

## PLAN が触る必要がありそうなファイル

| ファイル | 推定変更規模 | 理由 |
|---|---:|---|
| `skills/audit/SKILL.md` | 大 | Phase 4 の AskUserQuestion、ターン終了、resume、`CODE_REVIEW_STATE`、fold、Phase 5 表示を方式 B に変更 |
| `README.md` | 小 | 「ユーザーに提案」「自律実行しない」の説明を更新 |
| `docs/ADOPTION.md` | 中 | §1/§2/§5/§10/§12/§13 と v0.15.1 記録の更新 |
| `docs/ADOPTION.ja.md` | 中 | 英語版と同じ契約説明の日本語更新 |
| `tests/test_v015_contracts.py` | 中 | 現行の not-model-invocable、AskUserQuestion、#66 文言固定を新契約へ更新 |
| `tests/test_v016_docs_contracts.py` | 小〜中 | code-review 文言を契約として固定する場合に追加 |
| `tests/test_v016_contracts.py` | 小〜中 | Phase-4 evidence/finding の自律 code-review 経路を追加検証する場合 |
| `skills/audit/references/config-schema.md` | 小 | `reviewCommands.code` の意味や単一窓口契約を明文化する場合。キー構造自体の変更は不要そう |
| `docs/examples/doc-audit.example.json` | 小または変更不要 | 既存の `"reviewCommands": {"code": ...}` は方式 B と整合している |
| `tests/test_release_handoff.py` | 小 | `#66 remains open` の固定文言を完了状態へ更新する場合 |