## docaudit v0.13.1 — documentation consistency (#46–#50)

Docs-only patch. No runtime behavior, script output, or gate decision changes (`fix-scope.py` gains one comment line; `git diff --numstat` = `1 0`).

### Closes
- #46 README stale since v0.10.0 — `--import-audit-scope`, codex Phase-3 backend / `codexReview.required`, Phase-5 roll-up lines, release-notes link (no per-version "What's new" section any more).
- #47 `digestExclude` allowed values were written as globs — now documented as non-glob literal prefixes (incl. `.claude/worktrees`) with the seal-failure contract, in config-schema and ADOPTION en/ja; contract test (a) passes every documented prefix through `tree-digest.normalize()`.
- #48 audit `SKILL.md` — `generic-layers.py … --config`, doc-graph `update-failed` branch (4-state), `CODEX_REVIEW_AVAILABLE` lower-case binding, and the 6 low findings (`BASELINE_OK` in full mode, gate `codexReview` keys / degraded `{{GATE_VERDICT}}`, `bin` overrides are Phase-0-only, `HARNESS_ACTIVE` removed, `CM_HEALTHY` branch note, "step 3e" → "step 3").
- #49 ADOPTION en/ja — complete `codexReview` REFUSED conditions, Phase-4 severity table (`non-blocking` / `blocking` / `REFUSED`), file map +6, §5 table excerpt note + 3 missing keys (`layerGlobs`, `frontMatterOverrides`, `auditReportsInCorpus`), ja plain style.
- #50 references/example — `regressionRecheck` content-hash condition, reserved `tool` key note, nested `models.light`, example keys with defaults (`auditScope` deliberately absent), `fix-scope.py` fail-closed comment + docs.

### Release plumbing
- Version 0.13.1 on all five surfaces (`plugin.json`, `engine-shas.json` `0.13.1` entry with unchanged hashes, ADOPTION en/ja `claude plugin list` line, scaffold stamp); refresh line lists `0.13.0` as an upgradable stamp.
- New `tests/test_v0131_docs_contracts.py` (8 contract tests: digestExclude prefixes, `--config` lines, file map ⇔ scripts/references, README flags ⇔ argument-hints, example keys/defaults, refresh-line versions, en/ja structural parity, severity table ⇔ `decide-verdict.py`).
- `tests/test_release_handoff.py` retargeted to the v0.13.1 handoff script (`tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`, tracked with `git add -f`).

### Verification
- `python3 -m unittest discover -s tests -t .` → `Ran 495 tests … OK` (skip 0) — re-run by the boss.
- Handoff tests re-run in a detached checkout of HEAD.

### Follow-ups (not in this patch — candidates for new issues)
1. `fix-scope.py:87` `docGlobs` default `[]` vs `["docs/**/*.md","*.md"]` elsewhere (documented as intentional fail-closed here; aligning is a runtime change).
2. `seal-run.py` non-zero exits other than 5 have no explicit stop branch in `SKILL.md`, and post-failure behavior differs by backend (workflow vs codex, empty vs non-empty dispatch).

Review trail: `tasks/route/2026-08-27-issues-46-50-v0.13.1/` (PLAN rev.8, Sol ×5, Opus ×3, S1/S2 reports, REVIEW.md).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
