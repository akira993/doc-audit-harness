## Summary

docaudit v0.12.0 — closes the two remaining open issues and prepares the pending two-stage release (retrospective v0.11.0 tag + v0.12.0).

### #37 — gate-writes-report (fix)

The report-after-lock-release race (run A's report write breaking run B's sealed tree digest) and the same-day `_NN` suffix overwrite race are removed by moving report publication inside the lock-held deterministic gate:

- The orchestrator pre-renders the report body with a single verdict-independent `{{GATE_*}}` placeholder contract and hands it to the new run-ledger-bound `write-template.py` (O_EXCL, explicit `--replace`, invalidate-first receipt binding the template to the gate mechanically).
- `decide-verdict.py` substitutes typed, escaped values, selects the suffix via a temp+`link(2)` candidate loop (existing reports can never be overwritten or truncated), publishes only after the post-scan verification barrier and persistent state commit, records `reportStatus` in `last_run` and stdout, and only then unlinks the lock. `--break-lock` is refused for the whole gate+report interval.
- Post-commit failures never reverse the verdict; unresolved `pending`/`failed`/`written-durability-unknown` report states surface as `previousReportStatus` on the next open. Lock ownership is strengthened to a four-fact AND; required EVIDENCE keys are validated before lock open. The pre-fix race is demonstrated in `tasks/route/2026-08-25-issues-28-37-release/stage1-cause-demo.txt`; regression and fault-injection tests pin serialization, the barrier order, and every recovery row of the state table.
- Visible change: report file names and front-matter dates derive from the run id in UTC.

### #28 — opt-in Codex Phase-3 backend (feature)

Adopted after an A/B on isolated clones of a real repository (12 docs, `--full`, identical trees verified): the codex arm collected **12/12 verdicts in one attempt** (the Workflow-path collection losses of 38/60–59/60 that motivated the issue), 214s vs 330s wall, with spot-verified accurate rationales (details in `tasks/route/2026-08-25-issues-28-37-release/REVIEW.md`).

- New fail-closed `codex-dispatch.py`: one `codex exec -s read-only --output-schema` per dispatched doc, per-attempt private output directories, adoption requiring exit 0 AND single-fd validated fresh output (probe P4 showed exit code alone does not guarantee the `-o` file exists), process-group timeout kill, a bounded worker pool, verdict publication through the existing `write-verdict.py` atomic path, and a `returns.json` reproducing the existing retry contract. Incremental prompts list the sealed changedSet so uncommitted/untracked changes are verified.
- Opt-in via `phase3Backend: "codex"` (default `workflow`; invalid values rejected at seal) plus `phase3CodexTimeoutSeconds`; the effective backend is sealed into the manifest, verified by the gate, threaded through cache qualification (legacy history reads as `workflow`), and reported in the audit report. No silent fallback to Workflow.

### Release machinery

- Version bump to 0.12.0, engine-shas entry, ADOPTION en/ja updates, 0.10.1→0.12.0 skip-upgrade scaffold test.
- New fail-closed, restart-safe `release-handoff.sh` (two-stage: retrospective `docaudit--v0.11.0` at 01344ea, then v0.12.0 with a full-suite rerun at the approved commit before tagging; archive-based skills-dir sync with hide/protect filter semantics) covered by a ten-branch PATH-shim test suite.

Design went through two adversarial critique loops (5 rounds each, Sol high) plus a final `codex exec review`; the full adjudication trail is in `tasks/route/2026-08-25-issues-28-37-release/REVIEW.md` (PLAN rev.12).

Closes #37
Closes #28

## Test plan

- [x] `python3 -m unittest discover -s tests -t .` — 368 tests, OK (was 298 before this branch)
- [x] Pre-fix #37 race demonstrated on the old code and recorded; post-fix serialization verified by deterministic inter-process tests (pipe-READY flock holds, EEXIST injection, barrier-target mutation, crash-recovery rows)
- [x] A/B evaluation of the codex backend on isolated clones (12/12 collection, verified rationale accuracy)
- [x] `shellcheck` clean on `release-handoff.sh`; handoff branch behavior covered by PATH-shim tests
- [ ] After merge: run `bash tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh <merge-sha> <this-PR-number>` (user-run; tags, releases, issue closes, skills-dir sync)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
