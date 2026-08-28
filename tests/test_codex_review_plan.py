import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "codex-review-plan.py")


class TestCodexReviewPlan(unittest.TestCase):
    def test_invalid_config_reason_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"codexReview": {"required": True}}, handle)
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--mode", "incremental", "--config", config,
                 "--available", "false", "--available-reason", "invalid-config",
                 "--baseline-ok", "true"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {
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
                         "--baseline-ok", str(baseline_ok).lower()],
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


if __name__ == "__main__":
    unittest.main()
