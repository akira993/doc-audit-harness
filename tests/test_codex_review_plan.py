import itertools
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "codex-review-plan.py")
PROBE = os.path.join(ROOT, "skills", "audit", "scripts", "codex-probe.sh")

V015_CASES = {
    "present_unavailable_not_configured", "keyless_unavailable_not_configured",
    "keyless_old_record_available", "full_required", "full_disabled_required",
    "full_optional", "full_keyless",
}


def config_sha(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def sealed_args(config, repo_root):
    return ["--expect-config-sha", config_sha(config), "--repo-root", repo_root,
            "--history", os.path.join(repo_root, "history.json"),
            "--expect-history-sha", "none",
            "--worktree-digest", "sha256:" + "1" * 64]


class TestCodexReviewPlan(unittest.TestCase):
    def run_plan(self, config_value, available, available_reason, mode="incremental",
                 baseline_ok=True):
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump(config_value, handle)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--mode", mode, "--config", config,
                 "--available", str(available).lower(),
                 "--available-reason", available_reason,
                 "--baseline-ok", str(baseline_ok).lower(),
                 *sealed_args(config, tmp)],
                capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        return json.loads(proc.stdout)

    def test_invalid_config_reason_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"codexReview": {"required": True}}, handle)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--mode", "incremental", "--config", config,
                 "--available", "false", "--available-reason", "invalid-config",
                 "--baseline-ok", "true", *sealed_args(config, tmp)],
                capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {
            "carryForward": None, "carryForwardSha": "none",
            "action": "not-active", "promptVariant": None,
            "reason": "invalid-config", "state": "not-active",
        })

    def test_sixteen_row_truth_table(self):
        # enabled:false is deliberately absent: Phase 0 collapses it to
        # available:false/reason:disabled-by-config before this table is reached.
        for available, mode, required, baseline_ok in itertools.product(
                (False, True), ("incremental", "full"), (False, True), (False, True)):
            with self.subTest(available=available, mode=mode, required=required,
                              baseline_ok=baseline_ok):
                with tempfile.TemporaryDirectory() as tmp:
                    config = os.path.join(tmp, "config.json")
                    with open(config, "w", encoding="utf-8") as handle:
                        json.dump({"codexReview": {"required": required}}, handle)
                    proc = subprocess.run(
                        [sys.executable, SCRIPT, "--mode", mode, "--config", config,
                         "--available", str(available).lower(),
                         "--available-reason", "test-unavailable",
                         "--baseline-ok", str(baseline_ok).lower(),
                         *sealed_args(config, tmp)],
                        capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                actual = json.loads(proc.stdout)
                if not available:
                    expected = ("not-active", "not-active", None)
                elif mode == "full" and required:
                    expected = ("run", None, "full")
                elif mode == "full":
                    expected = ("skip", "skipped-full-run", None)
                elif baseline_ok:
                    expected = ("run", None, "diff")
                else:
                    expected = ("skip", "ref-invalid", None)
                self.assertEqual(
                    (actual["action"], actual["state"], actual["promptVariant"]),
                    expected)

    def test_v015_case_ids_are_fixed_and_complete(self):
        self.assertEqual(len(V015_CASES), 7)
        self.assertEqual(V015_CASES, {
            "present_unavailable_not_configured", "keyless_unavailable_not_configured",
            "keyless_old_record_available", "full_required", "full_disabled_required",
            "full_optional", "full_keyless",
        })

    def test_not_configured_direct_plans(self):
        cases = {
            "present_unavailable_not_configured": (
                {"codexReview": {}}, False, "not-configured"),
            "keyless_unavailable_not_configured": ({}, False, "not-configured"),
            "keyless_old_record_available": ({}, True, "ok"),
        }
        self.assertEqual(len(cases), 3)
        expected = {"action": "not-active", "state": "not-active",
                    "promptVariant": None, "reason": "not-configured",
                    "carryForward": None, "carryForwardSha": "none"}
        for case_id, (config, available, reason) in cases.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(self.run_plan(config, available, reason), expected)

    def test_full_mode_probe_to_planner_integration(self):
        expected = {
            "full_required": {"action": "run", "state": None,
                              "promptVariant": "full", "reason": "ready",
                              "carryForward": None, "carryForwardSha": "none"},
            "full_disabled_required": {"action": "not-active", "state": "not-active",
                                       "promptVariant": None, "reason": "disabled-by-config",
                                       "carryForward": None, "carryForwardSha": "none"},
            "full_optional": {"action": "skip", "state": "skipped-full-run",
                              "promptVariant": None, "reason": "full-run-without-required",
                              "carryForward": None, "carryForwardSha": "none"},
            "full_keyless": {"action": "not-active", "state": "not-active",
                             "promptVariant": None, "reason": "not-configured",
                             "carryForward": None, "carryForwardSha": "none"},
        }
        configs = {
            "full_required": {"codexReview": {"required": True}},
            "full_disabled_required": {"codexReview": {"enabled": False,
                                                         "required": True}},
            "full_optional": {"codexReview": {}},
            "full_keyless": {},
        }
        self.assertEqual(set(configs), set(expected))
        with tempfile.TemporaryDirectory() as tmp:
            codex = os.path.join(tmp, "codex")
            with open(codex, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n"
                             "if [ \"$1\" = \"--version\" ]; then echo v; exit 0; fi\n"
                             "if [ \"$1\" = \"exec\" ] && [ \"$2\" = \"--help\" ]; then exit 0; fi\n"
                             "exit 2\n")
            os.chmod(codex, 0o755)
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ["PATH"])
            for case_id, config_value in configs.items():
                with self.subTest(case_id=case_id):
                    config = os.path.join(tmp, case_id + ".json")
                    with open(config, "w", encoding="utf-8") as handle:
                        json.dump(config_value, handle)
                    probe = subprocess.run(
                        ["bash", PROBE, "--config", config, "--repo-root", tmp,
                         "--expect-config-sha", config_sha(config)],
                        capture_output=True, text=True, env=env)
                    self.assertEqual(probe.returncode, 0, probe.stderr)
                    self.assertEqual(len(probe.stdout.splitlines()), 1)
                    probe_out = json.loads(probe.stdout)
                    plan = subprocess.run(
                        [sys.executable, SCRIPT, "--mode", "full", "--config", config,
                         "--available", str(probe_out["codexReviewAvailable"]).lower(),
                         "--available-reason", probe_out["reason"],
                         "--baseline-ok", "false", *sealed_args(config, tmp)],
                        capture_output=True, text=True)
                    self.assertEqual(plan.returncode, 0, plan.stderr)
                    self.assertEqual(len(plan.stdout.splitlines()), 1)
                    self.assertEqual(json.loads(plan.stdout), expected[case_id])

    def test_full_carry_forward_resolves_files_against_repo_root_not_cwd(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as other_cwd:
            os.makedirs(os.path.join(repo, "docs"))
            with open(os.path.join(repo, "docs", "real.md"), "w", encoding="utf-8") as handle:
                handle.write("real\n")
            config = os.path.join(repo, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"codexReview": {"required": True}}, handle)
            history = os.path.join(repo, "history.json")
            history_value = {"entries": [], "phase4Runs": [{
                "runid": "20260831T000000Z-aaaa1111",
                "ts": "2026-08-31T00:00:00Z",
                "worktreeDigest": "previous",
                "contractVersion": "0.16.0",
                "configSha": config_sha(config),
                "carryForwardSha": "none",
                "unresolvedFileCount": 0,
                "truncated": False,
                "findings": [{"file": "docs/real.md", "severity": "HIGH"}],
            }]}
            with open(history, "w", encoding="utf-8") as handle:
                json.dump(history_value, handle)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--mode", "full", "--config", config,
                 "--expect-config-sha", config_sha(config), "--repo-root", repo,
                 "--available", "true", "--baseline-ok", "true",
                 "--history", history, "--expect-history-sha", config_sha(history),
                 "--worktree-digest", "current"],
                cwd=other_cwd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["carryForward"], {
            "files": [{"file": "docs/real.md", "severity": "HIGH"}]})


if __name__ == "__main__":
    unittest.main()
