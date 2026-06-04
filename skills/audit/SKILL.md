---
name: audit
description: Change-driven documentation audit. Use when the user asks to audit docs since the last audit, check documentation consistency after code/config changes, run a full doc consistency sweep, or verify nothing is stale before a release. Diffs since the anchor, maps changed files to impacted docs, delegates the project's doc checks, drives /code-review + /security-review, and emits one CONSISTENT/NEEDS FIX verdict. Report-only.
argument-hint: "[--full]"
---

# docaudit:audit — change-driven documentation audit

Report-only orchestrator. Reads the per-project adapter `${CLAUDE_PROJECT_DIR}/.claude/doc-audit.json`.
If that file is absent, tell the user to run `/docaudit:init` (Plan 3) or that this
repo has no adapter yet — do NOT invent project facts.

`SD="${CLAUDE_SKILL_DIR}"` ; `CFG="${CLAUDE_PROJECT_DIR}/.claude/doc-audit.json"`.
`--full` forces whole-corpus mode (ignores the anchor diff scope).

## Phase 1 — baseline + diff
Run: `bash "$SD/scripts/compute-baseline.sh" --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR"`.
Parse `{mode, baselineSha, changed[]}`. If `--full` was passed, treat mode as `full`.
If `mode=full` (no or invalid anchor), tell the user this is a full run and proceed
with the whole doc corpus as the change set context.

## Phase 2 — impact resolution
Pipe the `changed` list into:
`printf '%s\n' "${changed[@]}" | python3 "$SD/scripts/resolve-impact.py" --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR" --changed -`.
Parse `{impacted[], mapGapCandidates[], ssotRecheck[], truncated}`. If `truncated`,
`log()`/report the dropped count explicitly (never silent). Build a concise
`changeSummary` (per changed file: path + 1-line nature of change from `git diff --stat`/`git show`).

## Phase 3 — change-impact verification (Workflow fan-out)
Launch `Workflow({scriptPath: "$SD/references/workflow-template.js", args: {repoRoot: CLAUDE_PROJECT_DIR, changeSummary, impacted}})`.
Collect per-doc `{path, verdict, rationale, suggestion}`. (Built-in `/code-review`
& `/security-review` CANNOT run inside a subagent/Workflow — they run in Phase 4.)

## Phase 4 — existing layers + reviews (main loop, sequential)
Global gate: run this phase's delegated checks **iff** `impacted` is non-empty OR
`ssotRecheck` is non-empty OR mode is `full`.
1. From config `docAuditCommands`, run `existence` then `semantic` then `format`
   (e.g. `/check-docs`, `doc-lint`, `/review-docs`) — whole-tree (no per-file arg).
2. If `boundaryCommand` set and gate open, run it.
3. Run `reviewCommands.code` (e.g. `/code-review high`) on the working diff, then
   `reviewCommands.security` (e.g. `/security-review`). Normalize any
   `/security-audit ...` request to `/security-review`. If a review command is not
   available in this environment, skip it and WARN (do not fail the run).
   `/code-review ultra` is non-blocking — never wait on a cloud run; default to the
   configured effort.

## Phase 5 — synthesize + anchor
Map every finding to PASS/WARN/FAIL (high severity = FAIL, medium = WARN). Verdict =
**NEEDS FIX if any FAIL**, else **CONSISTENT** (WARN never blocks).
Write a single report to `reportPath` (e.g. `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md`,
6-field front matter `category: logs`), containing: change set, impacted docs +
per-doc verdicts, delegated-check results, review summaries, `mapGapCandidates`,
and the roll-up verdict. Do NOT edit any existing doc and do NOT auto-edit
`docs/README.md` — list "add report to index" as a manual follow-up.
On **CONSISTENT only**, run
`bash "$SD/scripts/write-anchor.sh" --repo-root "$CLAUDE_PROJECT_DIR" --anchor-path <anchorPath> --verdict CONSISTENT --mode <mode>`.

## Guardrails
Report-only. Never rewrite ADRs or `docs/logs/`. Surface fixes as proposals. mdq is
optional (fallback to grep). MCP servers are optional.
