## docaudit v0.16.0 — sealed-config verify-on-read (#63) + Phase-4 flip counter / carry-forward (#59)

### Security / integrity (#63)
- Every plugin-engine config consumer (10 Python scripts, 7 shell probes, 22 SKILL call sites, 13 SKILL-level getters via the new `sealed_config.py`) verifies the exact bytes it read against the sha sealed in EVIDENCE at open time. A mismatch exits 7 (`sealed-config-mismatch`) and is funnelled into `decide-verdict.py --taint-observed {config,history} --observed-by <script>`, which records `configAcceptanceRequired` / quarantine markers so the next open demands `--accept-config` even if the file was restored.
- `open-run.py` takes `--expect-config-sha` from the pre-check (`import-audit-scope.py --check` now also emits `scopePath`), refuses config changed before open (exit 2), consumes `--accept-config` exactly once, keeps the two-layer lock design (existing lock → unconditional exit 4), and recovers quarantine-pending history on the next normal open. `--release`/`--break-lock` merge holder markers into last_run and never block.
- The gate reads config once from the same fd that produced its signature; child `change-set-sha.py` mismatches propagate as config taint.

### Reproducibility (#59)
- History gains `phase4Runs` (full+completed runs only; `{file, severity}` findings ≤500; retention 5 + carry-forward source guard; strict lexical parser shared by resolve-impact / plan-dispatch / gate / codex-review-plan; invalid `phase4Runs` degrades without touching the deterministic PASS cache).
- The gate reports `phase4FlipsUnchangedContent` (symmetric difference of blocking-file sets between runs with identical worktreeDigest × contractVersion × configSha × carryForwardSha) as a warning, never a verdict input.
- `codex-review-plan.py` emits a data-only carry-forward (existing repo files + severity only, ≤50) for the full variant; Phase-4 evidence gains `file`, `promptVariant`, `carryForwardSha` with a complete eligibility table.
- Contract wording: the Phase-4 full review samples the defect pool; "fix N and re-run" is not guaranteed to converge.

### Behavior changes to know when upgrading from 0.15.x
1. Directly invoked probes with an invalid/absent/omitted config exit 2 without JSON (was exit 0 + `invalid-config`).
2. An installed harness copy runs directly only with an exact `0.16.0` stamp; any other stamp falls back to the plugin engine as pre-flight with a WARN and `/docaudit:init --harness --refresh` guidance.
3. Partial `*.py` sync is unsupported — update the whole plugin tree; mixed versions stop with exit 2.
4. Crash recovery: `--break-lock` carries quarantine markers into last_run; an unreadable last_run requires `--accept-config` and quarantines live history (cold start).

### Trust classes (documented in ADOPTION)
Sealed-config covers the plugin engine's decision path completely. Cross-run state (last_run / history / anchor) and project-defined `docAuditCommands` remain at repository-writer trust.

### Verification
`python3 -m unittest discover -s tests` → 716 tests OK (baseline 655). Contract counts: `call sites 22／exempt 3／getters 13／scripts 21／observers 19`, 21 consumers exercised with match/mismatch pairs.

PR #68. Route record: `tasks/route/2026-08-30-issues-59-63-65-66/`.
