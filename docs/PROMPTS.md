# docaudit — Prompt Examples

> 🌐 日本語版: [PROMPTS.ja.md](PROMPTS.ja.md)

A library of copy-paste prompts for asking Claude Code to run a docaudit audit for a
specific purpose. Each prompt wraps its instructions in XML tags (`<task>`, `<context>`,
`<scope>`, `<change>`, `<constraints>`, `<report>`) instead of one paragraph of prose,
because Claude parses structured tags far more reliably than free text — it can tell
exactly which sentence is the task, which is background, and which is a hard constraint,
rather than inferring the boundaries itself. This follows Anthropic's own guidance on
prompt structure: see [Claude prompting best
practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices).
Swap the bracketed/example values (doc names, change descriptions) for your own before
pasting. All patterns below assume docaudit is already installed and, except for pattern
5, that `.claude/doc-audit.json` already exists in the target repo.

---

## 1. Regular diff audit

Use this for routine, day-to-day checks after editing code, config, or docs — it verifies
only the docs impacted by changes since the last clean audit anchor.

```
<task>
Run docaudit's incremental documentation audit for this repository.
</task>
<context>
Routine day-to-day check: verify that the docs impacted by changes since the last
clean audit anchor still match the current code and config.
</context>
<constraints>
Report-only. Do not edit any files — just produce the verdict and findings.
</constraints>

Run /docaudit:audit
```

## 2. Pre-release full sweep

Use this before tagging a release (or after a large batch of changes) to validate the
whole documentation corpus, not just the diff since the anchor.

```
<task>
Run a full, whole-corpus documentation audit ahead of a release.
</task>
<context>
We are about to cut a release. Verify every doc against the current source, not just
the changes since the last anchor.
</context>
<constraints>
Report-only. Do not edit any files.
</constraints>

Run /docaudit:audit --full
```

---

## 3. Scoped audit

Use this when you only care about one subsystem or a handful of docs right now.
`/docaudit:audit` has no scope/path flag — it always resolves the full impacted set for
the current change set: incremental mode combines mapped `impactMap` and heuristic hits,
supplements them with graphify/semantic candidates when available, and `--full` includes every
`docGlobs` document — so scoping happens on the prompt side:
name the docs/subsystem in `<scope>` and ask for their verdicts to be called out
explicitly in the summary.

```
<task>
Run a documentation audit and pay particular attention to the docs in scope below.
</task>
<context>
docaudit itself has no scope flag — it always audits the full impacted set for the
current change set. Use the scope below only to tell me which docs you must
double-check and report on explicitly, not to skip anything else it finds.
</context>
<scope>
docs/api-reference.md, docs/adoption.md, and anything under src/api/**
</scope>
<constraints>
Report-only. Do not edit any files.
</constraints>

Run /docaudit:audit, then confirm explicitly whether each doc listed in <scope> was
covered by the impacted set and what its verdict was.
```

---

## 4. Change-impact pre-check

Use this right before or right after making one specific change, to confirm which docs
it touches and whether they still hold up.

```
<task>
Check which documentation is impacted by a specific change and verify it against
that change.
</task>
<change>
Renamed the REST endpoint POST /v1/login to POST /v1/sessions in src/api/auth.py.
</change>
<constraints>
Report-only. Do not edit any files — list the impacted docs and their verdicts only.
</constraints>

Run /docaudit:audit and, in the report, call out specifically whether the docs
affected by the <change> above are consistent with it.
```

---

## 5. Initial adoption

Use this the first time docaudit runs in a repo that has no `.claude/doc-audit.json`
yet. `/docaudit:init` always shows the drafted config and waits for explicit approval
before writing anything — it never writes without a yes from you.

```
<task>
Bootstrap docaudit for this repository.
</task>
<context>
This repo has no .claude/doc-audit.json yet. Inventory the repo and draft a config.
</context>
<constraints>
Show me the full draft config with a one-line rationale per key, and wait for my
explicit approval before writing anything.
</constraints>

Run /docaudit:init
```

Add `--scaffold` to the command above if you also want project-tailored layer-skill
skeletons generated (`/docaudit:init --scaffold`) instead of relying on the generic
format/existence/semantic fallback.

---

## 6. Scheduled / non-interactive runs

Use this when docaudit is triggered unattended — a schedule, a loop, a CI-style
invocation — where nothing can pause on a clarifying question.

```
<task>
Run docaudit's audit as an unattended, non-interactive check.
</task>
<context>
This is a scheduled/periodic run. No one is available to answer questions or
approve anything mid-run.
</context>
<constraints>
Do not ask questions — make the best judgment call with what's already in the repo.
Report-only; do not edit any files. If .claude/doc-audit.json is missing, say so in
the report instead of trying to create one.
</constraints>
<report>
Return the roll-up verdict, the impacted docs with their per-doc verdicts, and any
non-blocking warnings. Keep it concise.
</report>

Run /docaudit:audit
```

---

## 7. Install the local harness, then run the first audit

Use this when adopting docaudit and you want the repository-local `/check-docs`,
`doc-lint`, and `scripts/check-docs.py` structure. `init` will inventory existing doc
tools and ask whether to integrate, adjust, keep, or install new ones.

```
<task>
Set up docaudit with its local documentation harness, then run the first full audit.
</task>
<context>
Inventory this repository's existing documentation tools. If there is no suitable
existing structure, install /check-docs, doc-lint, and scripts/check-docs.py.
</context>
<constraints>
Show and obtain approval for the harness choice and config before writing. After setup,
list the config and all three generated harness files that must be committed. Do not
change existing documentation during init.
</constraints>
<report>
After the approved files are written, run the first whole-corpus audit and report its
verdict, pre-flight result, and any files that need documentation fixes.
</report>

Run /docaudit:init --harness, then run /docaudit:audit --full
```

---

## 8. Approve pre-flight fixes before the audit

Use this when the cheap whole-tree checks find repairable documentation failures and you
want to fix only those approved files before the deeper audit continues.

```
<task>
Run docaudit and, if pre-flight finds FAIL results, offer to fix them before continuing.
</task>
<context>
The local documentation harness is configured. I want the deterministic whole-tree
checks to run before the deep per-document verification.
</context>
<constraints>
If pre-flight fails, choose “fix and audit” only after showing the findings and proposed
documentation paths. Edit only paths authorized by docaudit's fix-scope check. Do not
edit ADRs, decisions, logs, .claude files, or any path outside the approved set. Re-run
pre-flight after the fix and stop if the scope check detects another change.
</constraints>
<report>
Report the pre-flight decision and final findings, followed by the audit verdict.
</report>

Run /docaudit:audit
```
