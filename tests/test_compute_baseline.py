import json, os, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "compute-baseline.sh")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


def write(repo, rel, content="x\n"):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def run_script(repo, config):
    cfg_rel = ".claude/doc-audit.json"
    write(repo, cfg_rel, json.dumps(config))
    git(repo, "add", "-A"); git(repo, "commit", "-m", "cfg")
    p = subprocess.run(["bash", SCRIPT, "--config", os.path.join(repo, cfg_rel), "--repo-root", repo],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class TestComputeBaseline(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        write(self.repo, "README.md", "init\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "init")

    def test_no_anchor_yields_full_mode(self):
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**", "apps/**"]})
        self.assertEqual(out["mode"], "full")

    def test_changed_files_since_anchor(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/a.md", "changed\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertEqual(out["mode"], "incremental")
        self.assertIn("docs/a.md", out["changed"])

    def test_untracked_and_unstaged_included(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/untracked.md", "new\n")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertIn("docs/untracked.md", out["changed"])

    def test_missing_anchor_sha_falls_back_to_full(self):
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": "0000000000000000000000000000000000000000"}))
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertEqual(out["mode"], "full")


if __name__ == "__main__":
    unittest.main()
