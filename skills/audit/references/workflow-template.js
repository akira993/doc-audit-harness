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

const a = args || {}
const impacted = (a.impacted || [])
const changeSummary = a.changeSummary || '(no summary provided)'
const repoRoot = a.repoRoot || '.'

phase('Verify')

const results = await parallel(
  impacted.map((d) => () =>
    agent(
      `Repo root: ${repoRoot}. A documentation-impact check.

CHANGED SOURCE (since last audit):
${changeSummary}

TASK: Read the doc at "${d.path}" (provenance: ${d.provenance}). Decide whether it
still ACCURATELY describes the changed source above. Use markdown-query/grep to
pull only the relevant chunks; do not read unrelated files. Report-only — do NOT edit.

Emit exactly one verdict:
- FAIL: the doc now states something contradicted by the change (must fix).
- WARN: the doc is plausibly stale or under-specified given the change (should review).
- PASS: the doc is unaffected or already consistent.
For provenance "heuristic", bias toward WARN/PASS unless a real contradiction exists
(it is an impactMap-gap candidate, not a known coupling).
Give a one-sentence rationale citing file:line, and a suggestion when FAIL/WARN.`,
      { label: `verify:${d.path}`, phase: 'Verify', schema: VERDICT, agentType: 'doc-impact-verifier' }
    )
  )
)

return results.filter(Boolean)
