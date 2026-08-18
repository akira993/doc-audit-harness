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

    def test_existing_doc_tool_candidates_cover_all_supported_sources(self):
        write(self.repo, ".claude/commands/lint-content.md", "# command\n")
        write(self.repo, ".claude/commands/release.md", "# unrelated\n")
        write(self.repo, ".claude/skills/docs-review/SKILL.md", "---\nname: docs-review\n---\n")
        write(self.repo, "package.json", json.dumps({"scripts": {
            "check-docs": "node docs.js", "docs:build": "x", "lint:docs": "x",
            "test": "x"
        }}))
        write(self.repo, "Makefile", "check-boundary:\n\ttrue\nlint-docs:\n\ttrue\n")
        write(self.repo, "Taskfile.yml", "version: '3'\ntasks:\n  docs:check:\n    cmds: [echo ok]\n")
        write(self.repo, "Justfile", "doc-lint:\n    echo ok\n")
        write(self.repo, "pyproject.toml", """
[project.scripts]
docs-check = "pkg:main"
serve = "pkg:serve"
[tool.poetry.scripts]
lint = "pkg:lint"
""")
        write(self.repo, ".github/workflows/docs.yml", """
name: CI
jobs:
  docs:
    steps:
      - name: Build documentation
        run: make docs
      - name: Tests
        run: markdownlint docs
""")
        write(self.repo, "scripts/check-docs-ci", "#!/bin/sh\n")

        out = run(self.repo)
        candidates = out["existingDocToolCandidates"]
        triples = {(c["kind"], c["path"], c["name"]) for c in candidates}
        expected = {
            ("claude-command", ".claude/commands/check-docs.md", "check-docs"),
            ("claude-command", ".claude/commands/lint-content.md", "lint-content"),
            ("claude-skill", ".claude/skills/docs-review/SKILL.md", "docs-review"),
            ("package-script", "package.json", "check-docs"),
            ("package-script", "package.json", "docs:build"),
            ("package-script", "package.json", "lint:docs"),
            ("make-target", "Makefile", "lint-docs"),
            ("taskfile-target", "Taskfile.yml", "docs:check"),
            ("just-target", "Justfile", "doc-lint"),
            ("pyproject-script", "pyproject.toml", "docs-check"),
            ("pyproject-script", "pyproject.toml", "lint"),
            ("github-workflow-step", ".github/workflows/docs.yml", "Build documentation"),
            ("github-workflow-step", ".github/workflows/docs.yml", "Tests"),
            ("script", "scripts/check-docs-ci", "check-docs-ci"),
        }
        self.assertTrue(expected.issubset(triples), expected - triples)
        self.assertNotIn(("claude-command", ".claude/commands/release.md", "release"), triples)
        self.assertTrue(all(set(item) == {"kind", "path", "name"} for item in candidates))

    def test_mentions_and_index_and_skip(self):
        out = run(self.repo)
        self.assertIn("docs/a.md", out["mentions"].get("apps", []))
        self.assertIn("docs/README.md", out["indexFiles"])
        self.assertEqual(out["frontMatter"]["total"], 2)


    def test_docglobs_derived_from_actual_docdirs(self):
        # docGlobs must derive from dirs that ACTUALLY contain docs (non-standard
        # layout: docs live in guide/, not docs/) — not assume a docs/ dir exists.
        repo = tempfile.mkdtemp()
        write(repo, "guide/intro.md", "x\n")
        write(repo, "top.md", "y\n")
        out = run(repo)
        self.assertIn("guide/**/*.md", out["docGlobs"])
        self.assertIn("*.md", out["docGlobs"])
        self.assertNotIn("docs/**/*.md", out["docGlobs"])


if __name__ == "__main__":
    unittest.main()
