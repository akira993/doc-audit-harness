v0.11.0 — the three deterministic-layer defects reported in #33 / #34 / #35, shipped as one minor release.

## What changed

**#33 — bare paths were invisible; severity depended on syntax**
- The existence layer now extracts backtick tokens from code-masked text (fenced blocks with nested blockquote/list markers, 4-space indented code) and additionally harvests bare ASCII path references from prose as a WARN-only detection net.
- A non-resolving backtick token that denotes a concrete file (letter-initial extension, not directory-shaped) is now **FAIL**; bare references, directory-shaped and extensionless tokens stay WARN.
- Normalization pipeline: `#`/`?` suffix stripping, `:locator` base resolution, safe percent-decode (NUL/control/`..` re-validation), realpath repo confinement, `..`/`//` rejection.
- Design note: after adversarial review (5 rounds), blocking power is limited to author-explicit syntax (links/backticks). Prose harvesting cannot reach blocking-grade precision (command examples, Japanese prose ambiguity), so bare findings are WARN by design — documented in config-schema.md.

**#34 — docGlobs forced every layer onto every path class**
- New `layerGlobs` config: per-layer `exclude` globs applied inside each generic check (also for explicit `--paths`). Semantic exclusion only removes docs from orphan *reporting* — their outgoing links still count, so no false orphans.
- New `frontMatterOverrides`: ordered `{globs, fields}` entries, first match wins, `fields: []` skips the check entirely.
- Corpus membership stays separate: impact resolution and `--full` coverage are unaffected by `layerGlobs`.

**#35 — the audit's own reports polluted the corpus**
- One report matcher, derived from the full `reportPath` template (literals escaped, `<YYYY-MM-DD>` → ASCII date regex, collision suffix `(_[0-9]{2,})?` at the `[_NN]` position or after the date), replaces the over-broad `doc_audit_*.md` glob everywhere: change-set exclusion (canonical), sibling scan, generic-layers enumeration, resolve-impact full/heuristic pools, impact-supplement candidates, start-run corpus count.
- Corpus exclusion is on by default; `auditReportsInCorpus: true` opts back in. Machinery exclusion (changed[]/sibling scan) stays unconditional to protect sealed evidence.
- `doc_audit_policy.md`-style non-report docs are no longer swallowed — they return to both changed[] and the corpus.
- SKILL.md now pins the report collision-suffix contract (`_02`…, zero-padded, never overwrite).

## Verification

- 298 tests green (`python3 -m unittest discover -s tests -t .`), including a report-matcher contract table run against all five implementations + decide-verdict, a compute-baseline.sh integration test, and scaffold refresh tests against a SHA-pinned historical 0.10.1 engine fixture.
- `codex exec review` (Sol high) findings resolved (untracked fixture force-added; docGlobs default fallback unified across all five `report_pattern` copies).
- Version residuals in distribution paths limited to the engine-shas history entry and the migration notes in ADOPTION (en/ja).

## Compatibility

- The backtick FAIL escalation can turn a previously-CONSISTENT audit into NEEDS FIX on repos with stale explicit references. Mitigations shipped in the same release: default report exclusion and `layerGlobs`.
- `engine-shas.json` gains a 0.11.0 entry (template SHAs unchanged; engine SHA updated). `/docaudit:init --harness --refresh` updates unmodified stamped 0.10.1 harnesses.

Plan/critique/implementation records: `tasks/route/2026-08-25-issues-33-34-35/` (PLAN rev.6, REVIEW with 5 critique rounds and 4 implementation rounds).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
