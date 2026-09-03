import base64
import hashlib
import importlib.util
import json
import os
import sys
import unittest
import zlib

from tests.wp12_helpers import RunFixture

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_SHA = "749ff0d3b5d4f5fc14f7c42a4364caf921759789"
REAL_DECIDE = os.path.join(ROOT, "skills", "audit", "scripts", "decide-verdict.py")
DECIDE = os.environ.get("DOCAUDIT_DECIDE_PATH", REAL_DECIDE)
SCRIPT_DIR = os.path.dirname(REAL_DECIDE)
TABLES = os.environ.get(
    "DOCAUDIT_TABLES_PATH",
    os.path.join(ROOT, "tests", "review_commands_code_tables.json.zlib.b64"))
SKILL = os.environ.get("DOCAUDIT_SKILL_PATH", os.path.join(ROOT, "skills", "audit", "SKILL.md"))
TABLES_SHA256 = "e20bcee03e6c8e39755dd69f754e8b71653c3720d58f23a738df66ad0ac5decf"
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sealed_tables():
    with open(TABLES, encoding="ascii") as handle:
        raw = zlib.decompress(base64.b64decode(handle.read()))
    if hashlib.sha256(raw).hexdigest() != TABLES_SHA256:
        raise AssertionError("sealed reviewCommands table hash mismatch")
    return json.loads(raw)


class TestReviewCommandsCodeRemoval(unittest.TestCase):
    def test_warning_literal_and_report_rendering_contract(self):
        decide = load(DECIDE, "decide_review_commands_warning_literal")
        warning = (
            "reviewCommands.code is no longer supported (removed in docaudit v0.18.0) and was ignored. "
            "Delete reviewCommands.code and reviewCommands.required from .claude/doc-audit.json; "
            "keep reviewCommands.security. Run /code-review as a separate PR-time step if you want it."
        )
        self.assertEqual(decide.REVIEW_COMMANDS_CODE_REMOVED, "reviewCommandsCodeRemoved")
        self.assertEqual(decide.REVIEW_COMMANDS_CODE_REMOVED_WARNING, warning)
        self.assertEqual(
            decide.review_commands_code_warning({"reviewCommands": {"required": False}}),
            "reviewCommandsCodeRemoved")
        rendered = decide.render_report(
            RunFixture(self).report_template(), "CONSISTENT", "2026-09-03", counts={},
            history_status="absent", warnings=["reviewCommandsCodeRemoved"], sibling={},
            anchor_written=False).decode()
        self.assertIn("reviewCommandsCodeRemoved", rendered)
        self.assertIn(warning, rendered)

    def test_warning_is_in_stdout_and_report_when_phase4_is_not_required(self):
        decide = load(DECIDE, "decide_review_commands_warning_report")
        fx = RunFixture(self, docs=(), config_extra={
            "reviewCommands": {"code": "/code-review high", "required": False,
                               "security": "/security-review"},
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        self.assertEqual(fx.write_template().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["warnings"], ["reviewCommandsCodeRemoved"])
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            report = handle.read()
        self.assertIn("reviewCommandsCodeRemoved", report)
        self.assertIn(decide.REVIEW_COMMANDS_CODE_REMOVED_WARNING, report)

    def test_required_true_is_ignored_by_gate_after_non_object_parent_refuses(self):
        refused = RunFixture(self, docs=(), config_extra={"reviewCommands": []})
        self.assertEqual(refused.open().returncode, 0)
        self.assertEqual(refused.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(refused.complete(verdicts={}, returns_override=[]).returncode, 0)
        refused_proc = refused.gate()
        self.assertEqual(refused_proc.returncode, 3, refused_proc.stdout + refused_proc.stderr)
        self.assertEqual(json.loads(refused_proc.stdout)["verdict"], "REFUSED")

        accepted = RunFixture(self, docs=(), config_extra={
            "reviewCommands": {
                "code": "/code-review high", "required": True,
                "security": "/security-review",
            },
        })
        self.assertEqual(accepted.open().returncode, 0)
        self.assertEqual(accepted.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(accepted.complete(verdicts={}, returns_override=[]).returncode, 0)
        accepted_proc = accepted.gate()
        self.assertEqual(accepted_proc.returncode, 0, accepted_proc.stdout + accepted_proc.stderr)
        result = json.loads(accepted_proc.stdout)
        self.assertEqual(result["warnings"].count("reviewCommandsCodeRemoved"), 1)
        self.assertNotEqual(result["verdict"], "REFUSED")

    def test_generated_characterization_table_drives_compatibility(self):
        decide = load(DECIDE, "decide_review_commands_removed")
        tables = sealed_tables()
        self.assertEqual(tables["baseSha"], BASE_SHA)
        self.assertEqual(len(tables["rows"]), 1344)
        baseline = []
        for row in tables["rows"]:
            baseline.append(row["baseline"])
            config = row["config"]
            expected = row["expected"]
            if expected["outcome"] == "REFUSED":
                with self.assertRaises(decide.Refused):
                    decide.review_commands_code_warning(config)
            else:
                warning = decide.review_commands_code_warning(config)
                if expected["warnings"]:
                    self.assertEqual(warning, "reviewCommandsCodeRemoved")
                else:
                    self.assertIsNone(warning)
        self.assertTrue(any(result == [2, "refuse", "invalid-review-config"]
                            for result in baseline))

    def test_security_and_codex_sequence_is_structural(self):
        with open(SKILL, encoding="utf-8") as handle:
            skill = handle.read()
        phase4 = skill.split("## Phase 4 —", 1)[1].split("## Phase 5", 1)[0]
        review_read = phase4.index('REVIEW_COMMANDS_JSON="$(python3')
        branch = phase4.index("Global gate:", review_read)
        security = phase4.index("reviewCommands.security", branch)
        codex_plan = phase4.index('CODEX_REVIEW_PLAN="$(python3', security)
        self.assertLess(review_read, branch)
        self.assertLess(branch, security)
        self.assertLess(security, codex_plan)
        self.assertEqual(phase4.count('REVIEW_COMMANDS_JSON="$(python3'), 1)
        self.assertEqual(phase4.count('CODEX_REVIEW_PLAN="$(python3'), 1)
        normalized = " ".join(phase4.split())
        instruction = (
            "Normalize any `/security-audit ...` request to `/security-review`, then run "
            "`reviewCommands.security` exactly as before."
        )
        self.assertEqual(normalized.count(instruction), 1)
