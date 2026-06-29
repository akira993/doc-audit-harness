"""Tests for start-run.py (manifest producer) and the start-run -> decide-verdict
end-to-end honest path."""
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = os.path.join(ROOT, "skills", "audit", "scripts", "start-run.py")
GATE = os.path.join(ROOT, "skills", "audit", "scripts", "decide-verdict.py")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        with open(os.path.join(self.repo, "f"), "w") as fh:
            fh.write("x")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.run_dir = tempfile.mkdtemp()

    def start(self, impact, mode="incremental", runid=None):
        impact_file = os.path.join(self.run_dir, "impact.json")
        with open(impact_file, "w") as fh:
            json.dump(impact, fh)
        cmd = ["python3", START, "--run-dir", self.run_dir, "--repo-root", self.repo,
               "--impact-json", impact_file, "--mode", mode]
        if runid:
            cmd += ["--runid", runid]
        return subprocess.run(cmd, capture_output=True, text=True)

    def manifest(self):
        return json.load(open(os.path.join(self.run_dir, "manifest.json")))


class TestStartRun(Base):
    def test_manifest_basics(self):
        p = self.start({"impacted": [{"path": "a.md", "provenance": "map"},
                                     {"path": "b.md", "provenance": "heuristic"}]})
        self.assertEqual(p.returncode, 0, p.stderr)
        m = self.manifest()
        self.assertEqual(m["head"], self.head)
        self.assertEqual(m["impacted"], ["a.md", "b.md"])
        self.assertTrue(m["phase4Expected"])  # impacted non-empty
        self.assertTrue(m["runid"].startswith("run-"))
        self.assertTrue(os.path.isdir(os.path.join(self.run_dir, "verdicts")))

    def test_plain_string_impacted(self):
        p = self.start({"impacted": ["a.md"]})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.manifest()["impacted"], ["a.md"])

    def test_phase4_false_when_nothing(self):
        self.start({"impacted": [], "ssotRecheck": []})
        self.assertFalse(self.manifest()["phase4Expected"])

    def test_phase4_true_on_ssot(self):
        self.start({"impacted": [], "ssotRecheck": ["SSOT.md"]})
        self.assertTrue(self.manifest()["phase4Expected"])

    def test_phase4_true_on_full(self):
        self.start({"impacted": []}, mode="full")
        m = self.manifest()
        self.assertEqual(m["mode"], "full")
        self.assertTrue(m["phase4Expected"])

    def test_runid_override(self):
        self.start({"impacted": ["a.md"]}, runid="run-fixed-123")
        self.assertEqual(self.manifest()["runid"], "run-fixed-123")

    def test_duplicate_impacted_errors(self):
        p = self.start({"impacted": ["a.md", "a.md"]})
        self.assertNotEqual(p.returncode, 0)

    def test_stdin_impact(self):
        p = subprocess.run(
            ["python3", START, "--run-dir", self.run_dir, "--repo-root", self.repo,
             "--impact-json", "-"],
            input=json.dumps({"impacted": ["a.md"]}), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.manifest()["impacted"], ["a.md"])


class TestEndToEnd(Base):
    """start-run -> subagents write verdicts -> decide-verdict, honest CONSISTENT."""

    def _write_verdict(self, runid, path, verdict):
        d = os.path.join(self.run_dir, "verdicts")
        fn = path.replace("/", "__") + ".json"
        with open(os.path.join(d, fn), "w") as fh:
            json.dump({"runid": runid, "path": path, "verdict": verdict, "rationale": "r"}, fh)

    def _phase4(self, findings):
        with open(os.path.join(self.run_dir, "phase4.json"), "w") as fh:
            json.dump({"findings": findings}, fh)

    def _decide(self):
        return subprocess.run(
            ["python3", GATE, "--run-dir", self.run_dir, "--repo-root", self.repo,
             "--anchor-path", ".claude/state/last-doc-audit.json", "--date", "2026-06-04"],
            capture_output=True, text=True)

    def test_honest_consistent_advances_anchor(self):
        self.start({"impacted": ["a.md", "b.md"]}, runid="run-e2e-1")
        m = self.manifest()
        self._write_verdict(m["runid"], "a.md", "PASS")
        self._write_verdict(m["runid"], "b.md", "WARN")
        self._phase4([])
        p = self._decide()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["verdict"], "CONSISTENT")
        self.assertTrue(out["anchorWritten"])
        anchor = json.load(open(os.path.join(self.repo, ".claude/state/last-doc-audit.json")))
        self.assertEqual(anchor["sha"], self.head)
        self.assertEqual(anchor["runid"], "run-e2e-1")

    def test_real_drift_does_not_advance(self):
        # one doc genuinely drifted (FAIL): the gate must NOT advance the anchor,
        # and there is no way for the orchestrator to override it.
        self.start({"impacted": ["a.md", "b.md"]}, runid="run-e2e-2")
        m = self.manifest()
        self._write_verdict(m["runid"], "a.md", "FAIL")
        self._write_verdict(m["runid"], "b.md", "PASS")
        self._phase4([])
        p = self._decide()
        self.assertEqual(json.loads(p.stdout)["verdict"], "NEEDS_FIX")
        self.assertFalse(os.path.exists(
            os.path.join(self.repo, ".claude/state/last-doc-audit.json")))


if __name__ == "__main__":
    unittest.main()
