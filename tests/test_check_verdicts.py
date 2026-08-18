"""Tests for the report-only Phase-3 completeness preflight."""

import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "skills", "audit", "scripts", "check-verdicts.py")
WRITE = os.path.join(ROOT, "skills", "audit", "scripts", "write-verdict.py")
GATE = os.path.join(ROOT, "skills", "audit", "scripts", "decide-verdict.py")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    )


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = os.path.join(self.tmp.name, "run")
        os.makedirs(os.path.join(self.run_dir, "verdicts"))
        self.runid = "run-check-1"
        self.impact_json = os.path.join(self.run_dir, "impact.json")

    def write_manifest(self, impacted):
        with open(os.path.join(self.run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"runid": self.runid, "impacted": impacted}, f)

    def write_impact(self, impacted):
        with open(self.impact_json, "w", encoding="utf-8") as f:
            json.dump({"impacted": impacted}, f)

    def write_verdict(self, name, path, verdict="PASS", runid=None):
        record = {
            "runid": runid or self.runid,
            "path": path,
            "verdict": verdict,
            "rationale": "checked",
        }
        with open(os.path.join(self.run_dir, "verdicts", name), "w", encoding="utf-8") as f:
            json.dump(record, f)

    def check(self):
        p = subprocess.run(
            [sys.executable, CHECK, "--run-dir", self.run_dir,
             "--impact-json", self.impact_json],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)


class TestCheckVerdicts(Base):
    def test_missing_includes_workflow_ready_provenance(self):
        self.write_manifest(["docs/a.md", "docs/b.md"])
        self.write_impact([
            {"path": "docs/a.md", "provenance": "mapped"},
            {"path": "docs/b.md", "provenance": "heuristic"},
        ])
        self.write_verdict("a.json", "docs/a.md")
        out = self.check()
        self.assertFalse(out["phase3Complete"])
        self.assertEqual(out["missing"], ["docs/b.md"])
        self.assertEqual(
            out["missingImpacted"],
            [{"path": "docs/b.md", "provenance": "heuristic"}],
        )

    def test_complete_when_every_path_has_one_valid_record(self):
        self.write_manifest(["docs/a.md", "docs/b.md"])
        self.write_impact([
            {"path": "docs/a.md", "provenance": "mapped"},
            {"path": "docs/b.md", "provenance": "both"},
        ])
        self.write_verdict("a.json", "docs/a.md")
        self.write_verdict("b.json", "docs/b.md", verdict="WARN")
        out = self.check()
        self.assertTrue(out["phase3Complete"])
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["invalid"], [])

    def test_missing_cached_verdict_is_still_reported(self):
        with open(os.path.join(self.run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"runid": self.runid, "impacted": ["docs/a.md", "docs/b.md"],
                       "dispatch": ["docs/a.md"], "cached": ["docs/b.md"]}, f)
        self.write_impact([{"path": "docs/a.md", "provenance": "mapped"},
                           {"path": "docs/b.md", "provenance": "mapped"}])
        self.write_verdict("a.json", "docs/a.md")
        out = self.check()
        self.assertEqual(out["missing"], ["docs/b.md"])
        self.assertFalse(out["phase3Complete"])

    def test_foreign_runid_and_broken_json_are_invalid_and_missing(self):
        self.write_manifest(["docs/a.md", "docs/b.md"])
        self.write_impact([
            {"path": "docs/a.md", "provenance": "mapped"},
            {"path": "docs/b.md", "provenance": "mapped"},
        ])
        self.write_verdict("foreign.json", "docs/a.md", runid="other-run")
        with open(os.path.join(self.run_dir, "verdicts", "broken.json"), "w") as f:
            f.write("not json")
        out = self.check()
        self.assertEqual(out["missing"], ["docs/a.md", "docs/b.md"])
        self.assertEqual(len(out["invalid"]), 2)
        self.assertTrue(any("runid" in item for item in out["invalid"]))
        self.assertTrue(any("invalid JSON" in item for item in out["invalid"]))

    def test_duplicate_valid_records_are_reported(self):
        self.write_manifest(["docs/a.md"])
        self.write_impact([{"path": "docs/a.md", "provenance": "mapped"}])
        self.write_verdict("a-1.json", "docs/a.md")
        self.write_verdict("a-2.json", "docs/a.md")
        out = self.check()
        self.assertEqual(out["duplicates"], ["docs/a.md"])
        self.assertFalse(out["phase3Complete"])

    def test_foreign_path_is_extra_and_invalid(self):
        self.write_manifest(["docs/a.md"])
        self.write_impact([{"path": "docs/a.md", "provenance": "mapped"}])
        self.write_verdict("a.json", "docs/a.md")
        self.write_verdict("extra.json", "docs/extra.md")
        out = self.check()
        self.assertEqual(out["extra"], ["docs/extra.md"])
        self.assertTrue(any("not in manifest.impacted" in item for item in out["invalid"]))
        self.assertFalse(out["phase3Complete"])

    def test_manifest_impact_mismatch_warns_and_keeps_unknown_missing(self):
        self.write_manifest(["docs/a.md", "docs/missing.md"])
        self.write_impact([
            {"path": "docs/a.md", "provenance": "mapped"},
            {"path": "docs/extra.md", "provenance": "heuristic"},
        ])
        self.write_verdict("a.json", "docs/a.md")
        out = self.check()
        self.assertTrue(out["manifestMismatch"])
        self.assertTrue(out["warnings"])
        self.assertEqual(out["missing"], ["docs/missing.md"])
        self.assertEqual(
            out["missingImpacted"],
            [{"path": "docs/missing.md", "provenance": "unknown"}],
        )


class TestRecoveryDrill(unittest.TestCase):
    def test_missing_then_writer_repairs_before_gate(self):
        from tests.wp12_helpers import RunFixture
        fx = RunFixture(self)
        fx.open(); fx.plan_start_seal()
        fx.write_verdict("docs/a.md")
        returns = [{"attempt": 1, "assignedPath": "docs/a.md", "returnedPath": "docs/a.md",
                    "verdict": "PASS", "rationale": "x", "suggestion": None}]
        fx.write_evidence("returns", returns)
        fx.write_evidence("phase4", {"findings": []})
        checked = subprocess.run(
            [sys.executable, CHECK, "--run-dir", fx.run_dir,
             "--impact-json", os.path.join(fx.run_dir, "impact.json"), "--returns"],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(checked.stdout)["missing"], ["docs/b.md"])
        fx.write_verdict("docs/b.md")
        returns.append({"attempt": 2, "assignedPath": "docs/b.md", "returnedPath": "docs/b.md",
                        "verdict": "PASS", "rationale": "fixed", "suggestion": None})
        fx.write_evidence("returns", returns)
        checked = subprocess.run(
            [sys.executable, CHECK, "--run-dir", fx.run_dir,
             "--impact-json", os.path.join(fx.run_dir, "impact.json"), "--returns"],
            capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(checked.stdout)["phase3Complete"])
        self.assertEqual(fx.gate().returncode, 0)


if __name__ == "__main__":
    unittest.main()
