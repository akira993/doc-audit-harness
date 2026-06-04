import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "inventory.py")


def write(repo, rel, content=""):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def run(repo):
    p = subprocess.run([sys.executable, SCRIPT, "--repo-root", repo],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        write(self.repo, "docs/README.md", "---\ntitle: Idx\ndescription: d\n---\n[a](./a.md)\n")
        write(self.repo, "docs/a.md", "---\ntitle: A\n---\nthis doc talks about apps and scripts\n")
        write(self.repo, "apps/x.py", "print(1)\n")
        write(self.repo, "scripts/y.sh", "echo hi\n")
        write(self.repo, "Makefile", "check-boundary:\n\techo ok\n")
        write(self.repo, ".claude/commands/check-docs.md", "# check-docs\n")
        write(self.repo, "node_modules/junk/z.md", "should be skipped\n")

    def test_doc_dirs_and_globs(self):
        out = run(self.repo)
        self.assertIn("docs", out["docDirs"])
        self.assertIn("docs/**/*.md", out["docGlobs"])

    def test_code_dirs_exclude_docs(self):
        out = run(self.repo)
        self.assertIn("apps", out["codeDirs"])
        self.assertIn("scripts", out["codeDirs"])
        self.assertNotIn("docs", out["codeDirs"])

    def test_frontmatter_suggestion_threshold(self):
        out = run(self.repo)
        self.assertIn("title", out["suggestedFrontMatterFields"])
        self.assertNotIn("description", out["suggestedFrontMatterFields"])

    def test_boundary_guess(self):
        out = run(self.repo)
        self.assertEqual(out["boundaryCommandGuess"], "make check-boundary")

    def test_existing_doc_tools_detected(self):
        out = run(self.repo)
        self.assertIn(".claude/commands/check-docs.md", out["existingDocTools"]["commands"])

    def test_mentions_and_index_and_skip(self):
        out = run(self.repo)
        self.assertIn("docs/a.md", out["mentions"].get("apps", []))
        self.assertIn("docs/README.md", out["indexFiles"])
        self.assertEqual(out["frontMatter"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
