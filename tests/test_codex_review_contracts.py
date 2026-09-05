"""Independent result, writer, and gate contracts for sealed codex review output."""

import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

from tests.wp12_helpers import RunFixture, write


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from codex_review_output import derive_findings, validate_result  # noqa: E402


def seal(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


class CodexReviewFixtureMixin:
    def prepared(self, *, mode="full"):
        fx = RunFixture(self, config_extra={"codexReview": {}})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode=mode).returncode, 0)
        for path in fx.docs:
            self.assertEqual(fx.write_verdict(path).returncode, 0)
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "PASS", "rationale": "checked", "suggestion": None}
                   for path in fx.docs]
        self.assertEqual(fx.write_evidence("returns", returns).returncode, 0)
        return fx

    def completed(self, findings=None, non_codex=None):
        fx = self.prepared()
        raw_result = {"findings": findings or [
            {"severity": "medium", "title": "same", "file": "docs/a.md"},
            {"severity": "medium", "title": "same", "file": "docs/a.md"},
            {"severity": "low", "title": "other", "file": "docs/b.md"},
        ]}
        state = {"state": "completed", "promptVariant": "full",
                 "carryForwardSha": "none"}
        proc = fx.complete_codex(raw_result, non_codex or [], state)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return fx

    def assert_refused_and_unlocked(self, fx, reason=None):
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        if reason:
            self.assertIn(reason, result["reason"])
        self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))
        return result


class TestCodexReviewOutputOracle(unittest.TestCase):
    def test_independent_oracle_preserves_order_unicode_and_duplicates(self):
        raw = {"findings": [
            {"severity": "critical", "title": "壊れた手順", "file": "docs/手順.md"},
            {"severity": "high", "title": "B", "file": "docs/b.md"},
            {"severity": "medium", "title": "C", "file": "docs/c.md"},
            {"severity": "low", "title": "C", "file": "docs/c.md"},
            {"severity": "low", "title": "C", "file": "docs/c.md"},
        ]}
        expected = [
            {"severity": "CRITICAL", "source": "codex-review",
             "title": "壊れた手順 (docs/手順.md)", "file": "docs/手順.md"},
            {"severity": "HIGH", "source": "codex-review",
             "title": "B (docs/b.md)", "file": "docs/b.md"},
            {"severity": "MEDIUM", "source": "codex-review",
             "title": "C (docs/c.md)", "file": "docs/c.md"},
            {"severity": "LOW", "source": "codex-review",
             "title": "C (docs/c.md)", "file": "docs/c.md"},
            {"severity": "LOW", "source": "codex-review",
             "title": "C (docs/c.md)", "file": "docs/c.md"},
        ]
        self.assertIs(validate_result(raw), raw)
        self.assertEqual(derive_findings(raw), expected)

    def test_schema_boundaries_are_rejected(self):
        valid = {"findings": [{"severity": "low", "title": "x", "file": "a"}]}
        bad = [
            [], {"findings": [], "extra": 1}, {"findings": "bad"},
            {"findings": [None]},
            {"findings": [{"severity": "low", "title": "x", "file": "a", "x": 1}]},
            {"findings": [{"severity": "urgent", "title": "x", "file": "a"}]},
            {"findings": [{"severity": "low", "title": "", "file": "a"}]},
            {"findings": [{"severity": "low", "title": "x"}]},
            {"findings": [{"severity": "low", "title": "x", "file": ""}]},
        ]
        validate_result(valid)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_result(value)

    def test_skill_state_derivation_stops_on_none(self):
        with open(os.path.join(ROOT, "skills", "audit", "SKILL.md"), encoding="utf-8") as handle:
            skill = handle.read()
        match = re.search(
            r'python3 -c \'([^\']*codexReviewResult[^\']*)\' "\$EVIDENCE"',
            skill,
        )
        self.assertIsNotNone(match)
        normalized_skill = " ".join(skill.split())
        self.assertNotIn('EVIDENCE="$(python3 "$SD/scripts/codex-review-exec.py"', skill)
        self.assertNotIn('CODEX_REVIEW_STATE="$(python3 -c', skill)
        self.assertIn("On exit 0, its complete stdout JSON MUST replace `EVIDENCE` verbatim",
                      normalized_skill)
        self.assertIn("do not touch `EVIDENCE`; release the run and stop", normalized_skill)
        self.assertIn("Check the exit code before binding", normalized_skill)
        self.assertIn("do not bind `CODEX_REVIEW_STATE`", normalized_skill)
        code = match.group(1)
        self.assertIn('s="completed" if', code)
        self.assertIn('sys.exit(2) if s is None else print(s)', code)
        cases = (
            ("sha256:" + "a" * 64, 0, "completed"),
            ("failed", 0, "execution-failed"),
            ("none", 2, ""),
        )
        for value, status, output in cases:
            with self.subTest(value=value):
                proc = subprocess.run(
                    [sys.executable, "-c", code, json.dumps({"codexReviewResult": value})],
                    capture_output=True, text=True,
                )
                self.assertEqual(proc.returncode, status, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout.strip(), output)


