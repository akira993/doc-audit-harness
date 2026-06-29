"""write-anchor.sh is RETIRED. The old `--verdict CONSISTENT` hand-off was the
hole the cure closes; the anchor is now written only by decide-verdict.py, which
DERIVES the verdict. These tests assert the old interface can no longer advance
the anchor."""
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "write-anchor.sh")


class TestWriteAnchorRetired(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.anchor = ".claude/state/last-doc-audit.json"

    def run_script(self, *args):
        return subprocess.run(["bash", SCRIPT, *args], capture_output=True, text=True)

    def test_hand_fed_verdict_no_longer_writes_anchor(self):
        # the exact old attack: hand-feed CONSISTENT
        p = self.run_script("--repo-root", self.repo, "--anchor-path", self.anchor,
                            "--verdict", "CONSISTENT", "--mode", "incremental")
        self.assertNotEqual(p.returncode, 0, "retired stub must fail loud")
        self.assertFalse(os.path.exists(os.path.join(self.repo, self.anchor)),
                         "no anchor may be written through the retired path")

    def test_points_at_decide_verdict(self):
        p = self.run_script()
        self.assertIn("decide-verdict.py", p.stderr)


if __name__ == "__main__":
    unittest.main()
