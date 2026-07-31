---
name: init
description: Bootstrap docaudit for a repo that has no .claude/doc-audit.json yet. Use when the user asks to set up docaudit, initialize the doc-audit harness, or run docaudit on a repo that lacks /check-docs / /review-docs / doc-lint. Inventories the repo, proposes a doc-audit.json config for approval, writes it, and points to the first audit. Generative (creates new config only); never edits existing docs.
argument-hint: "[--scaffold]"
---

# docaudit:init — bootstrap a repo's doc-audit adapter

Creates `${CLAUDE_PROJECT_DIR}/.claude/doc-audit.json` for a repo that has none.
Generative but additive: you may CREATE new config/state files; you must NOT edit
or rewrite any existing doc. Always propose the draft and get explicit user approval
before writing. `SD="${CLAUDE_SKILL_DIR%/init}/audit"` (the audit skill dir holding
the shared scripts).

If `.claude/doc-audit.json` already exists, stop and tell the user (offer `/docaudit:audit` instead) — do not overwrite it.

## Step 1 — inventory (deterministic)
Run: `python3 "$SD/scripts/inventory.py" --repo-root "$CLAUDE_PROJECT_DIR"`.
Parse the JSON: docDirs, docGlobs, frontMatter, suggestedFrontMatterFields, codeDirs,
suggestedDiffGlobs, existingDocTools, boundaryCommandGuess, indexFiles, mentions.
(Optional enrichment: if `markdown-query`/CocoIndex/Serena are available you may use
them to refine the impactMap couplings — they are NOT required; inventory.py alone
suffices. CocoIndex needs `sentence_transformers`; skip it if unavailable.)
Also run `command -v mdq`: if present, this repo can use conditional-force indexing —
propose an `indexing` block in Step 2. Likewise, check whether the `ctx_*` MCP tools
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
whether `.cocoindex_code/` already exists in the repo (two different proposals in Step 2
depending on the answer).

## Step 2 — draft the config
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
  `enabled:false` opts out. If `ax` was NOT detected, OMIT the key — the audit already runs
  without external-URL corroboration by default (conditional-force, like `indexing`).
- `codexReview`: if `codex` was detected in Step 1, propose
  `"codexReview": { "enabled": true, "bin": "codex" }` so Phase 4 runs a fourth, adversarial
  Codex review after `/code-review`/`/security-review`; tell the user its `critical`/`high`
  findings CAN affect the verdict (unlike `webExtract`/`indexing`/`contextMode`, which are
  purely advisory) and `enabled:false` opts out. If `codex` was NOT detected, OMIT the key —
  the audit already runs without the Codex review by default (conditional-force, like
  `indexing`).
- `symbolGraph`: if `codegraph` was detected in Step 1, propose
  `"symbolGraph": { "enabled": true, "tool": "codegraph", "bin": "codegraph" }` so
  doc-impact-verifier can corroborate a changed file's own-symbol claims via read-only
  `codegraph impact`/`node`; tell the user `enabled:false` opts out. This seam is purely
  advisory (never affects the verdict), like `webExtract`. If `codegraph` was NOT detected,
  OMIT the key.
- `docGraph`: if `graphify` was detected in Step 1, propose
  `"docGraph": { "enabled": true, "tool": "graphify", "bin": "graphify" }` so Phase 2 can
  supplement `mapGapCandidates` with graph-adjacency candidates; tell the user
  `enabled:false` opts out. If `graphify-out/` was NOT already gitignored (Step 1's
  `git check-ignore` check), also propose (with user approval) appending `graphify-out/` to
  `.gitignore` — additive, within the existing init discipline. If `graphify` was NOT
  detected, OMIT the key.