class TestCodexReviewWriter(CodexReviewFixtureMixin, unittest.TestCase):
    def test_writer_appends_derived_duplicates_after_non_codex_and_gate_preserves_verdict(self):
        non_codex = [
            {"source": "security-review", "severity": "FAIL", "title": "block", "file": "x"},
            {"source": "review", "severity": "WARN", "title": "warn", "file": "y"},
        ]
        fx = self.completed(non_codex=non_codex)
        with open(os.path.join(fx.run_dir, "phase4.json"), encoding="utf-8") as handle:
            phase4 = json.load(handle)
        self.assertEqual(phase4["findings"][:2], non_codex)
        self.assertEqual(phase4["findings"][2:4], [
            {"source": "codex-review", "severity": "MEDIUM",
             "title": "same (docs/a.md)", "file": "docs/a.md"},
            {"source": "codex-review", "severity": "MEDIUM",
             "title": "same (docs/a.md)", "file": "docs/a.md"},
        ])
        gated = fx.gate()
        self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)
        self.assertEqual(json.loads(gated.stdout)["verdict"], "NEEDS_FIX")

    def test_failed_adds_no_findings(self):
        fx = self.prepared()
        state = {"state": "execution-failed", "promptVariant": "full",
                 "carryForwardSha": "none"}
        proc = fx.complete_codex(None, [], state)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "phase4.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["findings"], [])

    def test_missing_findings_is_materialized_for_none_and_completed(self):
        cases = (
            ("not-active", None, None, []),
            ("completed", "full", {
                "findings": [{"severity": "low", "title": "derived", "file": "docs/a.md"}],
            }, [{"source": "codex-review", "severity": "LOW",
                 "title": "derived (docs/a.md)", "file": "docs/a.md"}]),
        )
        for state, variant, result, expected in cases:
            with self.subTest(state=state):
                fx = self.prepared()
                if state == "completed":
                    raw = encoded(result)
                    write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
                    fx.evidence["codexReviewResult"] = seal(raw)
                payload = {"codexReview": {
                    "state": state, "promptVariant": variant, "carryForwardSha": "none",
                }}
                proc = fx.write_evidence("phase4", payload)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                with open(os.path.join(fx.run_dir, "phase4.json"), encoding="utf-8") as handle:
                    self.assertEqual(json.load(handle)["findings"], expected)

    def test_supplied_codex_finding_is_independently_rejected_by_writer(self):
        raw = encoded({"findings": []})
        supplied = {"source": "codex-review", "severity": "LOW",
                    "title": "supplied (docs/a.md)", "file": "docs/a.md"}
        payload = {"findings": [supplied], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none",
        }}

        writer_fx = self.prepared()
        write(os.path.join(writer_fx.run_dir, "codex-review-result.json"), raw)
        writer_fx.evidence["codexReviewResult"] = seal(raw)
        before = json.loads(json.dumps(writer_fx.evidence))
        proc = writer_fx.write_evidence("phase4", payload)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertFalse(os.path.exists(os.path.join(writer_fx.run_dir, "phase4.json")))
        self.assertEqual(writer_fx.evidence, before)

    def test_directly_sealed_supplied_codex_finding_is_rejected_by_gate(self):
        raw = encoded({"findings": []})
        supplied = {"source": "codex-review", "severity": "LOW",
                    "title": "supplied (docs/a.md)", "file": "docs/a.md"}
        payload = {"findings": [supplied], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none",
        }}
        gate_fx = self.prepared()
        write(os.path.join(gate_fx.run_dir, "codex-review-result.json"), raw)
        gate_fx.evidence["codexReviewResult"] = seal(raw)
        gate_fx.seal_phase4(payload)
        self.assert_refused_and_unlocked(gate_fx, "codexReviewFindingsMismatch: +0 -1")

    def test_state_and_seal_three_by_three_table(self):
        result = encoded({"findings": []})
        for state in ("completed", "execution-failed", "not-active"):
            for seal_value in ("sha", "failed", "none"):
                expected_ok = ((state, seal_value) in {
                    ("completed", "sha"), ("execution-failed", "failed"),
                    ("not-active", "none")})
                with self.subTest(state=state, seal=seal_value):
                    fx = self.prepared()
                    write(os.path.join(fx.run_dir, "codex-review-result.json"), result)
                    fx.evidence["codexReviewResult"] = (
                        seal(result) if seal_value == "sha" else seal_value)
                    before = dict(fx.evidence)
                    payload = {"findings": [], "codexReview": {
                        "state": state,
                        "promptVariant": "full" if state != "not-active" else None,
                        "carryForwardSha": "none"}}
                    proc = fx.write_evidence("phase4", payload)
                    self.assertEqual(proc.returncode, 0 if expected_ok else 2,
                                     proc.stdout + proc.stderr)
                    if not expected_ok:
                        self.assertEqual(proc.stdout, "")
                        self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "phase4.json")))
                        self.assertEqual(fx.evidence, before)

    def test_writer_rejects_missing_mismatched_and_invalid_results(self):
        cases = ("missing", "mismatch", "invalid")
        for case in cases:
            with self.subTest(case=case):
                fx = self.prepared()
                payload = {"findings": [], "codexReview": {
                    "state": "completed", "promptVariant": "full",
                    "carryForwardSha": "none"}}
                if case == "missing":
                    fx.evidence["codexReviewResult"] = "sha256:" + "a" * 64
                elif case == "mismatch":
                    raw = encoded({"findings": []})
                    write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
                    fx.evidence["codexReviewResult"] = "sha256:" + "a" * 64
                else:
                    raw = b'{"findings":"bad"}'
                    write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
                    fx.evidence["codexReviewResult"] = seal(raw)
                before = dict(fx.evidence)
                proc = fx.write_evidence("phase4", payload)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "phase4.json")))
                self.assertEqual(fx.evidence, before)

    def test_writer_rejects_missing_and_invalid_seal_fields_without_changes(self):
        for value in (None, "bad", 1, []):
            with self.subTest(value=value):
                fx = self.prepared()
                if value is None:
                    del fx.evidence["codexReviewResult"]
                else:
                    fx.evidence["codexReviewResult"] = value
                before = json.loads(json.dumps(fx.evidence))
                proc = fx.write_evidence("phase4", {"findings": [], "codexReview": {
                    "state": "not-active", "promptVariant": None,
                    "carryForwardSha": "none"}})
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "phase4.json")))
                self.assertEqual(fx.evidence, before)

    def test_two_mib_exact_is_accepted(self):
        prefix = b'{"findings":[]}'
        raw = prefix + b" " * (2 * 1024 * 1024 - len(prefix))
        fx = self.prepared()
        write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
        fx.evidence["codexReviewResult"] = seal(raw)
        proc = fx.write_evidence("phase4", {"findings": [], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none"}})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestCodexReviewGateMutations(CodexReviewFixtureMixin, unittest.TestCase):
    def mutate_phase(self, fx, change):
        path = os.path.join(fx.run_dir, "phase4.json")
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
        change(value)
        fx.seal_phase4(value)

    def test_m1_to_m5_phase4_multiset_mutations(self):
        changes = {
            "M1": lambda value: value["findings"].pop(),
            "M2": lambda value: value["findings"][0].update(severity="CRITICAL"),
            "M3": lambda value: value["findings"][0].update(title="same! (docs/a.md)"),
            "M4": lambda value: value["findings"][0].update(file="docs/b.md"),
            "M5": lambda value: value["findings"].pop(0),
        }
        for mutation, change in changes.items():
            with self.subTest(mutation=mutation):
                fx = self.completed()
                self.mutate_phase(fx, change)
                self.assert_refused_and_unlocked(fx, "codexReviewFindingsMismatch")

    def test_m6_result_changed_without_resealing(self):
        fx = self.completed()
        write(os.path.join(fx.run_dir, "codex-review-result.json"), b'{"findings":[]}')
        self.assert_refused_and_unlocked(fx, "sha mismatch")

    def test_m7_invalid_result_resealed(self):
        fx = self.completed()
        raw = b'{"findings":"bad"}'
        write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
        fx.evidence["codexReviewResult"] = seal(raw)
        self.assert_refused_and_unlocked(fx, "codexReviewResult invalid")

    def test_m8_to_m11_state_seal_inconsistency(self):
        cases = (
            ("M8", "execution-failed", "sha"),
            ("M9", "completed", "none"),
            ("M10", "completed", "failed"),
            ("M11", "not-active", "failed"),
        )
        for mutation, state, seal_value in cases:
            with self.subTest(mutation=mutation):
                fx = self.completed()
                self.mutate_phase(
                    fx, lambda value, state=state: value["codexReview"].update(
                        state=state, promptVariant=None if state == "not-active" else "full"))
                if seal_value != "sha":
                    fx.evidence["codexReviewResult"] = seal_value
                self.assert_refused_and_unlocked(fx, "does not match")

    def test_m12_missing_result(self):
        fx = self.prepared()
        fx.evidence["codexReviewResult"] = "sha256:" + "a" * 64
        fx.seal_phase4({"findings": [], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none"}})
        self.assert_refused_and_unlocked(fx, "is missing")

    def test_m13_unsafe_result_kinds_and_oversize(self):
        for kind in ("symlink", "fifo", "oversize"):
            with self.subTest(kind=kind):
                fx = self.prepared()
                path = os.path.join(fx.run_dir, "codex-review-result.json")
                if kind == "symlink":
                    target = os.path.join(fx.run_dir, "target.json")
                    write(target, b'{"findings":[]}')
                    os.symlink(target, path)
                elif kind == "fifo":
                    os.mkfifo(path)
                else:
                    write(path, b" " * (2 * 1024 * 1024 + 1))
                fx.evidence["codexReviewResult"] = "sha256:" + "a" * 64
                fx.seal_phase4({"findings": [], "codexReview": {
                    "state": "completed", "promptVariant": "full",
                    "carryForwardSha": "none"}})
                self.assert_refused_and_unlocked(fx, "codex-review result")

    def test_writer_success_then_result_swap_is_independently_refused(self):
        fx = self.completed()
        write(os.path.join(fx.run_dir, "codex-review-result.json"), b'{"findings":[]}')
        self.assert_refused_and_unlocked(fx, "sha mismatch")


class TestCodexReviewGateStateTable(CodexReviewFixtureMixin, unittest.TestCase):
    def test_state_and_seal_three_by_three_table(self):
        raw = encoded({"findings": []})
        for state in ("completed", "execution-failed", "not-active"):
            for seal_value in ("sha", "failed", "none"):
                expected_ok = ((state, seal_value) in {
                    ("completed", "sha"),
                    ("execution-failed", "failed"),
                    ("not-active", "none"),
                })
                with self.subTest(state=state, seal=seal_value):
                    fx = self.prepared(mode="full")
                    if seal_value == "sha":
                        write(os.path.join(fx.run_dir, "codex-review-result.json"), raw)
                        fx.evidence["codexReviewResult"] = seal(raw)
                    else:
                        fx.evidence["codexReviewResult"] = seal_value
                    fx.seal_phase4({"findings": [], "codexReview": {
                        "state": state,
                        "promptVariant": "full" if state != "not-active" else None,
                        "carryForwardSha": "none",
                    }})
                    gated = fx.gate()
                    self.assertEqual(gated.returncode, 0 if expected_ok else 3,
                                     gated.stdout + gated.stderr)
                    if not expected_ok:
                        self.assertEqual(json.loads(gated.stdout)["verdict"], "REFUSED")
                    self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))

    def test_all_eight_eligibility_rows_and_phase4_absent_reach_gate(self):
        rows = (
            ("full", "full", "completed"),
            ("full", "full", "execution-failed"),
            ("full", None, "skipped-full-run"),
            ("full", None, "not-active"),
            ("incremental", "diff", "completed"),
            ("incremental", "diff", "execution-failed"),
            ("incremental", None, "ref-invalid"),
            ("incremental", None, "not-active"),
        )
        for mode, variant, state in rows:
            with self.subTest(mode=mode, variant=variant, state=state):
                fx = self.prepared(mode=mode)
                codex = {"state": state, "promptVariant": variant,
                         "carryForwardSha": "none"}
                result = {"findings": []} if state == "completed" else None
                proc = fx.complete_codex(result, [], codex)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                gated = fx.gate()
                self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)

        fx = RunFixture(self, docs=())
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        gated = fx.gate()
        self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)

    def test_each_nonterminal_state_rejects_a_non_none_seal(self):
        for mode, state in (("full", "skipped-full-run"),
                            ("full", "not-active"),
                            ("incremental", "ref-invalid")):
            with self.subTest(state=state):
                fx = self.prepared(mode=mode)
                fx.evidence["codexReviewResult"] = "failed"
                fx.seal_phase4({"findings": [], "codexReview": {
                    "state": state, "promptVariant": None, "carryForwardSha": "none"}})
                self.assert_refused_and_unlocked(fx, "does not match")


if __name__ == "__main__":
    unittest.main()
