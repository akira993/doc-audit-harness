import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANNER = os.path.join(ROOT, "skills", "audit", "scripts", "code-review-plan.py")


class CodeReviewPlanTests(unittest.TestCase):
    CASES = (
        ({}, "not-active", "not-configured", None, False, None),
        ({"reviewCommands": None}, "refuse", "invalid-review-config", None, False, None),
        ({"reviewCommands": {}}, "not-active", "not-configured", None, False, None),
        ({"reviewCommands": {"code": None}}, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "\u2003"}}, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review low"}}, "run", "pending", "low", False, None),
        ({"reviewCommands": {"code": "/code-review high", "required": True}}, "run", "pending", "high", True, None),
        ({"reviewCommands": {"code": "/code-review xhigh"}}, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/custom 高"}}, "legacy", "legacy-pending", None, False, "/custom 高"),
        ({"reviewCommands": {"code": "/custom", "required": True}}, "refuse", "invalid-review-config", None, False, None),
    )

    @classmethod
    def tearDownClass(cls):
        print(f"対象 {len(cls.CASES)} 件を検査")

    def run_plan(self, config, expected_sha=None):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            raw = (json.dumps(config, ensure_ascii=False, sort_keys=True) + "\n").encode()
            with open(path, "wb") as handle:
                handle.write(raw)
            sha = "sha256:" + hashlib.sha256(raw).hexdigest()
            return subprocess.run(
                [sys.executable, PLANNER, "--config", path,
                 "--expect-config-sha", expected_sha or sha],
                capture_output=True, text=True)

    def test_complete_decision_table_json(self):
        for config, action, state, effort, required, command in self.CASES:
            with self.subTest(config=config):
                proc = self.run_plan(config)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr, "")
                result = json.loads(proc.stdout)
                self.assertEqual(set(result), {"action", "state", "effort", "required", "command", "reason"})
                self.assertEqual((result["action"], result["state"], result["effort"],
                                  result["required"], result["command"]),
                                 (action, state, effort, required, command))
                if action == "refuse":
                    self.assertIn('set reviewCommands.code to "/code-review <low|medium|high>"', result["reason"])

    def test_changed_config_exits_7(self):
        proc = self.run_plan({}, "sha256:" + "0" * 64)
        self.assertEqual(proc.returncode, 7)
        self.assertEqual(proc.stdout, "")
        self.assertIn("sealed-config-mismatch", proc.stderr)


if __name__ == "__main__":
    unittest.main()
