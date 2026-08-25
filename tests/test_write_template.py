"""Tests for the self-bound report template writer and receipt lifecycle."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture, script, write


class TestWriteTemplate(unittest.TestCase):
    def module(self):
        path = script("write-template.py")
        spec = importlib.util.spec_from_file_location("write_template_test", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def binary_call(self, fx, raw, replace=False):
        args = [sys.executable, script("write-template.py"),
                "--repo-root", fx.repo, "--runid", fx.runid]
        if replace:
            args.append("--replace")
        return subprocess.run(args, input=raw, capture_output=True)

    def receipt(self, fx):
        path = os.path.join(fx.run_dir, "report-template.receipt.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_create_is_self_bound_and_writes_success_receipt(self):
        fx = RunFixture(self); fx.open()
        raw = b"template\n"
        proc = self.binary_call(fx, raw)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), raw)
        self.assertEqual(self.receipt(fx), {
            "bytes": len(raw), "failed": False,
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()})

    def test_existing_file_refusal_invalidates_receipt_and_replace_is_explicit(self):
        fx = RunFixture(self); fx.open()
        first = b"first\n"; second = b"second\n"
        self.assertEqual(self.binary_call(fx, first).returncode, 0)
        refused = self.binary_call(fx, second)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(self.receipt(fx), {"failed": True})
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), first)
        replaced = self.binary_call(fx, second, replace=True)
        self.assertEqual(replaced.returncode, 0, replaced.stderr.decode())
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), second)

    def test_size_limit_is_binary_inclusive_and_failure_keeps_receipt_invalid(self):
        fx = RunFixture(self); fx.open()
        maximum = 2 * 1024 * 1024
        self.assertEqual(self.binary_call(fx, b"x" * maximum).returncode, 0)
        too_large = self.binary_call(fx, b"y" * (maximum + 1), replace=True)
        self.assertEqual(too_large.returncode, 2)
        self.assertEqual(self.receipt(fx), {"failed": True})
        self.assertEqual(os.path.getsize(os.path.join(fx.run_dir, "report-template.md")), maximum)

    def test_symlink_is_not_followed_and_outside_file_is_unchanged(self):
        fx = RunFixture(self); fx.open()
        outside = os.path.join(fx.repo, "outside.txt")
        write(outside, "outside\n")
        os.symlink(outside, os.path.join(fx.run_dir, "report-template.md"))
        proc = self.binary_call(fx, b"replacement\n", replace=True)
        self.assertEqual(proc.returncode, 2)
        with open(outside, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "outside\n")
        self.assertEqual(self.receipt(fx), {"failed": True})

    def test_runid_cannot_select_a_directory_outside_the_ledger(self):
        fx = RunFixture(self); fx.open()
        proc = subprocess.run(
            [sys.executable, script("write-template.py"), "--repo-root", fx.repo,
             "--runid", "20260818T120001Z-deadbeef"],
            input=b"x", capture_output=True)
        self.assertEqual(proc.returncode, 2)

    def test_invalidate_first_survives_failure_before_template_create(self):
        fx = RunFixture(self); fx.open()
        self.assertEqual(self.binary_call(fx, b"old").returncode, 0)
        module = self.module()
        fake_stdin = mock.Mock(buffer=io.BytesIO(b"new"))
        argv = ["write-template.py", "--repo-root", fx.repo, "--runid", fx.runid,
                "--replace"]
        with mock.patch.object(module.sys, "stdin", fake_stdin), \
                mock.patch.object(module.sys, "argv", argv), \
                mock.patch.object(module, "replace_template", side_effect=OSError("crash point")), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(module.main(), 2)
        self.assertEqual(self.receipt(fx), {"failed": True})

    def test_invalidate_first_survives_crash_before_success_receipt(self):
        fx = RunFixture(self); fx.open()
        self.assertEqual(self.binary_call(fx, b"old").returncode, 0)
        module = self.module(); real_receipt = module.atomic_receipt; calls = []
        def receipt(run_dir, value):
            calls.append(value)
            if len(calls) == 2:
                raise KeyboardInterrupt("simulated kill")
            return real_receipt(run_dir, value)
        fake_stdin = mock.Mock(buffer=io.BytesIO(b"new"))
        argv = ["write-template.py", "--repo-root", fx.repo, "--runid", fx.runid,
                "--replace"]
        with mock.patch.object(module.sys, "stdin", fake_stdin), \
                mock.patch.object(module.sys, "argv", argv), \
                mock.patch.object(module, "atomic_receipt", side_effect=receipt):
            with self.assertRaises(KeyboardInterrupt):
                module.main()
        self.assertEqual(self.receipt(fx), {"failed": True})
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), b"new")


if __name__ == "__main__":
    unittest.main()
