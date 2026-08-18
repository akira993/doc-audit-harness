"""Run lifecycle tests for the v0.10 run ledger contract."""

import json
import os
import unittest

from tests.wp12_helpers import RunFixture, git, write


class TestStartRun(unittest.TestCase):
    def test_manifest_has_complete_contract_and_preserves_verdict_directory(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        marker = os.path.join(fx.run_dir, "verdicts", "keep.txt")
        write(marker, "keep")
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        for field in ("runid", "head", "mode", "baselineSha", "changedSet",
                      "changeSetSha", "impacted", "dispatch", "cached", "runClass",
                      "phase4Required", "preflightRequired", "contractVersion",
                      "digestExclude", "sealed", "worktreeDigest"):
            self.assertIn(field, manifest)
        self.assertTrue(manifest["sealed"])
        self.assertTrue(os.path.exists(marker))

    def test_full_uses_head_as_baseline(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(mode="full")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["baselineSha"], fx.head)
        self.assertEqual(manifest["mode"], "full")

    def test_full_rejects_empty_impact_when_corpus_exists(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(impacted=[], mode="full")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("full mode requires impacted", proc.stderr)

    def test_manifest_uses_default_doc_globs_and_excludes_claude_worktrees(self):
        fx = RunFixture(self)
        fx.config.pop("docGlobs")
        write(fx.config_path, json.dumps(fx.config, indent=2) + "\n")
        git(fx.repo, "add", fx.config_path)
        git(fx.repo, "commit", "-m", "use default document globs")
        fx.head = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        fx.open()
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["docGlobs"], ["docs/**/*.md", "*.md"])
        self.assertIn(".claude/worktrees", manifest["digestExclude"])

    def test_preflight_requires_phase4_even_when_incremental_impact_is_empty(self):
        fx = RunFixture(self, config_extra={"harness": {"state": "integrated"}})
        fx.open()
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertTrue(manifest["preflightRequired"])
        self.assertTrue(manifest["phase4Required"])
        fx.write_evidence("preflight", {"state": "integrated", "findings": [],
                                         "userDecision": None, "parsed": True})
        fx.write_evidence("returns", [])
        fx.evidence["phase4"] = "none"
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("phase4=none", json.loads(proc.stdout)["reason"])

    def test_open_rejects_invalid_runid(self):
        fx = RunFixture(self)
        proc = fx.open(runid="../escape")
        self.assertEqual(proc.returncode, 2)

    def test_start_rejects_unsafe_impacted_path(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(impacted=["../outside.md"])
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(proc.stderr)

    def test_seal_detects_new_path_after_dispatch(self):
        fx = RunFixture(self)
        fx.open()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        write(impact_path, json.dumps({"impacted": [{"path": "docs/a.md"}]}) + "\n")
        proc = fx.call("plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
                       "--repo-root", fx.repo, "--config", fx.config_path,
                       "--history", fx.history, "--impact-json", impact_path,
                       "--baseline-sha", fx.head, "--mode", "incremental",
                       "--contract-version", "0.10.0", "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        fx.evidence = json.loads(proc.stdout)
        proc = fx.call("start-run.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
                       "--repo-root", fx.repo, "--impact-json", impact_path,
                       "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
                       "--run-class", "standard", "--mode", "incremental",
                       "--config", fx.config_path, "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        fx.evidence = json.loads(proc.stdout)
        write(os.path.join(fx.repo, "new.py"), "new\n")
        proc = fx.call("seal-run.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                       "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["reason"], "change-set-drift")


class TestEndToEnd(unittest.TestCase):
    def test_incremental_empty_impact_is_consistent_and_advances_anchor(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["mode"], "incremental")
        self.assertEqual(manifest["changedSet"], [])
        self.assertEqual(manifest["impacted"], [])
        self.assertFalse(manifest["phase4Required"])
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(fx.anchor, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["sha"], fx.head)

    def test_consistent_run_writes_compatible_anchor(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(fx.anchor, encoding="utf-8") as handle:
            anchor = json.load(handle)
        self.assertEqual(anchor["sha"], fx.head)
        self.assertEqual(anchor["head"], fx.head)
        self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))

    def test_failed_doc_yields_needs_fix_without_anchor(self):
        fx = RunFixture(self)
        fx.open(); fx.plan_start_seal()
        fx.complete({"docs/a.md": "FAIL", "docs/b.md": "PASS"})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "NEEDS_FIX")
        self.assertFalse(os.path.exists(fx.anchor))

    def test_empty_corpus_cold_start_is_consistent(self):
        fx = RunFixture(self, docs=())
        fx.open(); fx.plan_start_seal(impacted=[])
        fx.complete(verdicts={})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")


if __name__ == "__main__":
    unittest.main()
