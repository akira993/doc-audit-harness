---
name: init
description: Bootstrap docaudit for a repo, or add and refresh its optional local documentation harness. Use when the user asks to set up docaudit, initialize the doc-audit harness, or run docaudit on a repo that lacks /check-docs / /review-docs / doc-lint. Inventories the repo, proposes a doc-audit.json config for approval, writes it, and points to the first audit. Generative and additive by default; existing-tool adjustment requires a separate approved diff.
argument-hint: "[--scaffold] [--harness] [--refresh] [--reask] [--import-audit-scope]"
---

# docaudit:init — bootstrap a repo's doc-audit adapter

Creates `${CLAUDE_PROJECT_DIR}/.claude/doc-audit.json` for a repo that has none.
Generative but additive: you may CREATE new config/state files; you must NOT edit
or rewrite any existing doc. Always propose the draft and get explicit user approval
before writing. `SD="${CLAUDE_SKILL_DIR%/init}/audit"` (the audit skill dir holding
the shared scripts).

If `.claude/doc-audit.json` already exists, normally stop and tell the user (offer
`/docaudit:audit` instead) — do not overwrite it. **Exceptions:** with `--harness`, continue through
Step 1 and change only `harness` and, when required, `docAuditCommands`; with
`--import-audit-scope`, follow only the import flow below. Preserve every other config key.
`--refresh` is valid only with `--harness` and is delegated to
`scaffold.py --harness --refresh`. `--reask` forces the harness choice even when `harness` is
already configured. Without `--reask`, never ask again for an existing `harness` key. If its
state is `installed`, `--harness` may create missing generated files; for any other configured
state, explain the state and require `--reask` before changing the decision.

With `--import-audit-scope`, an existing config is permitted. Bind `AUDIT_SCOPE_PATH` from config `auditScope.path`, defaulting to `.claude/audit-scope.json`, then run `AUDIT_SCOPE_CHECK="$(python3 "$SD/scripts/import-audit-scope.py" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --scope "$AUDIT_SCOPE_PATH" --check --json)"`. Show `diff.missing`, `diff.extra`, `translated`, `skippedNoImpact`, `configSha`, and `scopeSha`, then ask with AskUserQuestion. Only after approval bind `CONFIG_SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["configSha"])' "$AUDIT_SCOPE_CHECK")"` and `SCOPE_SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["scopeSha"])' "$AUDIT_SCOPE_CHECK")"`, then run `python3 "$SD/scripts/import-audit-scope.py" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --scope "$AUDIT_SCOPE_PATH" --write --expect-config-sha "$CONFIG_SHA" --expect-scope-sha "$SCOPE_SHA"`. Do not write without approval.

## Step 1 — inventory (deterministic)
Run: `python3 "$SD/scripts/inventory.py" --repo-root "$CLAUDE_PROJECT_DIR"`.
Parse the JSON: docDirs, docGlobs, frontMatter, suggestedFrontMatterFields, codeDirs,
suggestedDiffGlobs, existingDocTools, existingDocToolCandidates, boundaryCommandGuess,
indexFiles, mentions. `existingDocToolCandidates` contains display-only `{kind,path,name}`
candidates; inventory never wires one automatically.
(Optional enrichment: if `markdown-query`/CocoIndex/Serena are available you may use
them to refine the impactMap couplings — they are NOT required; inventory.py alone
suffices. CocoIndex needs `sentence_transformers`; skip it if unavailable.)
Also run `command -v mdq`: if present, this repo can use indexing (on by default when
`mdq` is installed; `enabled:false` opts out) — propose an `indexing` block in Step 2.
Likewise, check whether the `ctx_*` MCP tools
(context-mode) are available to you in this session — judge purely by tool availability,
NOT by globbing `~/.claude` plugin paths (never bake machine-specific globals into the
config). If available, propose a `contextMode` block in Step 2. Also run `command -v ax`:
if present, doc-impact-verifier can corroborate external-URL-dependent doc claims (read-
only) — propose a `webExtract` block in Step 2. Also run `command -v codex`: if present,
Phase 4 can run a fourth, adversarial Codex review whose `critical`/`high` findings CAN
affect the verdict — propose a `codexReview` block in Step 2. Also run `command -v
codegraph`: if present, doc-impact-verifier can corroborate a changed file's own-symbol
claims (read-only) — propose a `symbolGraph` block in Step 2. Also run `command -v
graphify`: if present, Phase 2 can supplement `mapGapCandidates` with graph-adjacency
candidates — propose a `docGraph` block in Step 2; also check
`(cd "$CLAUDE_PROJECT_DIR" && git check-ignore -q graphify-out)` to see whether
`graphify-out/` is already gitignored. Also run `command -v ccc`: if present, Phase 2 can
additionally supplement `mapGapCandidates` with semantic-search candidates — check
whether `.cocoindex_code/settings.yml` already exists in the repo (two different proposals in Step 2
depending on the answer).

