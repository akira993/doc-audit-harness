# Default heuristics (phase-2 fallback recall)

When the explicit `impactMap` misses, the engine adds docs whose content mentions
a changed file's identifier. Tuning lives in `config.heuristics`:

- `minIdentifierLength` (default **5**): shorter basenames/stems are ignored to
  avoid noise (`sw.js` stem `sw` is too short, skipped).
- `excludeBasenames` (merged with built-ins): generic filenames that match too
  much — `readme.md`, `index.md`, `changelog.md`, `license`, `__init__.py`,
  `makefile`, `main.md`, `test.md`.
- Cap: `maxImpactedDocs` (default 200). Mapped docs are kept first; heuristic-only
  docs fill the remainder; overflow is dropped and reported (never silent).

Heuristic-only hits are surfaced as `mapGapCandidates` — candidates for adding to
`impactMap` so future runs get high-precision mapped coverage.
