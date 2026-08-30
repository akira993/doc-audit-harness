You are a read-only investigator. Do NOT modify any file. Produce a precise fact sheet (Markdown, Japanese or English, with `file:line` citations for every claim; quote short code where useful). Do not propose designs; only report facts. If something cannot be determined, say "UNKNOWN" rather than guessing.

Repo: this working directory (doc-audit-harness). The docaudit skill lives in `skills/audit/` (SKILL.md + scripts/), tests in `tests/`, docs in `README.md`, `ADOPTION.md`, `docs/`. Ignore `tasks/route/**` and `node_modules/**` entirely.

Context: two GitHub issues are being designed together.
- #63: mid-run tampering of `.claude/doc-audit.json` (TOCTOU). open-run.py seals a sha of the config at open time, but later phases re-read the live file.
- #59: Phase-4 codex full review samples different findings each run; plan is (a) a gate-side "Phase-4 flip" counter keyed on the set of blocking-finding files (never titles) + worktreeDigest, (b) data-only carry-forward of the previous gate-reached run's findings (sourced only from `.claude/state/docaudit-history.json` written by decide-verdict.py) into the Phase-4 full-variant prompt.

Report the following sections, each exhaustively:

## A. Every consumer of the live config during an audit run
1. In `skills/audit/SKILL.md`: list every line that passes `--config "$CFG"` (or reads `$CFG` via python one-liners) with line number and which phase it belongs to. Also list where `CFG` is bound (line) and whether any later line rebinds it.
2. For every script under `skills/audit/scripts/`: does it read the config via `--config` argument, via a hard-coded `.claude/doc-audit.json` path, or both? Give the function/line that opens the file. Also note scripts that read `.claude/audit-scope.json` (live) and where.
3. Which scripts are also invoked from Phase 3 workflow / verifier code (`skills/audit/**/workflow-template.js`, agents) and read config or env (e.g. CODEGRAPH_DIR) — list with lines.

## B. open-run.py sealing
- What exactly is hashed for `config` (raw bytes? normalized JSON?), which function, which lines. What goes into the run directory at open time (files, permissions/mode), and the exact EVIDENCE JSON keys emitted (with the success-JSON example if present in tests). What `--accept-config` does (lines). Exit codes and their meanings. Whether audit-scope is sealed at open time (yes/no, lines).

## C. decide-verdict.py gate
- All checks that compare the config: list the line ranges that (i) re-read the live config, (ii) compare with sealed sha, (iii) record `config-changed` taint, (iv) exit/REFUSED paths. Include `verify_audit_scope_at_barrier` (lines).
- The exact JSON schema of the history entry it appends to `.claude/state/docaudit-history.json`: every key, with the line where each is set. Include counters (`verdictFlipsUnchangedContent` and any siblings), `worktreeDigest`, how the previous entry is located and compared (lines), and what constitutes a "flip".
- How Phase-4 codex results enter the gate: which file(s) in the run dir are read (name, expected schema: fields per finding such as file/title/severity), which severities are "blocking", how they affect the verdict (lines). Does the history entry currently record anything about Phase-4 findings? (keys/lines or "none").
- Any existing "warning" (non-REFUSED) output channel the gate has (how warnings reach the report) — lines.

## D. Phase 4 pipeline
- `codex-review-plan.py` (and any sibling like codex-review-run / parse scripts): inputs (args), how the prompt is assembled, where the `full` vs `incremental` variant is decided, what files it writes, whether it reads history or previous run dirs (lines). How findings JSON is parsed/validated and by which script (lines). Which config keys it reads (`codexReview`, `reviewCommands`, `phase4Required`, etc.).
- The exact SKILL.md lines for Phase 4 (start–end line numbers) and the manifest keys involved (`phase4Required`, ...).

## E. Config writes during a run
- `set-config-key.py`: what it does, atomicity, whether it updates any sealed hash (lines). The SKILL.md reopen flow after the harness question (line range) — quote the sentence that says the write invalidates the snapshot.
- `start-run.py`: every live read of config / audit-scope with line numbers (e.g. audit-scope sha computed around :224), and what it writes to manifest.json (keys).

## F. Tests and quality gates
- List test files under `tests/` with a one-line purpose each (from module docstring or first test names), especially those for open-run, decide-verdict, start-run, codex-review-plan, set-config-key, SKILL.md contract tests (tests that grep SKILL.md text).
- How the full test suite is run (exact commands from package.json scripts / Makefile / CI workflow / AGENTS.md), including lint/type/quality gates. Report the current pass/fail by actually running the full suite once (read-only run is fine) and give the summary line (counts).
- Any test fixtures that build a fake run dir / history (paths).

## G. Documentation surfaces that state these contracts
- Grep `README.md`, `ADOPTION.md`, `docs/**/*.md`, `skills/audit/SKILL.md`, `skills/init/**` for: "config sha", "sealed", "docaudit-history", "verdictFlipsUnchangedContent", "Phase 4", "Phase-4", "codex review", "reproduc", "再現", "TOCTOU", "tamper". For each hit give file:line and a ≤1-line quote. This is to find every doc that must change.

## H. Release plumbing
- Every location holding the version string `0.15.1` (files:lines), `engine-shas.json` location and how it is generated/verified (script + test), and `.claude/doc-audit.json` of this repo itself (relevant keys).

Finish with a "## Open questions / UNKNOWN" list.
