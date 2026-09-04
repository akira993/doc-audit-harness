"""Adversarial tests for the sealed v0.10 verdict gate."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture, git, plugin_version, write


DECIDE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills", "audit", "scripts", "decide-verdict.py")
SCRIPT_DIR = os.path.dirname(DECIDE)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import claim_record


class GateBase(unittest.TestCase):
    def prepared(self, verdicts=None, returns=None, phase4=None):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(verdicts, returns, phase4).returncode, 0)
        return fx

    def assert_refused(self, fx):
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "REFUSED")
        self.assertFalse(os.path.exists(fx.anchor))
        return proc


class TestHappy(GateBase):
    def test_all_pass_writes_anchor(self):
        fx = self.prepared()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")

    def test_config_replaced_after_read_is_tainted_from_fd_signature(self):
        fx = self.prepared()
        with tempfile.TemporaryDirectory() as hook_dir:
            hook = textwrap.dedent(r'''
                import os
                _os_open = os.open
                _os_read = os.read
                _target = os.path.realpath(os.environ["DOCAUDIT_SWAP_PATH"])
                _replacement = os.environ["DOCAUDIT_SWAP_REPLACEMENT"]
                _target_fd = None
                _swapped = False
                def tracked_open(path, *args, **kwargs):
                    global _target_fd
                    fd = _os_open(path, *args, **kwargs)
                    try: same = os.path.realpath(os.fspath(path)) == _target
                    except Exception: same = False
                    if same: _target_fd = fd
                    return fd
                def tracked_read(fd, *args, **kwargs):
                    global _swapped
                    data = _os_read(fd, *args, **kwargs)
                    if fd == _target_fd and not data and not _swapped:
                        _swapped = True
                        os.replace(_replacement, _target)
                    return data
                os.open = tracked_open
                os.read = tracked_read
            ''')
            write(os.path.join(hook_dir, "sitecustomize.py"), hook)
            replacement = fx.config_path + ".replacement"
            with open(fx.config_path, "rb") as source:
                write(replacement, source.read().decode("utf-8"))
            env = dict(os.environ, PYTHONPATH=hook_dir,
                       DOCAUDIT_SWAP_PATH=fx.config_path,
                       DOCAUDIT_SWAP_REPLACEMENT=replacement)
            proc = subprocess.run(
                [sys.executable, DECIDE,
                 "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                 "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                 "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                 "--date", "2026-08-18"],
                capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertEqual(result["reason"], "config-changed")
        with open(fx.last_run, encoding="utf-8") as handle:
            last_run = json.load(handle)
        self.assertTrue(last_run["configAcceptanceRequired"])
        self.assertEqual(last_run["expectedConfigSha"], fx.evidence["config"])

    def test_warn_never_blocks(self):
        fx = self.prepared({"docs/a.md": "WARN", "docs/b.md": "PASS"})
        self.assertEqual(json.loads(fx.gate().stdout)["verdict"], "CONSISTENT")

    def test_consistent_has_sibling_scan_object(self):
        result = json.loads(self.prepared().gate().stdout)
        self.assertIsInstance(result["siblingScan"], dict)

    def test_preflight_command_nonzero_blocks_when_unparsed(self):
        fx = RunFixture(self, config_extra={"harness": {"state": "adjusted"},
                        "docAuditCommands": {"format": "make docs"}})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        preflight = {"state": "passed", "findings": [], "userDecision": None,
                     "parsed": False, "commands": [{"layer": "format",
                     "command": "make docs", "kind": "script-backed", "ran": True,
                     "exitCode": 1, "parsed": False, "skippedReason": None}]}
        self.assertEqual(fx.write_evidence("preflight", preflight).returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "NEEDS_FIX")
        self.assertFalse(result["anchorWritten"])
        spec = importlib.util.spec_from_file_location("decide_under_test", DECIDE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertTrue(module.findings_fail({"parsed": False, "findings": [], "commands": [{"exitCode": 1}]}))


class TestGateWritesReport(GateBase):
    REPORT_CONFIG = {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}

    def prepared_report(self, *, phase4=None, template=None):
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(phase4=phase4).returncode, 0)
        self.assertEqual(fx.write_template(
            body=template if template is not None else fx.report_template()).returncode, 0)
        return fx

    def module(self):
        spec = importlib.util.spec_from_file_location("decide_report_test", DECIDE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def run_main(self, module, fx, *patches):
        argv = ["decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence)]
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            stack.enter_context(contextlib.redirect_stdout(output))
            code = module.main()
        return code, json.loads(output.getvalue())

    @staticmethod
    def replace_template_artifacts(fx, raw):
        raw = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        write(os.path.join(fx.run_dir, "report-template.md"), raw)
        write(os.path.join(fx.run_dir, "report-template.receipt.json"), json.dumps({
            "failed": False,
            "bytes": len(raw),
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }) + "\n")

    def paused_gate(self, fx, phase="publish"):
        ready_read, ready_write = os.pipe()
        resume_read, resume_write = os.pipe()
        child = r'''
import importlib.util
import os
import sys

ready = int(sys.argv[1])
resume = int(sys.argv[2])
phase = sys.argv[3]
script_path = sys.argv[4]
gate_args = sys.argv[5:]
sys.path.insert(0, os.path.dirname(script_path))
spec = importlib.util.spec_from_file_location("paused_gate", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
def pause():
    os.write(ready, b"READY\n")
    os.read(resume, 1)
if phase == "publish":
    real_publish = module.publish_report
    def paused_publish(*args, **kwargs):
        pause()
        return real_publish(*args, **kwargs)
    module.publish_report = paused_publish
else:
    def paused_scan(*args, **kwargs):
        pause()
        return module.sibling_skipped("controlled scan")
    module.run_sibling_step = paused_scan
sys.argv = ["decide-verdict.py"] + gate_args
raise SystemExit(module.main())
'''
        args = [sys.executable, "-c", child, str(ready_write), str(resume_read), phase, DECIDE,
                "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence)]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, pass_fds=(ready_write, resume_read))
        os.close(ready_write); os.close(resume_read)
        self.assertEqual(os.read(ready_read, 6), b"READY\n")
        os.close(ready_read)
        return proc, resume_write

    def last_state(self, fx):
        with open(fx.last_run, encoding="utf-8") as handle:
            return json.load(handle)

    def test_normal_report_is_written_inside_gate_and_next_run_is_consistent(self):
        fx = self.prepared_report()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["reportPath"], "docs/logs/doc_audit_2026-08-18.md")
        report = os.path.join(fx.repo, result["reportPath"])
        self.assertEqual(os.stat(report).st_mode & 0o777, 0o644)
        with open(report, encoding="utf-8") as handle:
            body = handle.read()
        self.assertEqual(body.count("2026-08-18"), 2)
        self.assertNotIn("{{GATE_", body)
        self.assertIn('reason: "n/a"', body)
        self.assertEqual(result["reportStatus"], "written")
        self.assertEqual(result["reportStatus"], self.last_state(fx)["reportStatus"])

        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        self.assertEqual(fx.write_template().returncode, 0)
        second = fx.gate()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)["verdict"], "CONSISTENT")

    def test_suffix_link_is_atomic_and_existing_report_is_not_overwritten(self):
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        existing = os.path.join(fx.repo, "docs/logs/doc_audit_2026-08-18.md")
        write(existing, "existing\n")
        fx.open(); fx.plan_start_seal(); fx.complete(); fx.write_template()
        result = json.loads(fx.gate().stdout)
        self.assertEqual(result["reportPath"], "docs/logs/doc_audit_2026-08-18_02.md")
        with open(existing, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "existing\n")

    def test_suffix_marker_in_directory_uses_the_sealed_candidate_parent(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs[_NN]/audit_<YYYY-MM-DD>.md"})
        existing = os.path.join(fx.repo, "docs/logs/audit_2026-08-18.md")
        write(existing, "existing\n")
        fx.open(); fx.plan_start_seal(); fx.complete(); fx.write_template()
        result = json.loads(fx.gate().stdout)
        self.assertEqual(result["reportPath"], "docs/logs_02/audit_2026-08-18.md")
        with open(existing, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "existing\n")

    def test_link_and_directory_fsync_use_the_same_open_parent(self):
        fx = self.prepared_report()
        module = self.module()
        real_link = module.os.link
        real_fsync_directory_fd = module.fsync_directory_fd
        linked_parent_fds = []
        fsynced_parent_fds = []

        def link(source, destination, **kwargs):
            self.assertEqual(destination, "doc_audit_2026-08-18.md")
            self.assertNotIn(os.sep, destination)
            linked_parent_fds.append(kwargs.get("dst_dir_fd"))
            return real_link(source, destination, **kwargs)

        def fsync_directory_fd(fd):
            fsynced_parent_fds.append(fd)
            return real_fsync_directory_fd(fd)

        code, result = self.run_main(
            module, fx, mock.patch.object(module.os, "link", side_effect=link),
            mock.patch.object(module, "fsync_directory_fd", side_effect=fsync_directory_fd))
        self.assertEqual(code, 0)
        self.assertIn("reportPath", result)
        self.assertEqual(len(linked_parent_fds), 1)
        self.assertIsInstance(linked_parent_fds[0], int)
        self.assertEqual(fsynced_parent_fds, linked_parent_fds)

    def test_reportless_and_missing_template_statuses_are_distinct(self):
        plain = self.prepared()
        plain_result = json.loads(plain.gate().stdout)
        self.assertNotIn("reportPath", plain_result)
        self.assertEqual(plain_result["reportStatus"], "not-requested")
        self.assertEqual(plain_result["reportStatus"], self.last_state(plain)["reportStatus"])

        missing = RunFixture(self, config_extra=self.REPORT_CONFIG)
        missing.open(); missing.plan_start_seal(); missing.complete()
        missing_proc = missing.gate()
        self.assertEqual(missing_proc.returncode, 3, missing_proc.stdout + missing_proc.stderr)
        result = json.loads(missing_proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertIn("reportTemplateMissing", result["warnings"])
        self.assertNotIn("reportPath", result)
        self.assertEqual(result["reportStatus"], "failed")
        self.assertEqual(result["reportStatus"], self.last_state(missing)["reportStatus"])

    def test_failed_helper_receipt_and_bad_token_contract_are_reportless(self):
        fx = self.prepared_report()
        duplicate = fx.write_template(body="new", replace=False)
        self.assertEqual(duplicate.returncode, 2)
        failed_proc = fx.gate()
        self.assertEqual(failed_proc.returncode, 3, failed_proc.stdout + failed_proc.stderr)
        result = json.loads(failed_proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertIn("reportTemplateInvalid", result["warnings"])
        self.assertEqual(result["reportStatus"], "failed")
        self.assertNotIn("reportPath", result)
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.anchor))

        bad = self.prepared_report()
        self.replace_template_artifacts(bad, self.prepared_report_template_with_duplicate_date())
        bad_proc = bad.gate()
        self.assertEqual(bad_proc.returncode, 3, bad_proc.stdout + bad_proc.stderr)
        out = json.loads(bad_proc.stdout)
        self.assertIn("reportTemplateInvalid", out["warnings"])
        self.assertNotIn("reportPath", out)

    @staticmethod
    def prepared_report_template_with_duplicate_date():
        return """created: {{GATE_REPORT_DATE}}
