import json, os, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "write-anchor.sh")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True)


class TestWriteAnchor(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        with open(os.path.join(self.repo, "f"), "w") as f:
            f.write("x")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "init")
        self.anchor = ".claude/state/last-doc-audit.json"

    def run_script(self, verdict, mode="incremental"):
        return subprocess.run(
            ["bash", SCRIPT, "--repo-root", self.repo, "--anchor-path", self.anchor,
             "--verdict", verdict, "--mode", mode, "--date", "2026-06-04"],
            capture_output=True, text=True)

    def test_writes_on_consistent(self):
        p = self.run_script("CONSISTENT")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.load(open(os.path.join(self.repo, self.anchor)))
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(data["sha"], head)
        self.assertEqual(data["verdict"], "CONSISTENT")
        self.assertEqual(data["date"], "2026-06-04")
        self.assertEqual(data["tool"], "docaudit")

    def test_noop_on_needs_fix(self):
        p = self.run_script("NEEDS_FIX")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo, self.anchor)))


if __name__ == "__main__":
    unittest.main()
