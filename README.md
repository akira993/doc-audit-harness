# docaudit — Documentation Audit Harness (Claude Code plugin)

[![release](https://img.shields.io/github/v/release/akira993/doc-audit-harness?display_name=release)](https://github.com/akira993/doc-audit-harness/releases/latest)

Change-driven documentation audit. Diffs the repo since the last clean audit
(anchor), maps changed code/config to the docs that describe them, verifies each
impacted doc still matches its source, can install or integrate a local
`/check-docs` + `doc-lint` harness, runs its cheap whole-tree checks before the
deep audit, delegates the project's existing doc checks, and runs the configured
`/security-review` layer — rolling
everything into a single CONSISTENT / NEEDS FIX / REFUSED verdict. Report-only,
except for user-approved pre-flight fixes restricted to named documentation files.

**New to docaudit? → [docs/ADOPTION.md](docs/ADOPTION.md)** (日本語: [docs/ADOPTION.ja.md](docs/ADOPTION.ja.md)) — full adoption guide: install,
onboarding, config reference, the impact-map method, the verdict/anchor lifecycle, and
hard-won gotchas. Copy-paste config template: [docs/examples/doc-audit.example.json](docs/examples/doc-audit.example.json).

## Requirements

- **Required:** [Claude Code](https://code.claude.com/docs), a **git** repo ([git](https://git-scm.com/)), and [Python 3](https://www.python.org/) (standard library only — no `pip install`).
- **Local harness (optional, prompted by `init`):** no extra dependency; docaudit can generate `/check-docs`, `doc-lint`, and `scripts/check-docs.py`, or integrate compatible commands already in the repository.
- **Optional:**
  - [`/security-review`](https://code.claude.com/docs) — Claude Code built-in review skill used by the configured security layer.
  - [`mdq` (markdown-query)](https://github.com/dahatake/skills) — Phase 0 auto-index + token-optimized chunked doc reads (~90%+ savings on large docs); the audit nudges you to install it when absent, else grep.
  - [`context-mode`](https://github.com/mksglu/context-mode) — sandboxed processing of large machine output (the git diff and review results) so only distilled summaries enter context, complementary to mdq; auto-used when its `ctx_*` tools are present, non-blocking status line when absent.
  - [`ax`](https://ax.yusuke.run/) — read-only, GET-only fetch of external upstream URLs so doc-impact-verifier can corroborate a doc's external-URL-dependent claims; static HTML only (no JS-rendered SPA support); key-gated by the `webExtract` key in `doc-audit.json`.
  - [`codex`](https://github.com/openai/codex) — `@openai/codex` CLI, no Claude Code plugin needed; key-gated Phase-4 review via the `codexReview` key in `doc-audit.json`, whose `critical`/`high` findings can block completion and whose non-completion is REFUSED when `codexReview.required:true`; also an opt-in, fail-closed Phase-3 backend selected by `phase3Backend:"codex"`.
  - [`codegraph`](https://github.com/colbymchenry/codegraph) — symbol graph that lets doc-impact-verifier corroborate a changed file's own-symbol claims via read-only `impact`/`node`; key-gated by the `symbolGraph` key in `doc-audit.json`.
  - [`graphify`](https://github.com/Graphify-Labs/graphify) — unified code+doc graph, a second independent Phase-2 candidate source for `mapGapCandidates` alongside the token heuristic; key-gated by the `docGraph` key in `doc-audit.json`.
  - [CocoIndex](https://github.com/cocoindex-io/cocoindex-code) (`ccc`) — local-embedding semantic search, a third independent Phase-2 candidate source; key-gated by the `semanticSearch` key in `doc-audit.json`; note the two-step install-then-`ccc init` requirement and that docaudit itself never runs `ccc init`.
  - [Serena](https://github.com/oraios/serena) — richer `init` discovery.
- **`--scaffold` only:** [`skill-creator`](https://github.com/anthropics/skills) (Anthropic) + [`superpowers:writing-skills`](https://github.com/obra/superpowers) to tailor the generated layer skills.

Full table with fallbacks → [docs/ADOPTION.md §2](docs/ADOPTION.md).

Since v0.16.0, every plugin-engine config read is checked against the SHA sealed when the run opened. A `sealed-config-mismatch` stops the run and requires explicit `--accept-config` on the next open even if the config was restored. Phase-4 full review is sampling, not a convergence guarantee; gate-written history carries forward only validated `file` plus `severity` data and reports `phase4FlipsUnchangedContent` when blocking status changes under the same worktree, contract, config, and carry-forward inputs. Project-defined `docAuditCommands` remain trusted at repository-writer level.

## Install (Claude Code plugin marketplace)

    /plugin marketplace add akira993/doc-audit-harness   # register this repo as a marketplace
    /plugin install docaudit@akira-plugins               # install; skills surface as /docaudit:audit, /docaudit:init

## Install (global, skills-dir — alternative)

    cp -R doc-audit-harness ~/.claude/skills/docaudit    # skills-dir plugin; auto-loads next session as docaudit@skills-dir
    rm -rf ~/.claude/skills/docaudit/.git ~/.claude/skills/docaudit/tests  # optional: drop development-only files from the copy
    # then in any repo: run /docaudit:init, or add .claude/doc-audit.json by hand
    #   (schema: skills/audit/references/config-schema.md)
    # NOTE: ~/.claude/skills/<name>/ (NOT ~/.claude/plugins/, which is marketplace-cache territory)

## Usage example

See [docs/PROMPTS.md](docs/PROMPTS.md) for copy-paste prompt examples covering common
audit workflows, including installing the local harness and approving a pre-flight fix.

First run in a repo (no adapter yet):

    /docaudit:init --harness   # drafts config and offers to install/integrate the local harness
    # commit the config and, when installed, the three generated harness files
    /docaudit:audit --full     # whole-corpus baseline; on CONSISTENT it sets the anchor

Day-to-day, after editing code / config / docs:

    /docaudit:audit            # diffs since the anchor → maps changed files to the docs they impact

docaudit is report-only unless you explicitly choose the pre-flight “fix and audit” path;
that exception is mechanically limited to approved documentation paths. Example roll-up
(major output lines only):

    Verdict: NEEDS FIX
    Change set:       3 files since anchor a1b2c3d
    Impacted docs:    docs/api.md  (FAIL — endpoint renamed; doc still says POST /v1/login)
                      README.md    (PASS)
    Delegated checks: existence ✔   semantic ✔   format ✔
    ✓ codex-review: completed (findings included in verdict when present)
    ✓ run class: standard (verifier=Sonnet; codex=Terra)
    Counts: {"impacted":2,"dispatch":2,"verdictFlipsUnchangedContent":0,"verdictFlipsUnchangedContentSameChangeSet":0,"phase4FlipsUnchangedContent":0}
    Report:           docs/logs/doc_audit_2026-06-06.md

Fix the flagged docs, then re-run `/docaudit:audit` until it reports **CONSISTENT** —
a clean verdict advances the anchor, so the next audit only looks at newer changes.

Release notes: see [GitHub Releases](https://github.com/akira993/doc-audit-harness/releases); version-specific compatibility impact is documented in [docs/ADOPTION.md §8](docs/ADOPTION.md).

## Dev / test

    claude --plugin-dir ~/Projects/doc-audit-harness     # load against a target repo
    python3 -m unittest discover -s tests -t . -v        # run script unit tests

## Modes

    /docaudit:audit [--full] [--break-lock] [--accept-config]
        --full          whole-corpus deep audit; disables the Phase-3 cache
        --break-lock    explicitly release a stale audit lock, then stop
        --accept-config acknowledge a config change refused by the previous run

    /docaudit:init [--scaffold] [--harness] [--refresh] [--reask] [--import-audit-scope]
        --scaffold      generate project-tailored layer skills
        --harness       install/integrate the local documentation harness
        --refresh       with --harness, refresh only unmodified stamped templates
        --reask         ask for the harness decision again
        --import-audit-scope import an existing audit-scope.json into the generated impact map

## License

MIT — see [LICENSE](LICENSE).