updated: {{GATE_REPORT_DATE}}
extra: {{GATE_REPORT_DATE}}
verdict: {{GATE_VERDICT}}
warnings: {{GATE_WARNINGS}}
anchor: {{GATE_ANCHOR_WRITTEN}}
counts: {{GATE_COUNTS}}
history: {{GATE_HISTORY_STATUS}}
sibling: {{GATE_SIBLING_SCAN}}
"""

    def test_invalid_utf8_template_is_rejected_by_gate(self):
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        fx.open(); fx.plan_start_seal(); fx.complete()
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "write-template.py"),
             "--repo-root", fx.repo, "--runid", fx.runid],
            input=b"\xff", capture_output=True)
        self.assertEqual(proc.returncode, 2, proc.stderr.decode())
        raw = b"\xff"
        write(os.path.join(fx.run_dir, "report-template.md"), raw)
        write(os.path.join(fx.run_dir, "report-template.receipt.json"), json.dumps({
            "failed": False,
            "bytes": len(raw),
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }) + "\n")
        gate = fx.gate()
        self.assertEqual(gate.returncode, 3, gate.stdout + gate.stderr)
        result = json.loads(gate.stdout)
        self.assertIn("reportTemplateInvalid", result["warnings"])

    def test_gate_bounded_read_rejects_template_at_two_mib_plus_one(self):
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        fx.open(); fx.plan_start_seal(); fx.complete()
        raw = b"x" * (2 * 1024 * 1024 + 1)
        write(os.path.join(fx.run_dir, "report-template.md"), raw)
        receipt = {"failed": False, "bytes": len(raw),
                   "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()}
        write(os.path.join(fx.run_dir, "report-template.receipt.json"),
              json.dumps(receipt) + "\n")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIn("reportTemplateInvalid", result["warnings"])
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.anchor))

    def test_owned_refused_commits_reason_before_report_and_releases_lock(self):
        fx = self.prepared_report(phase4=[{"title": "missing severity"}])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIn("reportPath", result)
        with open(fx.last_run, encoding="utf-8") as handle:
            state = json.load(handle)
        self.assertEqual(state["verdict"], "REFUSED")
        self.assertEqual(state["reportStatus"], "written")
        self.assertEqual(result["reportStatus"], state["reportStatus"])
        self.assertIn("severity", state["reason"])
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn('counts: "n/a"', body)
        self.assertIn('historyStatus: "n/a"', body)
        self.assertIn('siblingScan: "n/a"', body)
        self.assertIn("severity", body)
        self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))

    def test_optional_reason_token_may_be_absent(self):
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        fx.open(); fx.plan_start_seal(); fx.complete()
        template = fx.report_template().replace("reason: {{GATE_REASON}}\n", "")
        self.assertEqual(fx.write_template(body=template).returncode, 0)
        result = json.loads(fx.gate().stdout)
        self.assertEqual(result["verdict"], "CONSISTENT")
        self.assertIn("reportPath", result)

    def test_post_commit_failures_do_not_reverse_verdict(self):
        cases = (
            ("dir-fsync", "reportDurabilityUnknown"),
            ("status", "reportStatusUpdateFailed"),
            ("release", "lockReleaseFailed"),
            ("link", "reportWriteError"),
        )
        for failure, warning in cases:
            with self.subTest(failure=failure):
                fx = self.prepared_report()
                module = self.module()
                if failure == "dir-fsync":
                    patcher = mock.patch.object(module, "fsync_directory_fd", side_effect=OSError("fsync"))
                elif failure == "status":
                    patcher = mock.patch.object(module, "report_status_update", side_effect=OSError("status"))
                elif failure == "release":
                    patcher = mock.patch.object(module, "release_lock", side_effect=OSError("unlink"))
                else:
                    patcher = mock.patch.object(module.os, "link", side_effect=OSError(18, "EXDEV"))
                code, result = self.run_main(module, fx, patcher)
                self.assertEqual(code, 0)
                self.assertEqual(result["verdict"], "CONSISTENT")
                self.assertIn(warning, result["warnings"])
                self.assertEqual(result["reportStatus"],
                                 self.last_state(fx)["reportStatus"])
                if failure == "dir-fsync":
                    self.assertIn("reportPath", result)
                    self.assertEqual(self.last_state(fx)["reportStatus"],
                                     "written-durability-unknown")
                if failure == "status":
                    self.assertEqual(self.last_state(fx)["reportStatus"], "pending")
                    opened = fx.open(runid="20260818T120001Z-abcdef13")
                    self.assertEqual(json.loads(opened.stdout)["previousReportStatus"], "pending")
                if failure == "release":
                    recovered = fx.call("open-run.py", "--run-base", fx.run_base,
                                        "--repo-root", fx.repo, "--release", "--runid", fx.runid)
                    self.assertEqual(recovered.returncode, 0,
                                     recovered.stdout + recovered.stderr)

    def test_sibling_scan_interval_holds_flock_until_scan_completes(self):
        fx = self.prepared_report()
        proc, resume = self.paused_gate(fx, phase="scan")
        try:
            blocked = fx.open(runid="20260818T120001Z-abcdef13")
            self.assertEqual(blocked.returncode, 4)
            broken = fx.call("open-run.py", "--run-base", fx.run_base,
                             "--repo-root", fx.repo, "--break-lock")
            self.assertEqual(broken.returncode, 4)
            self.assertEqual(json.loads(broken.stdout)["reason"], "gate-running")
            os.write(resume, b"x")
            os.close(resume); resume = None
            stdout, stderr = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, stdout + stderr)
            self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))
        finally:
            if resume is not None:
                os.close(resume)
            if proc.poll() is None:
                proc.kill(); proc.wait()

    def test_gate_report_interval_holds_flock_and_previous_status_is_reread_afterward(self):
        fx = self.prepared_report()
        proc, resume = self.paused_gate(fx)
        try:
            self.assertEqual(self.last_state(fx)["reportStatus"], "pending")
            blocked = fx.open(runid="20260818T120001Z-abcdef13")
            self.assertEqual(blocked.returncode, 4)
            broken = fx.call("open-run.py", "--run-base", fx.run_base,
                             "--repo-root", fx.repo, "--break-lock")
            self.assertEqual(broken.returncode, 4)
            self.assertEqual(json.loads(broken.stdout)["reason"], "gate-running")
            os.write(resume, b"x")
            os.close(resume); resume = None
            stdout, stderr = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, stdout + stderr)
            self.assertEqual(self.last_state(fx)["reportStatus"], "written")
            opened = fx.open(runid="20260818T120001Z-abcdef13")
            self.assertEqual(opened.returncode, 0, opened.stderr)
            self.assertNotIn("previousReportStatus", json.loads(opened.stdout))
        finally:
            if resume is not None:
                os.close(resume)
            if proc.poll() is None:
                proc.kill(); proc.wait()

    def test_kill_during_report_leaves_stale_lock_for_break_lock_recovery(self):
        fx = self.prepared_report()
        proc, resume = self.paused_gate(fx)
        os.close(resume)
        proc.kill()
        proc.communicate(timeout=10)
        self.assertTrue(os.path.exists(os.path.join(fx.run_base, "lock")))
        recovered = fx.call("open-run.py", "--run-base", fx.run_base,
                            "--repo-root", fx.repo, "--break-lock")
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertEqual(self.last_state(fx)["reportStatus"], "pending")

    def test_temp_cleanup_and_parent_creation_failures_are_warnings(self):
        for failure in ("temp-unlink", "mkdir"):
            with self.subTest(failure=failure):
                fx = self.prepared_report()
                module = self.module()
                if failure == "temp-unlink":
                    real_unlink = module.os.unlink
                    def unlink(path):
                        if os.path.basename(path).startswith(".report-publication."):
                            raise OSError("temp cleanup")
                        return real_unlink(path)
                    patcher = mock.patch.object(module.os, "unlink", side_effect=unlink)
                else:
                    real_makedirs = module.os.makedirs
                    def makedirs(path, *args, **kwargs):
                        if path.endswith(os.path.join("docs", "logs")):
                            raise OSError("parent denied")
                        return real_makedirs(path, *args, **kwargs)
                    patcher = mock.patch.object(module.os, "makedirs", side_effect=makedirs)
                code, result = self.run_main(module, fx, patcher)
                self.assertEqual(code, 0)
                self.assertEqual(result["verdict"], "CONSISTENT")
                self.assertIn("reportWriteError", result["warnings"])

    def test_rendered_output_limit_and_unknown_token_are_invalid(self):
        fx = self.prepared_report()
        module = self.module()
        huge_scan = {"payload": "x" * (4 * 1024 * 1024)}
        code, result = self.run_main(
            module, fx, mock.patch.object(module, "run_sibling_step", return_value=huge_scan))
        self.assertEqual(code, 3)
        self.assertTrue(result["reason"].startswith("reportTemplateInvalid"))
        self.assertIn("reportTemplateInvalid", result["warnings"])
        self.assertEqual(result["reportStatus"], "written")
        self.assertIn("reportPath", result)
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.anchor))

        unknown = self.prepared_report()
        unknown_template = (unknown.report_template()
                            + "unknown: {{GATE_UNKNOWN}}\n")
        self.replace_template_artifacts(unknown, unknown_template)
        unknown_proc = unknown.gate()
        self.assertEqual(unknown_proc.returncode, 3,
                         unknown_proc.stdout + unknown_proc.stderr)
        out = json.loads(unknown_proc.stdout)
        self.assertIn("reportTemplateInvalid", out["warnings"])

    def test_scan_then_barrier_then_state_then_link_order(self):
        fx = self.prepared_report()
        module = self.module(); events = []
        real_scan = module.run_sibling_step
        real_lock = module.lock_recheck
        real_render = module.render_report
        real_atomic = module.atomic
        real_publish = module.publish_report
        def scan(*args, **kwargs):
            events.append("scan"); return real_scan(*args, **kwargs)
        def barrier(*args, **kwargs):
            events.append("barrier"); return real_lock(*args, **kwargs)
        def render(*args, **kwargs):
            result = real_render(*args, **kwargs); events.append("render"); return result
        def state(*args, **kwargs):
            events.append("state"); return real_atomic(*args, **kwargs)
        def link(*args, **kwargs):
            events.append("link"); return real_publish(*args, **kwargs)
        code, _ = self.run_main(
            module, fx, mock.patch.object(module, "run_sibling_step", side_effect=scan),
            mock.patch.object(module, "lock_recheck", side_effect=barrier),
            mock.patch.object(module, "render_report", side_effect=render),
            mock.patch.object(module, "atomic", side_effect=state),
            mock.patch.object(module, "publish_report", side_effect=link))
        self.assertEqual(code, 0)
        self.assertLess(events.index("scan"), events.index("barrier"))
        self.assertLess(events.index("barrier"), events.index("render"))
        self.assertLess(events.index("render"), events.index("state"))
        self.assertLess(events.index("state"), events.index("link"))

    def test_render_snapshot_precedes_all_state_and_publishes_captured_bytes(self):
        claim = {"source": "codex-review", "severity": "HIGH",
                 "title": "Claim A", "file": "docs/a.md"}
        phase4 = {"findings": [claim], "codexReview": {
            "state": "completed", "promptVariant": "diff", "carryForwardSha": "none"}}
        fx = RunFixture(self, config_extra=self.REPORT_CONFIG)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(phase4=phase4).returncode, 0)
        target = claim_record.extract_claim_targets(phase4)[0][0]
        record = {"runid": fx.runid, "findingId": target["findingId"],
                  "state": "refuted", "rationale": "checked",
                  "evidenceFile": "docs/a.md", "evidenceLine": 1}
        write(os.path.join(fx.run_dir, "claims", target["findingId"] + ".json"),
              claim_record.encode_claim_record(record))
        self.assertEqual(fx.write_template(
            body=fx.report_template() + "codexClaims: {{GATE_CODEX_CLAIMS}}\n").returncode, 0)
        module = self.module()
        real_render = module.render_report
        replacement = "SWAPPED AFTER RENDER\n" + fx.report_template()

        def render_then_swap(*args, **kwargs):
            rendered = real_render(*args, **kwargs)
            self.assertFalse(os.path.exists(fx.history))
            self.assertFalse(os.path.exists(fx.last_run))
            self.assertFalse(os.path.exists(fx.anchor))
            self.replace_template_artifacts(fx, replacement)
            return rendered

        code, result = self.run_main(
            module, fx, mock.patch.object(module, "render_report", side_effect=render_then_swap))
        self.assertEqual(code, 0)
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            report = handle.read()
        self.assertNotIn("SWAPPED AFTER RENDER", report)
        self.assertIn("verdict: CONSISTENT", report)

    def test_each_barrier_target_changed_during_scan_is_refused(self):
        for target in ("digest", "history", "anchor", "config", "lock"):
            with self.subTest(target=target):
                fx = self.prepared_report()
                module = self.module()
                def mutate(*args, **kwargs):
                    if target == "digest":
                        write(os.path.join(fx.repo, "src/app.py"), "changed\n")
                    elif target == "history":
                        write(fx.history, '{"entries":[]}\n')
                    elif target == "anchor":
                        write(fx.anchor, '{"sha":"changed"}\n')
                    elif target == "config":
                        write(fx.config_path, json.dumps(dict(fx.config, changed=True)) + "\n")
                    else:
                        write(os.path.join(fx.run_base, "lock"),
                              json.dumps({"runid": "changed"}) + "\n")
                    return module.sibling_skipped("injected")
                code, result = self.run_main(
                    module, fx, mock.patch.object(module, "run_sibling_step", side_effect=mutate))
                self.assertEqual(code, 3)
                self.assertEqual(result["verdict"], "REFUSED")

    def test_token_contract_and_escaping_are_fixed(self):
        module = self.module()
        self.assertEqual(module.REPORT_WARNING_CODES, {
            "reportWriteError", "reportTemplateMissing", "reportTemplateInvalid",
            "reportDurabilityUnknown", "reportStatusUpdateFailed", "lockReleaseFailed"})
        self.assertEqual(module.TOKEN_COUNTS["{{GATE_REPORT_DATE}}"], 2)
        self.assertTrue(all(count == 1 for token, count in module.TOKEN_COUNTS.items()
                            if token != "{{GATE_REPORT_DATE}}"))
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "skills", "audit", "SKILL.md"), encoding="utf-8") as handle:
            skill = handle.read()
        rows = dict(re.findall(
            r"^\| `(\{\{GATE_[A-Z0-9_]+\}\})` \| ([^|]+?) \|", skill, re.M))
        self.assertEqual(set(rows), set(module.TOKEN_COUNTS))
        for token, expected in module.TOKEN_COUNTS.items():
            if token in module.OPTIONAL_TOKENS:
                self.assertEqual(rows[token], "0 or 1")
            elif token == "{{GATE_CODEX_CLAIMS}}":
                self.assertEqual(rows[token],
                                 "1 when adjudication targets exist; otherwise 0 or 1")
            else:
                self.assertEqual(int(rows[token]), expected)
        escaped = module.safe_json("<x>&\u2028")
        self.assertEqual(escaped, '"\\u003cx\\u003e\\u0026\\u2028"')
        with self.assertRaises(module.TemplateInvalid):
            module.safe_json("bad\u202evalue")

    def test_report_suffix_start_requires_exact_integer_two(self):
        module = self.module()
        fx = RunFixture(self)
        base_rule = {
            "base": "docs/logs/doc_audit_2026-08-18.md",
            "suffixPrefix": "docs/logs/doc_audit_2026-08-18",
            "suffixSuffix": ".md",
            "suffixStart": 2,
        }
        for invalid in (True, 2.0):
            with self.subTest(value=invalid):
                manifest = {"reportDate": "2026-08-18",
                            "reportCandidateRule": dict(base_rule, suffixStart=invalid)}
                with self.assertRaises(module.Refused):
                    module.validate_report_rule(manifest, fx.repo, fx.runid)


class TestSiblingFailures(GateBase):
    def module(self):
        spec = importlib.util.spec_from_file_location("decide_under_test", DECIDE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def main_args(self, fx):
        return ["decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                "--date", "2026-08-18"]

    def run_main(self, module, fx, wrapped_run):
        output = io.StringIO()
        with mock.patch.object(module.subprocess, "run", side_effect=wrapped_run), \
                mock.patch.object(sys, "argv", self.main_args(fx)), \
                contextlib.redirect_stdout(output):
            return module.main(), json.loads(output.getvalue())

    @staticmethod
    def is_sibling_call(args):
        command = args[0] if args else []
        return isinstance(command, (list, tuple)) and any(
            os.path.basename(str(part)) == "sibling-scan.py" for part in command)

    def test_timeout_is_stable_and_uses_30_seconds(self):
        module = self.module()
        original = module.subprocess.run
        def timeout(*args, **kwargs):
            self.assertEqual(kwargs["timeout"], 30)
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
        module.subprocess.run = timeout
        try:
            out = module.run_sibling_scan({}, ".")
        finally:
            module.subprocess.run = original
        self.assertIn("skipped", out); self.assertEqual(out["phrases"], [])

    def test_nonzero_and_invalid_json_are_stable(self):
        module = self.module(); original = module.subprocess.run
        try:
            module.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a[0], 2, "", "bad")
            self.assertIn("skipped", module.run_sibling_scan({}, "."))
            module.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "not json", "")
            self.assertIn("skipped", module.run_sibling_scan({}, "."))
        finally:
            module.subprocess.run = original

    def test_report_pattern_failure_is_isolated(self):
        fx = self.prepared()
        module = self.module()
        real_run = module.subprocess.run
        sibling_calls = []
        def wrapped(*args, **kwargs):
            if self.is_sibling_call(args):
                sibling_calls.append(args[0])
            return real_run(*args, **kwargs)
        with mock.patch.object(module, "report_pattern", side_effect=RuntimeError("boom")):
            returncode, out = self.run_main(module, fx, wrapped)
        self.assertEqual(returncode, 0)
        self.assertEqual(out["verdict"], "CONSISTENT")
        self.assertTrue(out["anchorWritten"])
        self.assertIn("boom", out["siblingScan"]["skipped"])
        self.assertEqual(sibling_calls, [])

    def test_main_isolates_sibling_subprocess_failures(self):
        for failure in ("timeout", "nonzero", "invalid-json"):
            with self.subTest(failure=failure):
                fx = self.prepared()
                module = self.module()
                real_run = module.subprocess.run
                def wrapped(*args, **kwargs):
                    if not self.is_sibling_call(args):
                        return real_run(*args, **kwargs)
                    if failure == "timeout":
                        self.assertEqual(kwargs["timeout"], 30)
                        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
                    if failure == "nonzero":
                        return subprocess.CompletedProcess(args[0], 2, "", "failed")
                    return subprocess.CompletedProcess(args[0], 0, "not json", "")
                returncode, out = self.run_main(module, fx, wrapped)
                self.assertEqual(returncode, 0)
                self.assertEqual(out["verdict"], "CONSISTENT")
                self.assertTrue(out["anchorWritten"])
                self.assertIn("skipped", out["siblingScan"])
                with open(fx.anchor, encoding="utf-8") as handle:
                    self.assertEqual(json.load(handle)["sha"], fx.head)
                with open(fx.last_run, encoding="utf-8") as handle:
                    self.assertEqual(json.load(handle)["verdict"], "CONSISTENT")
                with open(fx.history, encoding="utf-8") as handle:
                    self.assertTrue(json.load(handle)["entries"])

    def test_main_refused_does_not_launch_sibling_scan(self):
        fx = self.prepared(phase4=[{"title": "missing severity"}])
        module = self.module()
        real_run = module.subprocess.run
        sibling_calls = []
        def wrapped(*args, **kwargs):
            if self.is_sibling_call(args):
                sibling_calls.append(args[0])
            return real_run(*args, **kwargs)
        returncode, out = self.run_main(module, fx, wrapped)
        self.assertEqual(returncode, 3)
        self.assertEqual(out["verdict"], "REFUSED")
        self.assertEqual(sibling_calls, [])

    def test_phase4_fail_blocks(self):
        fx = self.prepared(phase4=[{"severity": "HIGH", "message": "broken"}])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "NEEDS_FIX")

    def test_phase4_finding_without_severity_is_refused(self):
        for finding in ({"title": "critical issue"},
                        {"source": "security-review", "title": "missing"}):
            with self.subTest(finding=finding):
                fx = self.prepared(phase4=[finding])
                proc = fx.gate()
                self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
                result = json.loads(proc.stdout)
                self.assertEqual(result["verdict"], "REFUSED")
                self.assertIn("severity", result["reason"])
                self.assertNotIn("siblingScan", result)
        with open(fx.last_run, encoding="utf-8") as handle:
            state = json.load(handle)
        self.assertEqual(result["reportStatus"], "not-requested")
        self.assertEqual(result["reportStatus"], state["reportStatus"])


class TestAttacks(GateBase):
    def test_unsafe_prelock_refused_omits_report_status(self):
        fx = self.prepared()
        proc = fx.call(
            "decide-verdict.py", "--run-dir", fx.repo, "--repo-root", fx.repo,
            "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
            "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIn("unsafe state path", result["reason"])
        self.assertNotIn("reportStatus", result)
        self.assertFalse(os.path.exists(fx.last_run))

    def test_hand_fed_verdict_argument_does_not_exist(self):
        fx = self.prepared()
        proc = fx.call("decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                       "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                       "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                       "--verdict", "CONSISTENT")
        self.assertEqual(proc.returncode, 2)

    def test_assigned_path_mismatch_refuses(self):
        returns = [{"attempt": 1, "assignedPath": "docs/a.md", "returnedPath": "docs/b.md",
                    "verdict": "PASS", "rationale": "x", "suggestion": None},
                   {"attempt": 1, "assignedPath": "docs/b.md", "returnedPath": "docs/b.md",
                    "verdict": "PASS", "rationale": "x", "suggestion": None}]
        self.assert_refused(self.prepared(returns=returns))

    def test_return_verdict_mismatch_refuses(self):
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "WARN" if path == "docs/a.md" else "PASS",
                    "rationale": "x", "suggestion": None}
                   for path in ("docs/a.md", "docs/b.md")]
        self.assert_refused(self.prepared(returns=returns))

    def test_manifest_modification_refuses(self):
        fx = self.prepared()
        path = os.path.join(fx.run_dir, "manifest.json")
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
        value["runClass"] = "light"
        write(path, json.dumps(value) + "\n")
        self.assert_refused(fx)

    def test_returns_modification_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.run_dir, "returns.json"), "not json\n")
        proc = self.assert_refused(fx)
        with open(fx.last_run, encoding="utf-8") as handle:
            last_run = json.load(handle)
        self.assertEqual(last_run["runid"], fx.runid)
        self.assertEqual(last_run["verdict"], "REFUSED")
        self.assertEqual(last_run["reason"], json.loads(proc.stdout)["reason"])

    def test_missing_phase4_refuses(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        for path in fx.docs:
            fx.write_verdict(path)
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "PASS", "rationale": "x", "suggestion": None}
                   for path in fx.docs]
        fx.write_evidence("returns", returns)
        fx.evidence["phase4"] = "none"
        self.assert_refused(fx)

    def test_seal_after_worktree_change_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.repo, "src", "app.py"), "print('changed')\n")
        self.assert_refused(fx)

    def test_clean_head_switch_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.repo, "new.txt"), "new\n")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-m", "new head")
        self.assert_refused(fx)

    def test_evidence_key_missing_refuses(self):
        fx = self.prepared()
        fx.evidence.pop("returns")
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertNotIn("reportStatus", result)
        self.assertFalse(os.path.exists(fx.last_run))
        self.assertTrue(os.path.exists(os.path.join(fx.run_base, "lock")))
        released = fx.call("open-run.py", "--run-base", fx.run_base,
                           "--repo-root", fx.repo, "--release", "--runid", fx.runid)
        self.assertEqual(released.returncode, 0, released.stdout + released.stderr)

    def test_engine_version_missing_or_invalid_is_prelock_refused(self):
        cases = (("missing", None), ("null", None), ("number", 21), ("empty", ""))
        for label, value in cases:
            with self.subTest(label=label):
                fx = self.prepared()
                if label == "missing":
                    fx.evidence.pop("engineVersion")
                else:
                    fx.evidence["engineVersion"] = value
                spec = importlib.util.spec_from_file_location(
                    "decide_engine_prelock_" + label, DECIDE)
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                argv = ["decide-verdict.py", "--run-dir", fx.run_dir,
                        "--repo-root", fx.repo, "--config", fx.config_path,
                        "--anchor-path", fx.anchor_rel, "--runid", fx.runid,
                        "--expect-json", json.dumps(fx.evidence)]
                output = io.StringIO()
                with mock.patch.object(sys, "argv", argv), \
                     mock.patch.object(module.fcntl, "flock",
                                       side_effect=AssertionError("lock was acquired")), \
                     contextlib.redirect_stdout(output):
                    code = module.main()
                self.assertEqual(code, 3)
                result = json.loads(output.getvalue())
                self.assertNotIn("reportStatus", result)
                self.assertFalse(os.path.exists(fx.last_run))
                self.assertTrue(os.path.exists(os.path.join(fx.run_base, "lock")))
                released = fx.call("open-run.py", "--run-base", fx.run_base,
                                   "--repo-root", fx.repo, "--release", "--runid", fx.runid)
                self.assertEqual(released.returncode, 0, released.stdout + released.stderr)

    def test_engine_version_mismatch_refuses_after_identity_and_releases_lock(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"})
        fx.open(); fx.plan_start_seal(); fx.complete(); fx.write_template()
        fx.evidence["engineVersion"] = "9.9.9"
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertEqual(
            result["reason"],
            f"engine version changed during run: evidence=9.9.9 plugin={plugin_version()}")
        self.assertEqual(result["reportStatus"], "written")
        self.assertIn("reportPath", result)
        self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))
        with open(fx.last_run, encoding="utf-8") as handle:
            state = json.load(handle)
        self.assertEqual(state["verdict"], "REFUSED")
        self.assertEqual(state["reportStatus"], "written")
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            self.assertIn("verdict: REFUSED", handle.read())

    def test_engine_version_reason_precedes_title_claim_and_template_errors(self):
        fx = RunFixture(self, config_extra={
            "codexReview": {},
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        phase4 = {"findings": [{"source": "codex-review", "severity": "HIGH",
                                "title": " ", "file": "docs/a.md"}],
                  "codexReview": {"state": "completed", "promptVariant": "diff",
                                  "carryForwardSha": "none"}}
        self.assertEqual(fx.complete(phase4=phase4).returncode, 0)
        self.assertEqual(fx.write_template().returncode, 0)
        bad = (fx.report_template() + "duplicate: {{GATE_VERDICT}}\n").encode("utf-8")
        TestGateWritesReport.replace_template_artifacts(fx, bad)
        fx.evidence["engineVersion"] = "9.9.9"
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["reason"].startswith("engine version changed during run"))
        self.assertEqual(result["reportStatus"], "failed")
        self.assertIn("reportTemplateInvalid", result["warnings"])

    def test_none_sentinel_with_existing_file_refuses(self):
        fx = self.prepared()
        fx.evidence["phase4"] = "none"
        self.assert_refused(fx)

    def test_config_change_refuses_and_poison_blocks_next_open(self):
        fx = self.prepared()
        config = dict(fx.config)
        config["maxImpactedDocs"] = 50
        write(fx.config_path, json.dumps(config) + "\n")
        proc = self.assert_refused(fx)
        self.assertIn("config", json.loads(proc.stdout)["reason"])
        next_run = fx.open(runid="20260818T120001Z-abcdef13")
        self.assertEqual(next_run.returncode, 6)
        accepted = fx.open(runid="20260818T120001Z-abcdef13", accept=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_history_change_is_tainted_and_refused(self):
        fx = self.prepared()
        self.assertEqual(fx.gate().returncode, 0)
        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        with open(fx.history, "a", encoding="utf-8") as handle:
            handle.write(" ")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_anchor_change_is_removed_and_refused(self):
        fx = self.prepared()
        self.assertEqual(fx.gate().returncode, 0)
        fx.open(runid="20260818T120001Z-abcdef13")
        fx.plan_start_seal(); fx.complete()
        write(fx.anchor, json.dumps({"sha": "forged"}) + "\n")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(fx.anchor))

    def test_lock_and_history_tamper_still_quarantines_history(self):
        fx = self.prepared()
        lock = os.path.join(fx.run_base, "lock")
        write(lock, json.dumps({"runid": "tampered", "startedAt": "now"}) + "\n")
        write(fx.history, "{broken")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_lock_unlink_recreate_is_refused(self):
        fx = self.prepared()
        lock = os.path.join(fx.run_base, "lock")
        with open(lock, "rb") as handle:
            raw = handle.read()
        replacement = lock + ".replacement"
        write(replacement, raw)
        os.replace(replacement, lock)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("lock", json.loads(proc.stdout)["reason"])
        self.assertNotIn("reportStatus", json.loads(proc.stdout))
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.last_run))

    def test_old_gate_after_break_does_not_touch_later_run(self):
        fx = self.prepared()
        broken = fx.call("open-run.py", "--run-base", fx.run_base,
                         "--repo-root", fx.repo, "--break-lock")
        self.assertEqual(broken.returncode, 0, broken.stderr)
        later = "20260818T120001Z-deadbeef"
        with open(fx.config_path, "rb") as handle:
            config_sha = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        opened = fx.call("open-run.py", "--run-base", fx.run_base,
                         "--repo-root", fx.repo, "--runid", later,
                         "--expect-config-sha", config_sha,
                         "--skill-version", plugin_version())
        self.assertEqual(opened.returncode, 0, opened.stderr)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        lock = os.path.join(fx.run_base, "lock")
        with open(lock, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["runid"], later)
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.anchor))
        self.assertFalse(os.path.exists(fx.last_run))

    def test_manifest_replacement_after_snapshot_does_not_change_decision(self):
        fx = self.prepared()
        wrapper_dir = tempfile.TemporaryDirectory()
        self.addCleanup(wrapper_dir.cleanup)
        wrapper = os.path.join(wrapper_dir.name, "git")
        write(wrapper, """#!/bin/sh
