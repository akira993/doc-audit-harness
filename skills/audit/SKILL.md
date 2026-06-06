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

## Phase 0 — index preflight (deterministic)
Run: `bash "$SD/scripts/mdq-index.sh" --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR"`.
Parse `{mdqAvailable, reason, bin}` and bind `MDQ_AVAILABLE` (true/false) for Phase 3 and `MDQ_BIN` (the `bin` field, default `mdq`).
`mdqAvailable:false` is EXPECTED, not an error (`reason` is `not-installed` /
`disabled-by-config` / `index-failed`): record the reason and proceed in grep-degrade
mode — the engine is fully functional without mdq. When `mdqAvailable:true`, the whole
repo's Markdown is now indexed under `$CLAUDE_PROJECT_DIR/.mdq/index.sqlite`; indexing runs in a subprocess,
so doc bodies never enter context — only this JSON summary does. This phase always runs
first (both incremental and `--full`).

When `MDQ_AVAILABLE` is true, also run
`python3 "$SD/scripts/mdq-health.py" --bin "<MDQ_BIN>" --db "$CLAUDE_PROJECT_DIR/.mdq/index.sqlite"`
and bind `MDQ_HEALTHY` / `MDQ_CHUNKS` / `MDQ_STATUS` from its JSON
`{healthy, chunks, status}` (`status` ∈ `ok`/`empty-index`/`search-broken`/`probe-error`).
The probe is report-only and always exits 0; if it cannot run, treat `MDQ_HEALTHY` as
`false` and `MDQ_STATUS` as `probe-error` and continue. These feed the Phase-5 mdq status line.

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
Launch `Workflow({scriptPath: "$SD/references/workflow-template.js", args: {repoRoot: CLAUDE_PROJECT_DIR, changeSummary, impacted, mdqAvailable: MDQ_AVAILABLE}})`.
Collect per-doc `{path, verdict, rationale, suggestion}`. (Built-in `/code-review`
& `/security-review` CANNOT run inside a subagent/Workflow — they run in Phase 4.)

## Phase 4 — existing layers + reviews (main loop, sequential)
Global gate: run this phase's delegated checks **iff** `impacted` is non-empty OR
`ssotRecheck` is non-empty OR mode is `full`.
1. From config `docAuditCommands`, run `existence` then `semantic` then `format`
   (e.g. `/check-docs`, `doc-lint`, `/review-docs`) — whole-tree (no per-file arg).
   Invoke each exactly as the config value names it (a skill like `doc-lint` is
   invoked by name, not with a leading slash). **Fallback:** if `docAuditCommands`
   is absent, or a given layer's command is unavailable in this environment, run the
   built-in generic layer instead:
   `python3 "$SD/scripts/generic-layers.py" --layer <format|existence|semantic> --config "$CFG" --repo-root "$CLAUDE_PROJECT_DIR"`
   (in incremental mode you may add `--paths -` and pipe the impacted-doc list to scope it;
   the semantic layer always scans the full repo for orphan-reference resolution regardless).
   Fold its `findings[]` into the verdict: `severity:"FAIL"` -> NEEDS FIX, `severity:"WARN"` -> report only.
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
the **mdq status line** (below), and the roll-up verdict. Do NOT edit any existing doc and do NOT auto-edit
`docs/README.md` — list "add report to index" as a manual follow-up.

**mdq status line** — always include exactly one; it is **non-blocking** (never changes the verdict):
- `MDQ_AVAILABLE` false → `💡 mdq: not active — docs read in full. Install mdq for Phase-0 indexed, chunked reads (~90%+ token savings on large docs): clone github.com/dahatake/skills and run its ./setup/setup-markdown-query.sh`
- `MDQ_AVAILABLE` true and `MDQ_HEALTHY` true → `✓ mdq: active (indexed <MDQ_CHUNKS> chunks; chunked reads on)`
- `MDQ_AVAILABLE` true and `MDQ_HEALTHY` false → `⚠ mdq: installed but NOT firing (<MDQ_STATUS>) — not getting token savings; run mdq index --root . (or check indexing.roots). [non-blocking]`

On **CONSISTENT only**, run
`bash "$SD/scripts/write-anchor.sh" --repo-root "$CLAUDE_PROJECT_DIR" --anchor-path "$ANCHOR_PATH" --verdict CONSISTENT --mode "$MODE"`.

## Guardrails
Report-only. Never rewrite ADRs or `docs/logs/`. Surface fixes as proposals. mdq is
auto-detected in Phase 0; when present it is REQUIRED for doc reads (whole-repo index +
chunked `mdq search`/`get`), with grep used only when mdq is genuinely absent
(conditional-force). The engine still runs fully without mdq. MCP servers are optional.
