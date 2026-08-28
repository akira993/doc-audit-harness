## docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)

Closes #52, #53, #54.

### #52 — `fix-scope.py` docGlobs default
- Omitted `docGlobs` now uses the shared default `["docs/**/*.md","*.md"]` (was `[]`, deny-all) — same as the other 10 config consumers.
- New built-in deny: `CLAUDE.md` / `AGENTS.md` basenames at any depth, case-insensitive, regardless of `docGlobs` (the audit never edits its own instruction files during pre-flight fixes).
- Docs: the fail-closed note from v0.13.1 is removed; the built-in deny list is updated in 5 places.

### #53 — seal failure stop branches + unsealed manifest rejection
- `SKILL.md` Phase 3: exit 5, any other non-zero `seal-run.py` exit, and a `read-manifest.py` failure all release the run with the full `open-run.py --release` command and stop (no verifier launch).
- `read-manifest.py` rejects anything that is not `{"sealed": true, …}` (exit 2, `manifest is not sealed`). `codex-dispatch.py` keeps its own check as defense in depth.

### #54 — report-only Phase-0 probes
- `docGraph` / `semanticSearch` / `symbolGraph` are key-gated: an absent key reports `not-configured` and never runs the tool (matches `/docaudit:init`'s "OMIT the key = not adopted"); an invalid key / `enabled` / `bin` / `minScore` reports `invalid-config`. `enabled:false` still wins over an invalid `bin`/`minScore`.
- CocoIndex is initialized only when `.cocoindex_code/settings.yml` exists (ccc's own marker). Root cause of the `.gitignore` write: `ccc index` → `require_project_root(auto_init=True)` → `add_to_gitignore` when the marker is missing (legacy `.cocoindex_code/` dirs without `settings.yml` triggered it).
- Safety net: a `.gitignore` change during `ccc index` is reported as `gitignore-modified` (never reverted by the audit).
- Phase-5 status lines are reason-keyed (doc-graph 6-state / symbol-graph 6-state / semanticSearch 8-state); `*_PROBE_JSON` / `*_REASON` bindings added.
- **Migration**: configs that relied on auto-detection without these keys must add them via `/docaudit:init`. Other seams (`indexing`, `contextMode`, `webExtract`, `codexReview`) are unchanged.

### Test baseline fix
- `tests/test_import_audit_scope.py` no longer depends on the live `~/Projects/dir-framework` checkout (it was red on main: `48 != 46`). A frozen fixture from dir-framework `951570b` lives in `tests/data/dir-framework-scope/` with pinned sha256s.

### Release
- Version 0.13.2 on all five surfaces, `engine-shas.json` entry, ADOPTION §7 `v0.13.2 behavior changes` (en/ja), contract tests re-targeted, `release-handoff.sh` for tag/Release/issue close/skills-dir sync.
- Full suite: see REVIEW.md (route records under `tasks/route/2026-08-28-issues-52-54-v0.13.2/`).

Note: #52/#53 proposed a minor bump; shipped as a patch per the maintainer's instruction (behavior changes are listed in ADOPTION §7).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
