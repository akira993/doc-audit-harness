// docaudit phase-3: change-impact verification fan-out.
// Launch with Workflow({scriptPath: "<this file>", args: {repoRoot, changeSummary, impacted:[{path,provenance}]}})
export const meta = {
  name: 'docaudit-impact-verify',
  description: 'Verify each impacted doc still matches the changed source (PASS/WARN/FAIL)',
  phases: [{ title: 'Verify' }],
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    path: { type: 'string' },
    verdict: { type: 'string', enum: ['PASS', 'WARN', 'FAIL'] },
    rationale: { type: 'string' },
    suggestion: { type: 'string' },
  },
  required: ['path', 'verdict', 'rationale'],
}

// This runtime delivers Workflow `args` to the script as a JSON STRING, not a parsed
// object (other runtimes pass it as an object). Accept both shapes — otherwise every
// field below silently falls back to its default and the fan-out runs on 0 docs.
let a = args
if (typeof a === 'string') {
  try { a = JSON.parse(a) } catch (e) { a = null }
}
if (a == null || typeof a !== 'object') {
  // Fail loud: an empty impacted list here is a plumbing failure, not a real 0-impact result.
  throw new Error(
    `docaudit Phase 3: Workflow args did not reach the script in a usable shape (got ${typeof args}); ` +
    `the impacted-doc list would be empty due to a plumbing failure, not a real 0-impact result.`
  )
}
const impacted = (a.impacted || [])
const changeSummary = a.changeSummary || '(no summary provided)'
const repoRoot = a.repoRoot || '.'
const mdqAvailable = a.mdqAvailable === true || a.mdqAvailable === 'true'
const cmAvailable = a.cmAvailable === true || a.cmAvailable === 'true'
const dbPath = `${repoRoot}/.mdq/index.sqlite`

const readInstruction = (docPath) => mdqAvailable
  ? `The repo Markdown is already indexed with mdq (Phase 0). You MUST read the target ` +
    `doc via mdq, NOT a full-file Read: run ` +
    `\`mdq search --db "${dbPath}" --q "<keywords>" --paths "${docPath}" --top-k 5 --max-tokens 800\` ` +
    `(add \`--mode grep\` for exact identifiers), then ` +
    `\`mdq get --db "${dbPath}" --chunk-id <ID>\` to pull ONLY the relevant heading chunks. ` +
    `Do NOT Read the whole doc; use Read only for the specific changed SOURCE lines you must confirm.`
  : 'Use `grep -n` to pull only the relevant chunks of the doc; do not read unrelated files.'

const cmNote = cmAvailable
  ? ' This environment auto-optimizes large command output, so to confirm the SOURCE ' +
    'prefer `grep -n "<identifier>" <file>` for the exact lines over a full-file Read.'
  : ''

phase('Verify')

const results = await parallel(
  impacted.map((d) => () =>
    agent(
      `Repo root: ${repoRoot}. A documentation-impact check.

CHANGED SOURCE (since last audit):
${changeSummary}

TASK: Decide whether the doc at "${d.path}" (provenance: ${d.provenance}) still
ACCURATELY describes the changed source above. ${readInstruction(d.path)}${cmNote} Report-only — do NOT edit.

Emit exactly one verdict:
- FAIL: the doc now states something contradicted by the change (must fix).
- WARN: the doc is plausibly stale or under-specified given the change (should review).
- PASS: the doc is unaffected or already consistent.
For provenance "heuristic", bias toward WARN/PASS unless a real contradiction exists
(it is an impactMap-gap candidate, not a known coupling).
Give a one-sentence rationale citing file:line, and a suggestion when FAIL/WARN.`,
      { label: `verify:${d.path}`, phase: 'Verify', schema: VERDICT, agentType: 'docaudit:doc-impact-verifier' }
    )
  )
)

return results.filter(Boolean)
