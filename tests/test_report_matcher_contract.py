import importlib.util
import os
import re
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(ROOT, "skills", "audit", "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def load(name):
    path = os.path.join(SCRIPT_DIR, name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReportMatcherContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = [load(name) for name in (
            "change-set-sha.py", "generic-layers.py", "resolve-impact.py",
            "impact-supplement.py", "start-run.py")]
        cls.decide = load("decide-verdict.py")

    def patterns(self, config):
        return [module.report_pattern(config) for module in self.modules]

    def assert_contract(self, config, cases):
        patterns = self.patterns(config)
        self.assertEqual(patterns, [patterns[0]] * len(patterns))
        self.assertEqual(self.decide.report_pattern(config), patterns[0])
        actual = {path: bool(patterns[0] and re.fullmatch(patterns[0], path))
                  for path in cases}
        self.assertEqual(actual, cases)

    def test_explicit_suffix_placeholder_cases(self):
        config = {"docGlobs": ["docs/**/*.md"],
                  "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
        self.assert_contract(config, {
            "docs/logs/doc_audit_2026-08-25.md": True,
            "docs/logs/doc_audit_2026-08-25_2.md": False,
            "docs/logs/doc_audit_2026-08-25_02.md": True,
            "docs/logs/doc_audit_2026-08-25_100.md": True,
            "docs/logs/doc_audit_policy.md": False,
            "docs/logs/doc_audit_2026-08-25.txt": False,
            "docs/logs/doc_audit_２０２６-０８-２５.md": False,
            "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md": False,
        })

    def test_implicit_suffix_and_date_following_literal_cases(self):
        config = {"docGlobs": ["docs/**/*.md"],
                  "reportPath": "docs/logs/audit_<YYYY-MM-DD>_final.md"}
        self.assert_contract(config, {
            "docs/logs/audit_2026-08-25_final.md": True,
            "docs/logs/audit_2026-08-25_2_final.md": False,
            "docs/logs/audit_2026-08-25_02_final.md": True,
            "docs/logs/audit_2026-08-25_100_final.md": True,
            "docs/logs/audit_2026-08-25_final_02.md": False,
        })
        explicit = dict(config, reportPath="docs/logs/audit_<YYYY-MM-DD>_final[_NN].md")
        self.assert_contract(explicit, {
            "docs/logs/audit_2026-08-25_final.md": True,
            "docs/logs/audit_2026-08-25_final_02.md": True,
            "docs/logs/audit_2026-08-25_02_final.md": False,
        })

    def test_default_doc_globs_apply_when_omitted(self):
        self.assert_contract(
            {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"},
            {"docs/logs/doc_audit_2026-08-25_02.md": True})

    def test_validity_conditions_are_identical(self):
        configs = [
            {"docGlobs": ["docs/**/*.md"], "reportPath": "docs/logs/audit_<YYYY-MM-DD>.txt"},
            {"docGlobs": ["docs/**/*.md"], "reportPath": "docs/logs/audit.md"},
            {"docGlobs": ["docs/**/*.md"], "reportPath": "docs/<YYYY-MM-DD>.md"},
            {"docGlobs": ["docs/**/*.md"], "reportPath": "docs/<YYYY-MM-DD>/audit.md"},
            {"docGlobs": ["guide/**/*.md"], "reportPath": "docs/logs/audit_<YYYY-MM-DD>.md"},
        ]
        for config in configs:
            with self.subTest(config=config):
                patterns = self.patterns(config)
                self.assertEqual(patterns, [None] * len(patterns))
                self.assertIsNone(self.decide.report_pattern(config))


if __name__ == "__main__":
    unittest.main()