### Step 1.5 — harness choice (MANDATORY once)

Immediately after inventory, read `harness` from an existing config when present. If the key is
absent, or `--reask` was supplied, call `AskUserQuestion` exactly once for the harness choice.
If questions are unavailable (non-interactive), do not ask, generate, edit, or write config;
say 「`/docaudit:init --harness` を実行してください」 and stop this flow.

When `existingDocToolCandidates` is empty, ask with exactly these two choices:

- **「ハーネス構造（`/check-docs` + `doc-lint` + 決定的エンジン）を一緒に入れる（推奨）」**
- **「入れない」**

When candidates exist, list every candidate's `kind`, `path`, and `name`, construct and show a
concrete proposed `{format,existence,semantic}` mapping using only those candidate names, and ask
with at most these four choices:

- **「既存に統合」** — use the displayed mapping as `docAuditCommands`.
- **「既存を調整」** — propose compatibility changes and use the displayed mapping.
- **「そのまま」** — retain existing files and any already configured commands.
- **「新規に入れる」** — install the three-file harness instead.

Never set `integrated` unless all three `docAuditCommands` keys are written in the same config
update. For `adjusted`, first prepare a diff that makes the selected existing tool emit docaudit-
compatible `SUMMARY` and `VERDICT` lines (a semantic command must also emit strict
`path:line - FAIL|WARN - message` finding lines followed by a final standalone model `VERDICT`
line), show that diff, and obtain explicit approval before editing the existing file. If approval
is not given, do not edit and do not record `adjusted`.
After an approved adjustment, wire all three command keys in the same config update. Adjustment
is the only path here that may edit an existing tool; it remains outside `scaffold.py`.

Map the accepted answer to exactly one state:

| answer | state | required action |
|---|---|---|
| 入れる／新規に入れる | `installed` | run `python3 "$SD/scripts/scaffold.py" --repo-root "$CLAUDE_PROJECT_DIR" --harness [--refresh]`; parse its `docAuditCommands` |
| 入れない | `declined` | generate nothing and omit a new `docAuditCommands` value |
| 既存に統合 | `integrated` | write the displayed existing-tool mapping |
| 既存を調整 | `adjusted` | only after the approved diff is applied, write its mapping |
| そのまま | `existing-untouched` | do not edit or auto-wire the candidates |

Read `<version>` from `$SD/../../.claude-plugin/plugin.json` and make the decision object
`{"state":"…","decidedAt":"<current ISO-8601 timestamp>","engineVersion":"<version>"}`.
For an existing config, record the decision with one atomic invocation, adding the second
`--set` only for a state that requires wiring:

`python3 "$SD/scripts/set-config-key.py" --config "$CFG" --set 'harness={"state":"…","decidedAt":"…","engineVersion":"<version>"}' [--set 'docAuditCommands={"format":"…","existence":"…","semantic":"…"}']`

Here `CFG="$CLAUDE_PROJECT_DIR/.claude/doc-audit.json"`. For a new config, do not call
`set-config-key.py`; include the accepted `harness` object and any required `docAuditCommands`
directly in the Step-2 draft so Step 4 creates the complete approved JSON once. For `installed`,
the scaffold return value must wire existence=`/check-docs --only existence`,
format=`/check-docs --only format`, and semantic=`doc-lint`. Report every `created`, `skipped`,
and `skipReasons` entry. If an existing config was the `--harness` exception, stop after this
harness-only update; do not rebuild or rewrite the rest of the adapter.

## Step 2 — draft the config

For a newly drafted config, propose `"regressionRecheck": {"enabled": true}` so a prior FAIL can
be rechecked even when its document content is unchanged. This is a proposal for the new draft
only; never add or change this key in an existing config automatically.
Build a `doc-audit.json` draft from the inventory:
- `anchorPath`: `.claude/state/last-doc-audit.json`. `diffGlobs`: `suggestedDiffGlobs`.
  `docGlobs`: inventory `docGlobs`. `indexFiles`: inventory `indexFiles`.
- `frontMatterFields`: include `suggestedFrontMatterFields` ONLY if the user wants
  front-matter enforced (ask). `boundaryCommand`: `boundaryCommandGuess` if present.
