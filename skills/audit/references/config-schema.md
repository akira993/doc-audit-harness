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

`impacts` entries MUST be doc paths only; put commentary in `note`. `changed`
accepts a single path or a glob.

## Generic fallback layers

When `docAuditCommands` is absent (or a named command is unavailable), the audit
SKILL falls back to `scripts/generic-layers.py` — a portable, config-driven baseline
(`format` = relative-link resolution + optional front-matter fields; `existence` =
conservative repo-path-token resolution; `semantic` = orphan detection). This baseline
is intentionally weaker than a project's bespoke doc tools; richer checks come from
`docAuditCommands` or a project-tailored scaffold (Plan 4).
