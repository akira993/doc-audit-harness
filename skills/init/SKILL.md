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

## Step 2 — draft the config
Build a `doc-audit.json` draft from the inventory:
- `anchorPath`: `.claude/state/last-doc-audit.json`. `diffGlobs`: `suggestedDiffGlobs`.
  `docGlobs`: inventory `docGlobs`. `indexFiles`: inventory `indexFiles`.
- `frontMatterFields`: include `suggestedFrontMatterFields` ONLY if the user wants
  front-matter enforced (ask). `boundaryCommand`: `boundaryCommandGuess` if present.
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

## Guardrails
Additive only (new files). Never edit/rewrite existing docs or ADRs. MCP optional.
`--scaffold` (project-tailored layer skills) is NOT implemented here — it is Plan 4;
if asked, say so.
