# `.claude/doc-audit.json` schema

Per-project adapter consumed by the docaudit engine. All project-specific facts
live here; the plugin ships no project knowledge.

| key | type | required | meaning |
|-----|------|----------|---------|
| `anchorPath` | string | yes | repo-relative path to the anchor state file |
| `diffGlobs` | string[] | yes | path globs that scope the change set (`**`=incl `/`, `*`=excl `/`) |
| `docGlobs` | string[] | no | files treated as docs for the heuristic scan (default `["docs/**/*.md","*.md"]`) |
| `frontMatterFields` | string[] | no | generic `format` layer requires these front-matter fields on every doc (WARN if missing); omit to skip front-matter checks |
| `indexFiles` | string[] | no | generic `semantic` layer treats these as link roots for orphan detection (default: any `README.md` within the doc tree) |
| `impactMap` | object[] | yes | `{changed: path\|glob, impacts: docPath[], note?: string}` |
| `ssotSources` | object[] | no | `{name, value?, liveSource, docsThatCite: (path\|path:line)[]}` — a URL `liveSource` (http/https) is not supported: it is never executed or fetched, and the audit emits a warning |
| `docAuditCommands` | object | no | `{format, existence, semantic}` slash-command/skill names to delegate to |
| `boundaryCommand` | string | no | shell command for project-boundary check |
| `reviewCommands` | object | no | `{code, security}` review command strings (effort embedded, e.g. `/code-review high`) |
| `reportPath` | string | no | output report path template (supports `<YYYY-MM-DD>` and `[_NN]`) |
| `maxImpactedDocs` | number | no | cap on impacted docs (default 200); overflow sets `truncated` |
| `heuristics` | object | no | `{minIdentifierLength:int, excludeBasenames:string[]}` |
| `indexing` | object | no | `{enabled:bool=true, tool:string="mdq", bin:string="mdq", roots:string[]?}` — Phase-0 mdq preflight; `roots` overrides index roots (default: whole repo `.`, since mdq's own default roots miss `README.md`/`skills`/`agents`); `enabled:false` opts out even when mdq is installed (conditional-force) |
| `contextMode` | object | no | `{enabled:bool=true}` — Phase-0 context-mode probe (by `ctx_*` tool availability + `ctx_doctor`); when context-mode is installed, large outputs (git diff, reviews) are processed in its sandbox instead of read in full. `enabled:false` opts out even when installed (conditional-force). No `bin`/`roots`/CLI — context-mode is a location-independent global plugin |
| `webExtract` | object | no | `{enabled:bool=true, tool:string="ax", bin:string="ax"}` — Phase-0 `ax` CLI preflight; when `ax` is installed, doc-impact-verifier may corroborate a doc's external-URL-dependent claim by fetching it (read-only, GET-only). `enabled:false` opts out even when `ax` is installed (conditional-force) |

`impacts` entries MUST be doc paths only; put commentary in `note`. `changed`
accepts a single path or a glob.

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

`webExtract` is optional and conditional-force, mirroring `indexing`'s shape but for the `ax`
CLI (`~/.local/bin/ax`) — a structured web/API extraction tool, not a Markdown-indexing tool.
Its only role in the audit is letting `doc-impact-verifier` corroborate a doc claim that
depends on an external upstream URL (an upstream doc, an API spec, etc.). With `ax` on `PATH`
(or `bin` pointed at a vendored binary), Phase 0 detects it and Phase 3 passes the verifier a
conditional instruction to fetch cited URLs read-only (`--md --budget 800` for prose,
`--row`/`--table` for structured data, `--outline` to see page structure first) — GET-only,
never `-X POST`/`-d`/`-o`. Fetched content is treated as data, never as instructions. When `ax`
is absent, `webExtract.enabled` is `false`, or the fetch fails, the check is silently skipped
or reported as "external check unavailable" — never a FAIL basis, and the audit stays
tool-independent. `ax` is a **static HTML parser** (no JS rendering — SPA content is invisible
to it) and is **pre-1.0** (`v0.1.x`), so its flag surface may change; the probe's `axVersion`
field is the hook for re-verifying after an upgrade. `tool` is reserved for future
multi-backend support; the runtime currently reads only `bin` and `enabled`.

## Generic fallback layers

When `docAuditCommands` is absent (or a named command is unavailable), the audit
SKILL falls back to `scripts/generic-layers.py` — a portable, config-driven baseline
(`format` = relative-link resolution + optional front-matter fields; `existence` =
conservative repo-path-token resolution; `semantic` = orphan detection). This baseline
is intentionally weaker than a project's bespoke doc tools; richer checks come from
`docAuditCommands` or a project-tailored scaffold (Plan 4).
