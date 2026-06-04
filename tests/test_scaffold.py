import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "scaffold.py")


def run(repo, *extra):
    return subprocess.run([sys.executable, SCRIPT, "--repo-root", repo, *extra],
                          capture_output=True, text=True)


class TestScaffold(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_creates_three_layer_skills(self):
        p = run(self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(len(out["created"]), 3)
        for layer in ("format", "existence", "semantic"):
            f = os.path.join(self.repo, ".claude", "skills", f"docaudit-{layer}", "SKILL.md")
            self.assertTrue(os.path.isfile(f))
            t = open(f, encoding="utf-8").read()
            self.assertTrue(t.startswith("---\n"))
            self.assertIn(f"name: docaudit-{layer}", t)
            self.assertIn("description:", t)
            self.assertIn("CUSTOMIZE", t)
        self.assertEqual(out["skillNames"]["format"], "docaudit-format")

    def test_refuses_overwrite(self):
        d = os.path.join(self.repo, ".claude", "skills", "docaudit-format")
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write("ORIGINAL")
        out = json.loads(run(self.repo).stdout)
        self.assertIn(".claude/skills/docaudit-format/SKILL.md", out["skipped"])
        self.assertEqual(open(os.path.join(d, "SKILL.md")).read(), "ORIGINAL")

    def test_dry_run_writes_nothing(self):
        out = json.loads(run(self.repo, "--dry-run").stdout)
        self.assertEqual(len(out["created"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude", "skills")))

    def test_unknown_layer_exit2(self):
        self.assertEqual(run(self.repo, "--layers", "bogus").returncode, 2)

    def test_custom_prefix(self):
        out = json.loads(run(self.repo, "--prefix", "myproj", "--layers", "format").stdout)
        self.assertEqual(out["skillNames"]["format"], "myproj-format")
        self.assertTrue(os.path.isfile(
            os.path.join(self.repo, ".claude", "skills", "myproj-format", "SKILL.md")))


if __name__ == "__main__":
    unittest.main()
