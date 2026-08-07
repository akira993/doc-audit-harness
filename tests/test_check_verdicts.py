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


class TestRecoveryDrill(Base):
    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        with open(os.path.join(self.repo, "f"), "w", encoding="utf-8") as f:
            f.write("x")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.anchor = ".claude/state/last-doc-audit.json"

    def run_gate(self):
        return subprocess.run(
            [
                sys.executable,
                GATE,
                "--run-dir", self.run_dir,
                "--repo-root", self.repo,
                "--anchor-path", self.anchor,
                "--date", "2026-08-07",
            ],
            capture_output=True,
            text=True,
        )

    def test_missing_refuses_then_writer_repairs_and_gate_passes(self):
        impacted = ["docs/a.md", "docs/b.md"]
        with open(os.path.join(self.run_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({
                "runid": self.runid,
                "head": self.head,
                "mode": "incremental",
                "impacted": impacted,
                "phase4Expected": True,
            }, f)
        self.write_impact([
            {"path": "docs/a.md", "provenance": "mapped"},
            {"path": "docs/b.md", "provenance": "heuristic"},
        ])
        self.write_verdict("a.json", "docs/a.md")
        with open(os.path.join(self.run_dir, "phase4.json"), "w", encoding="utf-8") as f:
            json.dump({"findings": []}, f)

        incomplete = self.check()
        self.assertEqual(incomplete["missing"], ["docs/b.md"])
        refused = self.run_gate()
        self.assertEqual(refused.returncode, 3, refused.stdout + refused.stderr)
        self.assertEqual(json.loads(refused.stdout)["verdict"], "REFUSED")
        anchor_file = os.path.join(self.repo, self.anchor)
        self.assertFalse(os.path.exists(anchor_file))

        out_path = os.path.join(self.run_dir, "verdicts", "b.json")
        written = subprocess.run(
            [
                sys.executable,
                WRITE,
                "--run-dir", self.run_dir,
                "--out", out_path,
                "--runid", self.runid,
                "--path", "docs/b.md",
                "--verdict", "PASS",
            ],
            input="checked after retry\n",
            capture_output=True,
            text=True,
        )
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        self.assertTrue(self.check()["phase3Complete"])

        decided = self.run_gate()
        self.assertEqual(decided.returncode, 0, decided.stdout + decided.stderr)
        self.assertEqual(json.loads(decided.stdout)["verdict"], "CONSISTENT")
        self.assertTrue(os.path.exists(anchor_file))


if __name__ == "__main__":
    unittest.main()
