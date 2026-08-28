## Summary

docaudit **v0.14.0** — resolves #57, #58, #60 and ships stage 1 of #56 plus the minimal operational note for #59.

- **#58** `import-audit-scope.py` now accepts an absolute `--config`/`--scope` path under the repository root (component check → apparent/real root prefix → existing `validate_repo_path`; POSIX paths only). `SKILL.md`'s `CFG` binding is unchanged; `docaudit_paths.py` untouched.
- **#56 (stage 1)** `indexing` / `contextMode` / `webExtract` / `codexReview` now require a JSON boolean `enabled`; a non-boolean `enabled`, a non-object key (incl. `null`), or a non-string/empty/NUL-containing `bin` reports `invalid-config` and never runs the tool. An absent key still defaults to enabled (stage 2 — changing that default — is deliberately **not** in this PR; see the boss recommendation below). An invalid `indexing` key fires the Phase-0 mdq confirmation gate; `codexReview.required:true` + invalid key is now REFUSED instead of silently running codex. 20-variant decision-table tests per probe, 13 for the `contextMode` expression.
- **#57** New `skills/audit/scripts/probe-record.py` persists Phase-0 probe output to `$RUN_DIR/phase0-probes.json` (display-only, never a verdict input; the gate never reads it) and Phase-5 status lines are rendered from its `rebind` map on fresh and resumed runs (`state unknown after resume` when a record is missing/unreadable). Component-wise `O_DIRECTORY|O_NOFOLLOW` walk, dir-fd atomic replace, per-seam branch schemas. `EVIDENCE` is untouched.
- **#60** The codex probe reports the caller's `CODEX_HOME` and whether `auth.json` exists there (display-only; wrapper environments are not observed); the codex-review status line shows it and adds an env-first diagnosis when execution fails without an auth file. Probe JSON is now emitted via `json.dumps` (no more `tr -d` sanitizer).
- **#59 (minimal)** Operational note in `SKILL.md` Phase 4 and ADOPTION en/ja: first-time `full`+`required` runs may take several rounds; fix blocking findings only; carry the previous list forward as fenced JSON data. The engine-side ledger was **deferred** — five Sol critique rounds showed it needs the same trust class as history/anchor (open-run sealing, barrier recheck, transactional commit, taint recovery); the design constraints are captured in `tasks/route/2026-08-28-issues-56-60/59-design-note.md`.

Release: plugin/ADOPTION/engine-shas/scaffold stamp → `0.14.0`; ADOPTION §7 `v0.14.0 behavior changes` (en/ja, pinned by `test_v014_behavior_changes_paragraph`); `release-handoff.sh` re-targeted (tag `docaudit--v0.14.0`, closes 57/58/60 only).

Version note: 0.14.0 (minor) because the change is additive runtime behaviour (new persisted file, new probe keys, new semantics). If a patch (0.13.3) is preferred, say so before tagging — it is a cheap change at this point.

## Test plan

- [x] Full suite: `Ran 580 tests`, OK, skipped 0 (boss re-run after each stage: 569 → 579 → 580)
- [x] Scope check (`scope-check.py`, allowlist + protected-root hashes): clean after every worker stage
- [x] Forbidden engine files byte-identical to `dfdb8a9` (`decide-verdict.py`, `start-run.py`, `write-evidence.py`, `docaudit_paths.py`, …)
- [x] `bash -n` on the three probes and the handoff; `scaffold.py --harness --dry-run` stamps `0.14.0`
- [x] Plan critiqued by GPT-5.6 Sol ×5 rounds and Opus adversarial review ×2 (`tasks/route/2026-08-28-issues-56-60/REVIEW.md`)
- [ ] After merge: run `tasks/route/2026-08-28-issues-56-60/release-handoff.sh <merge-sha> <pr>` (tag, Release, close #57 #58 #60, skills-dir sync)

Closes #57, #58, #60.
Partially addresses #56 (stage 1) and #59 (operational note); both remain open.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
