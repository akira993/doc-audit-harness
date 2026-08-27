"""Tests for digest-bound single-read manifest loading."""

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "read-manifest.py")


def load_module():
    spec = importlib.util.spec_from_file_location("read_manifest_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class TestReadManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = b'{"runid":"r1","sealed":true}\n'
        with open(os.path.join(self.tmp.name, "manifest.json"), "wb") as handle:
            handle.write(self.raw)
        self.evidence = {"manifest": digest(self.raw)}

    def run_reader(self, evidence=None):
        return subprocess.run(
            [sys.executable, SCRIPT, "--run-dir", self.tmp.name, "--evidence",
             json.dumps(self.evidence if evidence is None else evidence)],
            capture_output=True, text=True)

    def test_matching_digest_outputs_parsed_json(self):
        proc = self.run_reader()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {"runid": "r1", "sealed": True})

    def test_digest_mismatch_after_manifest_change_has_empty_stdout(self):
        with open(os.path.join(self.tmp.name, "manifest.json"), "ab") as handle:
            handle.write(b" ")
        proc = self.run_reader()
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertIn("manifest sha", proc.stderr)

    def test_missing_manifest_has_empty_stdout(self):
        missing = tempfile.TemporaryDirectory()
        self.addCleanup(missing.cleanup)
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--run-dir", missing.name, "--evidence",
             json.dumps(self.evidence)], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertTrue(proc.stderr)

    def test_invalid_evidence_is_rejected(self):
        for evidence in ([], {}, {"manifest": None}, {"manifest": "sha256:not-a-sha"}):
            with self.subTest(evidence=evidence):
                proc = self.run_reader(evidence)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, "")
                self.assertIn("EVIDENCE", proc.stderr)

        proc = subprocess.run(
            [sys.executable, SCRIPT, "--run-dir", self.tmp.name, "--evidence", "{"],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertTrue(proc.stderr)

    def test_checked_bytes_are_parsed_without_a_second_open(self):
        module = load_module()
        replacement = b'{"runid":"replacement","sealed":true}\n'
        calls = []

        def opener(_path, mode):
            self.assertEqual(mode, "rb")
            calls.append(mode)
            return io.BytesIO(self.raw if len(calls) == 1 else replacement)

        value = module.read_manifest(self.tmp.name, self.evidence, opener=opener)
        self.assertEqual(value["runid"], "r1")
        self.assertEqual(calls, ["rb"])

    def test_sealed_manifest_change_is_rejected(self):
        from tests.wp12_helpers import RunFixture

        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), "ab") as handle:
            handle.write(b" ")
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--run-dir", fx.run_dir, "--evidence",
             json.dumps(fx.evidence)], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertIn("manifest sha", proc.stderr)


if __name__ == "__main__":
    unittest.main()
