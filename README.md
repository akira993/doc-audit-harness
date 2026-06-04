# docaudit — Documentation Audit Harness (Claude Code plugin)

Change-driven documentation audit. Diffs the repo since the last clean audit
(anchor), maps changed code/config to the docs that describe them, verifies each
impacted doc still matches its source, delegates the project's existing doc
checks, and drives `/code-review` + `/security-review` — rolling everything into
a single CONSISTENT / NEEDS FIX verdict. Report-only (no edits).

## Install (global)

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

Design spec: test-my-nc `docs/superpowers/specs/2026-06-04-doc-audit-harness-design.md`.
