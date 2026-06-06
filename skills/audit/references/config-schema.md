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
| `ssotSources` | object[] | no | `{name, value?, liveSource, docsThatCite: (path\|path:line)[]}` |
| `docAuditCommands` | object | no | `{format, existence, semantic}` slash-command/skill names to delegate to |
| `boundaryCommand` | string | no | shell command for project-boundary check |
| `reviewCommands` | object | no | `{code, security}` review command strings (effort embedded, e.g. `/code-review high`) |
| `reportPath` | string | no | output report path template (supports `<YYYY-MM-DD>` and `[_NN]`) |
| `maxImpactedDocs` | number | no | cap on impacted docs (default 200); overflow sets `truncated` |
| `heuristics` | object | no | `{minIdentifierLength:int, excludeBasenames:string[]}` |
| `indexing` | object | no | `{enabled:bool=true, tool:string="mdq", bin:string="mdq", roots:string[]?}` — Phase-0 mdq preflight; `roots` overrides index roots (default: whole repo `.`, since mdq's own default roots miss `README.md`/`skills`/`agents`); `enabled:false` opts out even when mdq is installed (conditional-force) |

`impacts` entries MUST be doc paths only; put commentary in `note`. `changed`
accepts a single path or a glob.

## Indexing (mdq, Phase 0)

`indexing` is optional and conditional-force. With `mdq` on `PATH` (or `bin` pointed at a
vendored binary), Phase 0 builds the index under `.mdq/index.sqlite` and Phase 3 reads
impacted docs as token-optimized chunks (`mdq search --paths <doc>` / `mdq get`). By
default it indexes the whole repo (`--root .`) — mdq's own default roots (`docs`,
`knowledge`, …) would miss `README.md`, `skills/**`, and `agents/**`; set `roots` to
narrow the scope. When `mdq` is absent, `indexing.enabled` is `false`, or indexing
fails, the audit silently degrades to grep — so the harness stays tool-independent. Add
`.mdq/` to `.gitignore` (it may also contain a `usage.jsonl` that logs query text verbatim).
`tool` is reserved for future multi-backend support; the runtime currently reads only
`bin` (to locate the executable), plus `enabled` and `roots` — `tool` itself is not consumed.

## Generic fallback layers

When `docAuditCommands` is absent (or a named command is unavailable), the audit
SKILL falls back to `scripts/generic-layers.py` — a portable, config-driven baseline
(`format` = relative-link resolution + optional front-matter fields; `existence` =
conservative repo-path-token resolution; `semantic` = orphan detection). This baseline
is intentionally weaker than a project's bespoke doc tools; richer checks come from
`docAuditCommands` or a project-tailored scaffold (Plan 4).
