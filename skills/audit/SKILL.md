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
Also bind `ANCHOR_PATH="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("anchorPath",""))' "$CFG")"` for Phase 5.
`--full` forces whole-corpus mode (ignores the anchor diff scope).

## Phase 1 — baseline + diff
Run: `bash "$SD/scripts/compute-baseline.sh" --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR"`.
Do NOT pass `--full` to this script (it only accepts `--config`/`--repo-root`; an unknown flag makes it `exit 2`). `--full` is a skill-level argument only: after parsing the script output, if the skill was invoked with `--full`, set the effective `MODE` to `full` in memory. Bind `MODE` to the effective mode for use in Phase 5.
Parse `{mode, baselineSha, changed[]}`. If `--full` was passed, treat mode as `full`.
If `mode=full` (no or invalid anchor), tell the user this is a full run and proceed
with the whole doc corpus as the change set context.

## Phase 2 — impact resolution
Build a concise `changeSummary` (per changed file: path + 1-line nature of change from `git diff --stat`/`git show`); it depends only on the Phase 1 `changed` list.
Pipe the `changed` list into:
`printf '%s\n' "${changed[@]}" | python3 "$SD/scripts/resolve-impact.py" --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR" --changed -`.
Parse `{impacted[], mapGapCandidates[], ssotRecheck[], truncated, counts{changed,impacted,mapped,heuristicOnly,candidatesBeforeCap}}`. If `truncated` is true, record the dropped count (the script also prints it to stderr) explicitly in the Phase 5 report — never silently discard it.

## Phase 3 — change-impact verification (Workflow fan-out)
Launch `Workflow({scriptPath: "$SD/references/workflow-template.js", args: {repoRoot: CLAUDE_PROJECT_DIR, changeSummary, impacted}})`.
Collect per-doc `{path, verdict, rationale, suggestion}`. (Built-in `/code-review`
& `/security-review` CANNOT run inside a subagent/Workflow — they run in Phase 4.)

## Phase 4 — existing layers + reviews (main loop, sequential)
Global gate: run this phase's delegated checks **iff** `impacted` is non-empty OR
`ssotRecheck` is non-empty OR mode is `full`.
1. From config `docAuditCommands`, run `existence` then `semantic` then `format`
   (e.g. `/check-docs`, `doc-lint`, `/review-docs`) — invoke each exactly as the config value names it (a skill like `doc-lint` is invoked by name, not with a leading slash). — whole-tree (no per-file arg).
2. If `boundaryCommand` set and gate open, run it.
3. Run `reviewCommands.code` (e.g. `/code-review high`) on the working diff, then
   `reviewCommands.security` (e.g. `/security-review`). Normalize any
   `/security-audit ...` request to `/security-review`. If a review command is not
   available in this environment, skip it and WARN (do not fail the run).
   `/code-review ultra` is non-blocking — never wait on a cloud run; default to the
   configured effort.

## Phase 5 — synthesize + anchor
Phase 3 subagent verdicts are already PASS/WARN/FAIL — use them directly. For Phase 4 tool outputs, map high-severity findings to FAIL and medium-severity to WARN. Verdict =
**NEEDS FIX if any FAIL**, else **CONSISTENT** (WARN never blocks).
Write a single report to `reportPath` (e.g. `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md`,
6-field front matter (title, description, category, created, updated, version) with `category: logs`), containing: change set, impacted docs +
per-doc verdicts, delegated-check results, review summaries, `mapGapCandidates`,
and the roll-up verdict. Do NOT edit any existing doc and do NOT auto-edit
`docs/README.md` — list "add report to index" as a manual follow-up.
On **CONSISTENT only**, run
`bash "$SD/scripts/write-anchor.sh" --repo-root "$CLAUDE_PROJECT_DIR" --anchor-path "$ANCHOR_PATH" --verdict CONSISTENT --mode "$MODE"`.

## Guardrails
Report-only. Never rewrite ADRs or `docs/logs/`. Surface fixes as proposals. mdq is
optional (fallback to grep). MCP servers are optional.
