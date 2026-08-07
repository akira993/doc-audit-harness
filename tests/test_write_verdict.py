"""Tests for the run-scoped verdict writer."""

import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "write-verdict.py")


class TestWriteVerdict(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_dir = os.path.join(self.tmp.name, "run")
        self.out = os.path.join(self.run_dir, "verdicts", "docs__a.md.json")

    def run_writer(self, rationale="because\n", verdict="PASS", out=None, path="docs/a.md"):
        return subprocess.run(
            [
                sys.executable,
                SCRIPT,
                "--run-dir", self.run_dir,
                "--out", out or self.out,
                "--runid", "run-test-1",
                "--path", path,
                "--verdict", verdict,
            ],
            input=rationale,
            capture_output=True,
            text=True,
        )

    def test_writes_and_echoes_stored_json(self):
        p = self.run_writer("checked on disk\n")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(self.out, encoding="utf-8") as f:
            stored = json.load(f)
        self.assertEqual(json.loads(p.stdout), stored)
        self.assertEqual(
            stored,
            {
                "runid": "run-test-1",
                "path": "docs/a.md",
                "verdict": "PASS",
                "rationale": "checked on disk\n",
            },
        )

    def test_rejects_output_outside_run_verdicts(self):
        outside = os.path.join(self.tmp.name, "outside.json")
        p = self.run_writer(out=outside)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(os.path.exists(outside))

    def test_rejects_verdicts_symlink_that_escapes_run_dir(self):
        outside_dir = os.path.join(self.tmp.name, "outside")
        os.makedirs(self.run_dir)
        os.makedirs(outside_dir)
        os.symlink(outside_dir, os.path.join(self.run_dir, "verdicts"))
        escaped = os.path.join(self.run_dir, "verdicts", "escaped.json")
        p = self.run_writer(out=escaped)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(outside_dir, "escaped.json")))

    def test_rejects_unknown_verdict_without_writing(self):
        p = self.run_writer(verdict="MAYBE")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(os.path.exists(self.out))

    def test_shell_syntax_quotes_and_newlines_are_saved_literally(self):
        pwned = os.path.join(self.tmp.name, "PWNED")
        rationale = f"$(touch {pwned})\nquote: ' and \"\nfinal line\n"
        p = self.run_writer(rationale=rationale)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(self.out, encoding="utf-8") as f:
            stored = json.load(f)
        self.assertEqual(stored["rationale"], rationale)
        self.assertFalse(os.path.exists(pwned))


if __name__ == "__main__":
    unittest.main()
