import ast
import base64
import hashlib
import json
import os
import tempfile
import unittest
import zlib

from tests.generate_code_review_remnants import BASE_SHA, generate


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_ROOT = os.environ.get("DOCAUDIT_REMNANT_SCAN_ROOT", ROOT)
BASELINE = os.path.join(ROOT, "tests", "code_review_remnants_base.json.zlib.b64")
BASELINE_SHA256 = "ffbe034ad8fb4877a106eb315047217f15a1f7d51965f8801f3e2a0e7d050901"

MIGRATION_ALLOWLIST = {
    ("docs/ADOPTION.md", 119, "removed-config"),
    ("docs/ADOPTION.md", 119, "removed-command"),
    ("docs/ADOPTION.ja.md", 102, "removed-config"),
    ("docs/ADOPTION.ja.md", 102, "removed-command"),
    ("skills/audit/references/config-schema.md", 60, "removed-config"),
    ("skills/audit/references/config-schema.md", 61, "removed-config"),
}
WARNING_ALLOWLIST = {
    ("skills/audit/scripts/decide-verdict.py", 57, "removed-config"),
    ("skills/audit/scripts/decide-verdict.py", 58, "removed-config"),
    ("skills/audit/scripts/decide-verdict.py", 59, "removed-command"),
}
HISTORY_ALLOWLIST = {
    ("docs/ADOPTION.md", 296, "removed-config"),
    ("docs/ADOPTION.md", 296, "removed-command"),
    ("docs/ADOPTION.md", 299, "removed-config"),
    ("docs/ADOPTION.md", 299, "removed-command"),
    ("docs/ADOPTION.md", 313, "removed-command"),
    ("docs/ADOPTION.ja.md", 266, "removed-config"),
    ("docs/ADOPTION.ja.md", 266, "removed-command"),
    ("docs/ADOPTION.ja.md", 271, "removed-config"),
    ("docs/ADOPTION.ja.md", 271, "removed-command"),
    ("docs/ADOPTION.ja.md", 283, "removed-command"),
    ("tests/test_v015_contracts.py", 201, "removed-command"),
    ("tests/test_v015_contracts.py", 205, "removed-command"),
}
COMPATIBILITY_TESTS = {
    "tests/test_review_commands_code_removed.py": (
        "test_warning_literal_and_report_rendering_contract",
        "test_warning_is_in_stdout_and_report_when_phase4_is_not_required",
        "test_required_true_is_ignored_by_gate_after_non_object_parent_refuses",
        "test_generated_characterization_table_drives_compatibility",
        "test_security_and_codex_sequence_is_structural",
    ),
    "tests/test_v016_docs_contracts.py": (
        "test_v018_code_review_migration_is_documented_per_file",
        "test_old_code_review_meaning_is_absent",
    ),
    "tests/test_start_run.py": (
        "test_removed_code_and_required_do_not_force_phase4_but_codex_required_does",
    ),
}
COMPATIBILITY_SUPPORT = {
    "tests/generate_code_review_remnants.py",
    "tests/generate_review_commands_code_tables.py",
    "tests/test_code_review_remnants.py",
}


def load_baseline():
    with open(BASELINE, encoding="ascii") as handle:
        raw = zlib.decompress(base64.b64decode(handle.read()))
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise AssertionError("sealed removed-symbol baseline hash mismatch")
    return json.loads(raw)


def compatibility_test_at(path, line):
    allowed = COMPATIBILITY_TESTS.get(path)
    if not allowed:
        return False
    with open(os.path.join(SCAN_ROOT, path), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in allowed
        and node.lineno <= line <= node.end_lineno
        for node in ast.walk(tree)
    )


class TestCodeReviewRemnants(unittest.TestCase):
    def test_base_inventory_is_nonempty_and_sealed(self):
        baseline = load_baseline()
        self.assertEqual(baseline["baseSha"], BASE_SHA)
        self.assertEqual(len(baseline["matches"]), 285)
        counts = {}
        for match in baseline["matches"]:
            counts[match["path"]] = counts.get(match["path"], 0) + 1
        self.assertEqual(counts["skills/audit/scripts/code-review-plan.py"], 2)
        self.assertEqual(counts["skills/audit/scripts/start-run.py"], 4)

    def test_key_and_access_forms_are_detected(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "skills", "audit"))
            os.makedirs(os.path.join(root, "docs"))
            with open(os.path.join(root, "skills", "audit", "sample.py"),
                      "w", encoding="utf-8") as handle:
                handle.write(
                    'review_commands = config.get("reviewCommands", {})\n'
                    'legacy_code = review_commands.get("code")\n'
                    'legacy_required = review_commands.get("required") is True\n')
            with open(os.path.join(root, "docs", "sample.json"),
                      "w", encoding="utf-8") as handle:
                handle.write(
                    '{\n  "reviewCommands": {\n    "code": "/custom",\n'
                    '    "required": true,\n    "security": "/security-review"\n  }\n}\n')
            matches = generate(root)["matches"]
        observed = {(item["path"], item["line"], item["symbol"]) for item in matches}
        self.assertIn(("skills/audit/sample.py", 2, "removed-config-access"), observed)
        self.assertIn(("skills/audit/sample.py", 3, "removed-config-access"), observed)
        self.assertIn(("docs/sample.json", 3, "removed-config-key"), observed)
        self.assertIn(("docs/sample.json", 4, "removed-config-key"), observed)

    def test_only_fixed_allowlisted_remnants_remain(self):
        actual = generate(SCAN_ROOT)["matches"]
        unexpected = []
        for match in actual:
            key = (match["path"], match["line"], match["symbol"])
            if key in MIGRATION_ALLOWLIST | WARNING_ALLOWLIST | HISTORY_ALLOWLIST:
                continue
            if (compatibility_test_at(match["path"], match["line"])
                    or match["path"] in COMPATIBILITY_SUPPORT):
                continue
            unexpected.append(
                f'{match["path"]}:{match["line"]}:{match["symbol"]}: {match["text"]}')
        self.assertEqual(unexpected, [], "unexpected removed-symbol remnants:\n" + "\n".join(unexpected))

        observed_migration = {
            (match["path"], match["line"], match["symbol"])
            for match in actual
            if (match["path"], match["line"], match["symbol"]) in MIGRATION_ALLOWLIST
        }
        self.assertEqual(observed_migration, MIGRATION_ALLOWLIST)
        migration_lines = {}
        for path, line, _symbol in observed_migration:
            migration_lines.setdefault(path, set()).add(line)
        self.assertEqual(migration_lines, {
            "docs/ADOPTION.md": {119},
            "docs/ADOPTION.ja.md": {102},
            "skills/audit/references/config-schema.md": {60, 61},
        })


if __name__ == "__main__":
    unittest.main()
