# docaudit — Documentation Audit Harness (Claude Code plugin)

[![release](https://img.shields.io/github/v/release/akira993/doc-audit-harness?display_name=release)](https://github.com/akira993/doc-audit-harness/releases/latest)

Change-driven documentation audit. Diffs the repo since the last clean audit
(anchor), maps changed code/config to the docs that describe them, verifies each
impacted doc still matches its source, can install or integrate a local
`/check-docs` + `doc-lint` harness, runs its cheap whole-tree checks before the
deep audit, delegates the project's existing doc checks, runs `/security-review`,
and offers `/code-review` for the user to run (it is not model-invocable) — rolling
everything into a single CONSISTENT / NEEDS FIX / REFUSED verdict. Report-only,
except for user-approved pre-flight fixes restricted to named documentation files.

In autonomous runs, `/code-review` is an expected user-invocation-only layer. Interactive
runs offer the user one chance to run the configured `/code-review` before continuing.

**New to docaudit? → [docs/ADOPTION.md](docs/ADOPTION.md)** (日本語: [docs/ADOPTION.ja.md](docs/ADOPTION.ja.md)) — full adoption guide: install,
onboarding, config reference, the impact-map method, the verdict/anchor lifecycle, and
hard-won gotchas. Copy-paste config template: [docs/examples/doc-audit.example.json](docs/examples/doc-audit.example.json).

## Requirements

- **Required:** [Claude Code](https://code.claude.com/docs), a **git** repo ([git](https://git-scm.com/)), and [Python 3](https://www.python.org/) (standard library only — no `pip install`).
- **Local harness (optional, prompted by `init`):** no extra dependency; docaudit can generate `/check-docs`, `doc-lint`, and `scripts/check-docs.py`, or integrate compatible commands already in the repository.
- **Optional (all degrade gracefully):** [`/security-review`](https://code.claude.com/docs) (Claude Code built-in; `/code-review` is offered for the user to run because it is not model-invocable), [`mdq` (markdown-query)](https://github.com/dahatake/skills) (Phase 0 auto-index + token-optimized chunked doc reads — ~90%+ savings on large docs; the audit nudges you to install it when absent, else grep), [`context-mode`](https://github.com/mksglu/context-mode) (sandboxed processing of large machine output — the git diff and review results — so only distilled summaries enter context, complementary to mdq; auto-used when its `ctx_*` tools are present, non-blocking status line when absent), [`ax`](https://ax.yusuke.run/) (read-only, GET-only fetch of external upstream URLs so doc-impact-verifier can corroborate a doc's external-URL-dependent claims; static HTML only — no JS-rendered SPA support; degrades gracefully when absent), [`codex`](https://github.com/openai/codex) (`@openai/codex` CLI, no Claude Code plugin needed — a fourth, adversarial Phase-4 review whose `critical`/`high` findings CAN block the verdict when it completes; degrades gracefully to no-op when absent), [`codegraph`](https://github.com/colbymchenry/codegraph) (symbol graph — lets doc-impact-verifier corroborate a changed file's own-symbol claims via read-only `impact`/`node`; degrades gracefully when absent), [`graphify`](https://github.com/Graphify-Labs/graphify) (unified code+doc graph — a second, independent Phase-2 candidate source for `mapGapCandidates` alongside the token heuristic; degrades gracefully when absent), [CocoIndex](https://github.com/cocoindex-io/cocoindex-code) (`ccc`, local-embedding semantic search — a third, independent Phase-2 candidate source; note the two-step install-then-`ccc init` requirement and that docaudit itself never runs `ccc init`; degrades gracefully when absent or not yet initialized) / [Serena](https://github.com/oraios/serena) (richer `init` discovery).
- **`--scaffold` only:** [`skill-creator`](https://github.com/anthropics/skills) (Anthropic) + [`superpowers:writing-skills`](https://github.com/obra/superpowers) to tailor the generated layer skills.

Full table with fallbacks → [docs/ADOPTION.md §2](docs/ADOPTION.md).

## Install (Claude Code plugin marketplace)

    /plugin marketplace add akira993/doc-audit-harness   # register this repo as a marketplace
    /plugin install docaudit@akira-plugins               # install; skills surface as /docaudit:audit, /docaudit:init

## Install (global, skills-dir — alternative)

    cp -R doc-audit-harness ~/.claude/skills/docaudit    # skills-dir plugin; auto-loads next session as docaudit@skills-dir
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
(illustrative):

    Verdict: NEEDS FIX
    Change set:       3 files since anchor a1b2c3d
    Impacted docs:    docs/api.md  (FAIL — endpoint renamed; doc still says POST /v1/login)
                      README.md    (PASS)
    Delegated checks: existence ✔   semantic ✔   format ✔
    Reviews:          /code-review ⚠ 1 medium    /security-review ✔
    Report:           docs/logs/doc_audit_2026-06-06.md

Fix the flagged docs, then re-run `/docaudit:audit` until it reports **CONSISTENT** —
a clean verdict advances the anchor, so the next audit only looks at newer changes.

## What's new in 0.10.0

- Interactive `init` asks once and records a five-state harness decision: install, integrate, adjust, preserve, or decline.
- Phase 0.5 runs cheap whole-tree checks before sealing and offers a tightly scoped, user-approved fix path.
- Every audit owns `docaudit-run/<runid>/`; a no-TTL lock prevents concurrent runs.
- The gate verifies sealed evidence, HEAD, the worktree digest, returns, and persistent-state integrity; failures become `REFUSED`.
- Deterministic PASS history can skip Phase 3 after two qualifying runs; `--full` always bypasses the cache.
- Deterministic light/standard classification selects Haiku/Sonnet verification and Luna/Terra Codex review defaults.
- NEEDS FIX reports scan all `docGlobs` siblings for quoted phrases carried in verifier returns.
- Full mode now impacts the complete documentation corpus, including on a clean tree.

## Dev / test

    claude --plugin-dir ~/Projects/doc-audit-harness     # load against a target repo
    python3 -m unittest discover -s tests -t . -v        # run script unit tests

## Modes

    /docaudit:audit [--full] [--break-lock] [--accept-config]
        --full          whole-corpus deep audit; disables the Phase-3 cache
        --break-lock    explicitly release a stale audit lock, then stop
        --accept-config acknowledge a config change refused by the previous run

    /docaudit:init [--scaffold] [--harness] [--refresh] [--reask]
        --scaffold      generate project-tailored layer skills
        --harness       install/integrate the local documentation harness
        --refresh       with --harness, refresh only unmodified stamped templates
        --reask         ask for the harness decision again

## License

MIT — see [LICENSE](LICENSE).
