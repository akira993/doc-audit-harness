# Adopting `docaudit` in a new project

A practical, end-to-end guide to installing the docaudit harness once and onboarding
any repository to it — from a 5-minute quick start to the config reference, the
impact-map design method, the verdict/anchor lifecycle, and the hard-won gotchas
from real-world use.

> 🌐 日本語版: [ADOPTION.ja.md](ADOPTION.ja.md)

> **docaudit is report-only.** It maps what changed to the docs that describe it,
> verifies them, drives `/code-review` + `/security-review`, and emits one
> **CONSISTENT / NEEDS FIX** verdict — but it **never edits your docs**. Every fix is
> yours to make. The only thing it writes is its own config (via `init`), its audit
> report, and the anchor state file.

---

## TL;DR — the 5-minute path

```bash
# 1) Install once, globally (skills-dir plugin)
cp -R /path/to/doc-audit-harness ~/.claude/skills/docaudit
#    start a NEW Claude Code session (or run /reload-plugins in the current one)
#    verify:  claude plugin list   → "docaudit@skills-dir  ✔ loaded"

# 2) In your repo, bootstrap a config (interactive: proposes → you approve → it writes)
cd ~/code/my-project
/docaudit:init
#    review the proposed .claude/doc-audit.json, then commit it

# 3) First audit (whole corpus). Report-only → fix what it flags, surgically.
/docaudit:audit --full
#    on a CONSISTENT verdict it writes .claude/state/last-doc-audit.json — commit it

# 4) From then on, just:
/docaudit:audit
#    incremental: only the docs impacted by changes since the anchor
```

Everything below is the detail behind these four steps.

---

## 1. Mental model — what docaudit actually does

docaudit adds the layer most doc tooling lacks: **"given the code/config that changed
since the last clean audit, which docs are now stale or wrong?"** It does this by
running five phases on each audit:

| Phase | What happens | Script / mechanism |
|------:|--------------|--------------------|
| 1 | **Baseline + diff** — read the anchor, compute the change set since it (merge-base diff + uncommitted + untracked), filtered by `diffGlobs`. No anchor ⇒ full mode. | `compute-baseline.sh` |
| 2 | **Impact resolution** — map changed files → impacted docs (explicit `impactMap` ∪ heuristic), plus `ssotSources` to re-verify, plus a `truncated` flag. | `resolve-impact.py` |
| 3 | **Change-impact verification** — one subagent per impacted doc adversarially checks *"does this doc still match the changed source?"* (PASS/WARN/FAIL). | Workflow fan-out + `doc-impact-verifier` agent |
| 4 | **Existing layers + reviews** — run your project's doc checks (or the built-in generic fallback), the boundary command, then `/code-review` + `/security-review`. | delegated commands / `generic-layers.py` |
| 5 | **Synthesize + anchor** — roll up to one verdict, write the report, and (only if CONSISTENT) update the anchor. | `write-anchor.sh` |

Key properties to internalize:

- **Report-only.** No phase edits your existing docs. Findings are proposals.
- **Anchor-based incremental.** The anchor (`.claude/state/last-doc-audit.json`) records
  *"the doc set was verified CONSISTENT as of commit X."* Subsequent runs diff from X.
- **Verdict rule:** any **FAIL** ⇒ NEEDS FIX (anchor NOT updated). **WARN never blocks**
  CONSISTENT (warnings are reported but allowed; the anchor means "no FAILs").
- **Two coverage strategies** for the format/existence/semantic layers: *delegate* to the
  project's own doc commands (rich, project-specific) or fall back to the *generic* built-in
  layers (portable, intentionally minimal). See §7.

---

## 2. Prerequisites

