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
        module = importlib.util.module_from_spec(spec)
        scripts_dir = os.path.dirname(path)
        sys.path.insert(0, scripts_dir)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(scripts_dir)
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
        raw = fx.report_template().encode("utf-8")
        proc = self.binary_call(fx, raw)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), raw)
        self.assertEqual(self.receipt(fx), {
            "bytes": len(raw), "failed": False,
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()})

    def test_existing_file_refusal_invalidates_receipt_and_replace_is_explicit(self):
        fx = RunFixture(self); fx.open()
        first = fx.report_template().encode("utf-8") + b"first\n"
        second = fx.report_template().encode("utf-8") + b"second\n"
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
        prefix = fx.report_template().encode("utf-8")
        exact = prefix + b"x" * (maximum - len(prefix))
        self.assertEqual(self.binary_call(fx, exact).returncode, 0)
        too_large = self.binary_call(fx, b"y" * (maximum + 1), replace=True)
        self.assertEqual(too_large.returncode, 2)
        self.assertEqual(self.receipt(fx), {"failed": True})
        self.assertEqual(os.path.getsize(os.path.join(fx.run_dir, "report-template.md")), maximum)

    def test_symlink_is_not_followed_and_outside_file_is_unchanged(self):
        fx = RunFixture(self); fx.open()
        outside = os.path.join(fx.repo, "outside.txt")
        write(outside, "outside\n")
        os.symlink(outside, os.path.join(fx.run_dir, "report-template.md"))
        proc = self.binary_call(fx, fx.report_template().encode("utf-8"), replace=True)
        self.assertEqual(proc.returncode, 2)
        with open(outside, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "outside\n")
        self.assertEqual(self.receipt(fx), {"failed": True})

    def test_runid_cannot_select_a_directory_outside_the_ledger(self):
        fx = RunFixture(self); fx.open()
        proc = subprocess.run(
            [sys.executable, script("write-template.py"), "--repo-root", fx.repo,
             "--runid", "20260818T120001Z-deadbeef"],
            input=fx.report_template().encode("utf-8"), capture_output=True)
        self.assertEqual(proc.returncode, 2)

    def test_invalidate_first_survives_failure_before_template_create(self):
        fx = RunFixture(self); fx.open()
        old = fx.report_template().encode("utf-8") + b"old"
        new = fx.report_template().encode("utf-8") + b"new"
        self.assertEqual(self.binary_call(fx, old).returncode, 0)
        module = self.module()
        fake_stdin = mock.Mock(buffer=io.BytesIO(new))
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
        old = fx.report_template().encode("utf-8") + b"old"
        new = fx.report_template().encode("utf-8") + b"new"
        self.assertEqual(self.binary_call(fx, old).returncode, 0)
        module = self.module(); real_receipt = module.atomic_receipt; calls = []
        def receipt(run_dir, value):
            calls.append(value)
            if len(calls) == 2:
                raise KeyboardInterrupt("simulated kill")
            return real_receipt(run_dir, value)
        fake_stdin = mock.Mock(buffer=io.BytesIO(new))
        argv = ["write-template.py", "--repo-root", fx.repo, "--runid", fx.runid,
                "--replace"]
        with mock.patch.object(module.sys, "stdin", fake_stdin), \
                mock.patch.object(module.sys, "argv", argv), \
                mock.patch.object(module, "atomic_receipt", side_effect=receipt):
            with self.assertRaises(KeyboardInterrupt):
                module.main()
        self.assertEqual(self.receipt(fx), {"failed": True})
        with open(os.path.join(fx.run_dir, "report-template.md"), "rb") as handle:
            self.assertEqual(handle.read(), new)

    def test_token_validator_rejects_unknown_aggregates_counts_and_bidi(self):
        module = self.module()
        valid = RunFixture(self).report_template()
        for malformed in ("{{GATE_VERDICT-x}}", "{{GATE_reason}}", "{{GATE_VERDICT }}"):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(
                        module.TokenCountError,
                        "report template contains an unknown gate token"):
                    module.validate_template_body(valid + malformed, 0)

        invalid_counts = valid.replace(
            "{{GATE_VERDICT}}", "{{GATE_VERDICT}}{{GATE_VERDICT}}"
        ).replace("warnings: {{GATE_WARNINGS}}\n", "")
        with self.assertRaises(module.TokenCountError) as caught:
            module.validate_template_body(invalid_counts, 0)
        message = str(caught.exception)
        self.assertIn(
            "report template token count is invalid for {{GATE_VERDICT}}; expected 1, found 2",
            message,
        )
        self.assertIn(
            "report template token count is invalid for {{GATE_WARNINGS}}; expected 1, found 0",
            message,
        )
        module.validate_template_body(valid, 0)
        module.validate_template_body(valid, None)
        with self.assertRaises(module.TokenCountError) as claim_required:
            module.validate_template_body(valid, 1)
        self.assertIn(
            "report template token count is invalid for {{GATE_CODEX_CLAIMS}}; "
            "expected 1, found 0",
            str(claim_required.exception),
        )
        module.validate_template_body(valid + "claims: {{GATE_CODEX_CLAIMS}}\n", 1)
        with self.assertRaisesRegex(module.TokenCountError, "bidirectional control character"):
            module.validate_template_body(valid + "\u202e", 0)

    def test_rejects_bad_template_inputs_before_create_and_keeps_failed_receipt(self):
        cases = {
            "duplicate": lambda body: body.replace(
                "{{GATE_VERDICT}}", "{{GATE_VERDICT}}{{GATE_VERDICT}}"),
            "missing": lambda body: body.replace("warnings: {{GATE_WARNINGS}}\n", ""),
            "unknown": lambda body: body + "{{GATE_VERDICT-x}}\n",
            "bidi": lambda body: body + "\u202e\n",
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                fx = RunFixture(self); fx.open()
                proc = self.binary_call(fx, mutate(fx.report_template()).encode("utf-8"))
                self.assertEqual(proc.returncode, 2, proc.stderr.decode())
                self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "report-template.md")))
                self.assertEqual(self.receipt(fx), {"failed": True})

        fx = RunFixture(self); fx.open()
        proc = self.binary_call(fx, b"\xff")
        self.assertEqual(proc.returncode, 2, proc.stderr.decode())
        self.assertIn("not valid UTF-8", proc.stderr.decode())
        self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "report-template.md")))
        self.assertEqual(self.receipt(fx), {"failed": True})

    def test_phase4_symlink_and_invalid_json_are_rejected(self):
        for kind in ("symlink", "invalid-json"):
            with self.subTest(kind=kind):
                fx = RunFixture(self); fx.open()
                phase4 = os.path.join(fx.run_dir, "phase4.json")
                if kind == "symlink":
                    outside = os.path.join(fx.repo, "outside-phase4.json")
                    write(outside, '{"findings": []}\n')
                    os.symlink(outside, phase4)
                else:
                    write(phase4, "{broken")
                proc = self.binary_call(fx, fx.report_template().encode("utf-8"))
                self.assertEqual(proc.returncode, 2, proc.stderr.decode())
                self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "report-template.md")))
                self.assertEqual(self.receipt(fx), {"failed": True})

    def test_phase4_limit_is_inclusive_and_oversize_skips_only_claim_count(self):
        target = (
            b'{"findings":[{"source":"codex-review","severity":"HIGH",'
            b'"file":"docs/a.md","title":"claim"}],"pad":"'
        )
        suffix = b'"}'
        limit = 2 * 1024 * 1024

        exact_fx = RunFixture(self); exact_fx.open()
        exact = target + b"x" * (limit - len(target) - len(suffix)) + suffix
        self.assertEqual(len(exact), limit)
        write(os.path.join(exact_fx.run_dir, "phase4.json"), exact)
        with_claim = exact_fx.report_template() + "claims: {{GATE_CODEX_CLAIMS}}\n"
        accepted = self.binary_call(exact_fx, with_claim.encode("utf-8"))
        self.assertEqual(accepted.returncode, 0, accepted.stderr.decode())

        large_fx = RunFixture(self); large_fx.open()
        oversized = target + b"x" * (limit + 1 - len(target) - len(suffix)) + suffix
        self.assertEqual(len(oversized), limit + 1)
        write(os.path.join(large_fx.run_dir, "phase4.json"), oversized)
        accepted = self.binary_call(large_fx, large_fx.report_template().encode("utf-8"))
        self.assertEqual(accepted.returncode, 0, accepted.stderr.decode())
        self.assertIn(
            "phase4.json exceeds MAX_PHASE4_BYTES; claim token count not checked",
            accepted.stderr.decode(),
        )

        invalid_other_token = large_fx.report_template().replace(
            "warnings: {{GATE_WARNINGS}}\n", "")
        template_path = os.path.join(large_fx.run_dir, "report-template.md")
        with open(template_path, "rb") as handle:
            accepted_bytes = handle.read()
        rejected = self.binary_call(
            large_fx, invalid_other_token.encode("utf-8"), replace=True)
        self.assertEqual(rejected.returncode, 2, rejected.stderr.decode())
        self.assertIn("{{GATE_WARNINGS}}", rejected.stderr.decode())
        self.assertEqual(self.receipt(large_fx), {"failed": True})
        with open(template_path, "rb") as handle:
            self.assertEqual(handle.read(), accepted_bytes)


if __name__ == "__main__":
    unittest.main()