- `indexing`: if `mdq` was detected in Step 1, propose
  `"indexing": { "enabled": true, "tool": "mdq", "bin": "mdq" }` so Phase 0 indexes the whole repo and
  Phase 3 reads chunks (big token savings); tell the user `enabled:false` opts out and
  `roots` narrows the scope. If `mdq` was NOT detected, OMIT the key — the audit already
  degrades to grep by default.
- `contextMode`: if the `ctx_*` tools (context-mode) were detected in Step 1, propose
  `"contextMode": { "enabled": true }` so the audit processes large outputs (git diff,
  reviews) in context-mode's sandbox (token savings on big audits); tell the user
  `enabled:false` opts out. If context-mode was NOT detected, OMIT the key — the audit
  already runs the normal full-read path by default (conditional-force, like `indexing`).
- `webExtract`: if `ax` was detected in Step 1, propose
  `"webExtract": { "enabled": true, "tool": "ax", "bin": "ax" }` so doc-impact-verifier can
  corroborate a doc's external-URL-dependent claims (read-only, GET-only); tell the user
  `enabled:false` opts out. If `ax` was NOT detected, OMIT the key; absent key ⇒ the audit reports
  `not-configured` and never runs the tool.
- `codexReview`: if `codex` was detected in Step 1, propose
  `"codexReview": { "enabled": true, "bin": "codex" }` so Phase 4 runs a fourth, adversarial
  Codex review after `/code-review`/`/security-review`; tell the user its `critical`/`high`
  findings CAN affect the verdict (unlike `webExtract`/`indexing`/`contextMode`, which are
  purely advisory) and `enabled:false` opts out. If `codex` was NOT detected, OMIT the key;
  absent key ⇒ the audit reports `not-configured` and never runs the tool.
- `symbolGraph`: if `codegraph` was detected in Step 1, propose
  `"symbolGraph": { "enabled": true, "tool": "codegraph", "bin": "codegraph" }` so
  doc-impact-verifier can corroborate a changed file's own-symbol claims via read-only
  `codegraph impact`/`node`; tell the user `enabled:false` opts out. This seam is purely
  advisory (never affects the verdict), like `webExtract`. If `codegraph` was NOT detected,
  OMIT the key; absent key ⇒ the audit reports `not-configured` and never runs the tool.
- `docGraph`: if `graphify` was detected in Step 1, propose
  `"docGraph": { "enabled": true, "tool": "graphify", "bin": "graphify" }` so Phase 2 can
  supplement `mapGapCandidates` with graph-adjacency candidates; tell the user
  `enabled:false` opts out. If `graphify-out/` was NOT already gitignored (Step 1's
  `git check-ignore` check), also propose (with user approval) appending `graphify-out/` to
  `.gitignore` — additive, within the existing init discipline. If `graphify` was NOT
  detected, OMIT the key; absent key ⇒ the audit reports `not-configured` and never runs the tool.
- `semanticSearch`: if `ccc` was detected in Step 1 AND `.cocoindex_code/settings.yml` already exists,
  propose `"semanticSearch": { "enabled": true, "tool": "cocoindex", "bin": "ccc", "minScore":
  0.4 }` directly (Phase 2 can supplement `mapGapCandidates` with semantic-search
  candidates). If `ccc` was detected but `.cocoindex_code/settings.yml` does NOT exist, the audit reports
  `not-initialized`; propose running
  `ccc init && ccc index` with **explicit user approval whose copy discloses that `ccc init`
  will append `/.cocoindex_code/` to `.gitignore`** — the audit itself never runs `ccc init`
  on its own; only after approval and successful execution does this flow propose the
  `semanticSearch` block. If `ccc` was NOT detected at all, OMIT the key. This seam is purely
  advisory (never affects the verdict), like `webExtract`/`docGraph`; absent key ⇒ the audit reports
  `not-configured` and never runs the tool.
- `reviewCommands`: `{code:"/code-review high", security:"/security-review"}`.
  `reportPath`: `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md` (or repo-root if no docs/logs).
  `maxImpactedDocs`: 60.
- `docAuditCommands`: if `existingDocTools` found project doc commands, wire them
  (`{format,existence,semantic}`) to those only when Step 1.5 selected `integrated` or
  `adjusted`; when Step 1.5 selected `installed`, use `scaffold.py --harness`'s return value.
  For `declined` or `existing-untouched`, preserve an existing value but do not invent a new one;
  otherwise **omit the key** so the audit falls back to the built-in generic layers (Plan 2).