if [ ! -e "$DOCAUDIT_SWAP_MARKER" ]; then
  printf '{replaced after snapshot' > "$DOCAUDIT_SWAP_MANIFEST"
  : > "$DOCAUDIT_SWAP_MARKER"
fi
exec "$DOCAUDIT_REAL_GIT" "$@"
""")
        os.chmod(wrapper, 0o755)
        env = os.environ.copy()
        env.update({
            "PATH": wrapper_dir.name + os.pathsep + env.get("PATH", ""),
            "DOCAUDIT_REAL_GIT": shutil.which("git"),
            "DOCAUDIT_SWAP_MARKER": os.path.join(wrapper_dir.name, "swapped"),
            "DOCAUDIT_SWAP_MANIFEST": os.path.join(fx.run_dir, "manifest.json"),
        })
        proc = subprocess.run(
            ["python3", os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      "skills", "audit", "scripts", "decide-verdict.py"),
             "--run-dir", fx.run_dir, "--repo-root", fx.repo,
             "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
             "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence)],
            capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{replaced after snapshot")


class TestS4aSealedGate(GateBase):
    FLIP_WARNING = (
        'verdict instability: 1 document(s) changed verdict with unchanged content since '
        'the previous run (1 with an unchanged change set) — single-pass verification '
        'samples the defect pool; "fix these 1 and re-run" is not guaranteed to converge '
        '(see ADOPTION)')

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def rewrite(path, value):
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        write(path, raw)
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def prepared_one(self, *, report=False):
        extra = ({"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
                 if report else None)
        fx = RunFixture(self, docs=("docs/a.md",), config_extra=extra)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete({"docs/a.md": "PASS"}).returncode, 0)
        if report:
            self.assertEqual(fx.write_template().returncode, 0)
        first = fx.gate()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        return fx

    def second_verdict(self, fx, *, report=False):
        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete({"docs/a.md": "FAIL"}).returncode, 0)
        if report:
            self.assertEqual(fx.write_template().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def assert_flip_counts(self, result, flips, same_change_set):
        self.assertEqual(result["counts"]["verdictFlipsUnchangedContent"], flips)
        self.assertEqual(
            result["counts"]["verdictFlipsUnchangedContentSameChangeSet"],
            same_change_set)

    def test_impact_sha_mismatch_has_fixed_reason(self):
        fx = self.prepared()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        impact = self.load(impact_path)
        impact["warnings"] = ["changed"]
        self.rewrite(impact_path, impact)
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertEqual(result["reason"], "impact sha mismatch")

    def test_phase4_required_type_has_highest_priority(self):
        for value in (None, 0, 1, "true"):
            with self.subTest(value=value):
                fx = self.prepared()
                write(fx.config_path, "{}\n")
                path = os.path.join(fx.run_dir, "manifest.json")
                manifest = self.load(path)
                manifest["phase4Required"] = value
                fx.evidence["manifest"] = self.rewrite(path, manifest)
                result = json.loads(self.assert_refused(fx).stdout)
                self.assertEqual(result["reason"],
                                 "manifest.phase4Required must be boolean")

    def test_phase4_evidence_conflict_precedes_finding_validation(self):
        fx = self.prepared(phase4=[{"title": "missing severity"}])
        path = os.path.join(fx.run_dir, "manifest.json")
        manifest = self.load(path)
        manifest["phase4Required"] = False
        fx.evidence["manifest"] = self.rewrite(path, manifest)
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertEqual(
            result["reason"], "phase4 evidence conflicts with manifest.phase4Required=false")

    def test_manifest_and_impact_provenance_mismatch_has_fixed_reason(self):
        fx = self.prepared()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        dispatch_path = os.path.join(fx.run_dir, "dispatch.json")
        impact = self.load(impact_path)
        impact["impacted"][0]["provenance"] = "heuristic"
        dispatch = self.load(dispatch_path)
        dispatch["impactSha"] = self.rewrite(impact_path, impact)
        fx.evidence["dispatch"] = self.rewrite(dispatch_path, dispatch)
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertEqual(result["reason"], "provenance mismatch")

    def test_unknown_provenance_with_all_shas_resealed_has_enum_reason(self):
        fx = self.prepared()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        dispatch_path = os.path.join(fx.run_dir, "dispatch.json")
        manifest_path = os.path.join(fx.run_dir, "manifest.json")
        impact = self.load(impact_path)
        path = impact["impacted"][0]["path"]
        impact["impacted"][0]["provenance"] = "unknown"
        dispatch = self.load(dispatch_path)
        dispatch["impactSha"] = self.rewrite(impact_path, impact)
        fx.evidence["dispatch"] = self.rewrite(dispatch_path, dispatch)
        manifest = self.load(manifest_path)
        manifest["provenance"][path] = "unknown"
        fx.evidence["manifest"] = self.rewrite(manifest_path, manifest)
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertEqual(result["reason"], f"provenance enum violation: {path}=unknown")

    def test_audit_scope_changed_after_seal_has_barrier_reason(self):
        scope_raw = b'{"version":1,"rules":[]}\n'
        metadata = {
            "path": ".claude/audit-scope.json",
            "sha256": hashlib.sha256(scope_raw).hexdigest(),
            "rules": 0,
            "importedAt": "2026-08-18T12:00:00Z",
        }
        fx = RunFixture(self, docs=("docs/a.md",), config_extra={"auditScope": metadata})
        scope_path = os.path.join(fx.repo, metadata["path"])
        write(scope_path, scope_raw)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        write(scope_path, b'{"version":1,"rules":[{"changed":true}]}\n')
        result = json.loads(self.assert_refused(fx).stdout)
        self.assertEqual(result["reason"], "audit-scope changed after seal")

    def test_flip_same_change_set_is_one_one_and_reaches_report_warning(self):
        fx = self.prepared_one(report=True)
        result = self.second_verdict(fx, report=True)
        self.assert_flip_counts(result, 1, 1)
        self.assertIn(self.FLIP_WARNING, result["warnings"])
        report = os.path.join(fx.repo, result["reportPath"])
        with open(report, encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn("verdict instability: 1 document(s)", body)
        self.assertIn('"verdictFlipsUnchangedContent":1', body)
        self.assertIn('"verdictFlipsUnchangedContentSameChangeSet":1', body)

    def test_flip_changed_change_set_is_one_zero(self):
        fx = self.prepared_one()
        write(os.path.join(fx.repo, "src", "app.py"), "print('changed code')\n")
        git(fx.repo, "add", "src/app.py")
        git(fx.repo, "commit", "-m", "change code only")
        result = self.second_verdict(fx)
        self.assert_flip_counts(result, 1, 0)

    def test_flip_changed_content_is_zero_zero(self):
        fx = self.prepared_one()
        write(os.path.join(fx.repo, "docs", "a.md"), "# changed document\n")
        git(fx.repo, "add", "docs/a.md")
        git(fx.repo, "commit", "-m", "change document")
        result = self.second_verdict(fx)
        self.assert_flip_counts(result, 0, 0)
        self.assertFalse(any(item.startswith("verdict instability:")
                             for item in result["warnings"]))


class TestCache(GateBase):
    def two_passes(self, fx):
        for number in range(2):
            runid = f"20260818T12000{number}Z-abcdef1{number}"
            self.assertEqual(fx.open(runid=runid).returncode, 0)
            self.assertEqual(fx.plan_start_seal().returncode, 0)
            self.assertEqual(fx.complete().returncode, 0)
            self.assertEqual(fx.gate().returncode, 0)

    def test_all_cached_third_run_is_consistent(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        self.assertEqual(fx.open(runid="20260818T120002Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["cached"]), set(fx.docs))
        self.assertEqual(manifest["dispatch"], [])
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")

    def test_codex_backend_is_written_to_history_and_qualifies_codex_cache(self):
        fx = RunFixture(self, config_extra={"phase3Backend": "codex"})
        self.two_passes(fx)
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        self.assertTrue(history["entries"])
        self.assertTrue(all(entry["backend"] == "codex" for entry in history["entries"]))
        self.assertEqual(fx.open(runid="20260818T120002Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["cached"]), set(fx.docs))
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_full_always_dispatches_after_qualified_history(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal(mode="full").returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["dispatch"]), set(fx.docs))
        self.assertEqual(manifest["cached"], [])

    def test_contract_version_change_is_cache_miss(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal(contract="0.11.0").returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["dispatch"]), set(fx.docs))

    def test_mixed_cache_and_dispatch_is_consistent(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        removed = False
        kept = []
        for entry in history["entries"]:
            if entry["path"] == "docs/b.md" and not removed:
                removed = True
                continue
            kept.append(entry)
        history["entries"] = kept
        write(fx.history, json.dumps(history, sort_keys=True, indent=2) + "\n")
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["cached"], ["docs/a.md"])
        self.assertEqual(manifest["dispatch"], ["docs/b.md"])
        fx.complete({"docs/b.md": "PASS"})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_corrupt_history_is_quarantined_after_cold_dispatch(self):
        fx = RunFixture(self)
        write(fx.history, "{broken")
        fx.open(); self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.evidence["historyStatus"], "corrupt")
        fx.complete()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_cached_content_key_tamper_is_refused_even_with_matching_evidence_sha(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        records = {}
        verdict_dir = os.path.join(fx.run_dir, "verdicts")
        for name in os.listdir(verdict_dir):
            path = os.path.join(verdict_dir, name)
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            records[record["path"]] = (path, record)
        first = sorted(records)[0]
        records[first][1]["contentSha"] = "sha256:" + "0" * 64
        for path, record in records.values():
            raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
            write(path, raw)
        material = bytearray()
        for doc in sorted(records):
            with open(records[doc][0], "rb") as handle:
                material.extend(handle.read())
        fx.evidence["cached"] = "sha256:" + hashlib.sha256(material).hexdigest()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "REFUSED")
        self.assertTrue(os.path.exists(fx.anchor))


class TestCodexReviewGate(GateBase):
    @staticmethod
    def codex_phase(state, mode="incremental"):
        if state in {"completed", "execution-failed"}:
            variant = "full" if mode == "full" else "diff"
        else:
            variant = None
        return {"findings": [], "codexReview": {
            "state": state, "promptVariant": variant, "carryForwardSha": "none"}}

    def prepared_codex(self, config, phase4, mode="incremental"):
        fx = RunFixture(self, config_extra=config)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode=mode).returncode, 0)
        self.assertEqual(fx.complete(phase4=phase4).returncode, 0)
        return fx

    def test_required_state_matrix(self):
        states = {
            "completed": 0,
            "execution-failed": 3,
            "ref-invalid": 3,
            "skipped-full-run": 3,
            "not-active": 3,
        }
        for state, returncode in states.items():
            with self.subTest(state=state):
                fx = self.prepared_codex(
                    {"codexReview": {"required": True}},
                    self.codex_phase(state, "full" if state == "skipped-full-run" else "incremental"),
                    mode="full" if state == "skipped-full-run" else "incremental")
                proc = fx.gate()
                self.assertEqual(proc.returncode, returncode, proc.stdout + proc.stderr)
                result = json.loads(proc.stdout)
                if state == "completed":
                    self.assertEqual(result["verdict"], "CONSISTENT")
                    self.assertEqual(result["codexReview"],
                                     {"state": "completed", "required": True,
                                      "degraded": False})
                else:
                    self.assertEqual(result["verdict"], "REFUSED")
                    self.assertEqual(result["reason"],
                                     "codex-review required but state=" + state)

    def test_required_with_not_active_state_is_refused(self):
        fx = self.prepared_codex(
            {"codexReview": {"required": True}},
            self.codex_phase("not-active"))
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertEqual(result["reason"],
                         "codex-review required but state=not-active")

    def test_required_missing_codex_review_and_phase4_are_refused(self):
        missing_key = self.prepared_codex(
            {"codexReview": {"required": True}}, {"findings": []})
        proc = missing_key.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["reason"],
                         "codexReview evidence invalid: codexReview must be an object")

        missing_file = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.assertEqual(missing_file.open().returncode, 0)
        self.assertEqual(missing_file.plan_start_seal().returncode, 0)
        for path in missing_file.docs:
            self.assertEqual(missing_file.write_verdict(path).returncode, 0)
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "PASS", "rationale": "checked", "suggestion": None}
                   for path in missing_file.docs]
        self.assertEqual(missing_file.write_evidence("returns", returns).returncode, 0)
        proc = missing_file.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["reason"],
                         "codex-review required but state=missing")

    def test_required_config_errors_are_refused(self):
        cases = [
            ({"codexReview": {"required": "yes"}},
             "codexReview.required must be boolean"),
            ({"codexReview": {"required": True, "enabled": False}},
             "codexReview.required conflicts with enabled:false"),
        ]
        for config, reason in cases:
            with self.subTest(reason=reason):
                fx = self.prepared_codex(
                    config, self.codex_phase("completed"))
                proc = fx.gate()
                self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["reason"], reason)

    def test_codex_review_evidence_shape_is_always_strict(self):
        cases = [
            (["completed"], "codexReview must be an object"),
            ({"state": 7, "promptVariant": "diff", "carryForwardSha": "none"},
             "state must be a string"),
            ({"state": "future-state", "promptVariant": "diff", "carryForwardSha": "none"},
             "state is not recognized"),
        ]
        for evidence, detail in cases:
            with self.subTest(detail=detail):
                fx = self.prepared_codex(
                    {}, {"findings": [], "codexReview": evidence})
                proc = fx.gate()
                self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["reason"],
                                 "codexReview evidence invalid: " + detail)

    def test_absent_codex_review_is_refused_as_mixed_version_evidence(self):
        fx = self.prepared_codex({}, {"findings": []})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertEqual(result["reason"],
                         "codexReview evidence invalid: codexReview must be an object")

    def test_degraded_report_is_decorated_but_state_and_anchor_are_plain(self):
        fx = self.prepared_codex(
            {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"},
            self.codex_phase("execution-failed"))
        self.assertEqual(fx.write_template().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        warning = ("codex-review did not run (execution-failed) — verdict excludes "
                   "the adversarial layer")
        self.assertEqual(result["verdict"], "CONSISTENT")
        self.assertIn(warning, result["warnings"])
        self.assertEqual(result["codexReview"],
                         {"state": "execution-failed", "required": False,
                          "degraded": True})
        with open(os.path.join(fx.repo, result["reportPath"]), encoding="utf-8") as handle:
            report = handle.read()
        self.assertIn(
            "verdict: CONSISTENT (codex-review did not run: execution-failed)", report)
        with open(fx.last_run, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["verdict"], "CONSISTENT")
        with open(fx.anchor, encoding="utf-8") as handle:
            anchor = json.load(handle)
        self.assertEqual(anchor["sha"], fx.head)
        self.assertNotIn("codex-review", json.dumps(anchor))

    def test_optional_ref_invalid_warns_without_refusing(self):
        fx = self.prepared_codex(
            {}, self.codex_phase("ref-invalid"))
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIn(
            "codex-review did not run (ref-invalid) — verdict excludes the adversarial layer",
            result["warnings"])

    def test_required_refusal_preserves_history_and_anchor_and_updates_last_run(self):
        fx = self.prepared_codex(
            {"codexReview": {"required": True}},
            self.codex_phase("completed"))
        first = fx.gate()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        with open(fx.history, "rb") as handle:
            history_before = handle.read()
        with open(fx.anchor, "rb") as handle:
            anchor_before = handle.read()

        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(phase4=self.codex_phase("execution-failed")).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        reason = "codex-review required but state=execution-failed"
        self.assertEqual(json.loads(proc.stdout)["reason"], reason)
        with open(fx.history, "rb") as handle:
            self.assertEqual(handle.read(), history_before)
        with open(fx.anchor, "rb") as handle:
            self.assertEqual(handle.read(), anchor_before)
        with open(fx.last_run, encoding="utf-8") as handle:
            last_run = json.load(handle)
        self.assertEqual(last_run["verdict"], "REFUSED")
        self.assertEqual(last_run["reason"], reason)


if __name__ == "__main__":
    unittest.main()
