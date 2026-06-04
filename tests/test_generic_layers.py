import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "generic-layers.py")


def run(repo, layer="all", config=None, paths=None):
    cfg = config or {"docGlobs": ["docs/**/*.md", "*.md"]}
    cf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(cfg, cf); cf.close()
    argv = [sys.executable, SCRIPT, "--config", cf.name, "--repo-root", repo, "--layer", layer]
    inp = None
    if paths is not None:
        argv += ["--paths", "-"]; inp = "\n".join(paths)
    p = subprocess.run(argv, input=inp, capture_output=True, text=True)
    os.unlink(cf.name)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def write(repo, rel, content):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)


class TestFormatLayer(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_broken_relative_link_is_fail(self):
        write(self.repo, "docs/a.md", "see [x](./missing.md)\n")
        out = run(self.repo, "format")
        fails = [f for f in out["findings"] if f["severity"] == "FAIL"]
        self.assertTrue(any("missing.md" in f["message"] for f in fails))

    def test_resolving_link_no_finding(self):
        write(self.repo, "docs/a.md", "see [b](./b.md)\n")
        write(self.repo, "docs/b.md", "hi\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if f["severity"] == "FAIL"], [])

    def test_external_link_skipped(self):
        write(self.repo, "docs/a.md", "see [g](https://example.com/x)\n")
        out = run(self.repo, "format")
        self.assertEqual(out["findings"], [])

    def test_frontmatter_field_warn_when_configured(self):
        write(self.repo, "docs/a.md", "---\ntitle: x\n---\nbody\n")
        out = run(self.repo, "format", config={"docGlobs": ["docs/**/*.md", "*.md"],
                                               "frontMatterFields": ["title", "version"]})
        warns = [f for f in out["findings"] if f["severity"] == "WARN"]
        self.assertTrue(any("version" in f["message"] for f in warns))
        self.assertFalse(any("title" in f["message"] for f in warns))

    def test_no_frontmatter_check_when_not_configured(self):
        write(self.repo, "docs/a.md", "no front matter here\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if "front matter" in f["message"]], [])


class TestExistenceLayer(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, "scripts"), exist_ok=True)
        open(os.path.join(self.repo, "scripts", "real.py"), "w").write("x\n")

    def test_nonresolving_repo_pathish_token_warns(self):
        write(self.repo, "docs/a.md", "see `scripts/ghost.py` for details\n")
        out = run(self.repo, "existence")
        self.assertTrue(any("scripts/ghost.py" in f["message"] for f in out["findings"]))

    def test_resolving_token_no_finding(self):
        write(self.repo, "docs/a.md", "see `scripts/real.py`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_non_path_backtick_ignored(self):
        write(self.repo, "docs/a.md", "run `make deploy` then `occ status`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_glob_token_skipped(self):
        write(self.repo, "docs/a.md", "edit `scripts/*.py`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])


if __name__ == "__main__":
    unittest.main()
