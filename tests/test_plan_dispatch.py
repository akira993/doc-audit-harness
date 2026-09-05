import hashlib
import json
import os
import unittest

from tests.wp12_helpers import RunFixture, write


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class TestPlanDispatchImpactBinding(unittest.TestCase):
    def run_plan(self, history_raw=None, expected_history_sha="omit"):
        fx = RunFixture(self, docs=("docs/a.md",))
        opened = fx.open()
        self.assertEqual(opened.returncode, 0, opened.stderr)
        if history_raw is not None:
            write(fx.history, history_raw)
        impact = {"impacted": [{"path": "docs/a.md", "provenance": "mapped"}]}
        if expected_history_sha != "omit":
            impact["historySha"] = expected_history_sha
        impact_raw = (json.dumps(impact, sort_keys=True) + "\n").encode("utf-8")
        impact_path = os.path.join(fx.run_dir, "impact.json")
        write(impact_path, impact_raw)
        proc = fx.call(
            "plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--config", fx.config_path, "--history", fx.history,
            "--impact-json", impact_path, "--baseline-sha", fx.head, "--mode", "incremental",
            "--contract-version", "0.10.0", "--evidence", json.dumps(fx.evidence),
            "--expect-config-sha", fx.evidence["config"])
        return fx, proc, impact_raw

    def test_matching_history_sha_is_accepted(self):
        raw = b'{"entries":[]}\n'
        fx, proc, _ = self.run_plan(raw, sha(raw))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["historyStatus"], "ok")

    def test_changed_history_exits_seven(self):
        old = b'{"entries":[]}\n'
        _fx, proc, _ = self.run_plan(b'{"entries":[]} \n', sha(old))
        self.assertEqual(proc.returncode, 7)
        self.assertIn("sealed-history-mismatch", proc.stderr)

    def test_null_sha_and_absent_history_are_accepted(self):
        fx, proc, _ = self.run_plan(None, None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["historyStatus"], "absent")

    def test_corrupt_history_with_matching_sha_uses_corrupt_path(self):
        raw = b"{broken\n"
        fx, proc, _ = self.run_plan(raw, sha(raw))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        evidence = json.loads(proc.stdout)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            dispatch = json.load(handle)
        self.assertEqual(dispatch["historyStatus"], "corrupt")
        self.assertEqual(evidence["historyStatus"], "corrupt")

    def test_invalid_phase4_runs_degrades_without_disabling_history(self):
        raw = b'{"entries":[],"phase4Runs":"bad"}\n'
        fx, proc, _ = self.run_plan(raw, sha(raw))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            dispatch = json.load(handle)
        self.assertEqual(dispatch["historyStatus"], "ok")
        self.assertTrue(any("phase4Runs ignored" in item
                            for item in dispatch["warnings"]))

    def test_dispatch_records_impact_sha_without_changing_evidence_keys(self):
        fx, proc, impact_raw = self.run_plan(None, "omit")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        evidence = json.loads(proc.stdout)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            dispatch = json.load(handle)
        self.assertEqual(dispatch["impactSha"], sha(impact_raw))
        self.assertRegex(dispatch["impactSha"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(set(evidence), {"runid", "runDir", "anchor", "config", "lockIno",
                                        "engineVersion",
                                        "preflight", "phase4", "codexReviewResult", "dispatch",
                                        "cached", "history",
                                        "historyStatus", "counts"})
        self.assertNotIn("impactSha", evidence)


if __name__ == "__main__":
    unittest.main()
