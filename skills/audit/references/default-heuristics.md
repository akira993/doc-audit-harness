# Default heuristics (phase-2 fallback recall)

When the explicit `impactMap` misses, the engine adds docs whose content mentions
a changed file's identifier. Tuning lives in `config.heuristics`:

- `minIdentifierLength` (default **5**): shorter basenames/stems are ignored to
  avoid noise (`sw.js` stem `sw` is too short, skipped).
- `excludeBasenames` (merged with built-ins): generic filenames that match too
  much — `readme.md`, `index.md`, `changelog.md`, `license`, `license.md`,
  `__init__.py`, `makefile`, `main.md`, `test.md`, `skill`, `skill.md`.
- `saturationWarnRatio` (default **0.5**, `0` disables): warn when this share of
  the report-excluded document corpus is heuristic-only; use it to promote missing map couplings.
- `excludeDocPathTokens` (default **false**): when true, changed documentation paths do not create
  fallback identifier tokens.
- `regressionRecheck.enabled` (default **false**): opt in to rechecking only unchanged documents
  whose content hash still matches the latest recorded FAIL; these are not impactMap-gap candidates.
- Cap: `maxImpactedDocs` (default 200). Mapped docs are kept first; heuristic-only
  docs fill the remainder; overflow is dropped and reported (never silent).

Heuristic-only hits are surfaced as `mapGapCandidates` — candidates for adding to
`impactMap` so future runs get high-precision mapped coverage.