- `semanticSearch`: if `ccc` was detected in Step 1 AND `.cocoindex_code/` already exists,
  propose `"semanticSearch": { "enabled": true, "tool": "cocoindex", "bin": "ccc", "minScore":
  0.4 }` directly (Phase 2 can supplement `mapGapCandidates` with semantic-search
  candidates). If `ccc` was detected but `.cocoindex_code/` does NOT exist, propose running
  `ccc init && ccc index` with **explicit user approval whose copy discloses that `ccc init`
  will append `/.cocoindex_code/` to `.gitignore`** — the audit itself never runs `ccc init`
  on its own; only after approval and successful execution does this flow propose the
  `semanticSearch` block. If `ccc` was NOT detected at all, OMIT the key. This seam is purely
  advisory (never affects the verdict), like `webExtract`/`docGraph`.
- `reviewCommands`: `{code:"/code-review high", security:"/security-review"}`.
  `reportPath`: `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md` (or repo-root if no docs/logs).
  `maxImpactedDocs`: 60.
- `docAuditCommands`: if `existingDocTools` found project doc commands, wire them
  (`{format,existence,semantic}`) to those; OTHERWISE **omit the key** so the audit
  falls back to the built-in generic layers (Plan 2).
- `impactMap`: propose a STARTER array from `mentions` (for each code dir/key file with
  mentions, `{changed: "<dir>/**" or "<file>", impacts: [the mentioned docs], note: "auto: from inventory mentions"}`).
  Tell the user this is a heuristic starter to PRUNE/EDIT; the engine's heuristic +
  `mapGapCandidates` will refine it over time. (Note: inventory samples the primary doc
  tree, not hidden dirs like `.claude/`, so add any `.claude/**` couplings by hand if wanted.)

## Step 3 — present for approval (MANDATORY)
Show the full draft JSON and a one-line rationale per key. Ask the user to approve or
edit. Do NOT write anything until approved (spec §8.3). Never invent project facts not
grounded in the inventory.

## Step 4 — write + next steps
On approval, write `.claude/doc-audit.json` (create `.claude/` if needed). Then tell the
user: review the impactMap, commit the config, and run `/docaudit:audit --full` to
produce the first CONSISTENT verdict + anchor (that audit, not init, writes the anchor).
If `mdq` is installed, no manual index step is needed — the first `/docaudit:audit`
Phase 0 builds the mdq index under `.mdq/` automatically (add `.mdq/` to `.gitignore`).

## Step 5 — --scaffold (opt-in; only when invoked with --scaffold)
Generate project-tailored layer skill skeletons so this repo owns richer checks than
the generic baseline. Do this AFTER Step 3 approval and BEFORE the Step 4 config write:
1. Preview then create: `python3 "$SD/scripts/scaffold.py" --repo-root "$CLAUDE_PROJECT_DIR" --prefix docaudit --dry-run`,
   then without `--dry-run`. It writes `.claude/skills/docaudit-{format,existence,semantic}/SKILL.md`
   skeletons and NEVER overwrites existing files. Parse `{created, skipped, skillNames}`;
   report skipped files to the user.
2. Set the config's `docAuditCommands` to `skillNames` (e.g.
   `{format:"docaudit-format", existence:"docaudit-existence", semantic:"docaudit-semantic"}`)
   so the audit delegates to the tailored skills instead of the generic fallback. Then
   write the config (Step 4).
3. Tailor each generated skeleton to THIS repo's real {layer} rules using the
   `skill-creator` / `skill-creator-max` and `superpowers:writing-skills` skills: replace
   each skeleton's "Checks (CUSTOMIZE — TODO)" section with concrete project checks,
   optimize the `description` for triggering, and run the trigger tests. Keep every
   generated skill report-only (propose fixes; never edit docs).
4. Tell the user to review + commit the new skills + config, then run `/docaudit:audit --full`.
Additive only: scaffold.py creates NEW skill files; it never edits existing docs/ADRs.

## Guardrails
Additive only (new files). Never edit/rewrite existing docs or ADRs. MCP optional.
`--scaffold` (Step 5) generates project-tailored layer skill skeletons via
`scripts/scaffold.py` (additive; never overwrites) and tailors them with
skill-creator-max / writing-skills.
