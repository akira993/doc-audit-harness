# `.claude/doc-audit.json` schema

Per-project adapter consumed by the docaudit engine. All project-specific facts
live here; the plugin ships no project knowledge.

| key | type | required | meaning |
|-----|------|----------|---------|
| `anchorPath` | string | yes | repo-relative path to the anchor state file |
| `diffGlobs` | string[] | yes | path globs that scope the change set (`**`=incl `/`, `*`=excl `/`) |
| `docGlobs` | string[] | no | files treated as docs for the heuristic scan (default `["docs/**/*.md","*.md"]`); pre-flight fix-path classification uses the same default |
| `frontMatterFields` | string[] | no | generic `format` layer requires these front-matter fields on every doc (WARN if missing); omit to skip front-matter checks |
| `layerGlobs` | object | no | per-layer generic exclusions: `{format?:{exclude:string[]},existence?:{exclude:string[]},semantic?:{exclude:string[]}}`; exclusions also apply to explicit `--paths` input |
| `frontMatterOverrides` | object[] | no | ordered generic `format` overrides: `{globs:string[],fields:string[]}`; the first entry whose `globs` contains a match wins, `fields:[]` skips the check, and no match falls back to `frontMatterFields` |
| `indexFiles` | string[] | no | generic `semantic` layer treats these as link roots for orphan detection (default: any `README.md` within the doc tree) |
| `impactMap` | object[] | yes | `{changed: path\|glob, impacts: docPath[], note?: string, source?: string}`; `source:"audit-scope"` is reserved for generated entries |
| `auditScope` | object | no | `{path, sha256, importedAt, rules}` written by the importer; do not edit by hand |
| `ssotSources` | object[] | no | `{name, value?, liveSource, docsThatCite: (path\|path:line)[]}` — a URL `liveSource` (http/https) is not supported: it is never executed or fetched, and the audit emits a warning |
| `docAuditCommands` | object | no | `{format, existence, semantic}` slash-command/skill names used by active pre-flight and delegated Phase 4 |
| `boundaryCommand` | string | no | shell command for project-boundary check |
| `reviewCommands` | object | no | `{code, security}` review command strings (effort embedded, e.g. `/code-review high`) |
| `reportPath` | string | no | output report path template (supports `<YYYY-MM-DD>` and `[_NN]`) |
| `auditReportsInCorpus` | boolean | no | only literal `true` keeps matching audit reports in corpus scans; omitted, `false`, or an invalid type excludes them (generic layers emit a config WARN for an invalid type) |
| `maxImpactedDocs` | number | no | cap on impacted docs (default 200); overflow sets `truncated` |
| `harness` | object | no | `{state,decidedAt,engineVersion}` where state is `installed`, `declined`, `integrated`, `adjusted`, or `existing-untouched`; absence is the v0.9 `unset` state |
| `verdictCache` | object | no | `{enabled:bool=true,minConsecutivePasses:int=2}`; values outside 2..10 disable cache and emit WARN |
| `phase3Backend` | string | no | Phase-3 verifier backend: `"workflow"` (default when omitted) or `"codex"`; any other value is rejected at seal |
| `phase3CodexTimeoutSeconds` | number | no | per-document Codex execution timeout in seconds (default 600; integer 60..3600); excludes worker-queue wait, resets for each retry, and has effect only when `phase3Backend` is `"codex"` |
| `models` | object | no | nested `{light:{enabled,maxChanged=10,maxImpacted=15,maxDiffLines=200,maxDiffBytes=65536,sensitiveTokens?}}` deterministic light-run limits; defaults are empirical, not measured service guarantees |
| `digestExclude` | string[] | no | Non-glob literal paths only — each accepted prefix itself or any path below it (a trailing `/` is normalized away). Values containing `*`, `?`, or `[` are rejected by `tree-digest.py`; `seal-run.py` fails (exit 2) and the run is not sealed. Accepted `digestExclude` prefixes: `.claude/state`, `.claude/worktrees`, `.mdq`, `.codegraph`, `graphify-out`, `.cocoindex_code`. |
| `protectedGlobs` | string[] | no | additional pre-flight fix deny patterns; built-in ADR/decisions/logs/`.claude` and case-insensitive `CLAUDE.md`/`AGENTS.md` basename denial cannot be removed |
| `heuristics` | object | no | `{minIdentifierLength:int, excludeBasenames:string[], saturationWarnRatio:number=0.5, excludeDocPathTokens:bool=false}` |
| `regressionRecheck` | object | no | `{enabled:bool=false}` — opt-in recheck of the latest prior FAIL for unchanged documents |
| `indexing` | object | no | `{enabled:bool=true, tool:string="mdq", bin:string="mdq", roots:string[]?}` — `enabled` must be a JSON boolean; `enabled:false` takes priority and reports `disabled-by-config` and omits bin. Otherwise a non-boolean `enabled`, a non-object key (including `null`), or a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config` (the tool is not run, a ⚠ status line is printed, and `indexing` fires the confirmation gate). An absent key remains enabled by default (intentional asymmetry). |
| `contextMode` | object | no | `{enabled:bool=true}` — `enabled` must be a JSON boolean; `enabled:false` takes priority and reports `disabled-by-config`. Otherwise a non-boolean `enabled` or a non-object key (including `null`) reports `invalid-config` (the tool is not run and a ⚠ status line is printed). An absent key remains enabled by default (intentional asymmetry). |
| `webExtract` | object | no | `{enabled:bool=true, tool:string="ax", bin:string="ax"}` — key-gated Phase-0 `ax` preflight: it runs only when this key exists, `enabled` is not false, and the tool is installed. An absent key reports `not-configured` and never runs the tool. `enabled` must be a JSON boolean; `enabled:false` takes priority and reports `disabled-by-config` with the default name. Otherwise a non-boolean `enabled`, a non-object key (including `null`), or a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config` (the tool is not run and a ⚠ status line is printed). |
| `codexReview` | object | no | `{enabled:bool=true, required:bool=false, bin:string="codex", model?:string, timeoutMs?:number=300000}` — key-gated Phase-0 `codex` preflight: it runs only when this key exists, `enabled` is not false, and the tool is installed. An absent key reports `not-configured` and never runs the tool. `enabled` must be a JSON boolean; `enabled:false` takes priority and reports `disabled-by-config` with the default name. Otherwise a non-boolean `enabled`, a non-object key (including `null`), or a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config` (the tool is not run and a ⚠ status line is printed). When this key exists, `required:true` makes a non-completed review REFUSED; it cannot conflict with an absent key. |
| `symbolGraph` | object | no | `{enabled:bool=true, tool:string="codegraph", bin:string="codegraph"}` — key-gated Phase-0 `codegraph` CLI preflight: it runs only when this key exists, `enabled` is not false, and the tool is installed. It may corroborate changed-file symbols via read-only `codegraph impact`/`node`; report-only, never affects the verdict. `tool` is reserved; the probe validates `enabled` and `bin`. `enabled:false` takes priority and reports `disabled-by-config`; it keeps a valid custom bin and uses the default name for an invalid bin. Otherwise a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config`. The `bin` override affects only the probe; Phase 3 Workflow invokes fixed `codegraph`. |
| `docGraph` | object | no | `{enabled:bool=true, tool:string="graphify", bin:string="graphify"}` — key-gated Phase-0 `graphify` CLI preflight: it runs only when this key exists, `enabled` is not false, and the tool is installed. Phase 2 then supplements `mapGapCandidates` with graph-adjacency candidates (provenance `graphify`); report-only, never affects the verdict. `tool` is reserved; the probe validates `enabled` and `bin`. `enabled:false` takes priority and reports `disabled-by-config`; it keeps a valid custom bin and uses the default name for an invalid bin. Otherwise a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config`. |
| `semanticSearch` | object | no | `{enabled:bool=true, tool:string="cocoindex", bin:string="ccc", minScore?:number=0.4}` — key-gated Phase-0 `ccc` (CocoIndex) preflight: it runs only when this key exists, `enabled` is not false, the tool is installed, and `.cocoindex_code/settings.yml` marks the repo initialized. Phase 2 supplements `mapGapCandidates` with semantic-search candidates (provenance `semantic`) scoring `>= minScore`. **The audit itself never runs `ccc init`** — an uninitialized repo degrades to `reason:not-initialized`, distinct from `not-installed`; initialize via `/docaudit:init` (user-approved, discloses the `.gitignore` write). Report-only, never affects the verdict. `tool` is reserved; the probe validates `enabled`/`bin`/`minScore`; Phase 2 uses `minScore`. `enabled:false` takes priority and reports `disabled-by-config`; it keeps a valid custom bin and uses the default name for an invalid bin. Otherwise a non-string, empty, whitespace-only or whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable `bin` reports `invalid-config`. |

`impacts` entries MUST be doc paths only; put commentary in `note`. `changed`
accepts a single path or a glob.

## Harness adoption state

`harness` records one explicit adoption decision. `broken` and `unanswered` are derived runtime
labels and MUST NOT be stored in config.

| current state | trigger / answer | next stored state | required side effect |
|---|---|---|---|
| `unset` (key absent) | install / new install | `installed` | create the three harness files and atomically write their returned `docAuditCommands` |
| `unset` (key absent) | decline (no candidates) | `declined` | no generated files and no new command mapping |
| `unset` (key absent) | integrate existing | `integrated` | atomically write all three existing command names; this state is invalid without `docAuditCommands` |
| `unset` (key absent) | adjust existing | `adjusted` | show a diff, obtain approval, edit, then atomically write all three command names |
| `unset` (key absent) | keep existing untouched | `existing-untouched` | do not edit or automatically wire candidates |
| any stored state | `/docaudit:init --reask` | any state above allowed by the current inventory | replace only the decision and its required command mapping after a new answer |
| `installed` | a generated file is missing | no config change (`broken` is derived) | skip pre-flight and suggest `/docaudit:init --harness --refresh` |

Every stored decision includes an ISO-8601 `decidedAt` value and the plugin version used as
`engineVersion`. Existing config updates use one `set-config-key.py` invocation with multiple
`--set` arguments when both `harness` and `docAuditCommands` change, preserving all other keys.
New configs include both values in the approved draft and are written once.

The Phase-0.5 firing rule is:

| stored `harness.state` | `docAuditCommands` | pre-flight |
|---|---|---|
| `installed`, `integrated`, `adjusted` | present or absent | run |
| `existing-untouched` or `unset` | present | run |
| `declined` | any | skip (Phase 4 command delegation remains unchanged) |
| any other combination | absent | skip |

For `installed`, the required generated set is `.claude/commands/check-docs.md`,
`.claude/skills/doc-lint/SKILL.md`, and `scripts/check-docs.py`. Its mapping is fixed to
`{existence:"/check-docs --only existence",format:"/check-docs --only format",semantic:"doc-lint"}`.
The copied engine accepts `--layer`, `--format json|text`, and `--exit-code`; text mode emits
`SUMMARY pass=<n> warn=<n> fail=<n>` followed by `VERDICT CONSISTENT|NEEDS FIX`, and
`--exit-code` returns 1 when any FAIL exists.

## Init and scaffold flags

- `/docaudit:init --harness` inventories even when config exists, then changes only harness files,
  `harness`, and the required `docAuditCommands` mapping. The ordinary existing-config stop rule
  still applies without this flag.
- `/docaudit:init --harness --refresh` delegates to `scaffold.py --harness --refresh`. A stamped
  file is overwritten only when its normalized body matches the shipped SHA for the version in
  its stamp. Modified, unstamped, and unknown-version files are preserved and reported as skipped.
- `/docaudit:init --reask` asks again even when `harness` is already stored. Without it, the
  stored answer is not asked again.
- `scaffold.py --dry-run` reports the same proposed `created`/`skipped` result without writing.
- Legacy `--scaffold` continues to create `docaudit-{format,existence,semantic}` skill skeletons.

When `--scaffold` and `--harness` are combined, the command mapping is deterministic:

| layer | selected command |
|---|---|
| `existence` | `/check-docs --only existence` (harness wins) |
| `format` | `/check-docs --only format` (harness wins) |
| `semantic` | `docaudit-semantic` (legacy tailored scaffold wins) |

Harness template stamps are excluded from the normalized SHA-256. Markdown stamps are the first
line after front matter; the engine stamp is the first line after its shebang. Shipped hashes are
versioned in `references/engine-shas.json` so refresh can distinguish an unchanged old template
from user customization.

## v0.10 run ledger and cache

Each audit uses `.claude/state/docaudit-run/<runid>/`; the sibling `lock` file has
no TTL and can be removed only by the matching `--release` or an explicit
`--break-lock`. History and last-run state are
`.claude/state/docaudit-history.json` and
`.claude/state/docaudit-last-run.json`. Old flat run files are ignored (cold
start). Full mode uses `HEAD` as its effective baseline, disables cache, and
includes every `docGlobs` document without applying `maxImpactedDocs`.

`phase0-probes.json` in that run directory stores display-only raw Phase-0 probe output with
`schemaVersion:1`. It is not evidence and the gate never reads it.

The orchestrator carries one `EVIDENCE` JSON object. Missing evidence uses the
literal `none` only where absence is valid: cold-start history, an empty cached
set, or an optional preflight/Phase 4 file. The gate accepts this object only via
`--expect-json` and reads each evidence file once for both SHA-256 comparison and
JSON parsing.

When Phase 0.5 is required, `preflight.json` retains `{state,findings[],userDecision,parsed}`
and adds `commands[]` records with `{layer,command,kind,ran,exitCode,parsed,skippedReason}`.
Non-installed classification always returns fixed `format`, `existence`, and `semantic` layer records;
missing or non-string command values are `invalid` and are paired by `layer`, never by position.
Model-driven commands are recorded as skipped before their single Phase-4 execution; invalid
commands are not executed.
`state:"no-command-ran"` with empty findings is valid only when every command is model-driven and
skipped with no FAIL; every invalid-command FAIL remains in `findings[]` and follows the normal FAIL flow.
For `installed`, `commands[]` contains only the copied engine's direct `--layer all` invocation as
one `layer:"all"`, `kind:"script-backed"` record; the three Phase-4 command names are not listed.

Phase 1 baseline output includes `machineryExcludedCount` and up to five paths in
`machineryExcludedSample`, separately from `filteredOut*`. These cover the same audit machinery
paths excluded from the sealed change set.

The gate always returns `siblingScan` for CONSISTENT and NEEDS_FIX. It has `phrases`, `matches`,
`sources:{findings,phase4,changeSet,notes}`, `truncated`, `truncatedTotal`, and
`phraseTruncated`; a local scan failure also has `skipped` and otherwise keeps the same shape.

During a run, history, anchor, lock, and config changes cause a fail-safe
`REFUSED`. If the current run still owns the lock, corrupt history is renamed to
`*.tainted-<runid>`, a changed anchor is removed, and a changed config is recorded
in last-run state; the next open exits 6 until `--accept-config` explicitly
acknowledges the change. A lock owned by a later run is never changed. Persistent
verifier processes that survive beyond a run, orchestrator compromise, and
transcript alteration remain outside the threat boundary, as does a verifier
that can directly forge a future anchor before that run starts. Deleting the
current lock is a residual denial of service: it prevents a false CONSISTENT
but can force the current run to end as REFUSED.

### Pre-flight, cache, and run class

Phase 0.5 runs after `open-run.py` has acquired the lock and before baseline/seal. A FAIL asks an
interactive user to fix and audit, continue without fixing, or stop. Only the first choice may
edit: `fix-scope.py` permits finding paths that match `docGlobs`, denies ADR/decisions/logs,
`.claude/**`, and `CLAUDE.md`/`AGENTS.md` basenames case-insensitively, adds `protectedGlobs`, and verifies that no path outside the
approved set changed. Non-interactive runs never edit. Pre-flight findings are gate evidence and
therefore block CONSISTENT when they contain FAIL.

`plan-dispatch.py` and `docaudit_cache.py` skip Phase 3 only for the most recent
`minConsecutivePasses` records of a document when every record is PASS and its `contentSha`,
`changeSetSha`, `contractVersion`, and Phase-3 backend match the current run. Missing backend fields
in old history entries mean `workflow`; explicit `workflow` is therefore compatible with old entries.
The gate repeats the qualification using the backend sealed in the manifest.
Only `decide-verdict.py` writes `.claude/state/docaudit-history.json`; absent history is a cold
start, corrupt history disables cache and is quarantined by the gate, and full mode disables
cache.

`classify-run.py` deterministically selects `light` or `standard`. Full mode, disabled light
routing, threshold overflow, a non-CONSISTENT previous run, or a changed path containing a
configured/default sensitive token makes the run standard. Light Phase 3 uses
`doc-impact-verifier-light` (Haiku); standard and every retry use Sonnet. Codex review honors an
explicit `codexReview.model`; otherwise light uses `gpt-5.6-luna` and standard uses
`gpt-5.6-terra`, both with medium reasoning effort.

## Indexing (mdq, Phase 0)

`indexing` is optional and conditional-force. With `mdq` on `PATH` (or `bin` pointed at a
vendored binary), Phase 0 builds the index under `.mdq/` (mdq's own default DB resolution —
e.g. `index-<lang>-<strategy>.sqlite` on current mdq, `index.sqlite` on older) and Phase 3 reads
impacted docs as token-optimized chunks (`mdq search --paths <doc>` / `mdq get`). By
default it indexes the whole repo (`--root .`) — mdq's own default roots (`docs`,
`knowledge`, …) would miss `README.md`, `skills/**`, and `agents/**`; set `roots` to
narrow the scope. When `indexing.enabled` is `false`, the audit silently degrades to grep
(an explicit opt-out). When `mdq` is absent, indexing fails, or the Phase-0 health probe
finds it installed but unhealthy, the audit's Phase-0 confirmation gate asks the user
(`AskUserQuestion`) to fix mdq first or explicitly approve continuing in grep-degrade mode
— it no longer degrades silently in those cases (a non-interactive session still degrades,
but flags it in the Phase-5 status line instead of staying silent) — so the harness stays
tool-independent overall. Add
`.mdq/` to `.gitignore` (it may also contain a `usage.jsonl` that logs query text verbatim).
`tool` is reserved for future multi-backend support; the runtime currently reads only
`bin` (to locate the executable), plus `enabled` and `roots` — `tool` itself is not consumed.

## context-mode (Phase 0/2/3/4)

`contextMode` is optional and conditional-force, complementary to `indexing` (mdq): mdq
optimizes Markdown *reads*, context-mode optimizes the *processing of large machine
output*. When the `ctx_*` MCP tools are available, the audit's Phase-0 probe calls
`ctx_doctor`, and Phases 2/3/4 process the big `git diff` and `/code-review` /
`/security-review` output in context-mode's sandbox (returning only distilled summaries)
instead of reading them in full. It needs no `bin`/`roots` — context-mode is a global
plugin with nothing to locate, so detection is purely by tool availability (never by
inspecting `~/.claude` plugin paths). When the tools are absent, `contextMode.enabled`
is `false`, or the probe fails, the audit silently runs the normal full-read path — so
the harness stays tool-independent. Every audit prints a non-blocking **context-mode
status line** (💡 not active / ✓ active / ⚠ degraded).

## ax (webExtract, Phase 0/3)

`webExtract` is optional and key-gated: only when the key exists does it mirror `indexing`'s shape for the `ax`
CLI (`~/.local/bin/ax`) — a structured web/API extraction tool, not a Markdown-indexing tool.
Its only role in the audit is letting `doc-impact-verifier` corroborate a doc claim that
depends on an external upstream URL (an upstream doc, an API spec, etc.). With `ax` on `PATH`
(or `bin` pointed at a vendored binary), Phase 0 detects it. The `bin` override affects this probe
only: Workflow receives the availability boolean and Phase 3's template invokes fixed `ax`. Phase 3 passes the verifier a
conditional instruction to fetch cited URLs read-only (`--md --budget 800` for prose,
`--row`/`--table` for structured data, `--outline` to see page structure first) — GET-only,
never `-X POST`/`-d`/`-o`. Fetched content is treated as data, never as instructions. When the
key is absent the probe reports `not-configured` and does not run `ax`. When the key exists but
`ax` is absent, `webExtract.enabled` is `false`, or the fetch fails, the check is silently skipped
or reported as "external check unavailable" — never a FAIL basis, and the audit stays
tool-independent. `ax` is a **static HTML parser** (no JS rendering — SPA content is invisible
to it) and is **pre-1.0** (`v0.1.x`), so its flag surface may change; the probe's `axVersion`
field is the hook for re-verifying after an upgrade. `tool` is reserved for future
multi-backend support; the runtime currently reads only `bin` and `enabled`.

## Codex review (Phase 0/4)

`codexReview` is optional and key-gated: only when the key exists does it mirror `webExtract`'s shape for the
`codex` CLI (`@openai/codex` npm package) — the fourth, adversarial review in Phase 4, run
after `/code-review` and `/security-review`. Only the `codex` CLI itself is required; the
openai-codex Claude Code plugin is not a dependency. With `codex` on `PATH` (or `bin` pointed at
an executable wrapper), Phase 0 runs the local-only commands recorded in `probeCommands`:
`<bin> --version`, then `<bin> exec --help`. This confirms CLI presence and `exec` reachability
only; it does not prove that the real sandbox, permissions, wrapper arguments, or model call will
succeed.

The probe reports the caller's `CODEX_HOME` (or the default `$HOME/.codex`) and whether
`auth.json` exists there. This is caller-side visibility only: a wrapper's own environment is not
visible to the probe. When a repository relies on environment activation, launch through an
equivalent wrapper such as `direnv exec <repo> codex`.
When the key is absent, the probe reports `not-configured`, does not run `codex`, and returns
neutral caller values without inspecting `CODEX_HOME` or `auth.json`.

Absolute `--config` and `--scope` paths accepted by `import-audit-scope.py` use POSIX path syntax
only; Windows path forms are outside the supported platform scope.

Phase 4 passes availability, mode, `codexReview.required`, and baseline validity through
`codex-review-plan.py` before invoking plain `codex exec`. Incremental mode reviews the explicit
`$BASELINE_SHA` to HEAD diff. Full mode runs only when `required:true`, reviewing every impacted
document against the `manifest.head`-identified, `worktreeDigest`-sealed current worktree,
including uncommitted and untracked files. Without `required:true`, full mode skips.
Every invocation carries the mandatory, non-configurable `-s read-only` flag and structured JSON
is forced via `--output-schema`.

The evidence state is one of `completed`, `execution-failed`, `ref-invalid`,
`skipped-full-run`, or `not-active`. Phase 5 displays four classes because
`execution-failed` and `ref-invalid` share the did-not-run warning. With the default
`required:false`, those two states warn and decorate a CONSISTENT report without changing the
internal verdict. With `required:true`, any state other than `completed`, missing evidence, or
`enabled:false` makes the gate REFUSED. A non-boolean `required` makes the gate REFUSED regardless
of its value. Enabling `required` after the
first baseline is established is recommended. A completed run's `critical`/`high` findings fold
into `phase4.json` as blocking; `medium`/`low` remain non-blocking.

## codegraph (symbolGraph, Phase 0/3)

`symbolGraph` is optional and key-gated, mirroring `webExtract`'s shape but for the
`codegraph` CLI — a symbol graph (call graph, impact/node lookup). Its sole role in the audit is
letting `doc-impact-verifier` corroborate a doc claim that depends on a *changed file's own*
symbols, the symbol-level counterpart of ax's external-URL seam. Only when the key exists,
`enabled` is not false, and `codegraph` is on `PATH` (or `bin` points at a vendored binary) does
Phase 0 keep the index fresh. The `bin` override
affects this probe only: Workflow receives the availability boolean and Phase 3's template invokes
fixed `codegraph`. A regular `<dir>/codegraph.db` (`CODEGRAPH_DIR` honored) → `codegraph sync .`;
an absent database → `codegraph init .`; a symlink or non-regular database/directory → no
execution and `index-failed`; the probe does not rely on version-dependent `init` idempotency. codegraph
self-generates `.codegraph/.gitignore`, so the probe never touches `.gitignore` itself. Phase 3
then passes the verifier a conditional instruction to use `codegraph impact <symbol> --json`
(post-filtered by `filePath` — its `affected[]` has no path-scoping flag, confirmed) or
`codegraph node <symbol> -f <changed-file>` (text output, `--json` does not exist on this
subcommand, confirmed; `-f` disambiguates directly). `codegraph affected` is NEVER used
(import-based; confirmed empty on subprocess-driven test-style repos). When `codegraph` is absent,
`symbolGraph.enabled` is `false`, or the index build fails, symbol-level corroboration is silently
unavailable — never a FAIL basis, and the audit stays tool-independent.
Its probe reasons are `ok`, `not-installed`, `disabled-by-config`, `index-failed`,
`not-configured`, and `invalid-config`.

## graphify (docGraph, Phase 0/2)

`docGraph` is optional and key-gated, for the `graphify` CLI — a unified code+doc graph.
Its role is a second, independent candidate source for Phase 2's `mapGapCandidates` (provenance
`graphify`), alongside the existing token heuristic — the first seam to integrate at the impact-
resolution point itself, not Phase 3/4. Only when the key exists, `enabled` is not false, and
`graphify` is on `PATH`, Phase 0 runs `graphify update .` (confirmed LLM-free and diff-based/idempotent), then checks
whether `graphify-out/` is gitignored via `git check-ignore -q graphify-out` (graphify does NOT
self-gitignore its output, unlike codegraph — a direct `.gitignore` read would miss global
gitignore/`.git/info/exclude`/pattern-wording differences, so this is the confirmed method). Phase
2's `impact-supplement.py` then runs `graphify affected "<changed-file>"` and, once per run,
`graphify query "<changeSummary>" --budget 800` — both are confirmed fixed-format TEXT output
(neither has `--json`), parsed by regex and doc-filtered (via `docGlobs`) before becoming a
candidate. A `No unique node match` uniqueness error (confirmed, exit 0) degrades that call to zero
candidates, not an error. **Side effect** (spec §6, not handled by this pass): a detected topology
change makes `graphify update .` write a dated backup under `graphify-out/<date>/`, which
accumulates over repeated runs — a disk-only concern when `graphify-out/` is gitignored. When
`graphify` is absent or `docGraph.enabled` is `false`, `mapGapCandidates` uses the token heuristic
only — never a FAIL basis, and the audit stays tool-independent.
Its probe reasons are `ok`, `not-installed`, `disabled-by-config`, `update-failed`,
`not-configured`, and `invalid-config`.

## CocoIndex (semanticSearch, Phase 0/2)

`semanticSearch` is optional and key-gated, for the `ccc` (CocoIndex) CLI — local-embedding
semantic search. Its role is a third, independent candidate source for Phase 2's
`mapGapCandidates` (provenance `semantic`), running alongside (not instead of) the graphify source
— one finds candidates via graph adjacency, the other via semantic similarity. **The single most
important rule for this seam: the audit itself NEVER runs `ccc init`.** `ccc init` auto-appends
`/.cocoindex_code/` to the target repo's `.gitignore` (confirmed real side effect), a write the
report-only audit phase must never trigger mid-run — so an absent `.cocoindex_code/settings.yml` marker is
its own terminal probe state, `reason:not-initialized`, distinct from `not-installed`. This is a
silent, expected degrade (no WARN) until the user runs `/docaudit:init`, which proposes running
`ccc init && ccc index` behind **explicit user approval that discloses the `.gitignore` write**.
Only when the key exists, `enabled` is not false, `ccc` is installed, and
`.cocoindex_code/settings.yml` exists does Phase 0 run `ccc index` (no path argument — it
operates on the cwd only; confirmed `ccc index .` errors "unexpected extra argument(s)") to refresh (confirmed
the heaviest of the three seams' Phase-0 costs, ~8.5s on this repo). Phase 2's
`impact-supplement.py` then runs `ccc search "<changeSummary>" --json --limit 10` once: `ccc
search` has **no built-in relevance cutoff** (confirmed — irrelevant queries still return `limit`
results, just at a visibly lower score band), so every result's `score` MUST clear `minScore`
(default `0.4`, a provisional value from this repo's own measurements — real hits landed at
0.36-0.62, noise at 0.23-0.26) before doc-filtering (via `docGlobs`) and admitting it as a
candidate. When `ccc` is absent, not yet initialized, or `semanticSearch.enabled` is `false`,
`mapGapCandidates` simply gets no semantic-search source — never a FAIL basis, and the audit stays
tool-independent. The probe compares `.gitignore` before and after `ccc index`; a change reports
`reason:gitignore-modified` and is never reverted by the audit.
Its probe reasons are `ok`, `not-installed`, `disabled-by-config`, `not-initialized`,
`index-failed`, `not-configured`, `invalid-config`, and `gitignore-modified`.

## Generic fallback layers

When `docAuditCommands` is absent (or a named command is unavailable), the audit
SKILL falls back to `scripts/generic-layers.py` — a portable, config-driven baseline
(`format` = relative-link resolution + optional front-matter fields; `existence` =
conservative repo-path-token resolution; `semantic` = orphan detection). This baseline
is intentionally weaker than a project's bespoke doc tools; richer checks come from
`docAuditCommands` or a project-tailored scaffold (Plan 4).

`layerGlobs.<layer>.exclude` is applied inside each generic check, including when `--paths`
explicitly supplies documents. For `semantic`, excluded documents are removed only from orphan
reporting; their outgoing links still count as references. `frontMatterOverrides` is evaluated in
array order and the first entry with any matching glob wins. Invalid shapes for either key produce
a WARN at `(config):1` and the invalid part is ignored.

The existence layer inspects both backtick tokens (including non-ASCII paths) and bare paths from
an ASCII path character class. A non-resolving backtick token that denotes a concrete file is a
FAIL; bare references and directory-like or extensionless backtick tokens remain WARN. This can
turn an existing repository from CONSISTENT to NEEDS FIX without adding a new key. Use
`layerGlobs` for intentional per-layer exclusions; generated audit reports are excluded from the
corpus by default to avoid self-audit noise.

Known limits: file/directory classification is syntax-based, so an extensionless file such as
`docs/LICENSE` is WARN rather than FAIL. Bare harvesting does not detect non-ASCII paths. Fenced
and four-space-indented code masking uses a conservative simplified Markdown recognizer and may
mask more content than a full parser.

Audit-report exclusion is derived from the complete `reportPath` template. A valid template is a
`.md` path whose sample-rendered path matches `docGlobs`, whose basename contains
`<YYYY-MM-DD>`, and whose basename has a non-empty prefix before that placeholder. Regex derivation
escapes every literal character, replaces `<YYYY-MM-DD>` with ASCII-only
`[0-9]{4}-[0-9]{2}-[0-9]{2}`, and replaces `[_NN]` with the optional suffix
`(_[0-9]{2,})?`. The optional suffix is always accepted: at the `[_NN]` position when present,
otherwise immediately after the date and before any following literal text. Report generation
starts collision suffixes at `_02`, keeps two-digit zero padding through `_99`, continues with
`_100`, and never overwrites an existing report. Set `auditReportsInCorpus` to boolean `true` only
when reports intentionally belong in corpus scans.
