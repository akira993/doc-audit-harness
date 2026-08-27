import importlib.util, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "scaffold.py")
SHAS = os.path.join(ROOT, "skills", "audit", "references", "engine-shas.json")
PLUGIN = os.path.join(ROOT, ".claude-plugin", "plugin.json")
HISTORICAL_ENGINE = os.path.join(ROOT, "tests", "data", "generic-layers-v0.10.1.py")
HISTORICAL_ENGINE_012 = os.path.join(ROOT, "tests", "data", "engine-0.12.0.py")


def run(repo, *extra):
    return subprocess.run([sys.executable, SCRIPT, "--repo-root", repo, *extra],
                          capture_output=True, text=True)


def write(repo, rel, content):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


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
            t = read(f)
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
        self.assertEqual(read(os.path.join(d, "SKILL.md")), "ORIGINAL")

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

    def test_harness_creates_three_stamped_files_and_contract(self):
        p = run(self.repo, "--harness")
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["created"], [
            ".claude/commands/check-docs.md",
            ".claude/skills/doc-lint/SKILL.md",
            "scripts/check-docs.py",
        ])
        command = read(os.path.join(self.repo, ".claude", "commands", "check-docs.md"))
        command_lines = command.splitlines()
        self.assertEqual(command_lines[0], "---")
        closing = command_lines.index("---", 1)
        self.assertIn("description:", "\n".join(command_lines[1:closing]))
        self.assertRegex(command_lines[closing + 1],
                         r"^<!-- docaudit-template: check-docs@[^ ]+ sha256:[0-9a-f]{64} -->$")
        invocation = "python3 scripts/check-docs.py --layer <LAYER> --format text --exit-code --config .claude/doc-audit.json --repo-root ."
        self.assertEqual(command.count(invocation), 1)
        self.assertIn("`--only <layer>`", command)
        self.assertIn("`<LAYER>=<layer>`", command)
        self.assertIn("`<LAYER>=all`", command)
        for heading in ("## PASS", "## WARN", "## FAIL", "## Verdict"):
            self.assertIn(heading, command)
        self.assertNotIn("## 判定", command)

        skill = read(os.path.join(self.repo, ".claude", "skills", "doc-lint", "SKILL.md"))
        skill_lines = skill.splitlines()
        self.assertEqual(skill_lines[0], "---")
        skill_closing = skill_lines.index("---", 1)
        self.assertIn("name: doc-lint", skill)
        self.assertIn("description:", "\n".join(skill_lines[1:skill_closing]))
        self.assertRegex(skill_lines[skill_closing + 1],
                         r"^<!-- docaudit-template: doc-lint@[^ ]+ sha256:[0-9a-f]{64} -->$")
        self.assertIn("--layer semantic --format text", skill)
        self.assertIn("report-only", skill.lower())
        self.assertIn("`path:line - FAIL|WARN - message`", skill)
        self.assertIn("`VERDICT CONSISTENT`", skill)
        self.assertIn("`VERDICT NEEDS FIX`", skill)

        engine = read(os.path.join(self.repo, "scripts", "check-docs.py"))
        self.assertTrue(engine.startswith("#!/usr/bin/env python3\n# docaudit-template:"))
        self.assertEqual(out["docAuditCommands"], {
            "existence": "/check-docs --only existence",
            "format": "/check-docs --only format",
            "semantic": "doc-lint",
        })

    def test_harness_dry_run_writes_nothing(self):
        out = json.loads(run(self.repo, "--harness", "--dry-run").stdout)
        self.assertEqual(len(out["created"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "scripts")))

    def test_harness_existing_files_are_skipped(self):
        path = write(self.repo, ".claude/commands/check-docs.md", "ORIGINAL\n")
        out = json.loads(run(self.repo, "--harness").stdout)
        self.assertIn(".claude/commands/check-docs.md", out["skipped"])
        self.assertIn({"path": ".claude/commands/check-docs.md", "reason": "exists"},
                      out["skipReasons"])
        self.assertEqual(read(path), "ORIGINAL\n")

    def test_harness_skips_symlinked_destination_parent(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        os.symlink(outside.name, os.path.join(self.repo, "scripts"))
        proc = run(self.repo, "--harness")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("scripts/check-docs.py", out["skipped"])
        reasons = {item["path"]: item["reason"] for item in out["skipReasons"]}
        self.assertIn("symlink", reasons["scripts/check-docs.py"])
        self.assertFalse(os.path.exists(os.path.join(outside.name, "check-docs.py")))

    def test_refresh_updates_unmodified_historical_template(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = """---
name: doc-lint
description: Report-only semantic documentation review for contradictions, stale claims, orphan pages, and missing cross-references after the deterministic check.
---

# doc-lint

First run this deterministic semantic check and quote its output verbatim:

`python3 scripts/check-docs.py --layer semantic --format text --config .claude/doc-audit.json --repo-root .`

Then inspect the repository documentation for contradictions, stale claims, orphan
pages, and missing cross-references. Report each finding with its path, line, severity,
and a proposed fix. This skill is report-only: never edit a file and never replace or
reinterpret the deterministic engine's `SUMMARY` or `VERDICT` lines.
"""
        shipped = json.loads(read(SHAS))["0.10.0"]["doc-lint"]
        self.assertEqual(module._normalized_sha(old), shipped)
        path = os.path.join(self.repo, ".claude", "skills", "doc-lint", "SKILL.md")
        write(self.repo, ".claude/skills/doc-lint/SKILL.md",
              module._markdown_with_stamp(old, "doc-lint", "0.10.0", shipped))
        out = json.loads(run(self.repo, "--harness", "--refresh").stdout)
        self.assertIn(".claude/skills/doc-lint/SKILL.md", out["created"])
        self.assertIn(f"@{out['stampVersion']} ", read(path))

    def test_refresh_preserves_modified_historical_doc_lint(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = """---
name: doc-lint
description: Report-only semantic documentation review for contradictions, stale claims, orphan pages, and missing cross-references after the deterministic check.
---

# doc-lint

First run this deterministic semantic check and quote its output verbatim:

`python3 scripts/check-docs.py --layer semantic --format text --config .claude/doc-audit.json --repo-root .`

Then inspect the repository documentation for contradictions, stale claims, orphan
pages, and missing cross-references. Report each finding with its path, line, severity,
and a proposed fix. This skill is report-only: never edit a file and never replace or
reinterpret the deterministic engine's `SUMMARY` or `VERDICT` lines.
"""
        shipped = json.loads(read(SHAS))["0.10.0"]["doc-lint"]
        path = os.path.join(self.repo, ".claude", "skills", "doc-lint", "SKILL.md")
        historical = module._markdown_with_stamp(old, "doc-lint", "0.10.0", shipped)
        modified = historical + "user customization\n"
        write(self.repo, ".claude/skills/doc-lint/SKILL.md", modified)
        out = json.loads(run(self.repo, "--harness", "--refresh").stdout)
        self.assertIn(".claude/skills/doc-lint/SKILL.md", out["skipped"])
        self.assertEqual(read(path), modified)
        self.assertIn("@0.10.0 ", read(path))

    def test_refresh_skips_from_0_10_1_stamp_to_latest_engine(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = read(HISTORICAL_ENGINE)
        shipped = json.loads(read(SHAS))["0.10.1"]["check-docs-engine"]
        self.assertEqual(module._normalized_sha(old), shipped)
        path = os.path.join(self.repo, "scripts", "check-docs.py")
        write(self.repo, "scripts/check-docs.py",
              module._python_with_stamp(old, "check-docs-engine", "0.10.1", shipped))

        proc = run(self.repo, "--harness", "--refresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["stampVersion"], "0.13.1")
        self.assertIn("scripts/check-docs.py", out["created"])
        refreshed = read(path)
        current = json.loads(read(SHAS))["0.13.1"]["check-docs-engine"]
        self.assertIn(f"# docaudit-template: check-docs-engine@0.13.1 sha256:{current}\n",
                      refreshed)
        self.assertEqual(module._normalized_sha(refreshed), current)

    def test_0_12_0_engine_fixture_matches_shipped_hash(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        fixture = read(HISTORICAL_ENGINE_012)
        shipped = json.loads(read(SHAS))["0.12.0"]["check-docs-engine"]
        self.assertEqual(module._normalized_sha(fixture), shipped)

    def test_refresh_updates_0_12_0_stamp_to_0_13_0(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = read(HISTORICAL_ENGINE_012)
        shipped = json.loads(read(SHAS))["0.12.0"]["check-docs-engine"]
        self.assertEqual(module._normalized_sha(old), shipped)
        path = os.path.join(self.repo, "scripts", "check-docs.py")
        write(self.repo, "scripts/check-docs.py",
              module._python_with_stamp(old, "check-docs-engine", "0.12.0", shipped))

        proc = run(self.repo, "--harness", "--refresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["stampVersion"], "0.13.1")
        self.assertIn("scripts/check-docs.py", out["created"])
        refreshed = read(path)
        current = json.loads(read(SHAS))["0.13.1"]["check-docs-engine"]
        self.assertIn(f"# docaudit-template: check-docs-engine@0.13.1 sha256:{current}\n",
                      refreshed)
        self.assertEqual(module._normalized_sha(refreshed), current)

    def test_refresh_preserves_modified_historical_engine(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = read(HISTORICAL_ENGINE)
        shipped = json.loads(read(SHAS))["0.10.1"]["check-docs-engine"]
        self.assertEqual(module._normalized_sha(old), shipped)
        historical = module._python_with_stamp(
            old, "check-docs-engine", "0.10.1", shipped)
        modified = historical + "# user customization\n"
        path = write(self.repo, "scripts/check-docs.py", modified)

        proc = run(self.repo, "--harness", "--refresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("scripts/check-docs.py", out["skipped"])
        self.assertIn({"path": "scripts/check-docs.py",
                       "reason": "modified or unknown template stamp"},
                      out["skipReasons"])
        self.assertEqual(read(path), modified)
        self.assertIn("@0.10.1 ", read(path))

    def test_refresh_does_not_overwrite_modified_or_unstamped_file(self):
        self.assertEqual(run(self.repo, "--harness").returncode, 0)
        command = os.path.join(self.repo, ".claude", "commands", "check-docs.md")
        modified = read(command) + "user customization\n"
        write(self.repo, ".claude/commands/check-docs.md", modified)
        skill = write(self.repo, ".claude/skills/doc-lint/SKILL.md", "unstamped\n")
        out = json.loads(run(self.repo, "--harness", "--refresh").stdout)
        self.assertIn(".claude/commands/check-docs.md", out["skipped"])
        self.assertIn(".claude/skills/doc-lint/SKILL.md", out["skipped"])
        reasons = {item["path"]: item["reason"] for item in out["skipReasons"]}
        self.assertIn("modified", reasons[".claude/commands/check-docs.md"])
        self.assertIn("missing", reasons[".claude/skills/doc-lint/SKILL.md"])
        self.assertEqual(read(command), modified)
        self.assertEqual(read(skill), "unstamped\n")

    def test_harness_engine_runs_in_temp_repo_with_exit_0_and_1(self):
        self.assertEqual(run(self.repo, "--harness").returncode, 0)
        write(self.repo, ".claude/doc-audit.json", json.dumps({
            "docGlobs": ["docs/**/*.md"], "indexFiles": ["docs/README.md"]
        }))
        write(self.repo, "docs/README.md", "# Docs\n\n[Good](good.md)\n")
        write(self.repo, "docs/good.md", "# Good\n")
        command = [sys.executable, "scripts/check-docs.py", "--layer", "all", "--format",
                   "text", "--exit-code", "--config", ".claude/doc-audit.json",
                   "--repo-root", "."]
        passed = subprocess.run(command, cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertIn("SUMMARY", passed.stdout)
        self.assertIn("VERDICT CONSISTENT", passed.stdout)
        write(self.repo, "docs/README.md", "# Docs\n\n[Broken](missing.md)\n")
        failed = subprocess.run(command, cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn("HIT FAIL", failed.stdout)
        self.assertIn("SUMMARY", failed.stdout)
        self.assertIn("VERDICT NEEDS FIX", failed.stdout)

    def test_engine_shas_match_current_generated_bodies(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        version = json.loads(read(PLUGIN))["version"]
        self.assertEqual(version, "0.13.1")
        shipped = json.loads(read(SHAS))[version]
        actual = {name: module._normalized_sha(text)
                  for name, text in module._harness_sources().items()}
        self.assertEqual(actual, shipped)
        self.assertEqual(run(self.repo, "--harness").returncode, 0)
        generated = {
            "check-docs": read(os.path.join(self.repo, ".claude", "commands", "check-docs.md")),
            "doc-lint": read(os.path.join(self.repo, ".claude", "skills", "doc-lint", "SKILL.md")),
            "check-docs-engine": read(os.path.join(self.repo, "scripts", "check-docs.py")),
        }
        self.assertEqual({name: module._normalized_sha(text) for name, text in generated.items()},
                         shipped)

    def test_combined_mode_prefers_harness_format_and_existence(self):
        out = json.loads(run(self.repo, "--scaffold", "--harness").stdout)
        self.assertEqual(out["docAuditCommands"], {
            "existence": "/check-docs --only existence",
            "format": "/check-docs --only format",
            "semantic": "docaudit-semantic",
        })

    def test_refresh_requires_harness(self):
        self.assertEqual(run(self.repo, "--refresh").returncode, 2)


if __name__ == "__main__":
    unittest.main()