| Need | Why | Required? |
|------|-----|-----------|
| [Claude Code](https://code.claude.com/docs) | runs the `/docaudit:*` skills | yes |
| A **git repository** at the audit root | the engine diffs with git | yes (see §10 for sub-dirs) |
| [Python 3](https://www.python.org/) (standard library only) | the engine scripts; no `pip install` needed | yes |
| [`git`](https://git-scm.com/) | diff/anchor | yes |
| [`/code-review`, `/security-review`](https://code.claude.com/docs) | Claude Code built-in review skills (Phase 4) | optional — skipped + WARNed if absent |
| [`markdown-query` (mdq)](https://github.com/dahatake/skills) | Phase 0 whole-repo index + Phase 3 chunked doc reads (~90%+ savings on large docs; upstream bench 97–99%) | optional — auto-used when present (conditional-force); grep when absent |
| [`context-mode`](https://github.com/mksglu/context-mode) | Phase 1 git diff + Phase 4 `/code-review`·`/security-review` output processed in its sandbox (only distilled summaries enter context) | optional — auto-used when its `ctx_*` tools are present (conditional-force); read in full when absent |
| [CocoIndex](https://github.com/cocoindex-io/cocoindex) / [Serena](https://github.com/oraios/serena) (MCP) | richer code↔doc discovery during `init` | optional — falls back to grep/heuristic |
| Project doc tools (`/check-docs`, `doc-lint`, …) | richer Phase-4 layers via delegation | optional — generic fallback otherwise |
| [`skill-creator`](https://github.com/anthropics/skills) / [`superpowers:writing-skills`](https://github.com/obra/superpowers) | author & tailor the `--scaffold` layer skills | optional — only for `/docaudit:init --scaffold` |

The engine is **MCP- and server-independent** by design; none of the optional pieces are
required to get a useful audit — and `mdq`, when installed, is auto-applied for
token-optimized doc reads (conditional-force) but degrades to grep when absent.
Every audit prints an **mdq status line**: a 💡 install nudge when mdq is absent, or a
⚠ non-blocking WARN when mdq is installed but its index isn't firing (`empty-index` /
`search-broken` / `probe-error`).

`context-mode` is mdq's complement, not a competitor: **mdq optimizes Markdown *reads*,
context-mode optimizes the *processing of large machine output*.** When its `ctx_*` tools are
present, the audit runs the Phase-1 git diff and the Phase-4 `/code-review` + `/security-review`
results through context-mode's sandbox and pulls back only distilled summaries — the raw bytes
never enter context. It is conditional-force the same way (auto-used when available; opt out with
`"contextMode": {"enabled": false}` even when installed) and degrades silently when absent — the
engine needs no `bin`/`roots` for it because context-mode is a location-independent global plugin.
Every audit prints a non-blocking **context-mode status line** immediately after the mdq one:
💡 when not active, ✓ when active, ⚠ when installed but degraded (it never changes the verdict).

---

## 3. Install

### 3a. Global (recommended) — a "skills-dir" plugin

```bash
cp -R /path/to/doc-audit-harness ~/.claude/skills/docaudit
# optional: drop the dev cruft from the copy
rm -rf ~/.claude/skills/docaudit/.git ~/.claude/skills/docaudit/tests
```

A directory under **`~/.claude/skills/<name>/`** that contains `.claude-plugin/plugin.json`
auto-loads next session as `<name>@skills-dir` and exposes its skills + agents in **every**
project.

> ⚠️ **Use `~/.claude/skills/`, NOT `~/.claude/plugins/`.** `~/.claude/plugins/` is
> marketplace-cache territory tracked by `installed_plugins.json`; a bare copy there is
> **not** auto-discovered. (This is the #1 install gotcha.)

**Verify:**
```bash
claude plugin list                 # → docaudit@skills-dir  Version 0.4.4  Scope: user  ✔ loaded
claude plugin details docaudit     # component inventory + token cost
```
In an already-running session, run **`/reload-plugins`** so the slash commands register now
(otherwise they appear next session).

### 3b. Dev / per-session (no install)

```bash
cd ~/code/my-project
claude --plugin-dir /path/to/doc-audit-harness   # loads for this session only
```

### 3c. Updating an existing global install

The global copy is a **snapshot** — editing the source repo does **not** update it. After
pulling a new version, re-sync:
```bash
cp -R /path/to/doc-audit-harness/. ~/.claude/skills/docaudit/
# or just the scripts if that's all that changed:
cp /path/to/doc-audit-harness/skills/audit/scripts/*.py ~/.claude/skills/docaudit/skills/audit/scripts/
```

---

## 4. Onboard a project

### 4a. Automatic — `/docaudit:init` (recommended)

```bash
cd ~/code/my-project
/docaudit:init
```
It will:
1. **Inventory** the repo (doc dirs, front-matter convention, code dirs, existing doc tools,
   code→doc "mentions", index files) — deterministic, grep/find based.
2. **Draft** a `.claude/doc-audit.json` proposal and show it to you with a one-line rationale
   per key.
3. **Wait for your approval** (it never writes without it), then write the config.
4. Point you at the first audit.

`init` is **additive**: it only creates new files; it never edits existing docs. Add
`--scaffold` to also generate project-tailored layer-skill skeletons (§7).

> The inventory derives `docGlobs` from the directories that **actually** contain docs, so
> non-standard layouts (docs under `guide/`, `vps/`, …) are handled. Symlinked doc dirs and
> `node_modules`/`.venv` are excluded automatically. Still review the proposal — you know
> your repo's couplings better than a grep does.

### 4b. Manual — write `.claude/doc-audit.json` yourself

Copy `docs/examples/doc-audit.example.json` to `your-repo/.claude/doc-audit.json` and edit.
See §5 for the schema and §6 for the impact map.

---

## 5. Config reference — `.claude/doc-audit.json`

The per-project adapter. **All project-specific knowledge lives here; the plugin ships
none.** (Canonical schema: `skills/audit/references/config-schema.md`.)

| key | type | required | meaning |
|-----|------|----------|---------|
| `anchorPath` | string | yes | repo-relative path to the anchor state file (convention: `.claude/state/last-doc-audit.json`) |
| `diffGlobs` | string[] | yes | path globs that scope the change set. `**` matches across `/`; `*` does not. |
| `docGlobs` | string[] | no | files treated as docs for the heuristic/generic scan (default `["docs/**/*.md","*.md"]`) |
| `impactMap` | object[] | yes | `{changed: path\|glob, impacts: [docPath,…], note?: string}` — the heart (see §6). May start empty `[]`. |
| `ssotSources` | object[] | no | `{name, value?, liveSource, docsThatCite: [path\|path:line,…]}` — cross-doc value consistency |
| `docAuditCommands` | object | no | `{format, existence, semantic}` — slash-command/skill names to delegate Phase 4 to. Omit ⇒ generic fallback. |
| `boundaryCommand` | string | no | shell command for a project-boundary / forbidden-pattern check (e.g. `make check-boundary`) |
| `reviewCommands` | object | no | `{code, security}` — review command strings with effort embedded (e.g. `"/code-review high"`, `"/security-review"`) |
| `reportPath` | string | no | report output template; supports `<YYYY-MM-DD>` and a `[_NN]` collision suffix |
| `maxImpactedDocs` | number | no | cap on impacted docs (default 200); overflow sets `truncated` (surfaced, never silent) |
| `heuristics` | object | no | `{minIdentifierLength:int, excludeBasenames:[string,…]}` — tune heuristic recall noise |
| `frontMatterFields` | string[] | no | generic `format` layer requires these front-matter fields on every doc (WARN if missing); omit to skip |
| `indexFiles` | string[] | no | generic `semantic` layer link-roots for orphan detection (default: any `README.md` in the doc tree) |

Rules: `impacts` entries are **doc paths only** — put commentary in `note`. `changed` is a
single path or a glob. Glob semantics are the engine's own: `**`=any incl `/`, `*`=any excl
`/`, `?`=one non-`/`.

A minimal viable config is just `anchorPath` + `diffGlobs` + `impactMap` (the latter may be
`[]`, relying on the heuristic until you grow it).

---

## 6. Building a good `impactMap` (the heart)

The impact map is what makes the audit *change-driven*. Each entry says **"when this
source path changes, re-check these docs."**

```json
{ "changed": "src/api/**", "impacts": ["docs/api-reference.md", "README.md"],
  "note": "public API surface documented in api-reference.md + README quickstart" }
```

**Two signals, combined as a UNION:**
- **Mapped (precision):** explicit `impactMap` entries → high-confidence couplings.
- **Heuristic (recall):** if a changed file's basename/stem appears in a doc's text, that doc
  is added as a candidate and surfaced as a **`mapGapCandidate`** — a hint to add a real
  mapping. The heuristic only *adds*; it never removes a mapped doc.

**How to seed it:**
1. List your top-level code/config dirs and key files (`src/`, `scripts/`, `Makefile`,
   config files, schema/migrations, IaC, CI).
2. For each, grep your docs for mentions to find what documents it.
3. Write `{changed, impacts, note}` entries for the real couplings. Start small — the
   heuristic + `mapGapCandidates` will reveal the rest over time.
4. After each audit, promote recurring `mapGapCandidates` into explicit mappings.

**`ssotSources`** is for *values* repeated across docs (versions, IPs, sizes). It flags a
re-check when a **changed file** is one of the `docsThatCite` entries, or is the file in
`liveSource`. The harness compares the value **textually across docs** (it does **not**
execute `liveSource` — server/command sources are recorded for manual follow-up).

---

## 7. Delegate vs generic fallback (Phase 4)

- **If your project already has doc tooling** (e.g. `/check-docs`, `doc-lint`,
  `/review-docs`), wire them:
  ```json
  "docAuditCommands": { "format": "/review-docs", "existence": "/check-docs", "semantic": "doc-lint" }
  ```
  The audit delegates to them whole-tree. Invoke each exactly as named (a *skill* like
  `doc-lint` has no leading slash; a *command* does).
- **If it doesn't,** omit `docAuditCommands`. Phase 4 falls back to the built-in
  `generic-layers.py` — a portable baseline:
  - `format`: relative-link resolution (broken ⇒ FAIL) + optional `frontMatterFields` (missing ⇒ WARN).
  - `existence`: conservative repo-path-token resolution (non-resolving ⇒ WARN).
  - `semantic`: orphan detection (unlinked doc ⇒ WARN).
  The generic baseline is **intentionally weaker** than bespoke tools.
- **`/docaudit:init --scaffold`** generates *project-tailored* layer-skill skeletons into your
  `.claude/skills/` and wires `docAuditCommands` to them, then helps you flesh them out with
  `skill-creator` / `writing-skills`. Opt-in; for projects that want richer, owned checks.

---

## 8. Running audits — the verdict & anchor lifecycle

- **`/docaudit:audit --full`** — whole-corpus deep audit. Use it for the first run, after big
  changes, or periodically. Always used automatically when no anchor exists.
- **`/docaudit:audit`** — incremental: scopes to docs impacted by changes since the anchor.
- **Verdict:** `FAIL` ⇒ **NEEDS FIX** (anchor not updated). Only `WARN`/`PASS` ⇒ **CONSISTENT**
  (anchor updated). Severity mapping: Phase-3 verdicts are used directly; for Phase-4 tools,
  high-severity → FAIL, medium → WARN.
- **Anchor:** written **only on CONSISTENT**, recording the current HEAD SHA. **Commit it**
  (convention: a `docs(audit): …` commit) so the baseline is shared and survives squash-merges.

**Correct anchor ordering** (so the anchor records the *consistent* state):
1. Fix findings and **commit** them.
2. Re-run `--full`; on CONSISTENT the engine writes the anchor at the now-current SHA.
3. **Commit the anchor** (+ report) as a separate, meta commit.

---

## 9. First-audit playbook

This mirrors a real onboarding. Expect the first `--full` to find genuine drift — that's the
point.

1. **Run** `/docaudit:audit --full`. Read the report at `reportPath`.
2. **Triage every finding in context — do not trust raw counts.** A "broken link" inside a
   fenced code block is a false positive; a "stale 予定/TODO" inside a historical plan/log or a
   "future roadmap" section is *not* stale. Verify before you touch anything.
3. **Fix only genuine FAILs, surgically** — change only what the finding names. Never rewrite
   ADRs or historical logs (append a superseding note instead); never "tidy" adjacent content.
4. **Re-run** `--full`. Repeat until verdict = **CONSISTENT**.
5. **Write + commit the anchor.** You're now on incremental.
6. **Triage WARNs separately** (they didn't block the anchor): index any orphan docs, decide
   whether forward-looking "予定/future" language is legitimate (usually yes), tune the config
   (§11) so future runs don't re-flag noise.

---

## 10. Hard-won gotchas (read this)

- **Sub-directory targets aren't git roots.** If you point docaudit at a sub-project that is
  *not its own git repo*, git resolves to the parent repo and returns parent-relative paths,
  which mismatch a sub-dir-relative config — so **incremental/anchor diffing breaks**. Two
  options: (a) **full-mode-only**: write a config scoped to the sub-dir's own content, omit the
  anchor (so every run is `--full`), and note the constraint in a `_note` key; or (b) **fold the
  sub-project into the parent repo's config** (add its doc globs + impact-map entries there).
  Full-mode works fine for small sub-projects.
- **Symlinked doc dirs are not traversed** (`os.walk(followlinks=False)`). A `docs/ → ../docs`
  symlink won't be scanned from the sub-project; audit the symlink *target* from its real repo
  instead.
- **`node_modules`/`.venv`/`dist`/… are pruned** from doc scans. (If you run an older build,
  scope `docGlobs` tightly to avoid scanning vendored markdown.)
- **Heuristic over-count on common filenames.** A changed `*/SKILL.md`, `*/README.md`, etc.
  whose basename token appears in many docs floods the heuristic. The mapped docs are the
  correct ones; add noisy basenames to `heuristics.excludeBasenames` or raise
  `minIdentifierLength`. `truncated` is always surfaced — never silently dropped.
- **Forward-looking language is not "stale."** "予定 / future / TODO / 将来拡張" inside
  roadmaps, proposals, requirements, and historical plan/spec/log dirs are legitimate.
  Exclude those dirs from the stale-claim scan; don't edit roadmap text to satisfy a heuristic.
- **ADRs and logs are append-only.** The audit is report-only and proposes a *new* ADR /
  superseding note rather than a rewrite. Honor that when fixing.
- **`/security-audit` doesn't exist** — the real command is `/security-review` (the harness
  normalizes it). `/code-review` operates on the working diff; both are **no-ops on a clean,
  synced tree** (no pending diff) — that's expected, not a failure.
- **The global install is a snapshot** — re-sync after updating the source (§3c).
- **Never fabricate a CONSISTENT anchor.** If you can't actually verify consistency (e.g. you
  skipped a layer), don't write the anchor. NEEDS FIX with an honest report is the correct
  outcome.

---

## 11. Customization & tuning

- **Heuristic noise:** `heuristics.minIdentifierLength` (default 5; raise to 6–7 for noisy
  repos) and `heuristics.excludeBasenames` (merged with built-in generics like
  `readme.md`/`index.md`/`skill.md`).
- **Cap:** `maxImpactedDocs` (default 200) bounds the fan-out; overflow is reported.
- **Scope:** keep `diffGlobs` to real source/config; keep `docGlobs` to real docs (exclude
  generated/build output, vendored trees).
- **Reports:** `reportPath` (e.g. `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md`); ensure the dir
  exists and the report carries your repo's front-matter convention if you index it.
- **Generic format strictness:** set `frontMatterFields` to enforce a front-matter contract;
  set `indexFiles` to define what "linked" means for orphan detection.

---

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/docaudit:*` not available | install location / not reloaded | use `~/.claude/skills/docaudit`; run `/reload-plugins` or restart; check `claude plugin list` |
| "this repo has no adapter" | no `.claude/doc-audit.json` | run `/docaudit:init` or create it manually (§5) |
| Audit always full / huge `changed` set | no/invalid anchor, or `diffGlobs` too broad | run a clean `--full` to write an anchor; tighten `diffGlobs` |
| Flood of heuristic "impacted" docs | common basename token | add to `excludeBasenames` / raise `minIdentifierLength`; promote real couplings to `impactMap` |
| Tons of "broken link" findings | links inside code fences, or generated docs scanned | verify in context (code-fence false positives); tighten `docGlobs` |
| Many "stale 予定" findings | scanning historical/roadmap docs | exclude plan/spec/log dirs from the stale scan; these are usually legitimate |
| Incremental misses changes in a sub-dir | sub-dir is not a git root | use full-mode-only or fold into the parent (§10) |
| `/code-review` / `/security-review` "did nothing" | clean, synced tree (no pending diff) | expected — commit/leave changes to review, or ignore |
| Updated the plugin but behavior unchanged | global install is a snapshot | re-sync (§3c) |

---

## 13. Per-project adoption checklist

- [ ] docaudit installed globally and `claude plugin list` shows it loaded
- [ ] `/docaudit:init` run (or `.claude/doc-audit.json` written by hand) and **reviewed**
- [ ] `anchorPath`, `diffGlobs`, `impactMap` present; `docGlobs` scoped (no vendored/build trees)
- [ ] `docAuditCommands` wired (if the project has doc tools) or omitted (generic fallback)
- [ ] `reviewCommands` + `reportPath` set; report dir exists
- [ ] config committed
- [ ] `/docaudit:audit --full` run; findings triaged **in context** and fixed surgically
- [ ] verdict = CONSISTENT; anchor written and **committed**
- [ ] WARNs reviewed; config tuned to suppress genuine noise
- [ ] (optional) `--scaffold` used for project-tailored layers
- [ ] (sub-dir target only) full-mode `_note` recorded, or folded into parent

---

## Appendix — plugin file map

```
doc-audit-harness/
├── .claude-plugin/plugin.json          # manifest (name: docaudit)
├── skills/
│   ├── audit/SKILL.md                  # /docaudit:audit [--full] — 5-phase orchestrator
│   │   ├── scripts/compute-baseline.sh # Phase 1: anchor → change set (merge-base)
│   │   ├── scripts/resolve-impact.py   # Phase 2: change set → impacted docs (UNION)
│   │   ├── scripts/write-anchor.sh     # Phase 5: anchor write (CONSISTENT only)
│   │   ├── scripts/generic-layers.py   # Phase 4 fallback: format/existence/semantic
│   │   ├── scripts/inventory.py        # init: deterministic repo inventory
│   │   ├── scripts/scaffold.py         # init --scaffold: tailored layer skeletons
│   │   └── references/{config-schema,default-heuristics,workflow-template}.*
│   └── init/SKILL.md                   # /docaudit:init [--scaffold]
│                                        #   (generic format/existence/semantic layers are
│                                        #    realized as generic-layers.py above, NOT skill dirs)
├── agents/doc-impact-verifier.md       # per-doc verification subagent
├── docs/ADOPTION.md                    # ← this guide (English)
├── docs/ADOPTION.ja.md                 # Japanese translation
├── docs/examples/doc-audit.example.json # copy-paste config template (see §4b)
└── tests/                              # engine unit tests (python3 -m unittest discover -s tests -t .)
```

For the full design rationale (why each decision was made), see the originating project's
design spec referenced in the top-level `README.md`.
