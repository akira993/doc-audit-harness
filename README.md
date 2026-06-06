# docaudit — Documentation Audit Harness (Claude Code plugin)

Change-driven documentation audit. Diffs the repo since the last clean audit
(anchor), maps changed code/config to the docs that describe them, verifies each
impacted doc still matches its source, delegates the project's existing doc
checks, and drives `/code-review` + `/security-review` — rolling everything into
a single CONSISTENT / NEEDS FIX verdict. Report-only (no edits).

**New to docaudit? → [docs/ADOPTION.md](docs/ADOPTION.md)** (日本語: [docs/ADOPTION.ja.md](docs/ADOPTION.ja.md)) — full adoption guide: install,
onboarding, config reference, the impact-map method, the verdict/anchor lifecycle, and
hard-won gotchas. Copy-paste config template: [docs/examples/doc-audit.example.json](docs/examples/doc-audit.example.json).

## Install (Claude Code plugin marketplace)

    /plugin marketplace add akira993/doc-audit-harness   # register this repo as a marketplace
    /plugin install docaudit@akira-plugins               # install; skills surface as /docaudit:audit, /docaudit:init

## Install (global, skills-dir — alternative)

    cp -R doc-audit-harness ~/.claude/skills/docaudit    # skills-dir plugin; auto-loads next session as docaudit@skills-dir
    # then in any repo: run /docaudit:init, or add .claude/doc-audit.json by hand
    #   (schema: skills/audit/references/config-schema.md)
    # NOTE: ~/.claude/skills/<name>/ (NOT ~/.claude/plugins/, which is marketplace-cache territory)

## Dev / test

    claude --plugin-dir ~/Projects/doc-audit-harness     # load against a target repo
    python3 -m unittest discover -s tests -t . -v        # run script unit tests

## Modes

    /docaudit:audit            incremental (diff since anchor)
    /docaudit:audit --full     whole-corpus deep audit / first run
    /docaudit:init             bootstrap .claude/doc-audit.json for a repo that has none
    /docaudit:init --scaffold  also generate project-tailored layer skills (skill-creator)

## License

MIT — see [LICENSE](LICENSE).
