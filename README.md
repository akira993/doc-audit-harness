# docaudit — Documentation Audit Harness (Claude Code plugin)

[![release](https://img.shields.io/github/v/release/akira993/doc-audit-harness?display_name=release)](https://github.com/akira993/doc-audit-harness/releases/latest)

Change-driven documentation audit. Diffs the repo since the last clean audit
(anchor), maps changed code/config to the docs that describe them, verifies each
impacted doc still matches its source, delegates the project's existing doc
checks, and drives `/code-review` + `/security-review` — rolling everything into
a single CONSISTENT / NEEDS FIX verdict. Report-only (no edits).

**New to docaudit? → [docs/ADOPTION.md](docs/ADOPTION.md)** (日本語: [docs/ADOPTION.ja.md](docs/ADOPTION.ja.md)) — full adoption guide: install,
onboarding, config reference, the impact-map method, the verdict/anchor lifecycle, and
hard-won gotchas. Copy-paste config template: [docs/examples/doc-audit.example.json](docs/examples/doc-audit.example.json).

## Requirements

- **Required:** [Claude Code](https://code.claude.com/docs), a **git** repo ([git](https://git-scm.com/)), and [Python 3](https://www.python.org/) (standard library only — no `pip install`).
- **Optional (all degrade gracefully):** [`/code-review` + `/security-review`](https://code.claude.com/docs) (Claude Code built-ins), [`mdq` (markdown-query)](https://github.com/dahatake/skills) (Phase 0 auto-index + token-optimized chunked doc reads — ~90%+ savings on large docs; the audit nudges you to install it when absent, else grep), [`context-mode`](https://github.com/mksglu/context-mode) (sandboxed processing of large machine output — the git diff and `/code-review` + `/security-review` results — so only distilled summaries enter context, complementary to mdq; auto-used when its `ctx_*` tools are present, non-blocking status line when absent), [`ax`](https://ax.yusuke.run/) (read-only, GET-only fetch of external upstream URLs so doc-impact-verifier can corroborate a doc's external-URL-dependent claims; static HTML only — no JS-rendered SPA support; degrades gracefully when absent), [CocoIndex](https://github.com/cocoindex-io/cocoindex) / [Serena](https://github.com/oraios/serena) (richer `init` discovery).
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

First run in a repo (no adapter yet):

    /docaudit:init             # writes .claude/doc-audit.json (detects docs + existing doc checks)
    /docaudit:audit --full     # whole-corpus baseline; on CONSISTENT it sets the anchor

Day-to-day, after editing code / config / docs:

    /docaudit:audit            # diffs since the anchor → maps changed files to the docs they impact

docaudit is report-only — it never edits your docs. Example roll-up (illustrative):

    Verdict: NEEDS FIX
    Change set:       3 files since anchor a1b2c3d
    Impacted docs:    docs/api.md  (FAIL — endpoint renamed; doc still says POST /v1/login)
                      README.md    (PASS)
    Delegated checks: existence ✔   semantic ✔   format ✔
    Reviews:          /code-review ⚠ 1 medium    /security-review ✔
    Report:           docs/logs/doc_audit_2026-06-06.md

Fix the flagged docs, then re-run `/docaudit:audit` until it reports **CONSISTENT** —
a clean verdict advances the anchor, so the next audit only looks at newer changes.

## Dev / test

    claude --plugin-dir ~/Projects/doc-audit-harness     # load against a target repo
    python3 -m unittest discover -s tests -t . -v        # run script unit tests

## Modes

    /docaudit:audit            incremental (diff since anchor)
    /docaudit:audit --full     whole-corpus deep audit / first run
    /docaudit:init             bootstrap .claude/doc-audit.json for a repo that has none
    /docaudit:init --scaffold  also generate project-tailored layer skills (skill-creator / writing-skills)

## License

MIT — see [LICENSE](LICENSE).
