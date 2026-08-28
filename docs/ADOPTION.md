# Adopting `docaudit` in a new project

A practical, end-to-end guide to installing the docaudit harness once and onboarding
any repository to it — from a 5-minute quick start to the config reference, the
impact-map design method, the verdict/anchor lifecycle, and the hard-won gotchas
from real-world use.

> 🌐 日本語版: [ADOPTION.ja.md](ADOPTION.ja.md)

> **docaudit is report-only by default.** It maps what changed to the docs that describe it,
> verifies them, runs `/security-review`, offers `/code-review` for the user to run
> (it is not model-invocable), and emits one
> **CONSISTENT / NEEDS FIX / REFUSED** verdict. The sole documentation-edit exception is
> a pre-flight FAIL that you explicitly choose to fix; `fix-scope.py` then limits edits
> to approved doc paths and rejects changes elsewhere. Non-interactive runs never edit.

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
| 3 | **Change-impact verification** — one verifier per impacted doc adversarially checks *"does this doc still match the changed source?"* (PASS/WARN/FAIL). | Workflow fan-out by default; opt-in `codex-dispatch.py` backend |
| 4 | **Existing layers + reviews** — run your project's doc checks (or the built-in generic fallback), the boundary command, then `/security-review`; offer `/code-review` for the user to run because it is not model-invocable. | delegated commands / `generic-layers.py` |
| 5 | **Gate + report + anchor** — roll up to one verdict, write the report while holding the run lock, and (only if CONSISTENT) update the anchor. | `write-template.py` + `decide-verdict.py` |

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
| [`/code-review`, `/security-review`](https://code.claude.com/docs) | Claude Code built-in review skills (Phase 4); `/security-review` runs in the audit, while `/code-review` is user-invocation-only | optional — `/security-review` runs when available; `/code-review` is offered to the user and is not model-invocable |
| [`markdown-query` (mdq)](https://github.com/dahatake/skills) | Phase 0 whole-repo index + Phase 3 chunked doc reads (~90%+ savings on large docs; upstream bench 97–99%) | optional — auto-used when present (conditional-force); grep when absent |
| [`context-mode`](https://github.com/mksglu/context-mode) | Phase 1 git diff + Phase 4 `/code-review`·`/security-review` output processed in its sandbox (only distilled summaries enter context) | optional — auto-used when its `ctx_*` tools are present (conditional-force); read in full when absent |
| [`ax`](https://ax.yusuke.run/) | Phase 3: lets doc-impact-verifier corroborate a doc's external-URL-dependent claims via a read-only, GET-only fetch (static HTML only — no JS-rendered SPA support) | optional — auto-used when installed (conditional-force); external-URL claims go unverified when absent |
| [`codex`](https://github.com/openai/codex) (`@openai/codex` CLI) | optional Phase-3 per-document backend, and Phase 4's fourth adversarial review, both via `codex exec -s read-only` | optional — Phase 3 requires explicit `phase3Backend:"codex"`; Phase 4 review is conditional-force; **completed `critical`/`high` review findings CAN block the verdict** — see below |
| [`codegraph`](https://github.com/colbymchenry/codegraph) | Phase 3: lets doc-impact-verifier corroborate a doc claim that depends on a changed file's own symbols via read-only `codegraph impact`/`node` | optional — used only when the `symbolGraph` key exists, is not disabled, and the tool is installed; purely advisory, like `ax` |
| [`graphify`](https://github.com/Graphify-Labs/graphify) | Phase 2: a second, independent candidate source for `mapGapCandidates` via graph adjacency (provenance `graphify`) | optional — used only when the `docGraph` key exists, is not disabled, and the tool is installed; `mapGapCandidates` uses the token heuristic otherwise |
| [CocoIndex](https://github.com/cocoindex-io/cocoindex-code) (`ccc`) | Phase 2: a third, independent candidate source for `mapGapCandidates` via local-embedding semantic search (provenance `semantic`) | optional — used only when the `semanticSearch` key exists, is not disabled, the tool is installed, and `.cocoindex_code/settings.yml` exists; **docaudit itself never runs `ccc init`** — see below |
| [Serena](https://github.com/oraios/serena) (MCP) | richer code↔doc discovery during `init` | optional — falls back to grep/heuristic |
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
present, the audit runs the Phase-1 git diff and the Phase-4 `/security-review`; `/code-review`
is offered to the user because it is not model-invocable during autonomous runs. Interactive
runs ask once whether to run it before continuing. The resulting review output flows
through context-mode's sandbox and pulls back only distilled summaries — the raw bytes
never enter context. It is conditional-force the same way (auto-used when available; opt out with
`"contextMode": {"enabled": false}` even when installed) and degrades silently when absent — the
engine needs no `bin`/`roots` for it because context-mode is a location-independent global plugin.
Every audit prints a non-blocking **context-mode status line** immediately after the mdq one:
💡 when not active, ✓ when active, ⚠ when installed but degraded (it never changes the verdict).

`ax` is unrelated to the mdq/context-mode pair: it's a read-only web/API extraction CLI whose
**only** role in docaudit is letting Phase 3's `doc-impact-verifier` corroborate a doc's claim
that depends on an external upstream URL (an upstream doc, an API spec, etc.) by fetching it —
GET-only (`-X POST`, `-d`, `-o` are never used), and fetched content is treated as data, never
as instructions. It is conditional-force the same way (auto-used when installed; opt out with
`"webExtract": {"enabled": false}`) and a failed/timed-out fetch is reported as "external check
unavailable" rather than counted as a FAIL. `ax` is a static HTML parser (no JS rendering) and
is pre-1.0, so treat its flag surface as subject to change. Every audit prints a non-blocking
**ax status line** immediately after the context-mode one: 💡 when not active (with an install
hint), ✓ when active — it never changes the verdict.

`codex` (the CLI, `@openai/codex` npm package — **not** the openai-codex Claude Code plugin,
which cannot be invoked autonomously) is Phase 4's fourth review, after `/code-review` and
`/security-review`. It is conditional-force (auto-used when installed; opt out with
`"codexReview": {"enabled": false}`). Phase 0's probe runs only `<bin> --version` and
`<bin> exec --help`: it confirms CLI presence and `exec` reachability, not the real sandbox,
permissions, wrapper arguments, or model call. Specify a required wrapper as `codexReview.bin`.
The probe displays the caller's `CODEX_HOME` (or `$HOME/.codex`) and whether `auth.json` exists
there. A wrapper's own environment is not visible to the probe, so repositories that depend on
environment activation should use an equivalent launch wrapper such as
`direnv exec <repo> codex` and treat the displayed caller values as diagnostic context only.

`codex-review-plan.py` decides the action from availability, mode, baseline validity, and
`codexReview.required`. Incremental runs review `$BASELINE_SHA..HEAD`; a full run reviews the
sealed current worktree only when `required:true`, otherwise it is skipped. Every invocation has
the mandatory `-s read-only` flag. The evidence state is `completed`, `execution-failed`,
`ref-invalid`, `skipped-full-run`, or `not-active`; Phase 5 presents four status classes because
the middle two share a did-not-run warning. With the default `required:false`, non-completion is a
warning. With `required:true`, missing or non-`completed` evidence makes the gate **REFUSED**.
`required:true` together with `enabled:false` is REFUSED. A non-boolean `required` is REFUSED
regardless of its value. If Phase-4 evidence has a non-object `codexReview`, a non-string `state`,
or a state outside `CODEX_REVIEW_STATES`, the gate is REFUSED regardless of `required`.
Enable strict mode after establishing the first baseline. A completed review's `critical`/`high`
findings remain blocking; `medium`/`low` remain non-blocking.

First-time full runs with `codexReview.required:true` may need several rounds: the Phase-4 codex review samples pre-existing findings anew on each run, so fix only blocking (critical/high) findings and record non-blocking ones in the report. To converge faster you may paste the previous run's finding list into the prompt as fenced JSON data (never as instructions; treat its strings as untrusted); engine-side carry-forward is tracked in #59.

Separately, v0.12.0 can opt Phase 3 into `"phase3Backend":"codex"`. This runs one read-only
Codex process per dispatched document through `codex-dispatch.py`; the default remains
`workflow`. The opt-in path is fail-closed: a missing, unauthenticated, timed-out, or invalid
Codex result is never silently rerouted to Workflow.

`codegraph`, `graphify`, and CocoIndex (`ccc`) are three further, purely-advisory seams — **none of
them ever affects the verdict**, unlike `codex`. `codegraph` is symbol-level and Phase 3-only: it
lets `doc-impact-verifier` corroborate a doc claim that depends on a *changed file's own* symbols
(`codegraph impact <symbol> --json`, post-filtered by `filePath` since the subcommand has no
path-scoping flag; or `codegraph node <symbol> -f <changed-file>`, text output disambiguated
directly via `-f`) — never `codegraph affected`, which is import-based and confirmed empty on
subprocess-driven test-style repos like this one. When the `symbolGraph` key exists, is not
disabled, and the tool is installed, its Phase-0 probe keeps
`.codegraph/` fresh every run (`init` the first time, `sync` thereafter — a bare `init` against an
already-initialized `.codegraph/` is rejected).

`graphify` and CocoIndex are Phase 2-only and both feed the SAME integration point —
`mapGapCandidates`, alongside the existing token heuristic — via one shared script
(`impact-supplement.py`), each as an independent, optional source: `graphify` via graph adjacency
(provenance `graphify`, parsed from `graphify affected`/`graphify query --budget`'s confirmed
fixed-format TEXT output — neither has `--json`), CocoIndex via local-embedding semantic search
(provenance `semantic`, from `ccc search --json`, admitted only when `score >= minScore`, default
`0.4` — `ccc search` has **no built-in relevance cutoff**, confirmed: irrelevant queries still
return `limit` results, just at a visibly lower score band). Both are key-gated: their key must
exist, not be disabled, and their tool must be installed before they merge into
`mapGapCandidates` using ONLY the residual slots left after `resolve-impact.py`'s own cap, in strict
priority `mapped` ≥ `regression` ≥ `heuristic` ≥ `graphify` ≥ `semantic` — neither ever displaces an existing
candidate (Issue #8 anti-regression). **The one rule that matters most for CocoIndex: docaudit
itself NEVER runs `ccc init`** — `ccc init` auto-appends `/.cocoindex_code/` to the repo's
`.gitignore` (confirmed real side effect), a write the report-only audit phase must not trigger
mid-run, so an absent `.cocoindex_code/settings.yml` marker is its own silent `not-initialized` degrade state, distinct
from "not installed"; initialization only happens inside `/docaudit:init`, behind explicit user
approval that discloses the `.gitignore` write. The probe compares `.gitignore` before and after
`ccc index`; any change is reported as `gitignore-modified` and is never reverted by the audit.

Impact provenance is `mapped` for `impactMap` only, `regression` for a recheck of a prior FAIL only when its current content hash matches history (not an impactMap-gap candidate), `heuristic` for heuristic only, `both` when
both reach the same document, `graphify` or `semantic` for their optional supplement, and `full`
for every `docGlobs` document in a no-anchor or explicit `--full` run.

A healthy configuration reaches most selected documents through `mapped`; the token `heuristic`
should be residual coverage for couplings not yet promoted to `impactMap`. Audit cost is driven
mainly by anchor age, not by `maxImpactedDocs`: measurements on this repository found about 92
documents (roughly 3.6M tokens) for an old anchor, versus a median of about 18 documents for a
single-commit window.

`regressionRecheck.enabled` is opt-in. It adds the latest prior FAIL using provenance `regression`
only when the document's current content hash matches history; it is not an `impactMap`-gap candidate. A single verifier
run can vary, so fixing N reported findings and rerunning does not guarantee `CONSISTENT`. Gate
counts `verdictFlipsUnchangedContent` when content, contract version, and backend match but the
verdict changes. Code-side changes can legitimately cause that result even when document content
does not change; `verdictFlipsUnchangedContentSameChangeSet` is the M-item subset with the same
change set, and is the lower bound for pure instability. When one defect is found, sweep the same
defect class across the relevant corpus instead of repairing only the reported instances.

Every audit prints three further non-blocking status lines immediately after the codex-review one:
**symbol-graph** (💡 not configured / ⚠ invalid / 💡 not active / ✓ active / ⚠ index build failed), **doc-graph** (💡 not configured / ⚠ invalid / 💡 not active /
✓ active + `graphify-out/` gitignored / ⚠ active but `graphify-out/` NOT gitignored — add it), and
**semanticSearch** (💡 not configured / ⚠ invalid / 💡 not active-not-installed / 💡 not active-not-initialized, with a
`/docaudit:init` hint / ✓ active, naming the configured `minScore` / ⚠ index update failed / ⚠ gitignore-modified) — none
of the three ever changes the verdict.

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
claude plugin list                 # → docaudit@skills-dir  Version 0.13.2  Scope: user  ✔ loaded
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

**v0.12.0 behavior changes:** the deterministic gate now writes the report while it holds the
run lock. The orchestrator first passes the placeholder-bearing body to `write-template.py`;
after the gate, `previousReportStatus` surfaces an earlier `pending`, `failed`, or
`written-durability-unknown` report state. Phase 3 also has the explicit, fail-closed
`phase3Backend:"codex"` opt-in described below. Report filenames and front-matter dates are
derived from the run ID in **UTC**, so they may differ from the local date around midnight.

**v0.13.2 behavior changes:** omitted `docGlobs` now defaults to
`["docs/**/*.md","*.md"]` for pre-flight fix classification; `CLAUDE.md` and `AGENTS.md`
are always denied (case-insensitive); an absent `docGraph` / `semanticSearch` /
`symbolGraph` key reports `not-configured` and never runs the tool; an invalid key reports
`invalid-config`. CocoIndex counts as initialized only when `.cocoindex_code/settings.yml`
exists; a `.gitignore` change during `ccc index` reports `gitignore-modified` and is never
reverted by the audit; any `seal-run.py` or `read-manifest.py` failure releases the run and
stops; `read-manifest.py` rejects an unsealed manifest; configs that relied on auto-detection
must add the key via `/docaudit:init`.

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
2. **Ask once about the local harness.** With no existing candidates, choose whether to install
   `/check-docs` + `doc-lint` + `scripts/check-docs.py`. With candidates, choose integrate,
   adjust, keep untouched, or install new. The stored states are `installed`, `declined`,
   `integrated`, `adjusted`, and `existing-untouched`.
3. **Draft** a `.claude/doc-audit.json` proposal and show it to you with a one-line rationale
   per key.
4. **Wait for your approval** (it never writes without it), then write the config.
5. Point you at the first audit.

`init` is **additive**: it only creates new files; it never edits existing docs. Add
`--scaffold` to also generate project-tailored layer-skill skeletons (§7). Use
`--harness` to operate on the harness when a config already exists, `--reask` to replace a
stored decision, and `--harness --refresh` to refresh only unmodified stamped templates.
When `installed` is selected, commit the config and all three generated files together:
`.claude/commands/check-docs.md`, `.claude/skills/doc-lint/SKILL.md`, and
`scripts/check-docs.py`.

Existing unmodified stamped 0.10.1, 0.11.0, 0.12.0, 0.13.0, or 0.13.1 templates can be updated directly to 0.13.2 with
`/docaudit:init --harness --refresh`; user-modified templates remain untouched.

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

This table is an excerpt of the main keys. See `skills/audit/references/config-schema.md` for the complete list.

| key | type | required | meaning |
|-----|------|----------|---------|
| `anchorPath` | string | yes | repo-relative path to the anchor state file (convention: `.claude/state/last-doc-audit.json`) |
| `diffGlobs` | string[] | yes | path globs that scope the change set. `**` matches across `/`; `*` does not. |
| `docGlobs` | string[] | no | files treated as docs for the heuristic/generic scan (default `["docs/**/*.md","*.md"]`); pre-flight fix paths use the same default. |
| `impactMap` | object[] | yes | `{changed: path\|glob, impacts: [docPath,…], note?: string, source?: string}` — the heart (see §6). `source:"audit-scope"` is generated. May start empty `[]`. |
| `auditScope` | object | no | `{path,sha256,importedAt,rules}` importer metadata; do not edit it by hand. |
| `ssotSources` | object[] | no | `{name, value?, liveSource, docsThatCite: [path\|path:line,…]}` — cross-doc value consistency |
| `docAuditCommands` | object | no | `{format, existence, semantic}` — slash-command/skill names to delegate Phase 4 to. Omit ⇒ generic fallback. |
| `boundaryCommand` | string | no | shell command for a project-boundary / forbidden-pattern check (e.g. `make check-boundary`) |
| `reviewCommands` | object | no | `{code, security}` — review command strings with effort embedded (e.g. `"/code-review high"`, `"/security-review"`) |
| `reportPath` | string | no | report output template; supports `<YYYY-MM-DD>` and a `[_NN]` collision suffix |
| `maxImpactedDocs` | number | no | cap on impacted docs (default 200); overflow sets `truncated` (surfaced, never silent) |
| `heuristics` | object | no | `{minIdentifierLength:int, excludeBasenames:[string,…], saturationWarnRatio:number=0.5, excludeDocPathTokens:bool=false}` — tune heuristic recall noise; `0` disables the saturation warning. |
| `regressionRecheck` | object | no | `{enabled:bool=false}` — opt-in recheck of latest prior FAILs whose document content is unchanged. |
| `frontMatterFields` | string[] | no | generic `format` layer requires these front-matter fields on every doc (WARN if missing); omit to skip |
| `layerGlobs` | object | no | per-layer generic exclusions for `format`, `existence`, and `semantic`. |
| `frontMatterOverrides` | object[] | no | ordered generic `format` field overrides selected by matching globs. |
| `indexFiles` | string[] | no | generic `semantic` layer link-roots for orphan detection (default: any `README.md` in the doc tree) |
| `auditReportsInCorpus` | boolean | no | only literal `true` keeps matching audit reports in corpus scans. |
| `harness` | object | no | `{state,decidedAt,engineVersion}`; state is one of the five decisions above. Absence is the compatible `unset` state. |
| `verdictCache` | object | no | `{enabled:true,minConsecutivePasses:2}`; allowed pass count is 2..10, otherwise cache is disabled with a WARN. |
| `phase3Backend` | string | no | `"workflow"` (default) or `"codex"`; invalid values are rejected when the run is sealed. |
| `phase3CodexTimeoutSeconds` | number | no | Codex per-document execution timeout; integer 60..3600, default 600, used only by the Codex Phase-3 backend. |
| `models` | object | no | nested `{light:{enabled,maxChanged,maxImpacted,maxDiffLines,maxDiffBytes,sensitiveTokens}}` deterministic light-run limits. |
| `codexReview` | object | no | `{enabled,required:bool=false,bin,model?,timeoutMs?}`; `required:true` REFUSES a non-completed review. Enable it after establishing a baseline. |
| `digestExclude` | string[] | no | Non-glob literal paths only — each accepted prefix itself or any path below it (a trailing `/` is normalized away). Values containing `*`, `?`, or `[` are rejected by `tree-digest.py`; `seal-run.py` fails (exit 2) and the run is not sealed. Accepted `digestExclude` prefixes: `.claude/state`, `.claude/worktrees`, `.mdq`, `.codegraph`, `graphify-out`, `.cocoindex_code`. |
| `protectedGlobs` | string[] | no | extra paths denied to pre-flight fixes; built-in ADR/decisions/logs/`.claude` and case-insensitive `CLAUDE.md`/`AGENTS.md` basename protection cannot be removed. |

Rules: `impacts` entries are **doc paths only** — put commentary in `note`. `changed` is a
single path or a glob. Glob semantics are the engine's own: `**`=any incl `/`, `*`=any excl
`/`, `?`=one non-`/`.

A minimal viable config is just `anchorPath` + `diffGlobs` + `impactMap` (the latter may be
`[]`, relying on the heuristic until you grow it).

---

## 6. Building a good `impactMap` (the heart)

### When `audit-scope.json` exists

`audit-scope.json` is the source of truth; `impactMap` entries marked `source:"audit-scope"` are generated output. Phase 0 stops on drift. Restore it with `/docaudit:init --import-audit-scope`. Importing between runs does not need `--accept-config`; exit 6 applies only when an active run refuses a config change. An active run lock rejects imports. `{"impact":"none"}` suppresses generated mapping, but the heuristic can still select that document.

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
execute `liveSource` — server/command sources are recorded for manual follow-up). A URL
`liveSource` (http/https) is likewise not supported: it is never fetched or verified, and
the audit emits a warning so you track that value manually.

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
  - `existence`: repo-path-token resolution from backticks and bare ASCII paths
    (a non-resolving concrete backtick file ⇒ FAIL; other non-resolving paths ⇒ WARN).
  - `semantic`: orphan detection (unlinked doc ⇒ WARN).
  The generic baseline is **intentionally weaker** than bespoke tools.
- **If `init` installs the v0.10 harness,** it writes this fixed mapping, used by
  pre-flight and Phase 4:
  ```json
  "docAuditCommands": {
    "existence": "/check-docs --only existence",
    "format": "/check-docs --only format",
    "semantic": "doc-lint"
  }
  ```
  The copied engine also supports `scripts/check-docs.py --format text --exit-code` and
  emits machine-readable `SUMMARY` and `VERDICT` lines.
- **`/docaudit:init --scaffold`** generates *project-tailored* layer-skill skeletons into your
  `.claude/skills/` and wires `docAuditCommands` to them, then helps you flesh them out with
  `skill-creator` / `writing-skills`. Opt-in; for projects that want richer, owned checks.

---

### Phase 3 structural blind spots

**Phase 3 alone does not guarantee** cross-document consistency (for example, a guide says
`.dev.vars` while `.env.example` and source say `.env.local`), `X.md §N`-style references outside
`docGlobs` (source comments, dotfiles, or generated-file headers), or that a procedure's
prerequisites such as a running development server are satisfiable. Phase 4 code/security review,
Codex review (incremental, or full with `codexReview.required`), and the gate's sibling scan are
cross-cutting complementary layers. The Codex review prompt explicitly checks these three areas.

---

## 8. Running audits — the verdict & anchor lifecycle

- **`/docaudit:audit --full`** — whole-corpus deep audit. Use it for the first run, after big
  changes, or periodically. Always used automatically when no anchor exists. Full mode treats
  every `docGlobs` document as impacted and disables the cache.
- **`/docaudit:audit`** — incremental: scopes to docs impacted by changes since the anchor.
- **Run ledger + lock:** the audit first creates `.claude/state/docaudit-run/<runid>/` and
  exclusively creates the sibling `lock`. There is no TTL or automatic takeover. A stale lock
  requires the explicit, stop-only `/docaudit:audit --break-lock` operation; a gate-held lock
  cannot be broken.
- **Pre-flight (Phase 0.5):** after the run opens and before baseline/seal, script-backed active
  harness commands run across the whole tree; model-driven commands are recorded in
  `preflight.commands` as skipped and run once in Phase 4. On FAIL, an interactive run asks “fix and audit”,
  “continue without fixing”, or “stop”. Only the first choice may edit, and `fix-scope.py`
  limits it to approved docs. Non-interactive runs retain the FAIL evidence and never edit.
- **Sealed evidence:** the orchestrator carries one SHA-bearing `EVIDENCE` object. Before
  verifier fan-out, `seal-run.py` fixes HEAD, the complete change-set hash, and the worktree
  digest, including the resolved Phase-3 backend. `decide-verdict.py` reads each evidence file once, checks verifier returns against
  assigned paths, and is the sole writer of history, last-run state, and the anchor. Old flat
  files under `docaudit-run/` are ignored.
- **Deterministic cache:** `plan-dispatch.py` skips Phase 3 only when a doc has the configured
  number (default 2) of consecutive PASS records with identical doc content, `changeSetSha`,
  contract version, and backend. Old history without a backend means `workflow`.
  Missing/corrupt history is a cold start; `--full` bypasses cache.
- **Run class:** `classify-run.py` chooses `light` or `standard` from mode, counts, diff size,
  sensitive path tokens, and last-run verdict. Light uses `doc-impact-verifier-light` (Haiku),
  while standard and every Workflow retry use Sonnet. The Codex Phase-3 backend uses Luna for
  light and Terra for standard, both at medium effort. Codex review uses the same defaults unless
  `codexReview.model` is set.
- **Verdict:** `FAIL` ⇒ **NEEDS FIX** (anchor not updated). Only `WARN`/`PASS` ⇒ **CONSISTENT**
  (anchor updated). Invalid or changed evidence/state ⇒ **REFUSED**. Phase-3 verdicts are used directly.
  Both CONSISTENT and NEEDS FIX run the non-blocking, 30-second `sibling-scan.py`: it checks phrases
  from verifier findings, Phase-4 titles, and removed change-set lines, then reports one status line.
- **Report:** when `reportPath` is configured, the orchestrator submits one complete placeholder
  template through `write-template.py` before the gate. The gate renders and publishes it while
  holding the run lock, and returns `reportPath`, fixed warning codes, and `reportStatus`.
  A later open reports unresolved `pending`, `failed`, or `written-durability-unknown` status.
  The report date comes from the run ID in UTC, not the local calendar date.
- **Anchor:** written **only on CONSISTENT**, recording the current HEAD SHA. **Commit it**
  (convention: a `docs(audit): …` commit) so the baseline is shared and survives squash-merges.
  Existing anchors with only `sha` remain compatible; v0.10 adds run/digest metadata.

Phase-4 severity mapping:

| severity | gate effect |
|---|---|
| `PASS` | `non-blocking` accepted without blocking the verdict |
| `WARN` | `non-blocking` accepted without blocking the verdict |
| `MEDIUM` | `non-blocking` accepted without blocking the verdict |
| `LOW` | `non-blocking` accepted without blocking the verdict |
| `INFO` | `non-blocking` accepted without blocking the verdict |
| `FAIL` | `blocking` contributes a blocking finding |
| `HIGH` | `blocking` contributes a blocking finding |
| `CRITICAL` | `blocking` contributes a blocking finding |
| any other value | `REFUSED` with `unknown finding severity` |

**Correct anchor ordering** (so the anchor records the *consistent* state):
1. Fix findings and **commit** them.
2. Re-run `--full`; on CONSISTENT the engine writes the anchor at the now-current SHA.
3. **Commit the anchor** (+ report) as a separate, meta commit.

### v0.13.0 compatibility impact

- The gate has additional **REFUSED** conditions for provenance/audit-scope integrity and strict
  Codex-review evidence. Manifests now carry `provenance` and `auditScopeSha`; dispatch carries
  `impactSha`.
- A run in flight across this version boundary must be stopped with `--break-lock` and restarted.
  Phase 3 and Phase 4 read the sealed manifest through `read-manifest.py`, and `codex-dispatch.py`
  now requires `--evidence`.
- Phase 4's Codex path uses its deterministic plan table; Phase 5's Codex line has four display
  classes. `check-docs` has three correctness fixes. The new `counts` fields and the optional
  `regressionRecheck`, `excludeDocPathTokens`, `codexReview.required`, and `auditScope` settings
  are backward-compatible defaults (disabled or absent).

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
- **Locks are never taken over automatically.** Exit 4 means another run owns the lock. Verify
  that run is dead before using `/docaudit:audit --break-lock`; the command releases the lock
  and stops, so start the audit again afterward.
- **Config changes are acknowledged, not guessed.** If a run detects that
  `.claude/doc-audit.json` changed, it REFUSES and the next open exits 6 until you inspect the
  diff and explicitly run `/docaudit:audit --accept-config`.
- **Read `REFUSED` as “the run is invalid”, not “the docs are wrong”.** Common reasons include
  missing/changed evidence, lock identity mismatch, an unsealed manifest, HEAD/worktree or
  `changeSetSha` drift, return/path mismatch, and changed history/anchor/config. Restore or
  inspect the named state, then start a fresh audit; never manufacture evidence or an anchor.
- **`--refresh` uses shipped hashes.** `engine-shas.json` is keyed by the installed plugin
  version. `/docaudit:init --harness --refresh` overwrites only a stamped generated file whose
  normalized body still matches that version's shipped SHA; modified, unstamped, or unknown
  versions are preserved and reported as skipped.
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
| Audit open exits 4 / reports `locked:true` | another run owns `.claude/state/docaudit-run/lock` | inspect the reported holder; if it is definitely stale, run `/docaudit:audit --break-lock`, then start a new audit |
| Audit open exits 6 / `config-change-unaccepted` | a prior run detected a config change | inspect `git diff .claude/doc-audit.json`; after approving it, run `/docaudit:audit --accept-config` |
| Verdict is `REFUSED` | gate could not validate the run snapshot | follow `reason`; representative values include evidence SHA mismatch, lock/run identity mismatch, manifest not sealed, HEAD/worktree drift, `changeSetSha` mismatch, return mismatch, or changed history/anchor/config |
| Installed harness is `broken` or refresh skips files | one of the three generated files is absent, modified, unstamped, or has an unknown template version | restore intentionally, or run `/docaudit:init --harness --refresh`; review `created`, `skipped`, and `skipReasons` |

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
├── .claude-plugin/plugin.json
├── skills/audit/SKILL.md
├── skills/init/SKILL.md
├── skills/audit/scripts/ax-probe.sh
├── skills/audit/scripts/change-set-sha.py
├── skills/audit/scripts/check-verdicts.py
├── skills/audit/scripts/classify-run.py
├── skills/audit/scripts/cocoindex-probe.sh
├── skills/audit/scripts/codegraph-probe.sh
├── skills/audit/scripts/codex-dispatch.py
├── skills/audit/scripts/codex-probe.sh
├── skills/audit/scripts/codex-review-plan.py
├── skills/audit/scripts/compute-baseline.sh
├── skills/audit/scripts/decide-verdict.py
├── skills/audit/scripts/docaudit_cache.py
├── skills/audit/scripts/docaudit_paths.py
├── skills/audit/scripts/fix-scope.py
├── skills/audit/scripts/generic-layers.py
├── skills/audit/scripts/graphify-probe.sh
├── skills/audit/scripts/harness-command-kind.py
├── skills/audit/scripts/impact-supplement.py
├── skills/audit/scripts/import-audit-scope.py
├── skills/audit/scripts/inventory.py
├── skills/audit/scripts/mdq-health.py
├── skills/audit/scripts/mdq-index.sh
├── skills/audit/scripts/open-run.py
├── skills/audit/scripts/plan-dispatch.py
├── skills/audit/scripts/read-manifest.py
├── skills/audit/scripts/resolve-impact.py
├── skills/audit/scripts/scaffold.py
├── skills/audit/scripts/seal-run.py
├── skills/audit/scripts/set-config-key.py
├── skills/audit/scripts/sibling-scan.py
├── skills/audit/scripts/start-run.py
├── skills/audit/scripts/tree-digest.py
├── skills/audit/scripts/write-anchor.sh
├── skills/audit/scripts/write-evidence.py
├── skills/audit/scripts/write-template.py
├── skills/audit/scripts/write-verdict.py
├── skills/audit/references/codex-phase3-verdict.schema.json
├── skills/audit/references/codex-review-output.schema.json
├── skills/audit/references/config-schema.md
├── skills/audit/references/default-heuristics.md
├── skills/audit/references/engine-shas.json
├── skills/audit/references/workflow-template.js
├── agents/doc-impact-verifier-light.md
├── agents/doc-impact-verifier.md
├── docs/ADOPTION.md
├── docs/ADOPTION.ja.md
├── docs/examples/doc-audit.example.json
└── tests/
```

For the full design rationale (why each decision was made), see the originating project's
design spec referenced in the top-level `README.md`.