- `impactMap`: when `audit-scope.json` exists, first run `import-audit-scope.py --check --json --doc-glob <each draft docGlobs value>` and use its `translated` output as the STARTER; this takes priority over `mentions`. Otherwise propose a STARTER array from `mentions` (for each code dir/key file with
  mentions, `{changed: "<dir>/**" or "<file>", impacts: [the mentioned docs], note: "auto: from inventory mentions"}`).
  Tell the user this is a heuristic starter to PRUNE/EDIT; the engine's heuristic +
  `mapGapCandidates` will refine it over time. (Note: inventory samples the primary doc
  tree, not hidden dirs like `.claude/`, so add any `.claude/**` couplings by hand if wanted.)

## Step 3 — present for approval (MANDATORY)
Show the full draft JSON and a one-line rationale per key. Ask the user to approve or
edit. Do NOT write anything until approved (spec §8.3). Never invent project facts not
grounded in the inventory.

## Step 4 — write + next steps
When scope was used, use the Write tool to write the approved draft without auto entries to `DRAFT_CONFIG_PATH` outside the repo (for example under `$TMPDIR`). Bind `DRAFT_SHA="$(python3 -c 'import hashlib,sys; print("sha256:"+hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$DRAFT_CONFIG_PATH")"` and bind `SCOPE_SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["scopeSha"])' "$AUDIT_SCOPE_CHECK")"` from the check output. Create the final config once with `python3 "$SD/scripts/import-audit-scope.py" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --scope "$AUDIT_SCOPE_PATH" --write --base-config - --expect-base-config-sha "$DRAFT_SHA" --expect-scope-sha "$SCOPE_SHA" < "$DRAFT_CONFIG_PATH"`. Otherwise, on approval write `.claude/doc-audit.json` (create `.claude/` if needed). Then tell the
user: review the impactMap and commit the config. When `harness.state` is `installed`, explicitly
list and tell the user to commit all three generated files — `.claude/commands/check-docs.md`,
`.claude/skills/doc-lint/SKILL.md`, and `scripts/check-docs.py` — together with the config before
running `/docaudit:audit --full` to produce the first CONSISTENT verdict + anchor (that audit, not
init, writes the anchor).
If `mdq` is installed, no manual index step is needed — the first `/docaudit:audit`
Phase 0 builds the mdq index under `.mdq/` automatically (add `.mdq/` to `.gitignore`).
Do not generate a test skeleton for the harness. Suggest only one or two concrete lines, for
example: place a unittest/pytest subprocess check under `tests/`, or a Vitest command-execution
check beside the project's existing tests, covering both exit 0 and exit 1.

## Step 5 — --scaffold (opt-in; only when invoked with --scaffold)
Generate project-tailored layer skill skeletons so this repo owns richer checks than
the generic baseline. Do this AFTER Step 3 approval and BEFORE the Step 4 config write:
1. Preview then create: `python3 "$SD/scripts/scaffold.py" --repo-root "$CLAUDE_PROJECT_DIR" --prefix docaudit --dry-run`,
   then without `--dry-run`. It writes `.claude/skills/docaudit-{format,existence,semantic}/SKILL.md`
   skeletons and NEVER overwrites existing files. Parse `{created, skipped, skillNames}`;
   report skipped files to the user.
2. Set the config's `docAuditCommands` to `skillNames` (e.g.
   `{format:"docaudit-format", existence:"docaudit-existence", semantic:"docaudit-semantic"}`),
   except when combined with `--harness`: harness wins for `format`/`existence`, while
   `docaudit-semantic` wins for `semantic`
   so the audit delegates to the tailored skills instead of the generic fallback. Then
   write the config (Step 4).
3. Tailor each generated skeleton to THIS repo's real {layer} rules using the
   `skill-creator` / `skill-creator-max` and `superpowers:writing-skills` skills: replace
   each skeleton's "Checks (CUSTOMIZE — TODO)" section with concrete project checks,
   optimize the `description` for triggering, and run the trigger tests. Keep every
   generated skill report-only (propose fixes; never edit docs).
4. Tell the user to review + commit the new skills + config, then run `/docaudit:audit --full`.
Additive only: scaffold.py creates NEW skill files; it never edits existing docs/ADRs. Its
`--refresh` exception overwrites only generated harness files whose stamp and normalized body
still match a shipped template; modified or unstamped files are skipped with a reason.

## Guardrails
Additive only (new files), except for an explicitly approved existing-tool adjustment and the
safe `--refresh` rule above. Never edit/rewrite existing docs or ADRs. MCP optional.
`--scaffold` (Step 5) generates project-tailored layer skill skeletons via
`scripts/scaffold.py` (additive; never overwrites) and tailors them with
skill-creator-max / writing-skills.
