import hashlib
import importlib.util
import json
import os
import re
import sys
import unittest

from tests.wp12_helpers import RunFixture, write


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECIDE = os.path.join(ROOT, "skills", "audit", "scripts", "decide-verdict.py")
SCRIPT_DIR = os.path.dirname(DECIDE)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def codex(state="not-active", variant=None):
    return {"state": state, "promptVariant": variant, "carryForwardSha": "none"}


def phase4(state=None, findings=None, *, codex_value=None):
    value = {"findings": findings or [], "codexReview": codex_value or codex()}
    if state is not None:
        value["codeReview"] = {"state": state}
    return value


class CodeReviewGateTests(unittest.TestCase):
    def prepare(self, review_commands=None, phase4_value=None, *, docs=("docs/a.md",),
                report=False, mode="incremental"):
        extra = {}
        if review_commands is not None:
            extra["reviewCommands"] = review_commands
        if report:
            extra["reportPath"] = "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"
        fx = RunFixture(self, docs=docs, config_extra=extra)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=list(docs), mode=mode).returncode, 0)
        self.assertEqual(fx.complete(phase4=phase4_value).returncode, 0)
        if report:
            self.assertEqual(fx.write_template().returncode, 0)
        return fx

    def result(self, fx, expected_code):
        proc = fx.gate()
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    @staticmethod
    def rewrite_json(path, value):
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        write(path, raw)
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def test_optional_states_and_warning(self):
        for state in ("blocked-by-settings", "not-run"):
            with self.subTest(state=state):
                fx = self.prepare({"code": "/code-review low"}, phase4(state))
                result = self.result(fx, 0)
                self.assertIn("codeReviewNotRun", result["warnings"])
                self.assertEqual(result["codeReviewStatus"],
                                 self.module().CODE_REVIEW_STATUS_LINES[state])

    def test_required_not_run_is_refused(self):
        fx = self.prepare({"code": "/code-review high", "required": True},
                          phase4("not-run"))
        result = self.result(fx, 3)
        self.assertEqual(result["reason"], "code-review-required-not-run")

    def test_complete_eligibility_table(self):
        cases = (
            (None, phase4(), 0),
            (None, phase4("ran"), 3),
            ({"code": "/code-review low"}, phase4("ran"), 0),
            ({"code": "/code-review low"}, phase4(), 3),
            ({"code": "/custom"}, phase4(), 0),
            ({"code": "/custom"}, phase4("ran"), 3),
        )
        for configured, evidence, expected in cases:
            with self.subTest(configured=configured, evidence=evidence):
                self.result(self.prepare(configured, evidence), expected)

        optional = RunFixture(self, docs=(), config_extra={
            "reviewCommands": {"code": "/code-review medium"}})
        self.assertEqual(optional.open().returncode, 0)
        self.assertEqual(optional.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(optional.complete(verdicts={}, returns_override=[]).returncode, 0)
        result = self.result(optional, 0)
        self.assertEqual(result["codeReviewStatus"],
                         self.module().CODE_REVIEW_STATUS_LINES["phase4-not-required"])
        for configured, status_key in ((None, "not-active"), ({"code": "/custom"}, "legacy")):
            with self.subTest(configured=configured):
                extra = {} if configured is None else {"reviewCommands": configured}
                fx = RunFixture(self, docs=(), config_extra=extra)
                self.assertEqual(fx.open().returncode, 0)
                self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
                self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
                result = self.result(fx, 0)
                self.assertEqual(result["codeReviewStatus"],
                                 self.module().CODE_REVIEW_STATUS_LINES[status_key])

    def test_config_refuse_precedes_sentinel_and_publishes_report(self):
        fx = self.prepare({"code": "/code-review xhigh"}, phase4(), report=True)
        fx.evidence["phase4"] = "none"
        result = self.result(fx, 3)
        self.assertIn("invalid reviewCommands.code", result["reason"])
        self.assertIn("reportPath", result)
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn("✗ code-review: invalid configuration (audit refused)", body)
        self.assertIn("docs/ADOPTION.md#code-review-autonomous-execution-and-opt-out", body)

    def test_phase4_required_type_has_highest_priority_and_default_status(self):
        for value in (None, 0, 1, "true"):
            with self.subTest(value=value):
                fx = self.prepare({"code": "/code-review xhigh"}, phase4())
                path = os.path.join(fx.run_dir, "manifest.json")
                with open(path, encoding="utf-8") as handle:
                    manifest = json.load(handle)
                manifest["phase4Required"] = value
                fx.evidence["manifest"] = self.rewrite_json(path, manifest)
                result = self.result(fx, 3)
                self.assertEqual(result["reason"], "manifest.phase4Required must be boolean")
                self.assertEqual(result["codeReviewStatus"],
                                 self.module().DEFAULT_CODE_REVIEW_STATUS)

    def test_sentinel_conflict_precedes_code_review_eligibility(self):
        fx = self.prepare({"code": "/code-review low"}, phase4("ran"))
        manifest_path = os.path.join(fx.run_dir, "manifest.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["phase4Required"] = False
        fx.evidence["manifest"] = self.rewrite_json(manifest_path, manifest)
        phase4_path = os.path.join(fx.run_dir, "phase4.json")
        with open(phase4_path, encoding="utf-8") as handle:
            evidence = json.load(handle)
        evidence["codeReview"] = {"state": "unknown"}
        fx.evidence["phase4"] = self.rewrite_json(phase4_path, evidence)
        result = self.result(fx, 3)
        self.assertEqual(
            result["reason"], "phase4 evidence conflicts with manifest.phase4Required=false")
        self.assertEqual(result["codeReviewStatus"], self.module().DEFAULT_CODE_REVIEW_STATUS)

    def test_gate_rejects_unknown_and_non_object_code_review_evidence(self):
        for value in ({"state": "unknown"}, [], "ran", None):
            with self.subTest(value=value):
                fx = self.prepare({"code": "/code-review low"}, phase4("ran"))
                path = os.path.join(fx.run_dir, "phase4.json")
                with open(path, encoding="utf-8") as handle:
                    evidence = json.load(handle)
                evidence["codeReview"] = value
                fx.evidence["phase4"] = self.rewrite_json(path, evidence)
                self.result(fx, 3)

    def test_fake_findings_are_rejected_except_p6_ran(self):
        finding = {"source": "code-review", "file": "src/app.py", "title": "bug"}
        cases = (
            (None, phase4(findings=[finding])),
            ({"code": "/custom"}, phase4(findings=[finding])),
            ({"code": "/code-review low"}, phase4("not-run", [finding])),
        )
        for configured, evidence in cases:
            with self.subTest(configured=configured):
                self.result(self.prepare(configured, evidence), 3)
        accepted = self.result(self.prepare(
            {"code": "/code-review low"}, phase4("ran", [finding])), 0)
        self.assertEqual(accepted["verdict"], "NEEDS_FIX")

    def test_code_review_missing_or_unknown_severity_blocks_only_for_that_source(self):
        for finding in (
                {"source": "code-review", "file": "src/app.py", "title": "missing"},
                {"source": "code-review", "file": "src/app.py", "title": "unknown",
                 "severity": "UNSPECIFIED"}):
            with self.subTest(finding=finding):
                result = self.result(self.prepare(
                    {"code": "/code-review low"}, phase4("ran", [finding])), 0)
                self.assertEqual(result["verdict"], "NEEDS_FIX")
        other = {"source": "security-review", "title": "missing"}
        self.result(self.prepare(None, phase4(findings=[other])), 3)

    def test_code_review_findings_do_not_enter_phase4_runs(self):
        findings = [
            {"source": "codex-review", "file": "docs/a.md", "severity": "HIGH"},
            {"source": "code-review", "file": "src/app.py", "severity": "HIGH"},
        ]
        fx = self.prepare(
            {"code": "/code-review low"},
            phase4("ran", findings, codex_value=codex("completed", "full")),
            mode="full")
        self.result(fx, 0)
        with open(fx.history, encoding="utf-8") as handle:
            runs = json.load(handle)["phase4Runs"]
        self.assertEqual(runs[0]["findings"],
                         [{"file": "docs/a.md", "severity": "HIGH"}])

    def test_token_contract_and_all_fixed_lines(self):
        module = self.module()
        self.assertEqual(module.TOKEN_COUNTS["{{GATE_CODE_REVIEW_STATUS}}"], 1)
        self.assertNotIn("{{GATE_CODE_REVIEW_STATUS}}", module.OPTIONAL_TOKENS)
        template = RunFixture(self).report_template()
        for line in module.CODE_REVIEW_STATUS_LINES.values():
            rendered = module.render_report(
                template, "CONSISTENT", "2026-08-31", counts={}, history_status="absent",
                warnings=[], sibling={}, code_review_status=line)
            self.assertEqual(rendered.decode().count(line), 1)

    def test_skill_placeholder_table_matches_gate_tokens(self):
        module = self.module()
        with open(os.path.join(ROOT, "skills", "audit", "SKILL.md"), encoding="utf-8") as handle:
            skill = handle.read()
        rows = dict(re.findall(
            r"^\| `(\{\{GATE_[A-Z0-9_]+\}\})` \| ([^|]+?) \|", skill, re.M))
        self.assertEqual(set(rows), set(module.TOKEN_COUNTS))
        for token, expected in module.TOKEN_COUNTS.items():
            if token in module.OPTIONAL_TOKENS:
                self.assertEqual(rows[token], "0 or 1")
            else:
                self.assertEqual(int(rows[token]), expected)

    @staticmethod
    def module():
        spec = importlib.util.spec_from_file_location("decide_code_review_test", DECIDE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


if __name__ == "__main__":
    unittest.main()
