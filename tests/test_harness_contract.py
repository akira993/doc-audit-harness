import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT_SKILL = os.path.join(ROOT, "skills", "init", "SKILL.md")
AUDIT_SKILL = os.path.join(ROOT, "skills", "audit", "SKILL.md")
SCHEMA = os.path.join(ROOT, "skills", "audit", "references", "config-schema.md")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TestHarnessContract(unittest.TestCase):
    def test_phase3_codex_backend_is_documented_as_sealed_and_fail_closed(self):
        skill = read(AUDIT_SKILL)
        schema = read(SCHEMA)
        for key in ("phase3Backend", "phase3CodexTimeoutSeconds"):
            self.assertIn(f"`{key}`", schema)
        self.assertIn('`"workflow"` (default when omitted) or `"codex"`', schema)
        self.assertIn("Use only sealed `manifest.phase3Backend`", skill)
        self.assertIn("codex-dispatch.py", skill)
        self.assertIn("gpt-5.6-luna", skill)
        self.assertIn("gpt-5.6-terra", skill)
        self.assertIn("Never silently fall back to Workflow", skill)
        self.assertIn("Phase-3 backend: <manifest.phase3Backend>", skill)

    def test_init_documents_every_stored_transition(self):
        text = read(INIT_SKILL)
        for state in ("installed", "declined", "integrated", "adjusted",
                      "existing-untouched"):
            self.assertIn(f"`{state}`", text)
        self.assertIn("existingDocToolCandidates", text)
        self.assertIn("AskUserQuestion` exactly once", text)
        self.assertIn("`--reask` forces", text)
        self.assertIn("set-config-key.py", text)
        self.assertIn("[--set 'docAuditCommands=", text)
        self.assertIn("diff", text.lower())
        self.assertIn("explicit approval", text)

    def test_schema_has_transition_firing_and_precedence_tables(self):
        text = read(SCHEMA)
        for state in ("installed", "declined", "integrated", "adjusted",
                      "existing-untouched", "unset"):
            self.assertIn(f"`{state}`", text)
        self.assertIn("Phase-0.5 firing rule", text)
        self.assertIn("`/check-docs --only existence` (harness wins)", text)
        self.assertIn("`docaudit-semantic` (legacy tailored scaffold wins)", text)
        self.assertIn("--harness --refresh", text)
        self.assertIn("--reask", text)


if __name__ == "__main__":
    unittest.main()
