import contextlib, importlib.util, io, json, os, subprocess, sys, tempfile, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "scaffold.py")
SHAS = os.path.join(ROOT, "skills", "audit", "references", "engine-shas.json")
PLUGIN = os.path.join(ROOT, ".claude-plugin", "plugin.json")
HISTORICAL_ENGINE = os.path.join(ROOT, "tests", "data", "generic-layers-v0.10.1.py")
HISTORICAL_ENGINE_012 = os.path.join(ROOT, "tests", "data", "engine-0.12.0.py")
HISTORICAL_ENGINE_019 = os.path.join(ROOT, "tests", "data", "generic-layers-v0.19.0.py")


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


def load_module():
    spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binary_state(path):
    if os.path.islink(path):
        return ("symlink", os.readlink(path))
    if not os.path.exists(path):
        return ("missing", None)
    with open(path, "rb") as handle:
        return ("file", handle.read())


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

    def test_refresh_updates_unmodified_0_19_0_doc_lint_and_engine(self):
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        shipped_all = json.loads(read(SHAS))
        shipped = shipped_all["0.19.0"]
        self.assertEqual(shipped, {
            "check-docs": "a5c1efbcbe1bdbece74cb188228fd676d4c6c0446a42f27d6514afe40c5f1ab8",
            "doc-lint": "ebc5944f8739b4b0ff9740f442fe05225c6df300f6fcb471ba20120f30366727",
            "check-docs-engine": "3ba2bc34da259ebdefba32b431bc6267595fe2f75d47b530313455411682abd1",
        })
        old_lint = """---
name: doc-lint
description: Report-only semantic documentation review for contradictions, stale claims, orphan pages, and missing cross-references after the deterministic check.
---

# doc-lint

First run this deterministic semantic check and quote its output verbatim:

`python3 scripts/check-docs.py --layer semantic --format text --config .claude/doc-audit.json --repo-root .`

Then inspect the repository documentation for contradictions, stale claims, orphan
pages, and missing cross-references. List every finding on one line exactly as
`path:line - FAIL|WARN - message`, including a proposed fix in the message. After all
findings, print one final standalone line: `VERDICT CONSISTENT` when there are no FAIL
findings, or `VERDICT NEEDS FIX` when there is at least one FAIL finding. This skill is
report-only: never edit a file and never replace or reinterpret the deterministic
engine's `SUMMARY` or `VERDICT` lines.
"""
        self.assertEqual(module._normalized_sha(old_lint), shipped["doc-lint"])
        old_engine = read(HISTORICAL_ENGINE_019)
        self.assertEqual(module._normalized_sha(old_engine), shipped["check-docs-engine"])
        paths = {
            "check-docs": ".claude/commands/check-docs.md",
            "doc-lint": ".claude/skills/doc-lint/SKILL.md",
            "check-docs-engine": "scripts/check-docs.py",
        }
        # check-docs itself did not change for 0.21.0, so an existing local
        # command remains untouched while the two changed templates refresh.
        write(self.repo, paths["check-docs"], "local check-docs command\n")
        write(self.repo, paths["doc-lint"], module._markdown_with_stamp(
            old_lint, "doc-lint", "0.19.0", shipped["doc-lint"]))
        write(self.repo, paths["check-docs-engine"], module._python_with_stamp(
            old_engine, "check-docs-engine", "0.19.0", shipped["check-docs-engine"]))
        proc = run(self.repo, "--harness", "--refresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["stampVersion"], "0.21.0")
        self.assertIn(paths["check-docs"], out["skipped"])
        self.assertTrue({paths["doc-lint"], paths["check-docs-engine"]} <= set(out["created"]))
        self.assertEqual(read(os.path.join(self.repo, paths["check-docs"])), "local check-docs command\n")
        self.assertEqual(module._normalized_sha(read(os.path.join(self.repo, paths["doc-lint"]))),
                         shipped_all["0.21.0"]["doc-lint"])
        self.assertEqual(module._normalized_sha(read(os.path.join(self.repo, paths["check-docs-engine"]))),
                         shipped_all["0.21.0"]["check-docs-engine"])

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
        self.assertEqual(out["stampVersion"], "0.21.0")
        self.assertIn("scripts/check-docs.py", out["created"])
        refreshed = read(path)
        current = json.loads(read(SHAS))["0.21.0"]["check-docs-engine"]
        self.assertIn(f"# docaudit-template: check-docs-engine@0.21.0 sha256:{current}\n",
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
        self.assertEqual(out["stampVersion"], "0.21.0")
        self.assertIn("scripts/check-docs.py", out["created"])
        refreshed = read(path)
        current = json.loads(read(SHAS))["0.21.0"]["check-docs-engine"]
        self.assertIn(f"# docaudit-template: check-docs-engine@0.21.0 sha256:{current}\n",
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
                       "reason": "modified template body"},
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

    def test_refresh_keeps_current_body_with_old_version_stamp(self):
        module = load_module()
        initial = json.loads(run(self.repo, "--harness").stdout)
        version = initial["stampVersion"]
        rel = ".claude/commands/check-docs.md"
        path = os.path.join(self.repo, rel)
        old_version_stamp = read(path).replace(f"@{version} ", "@0.10.0 ", 1)
        write(self.repo, rel, old_version_stamp)
        before = binary_state(path)

        proc = run(self.repo, "--harness", "--refresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["created"], [])
        self.assertEqual(set(out["upToDate"]), {
            ".claude/commands/check-docs.md",
            ".claude/skills/doc-lint/SKILL.md",
            "scripts/check-docs.py",
        })
        self.assertIn({"path": rel, "reason": "up-to-date"}, out["skipReasons"])
        self.assertEqual(binary_state(path), before)
        shipped = json.loads(read(SHAS))
        classified = module.classify_harness_file(
            self.repo, rel, "check-docs", version, shipped)
        self.assertEqual(classified["class"], "current")

    def test_refresh_missing_files_are_created_and_dry_run_is_would_write(self):
        dry = run(self.repo, "--harness", "--refresh", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        dry_out = json.loads(dry.stdout)
        self.assertEqual(len(dry_out["created"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".claude")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "scripts")))

        actual = run(self.repo, "--harness", "--refresh")
        self.assertEqual(actual.returncode, 0, actual.stderr)
        actual_out = json.loads(actual.stdout)
        self.assertEqual(actual_out["created"], dry_out["created"])
        for rel in actual_out["created"]:
            self.assertTrue(os.path.isfile(os.path.join(self.repo, rel)))

    def test_check_stamps_classification_matrix_and_read_only_behavior(self):
        cases = (
            ("crlf", "current", "up-to-date"),
            ("modified", "not-refreshable", "modified"),
            ("missing-stamp", "not-refreshable", "missing"),
            ("duplicate-stamp", "not-refreshable", "unique"),
            ("duplicate-stamp-whitespace-markdown", "not-refreshable", "unique"),
            ("duplicate-stamp-whitespace-python", "not-refreshable", "unique"),
            ("front-matter-stamp", "not-refreshable", "canonical"),
            ("wrong-name", "not-refreshable", "destination"),
            ("markdown-python-stamp", "not-refreshable", "syntax"),
            ("python-html-stamp", "not-refreshable", "syntax"),
            ("symlink", "not-refreshable", "symlink"),
            ("parent-symlink", "not-refreshable", "symlink"),
            ("non-utf8", "not-refreshable", "UTF-8"),
            ("too-large", "not-refreshable", "byte limit"),
            ("missing", "missing", "does not exist"),
        )
        for case, expected_class, detail in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as repo:
                created = run(repo, "--harness")
                self.assertEqual(created.returncode, 0, created.stderr)
                rel = ".claude/commands/check-docs.md"
                path = os.path.join(repo, rel)
                if case == "crlf":
                    with open(path, "rb") as handle:
                        raw = handle.read().replace(b"\n", b"\r\n")
                    with open(path, "wb") as handle:
                        handle.write(raw)
                elif case == "modified":
                    write(repo, rel, read(path) + "local edit\n")
                elif case == "missing-stamp":
                    write(repo, rel, "\n".join(
                        line for line in read(path).splitlines()
                        if "docaudit-template:" not in line) + "\n")
                elif case == "duplicate-stamp":
                    lines = read(path).splitlines(keepends=True)
                    stamp = next(line for line in lines if "docaudit-template:" in line)
                    index = lines.index(stamp)
                    lines.insert(index + 1, stamp)
                    write(repo, rel, "".join(lines))
                elif case == "duplicate-stamp-whitespace-markdown":
                    text = read(path)
                    stamp = next(line for line in text.splitlines()
                                 if "docaudit-template:" in line)
                    variant = stamp.replace(
                        "<!-- docaudit-template:", "<!--   docaudit-template:", 1)
                    write(repo, rel, text + variant + "\n")
                elif case == "duplicate-stamp-whitespace-python":
                    rel = "scripts/check-docs.py"
                    path = os.path.join(repo, rel)
                    text = read(path)
                    stamp = next(line for line in text.splitlines()
                                 if "docaudit-template:" in line)
                    variant = stamp.replace("# docaudit-template:",
                                            "#docaudit-template:", 1)
                    write(repo, rel, text + variant + "\n")
                elif case == "front-matter-stamp":
                    lines = read(path).splitlines(keepends=True)
                    index = next(i for i, line in enumerate(lines)
                                 if "docaudit-template:" in line)
                    stamp = lines.pop(index)
                    closing = lines.index("---\n", 1)
                    lines.insert(closing, stamp)
                    write(repo, rel, "".join(lines))
                elif case == "wrong-name":
                    write(repo, rel, read(path).replace(
                        "docaudit-template: check-docs@",
                        "docaudit-template: other@", 1))
                elif case == "markdown-python-stamp":
                    write(repo, rel, read(path).replace(
                        "<!-- docaudit-template:",
                        "# docaudit-template:", 1).replace(" -->", "", 1))
                elif case == "python-html-stamp":
                    rel = "scripts/check-docs.py"
                    path = os.path.join(repo, rel)
                    text = read(path)
                    line = next(line for line in text.splitlines()
                                if "docaudit-template:" in line)
                    write(repo, rel, text.replace(line, f"<!-- {line[2:]} -->", 1))
                elif case == "symlink":
                    other = write(repo, "other.md", read(path))
                    os.unlink(path)
                    os.symlink(other, path)
                elif case == "parent-symlink":
                    rel = "scripts/check-docs.py"
                    path = os.path.join(repo, rel)
                    moved = os.path.join(repo, "saved-scripts")
                    os.rename(os.path.join(repo, "scripts"), moved)
                    os.symlink(moved, os.path.join(repo, "scripts"))
                elif case == "non-utf8":
                    with open(path, "wb") as handle:
                        handle.write(b"\xff\xfe")
                elif case == "too-large":
                    with open(path, "ab") as handle:
                        handle.write(b"x" * (1024 * 1024 + 1))
                elif case == "missing":
                    os.unlink(path)

                before = {candidate: binary_state(os.path.join(repo, candidate))
                          for candidate in (
                              ".claude/commands/check-docs.md",
                              ".claude/skills/doc-lint/SKILL.md",
                              "scripts/check-docs.py",
                          )}
                checked = run(repo, "--harness", "--check-stamps")
                self.assertEqual(checked.returncode, 0, checked.stderr)
                out = json.loads(checked.stdout)
                item = next(item for item in out["files"] if item["path"] == rel)
                self.assertEqual(item["class"], expected_class)
                self.assertIn(detail, item["detail"])
                self.assertEqual(out["eligible"], case == "crlf")
                after = {candidate: binary_state(os.path.join(repo, candidate))
                         for candidate in before}
                self.assertEqual(after, before)
                if case == "duplicate-stamp-whitespace-markdown":
                    refreshed = run(repo, "--harness", "--refresh")
                    self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
                    self.assertIn(rel, json.loads(refreshed.stdout)["skipped"])
                    self.assertEqual(binary_state(path), before[rel])

    def test_check_stamps_option_exclusions(self):
        combinations = (
            ("--check-stamps",),
            ("--harness", "--check-stamps", "--refresh"),
            ("--harness", "--check-stamps", "--scaffold"),
            ("--harness", "--check-stamps", "--dry-run"),
        )
        for arguments in combinations:
            with self.subTest(arguments=arguments):
                proc = run(self.repo, *arguments)
                self.assertEqual(proc.returncode, 2)

    def test_check_stamps_rejects_missing_current_engine_shas_entry(self):
        module = load_module()
        plugin = write(self.repo, "plugin.json", json.dumps({"version": "9.9.9"}))
        shas = write(self.repo, "engine-shas.json", "{}")
        stderr = io.StringIO()
        stdout = io.StringIO()
        arguments = [SCRIPT, "--repo-root", self.repo, "--harness", "--check-stamps"]
        with mock.patch.object(module, "PLUGIN_JSON", plugin), \
                mock.patch.object(module, "ENGINE_SHAS", shas), \
                mock.patch.object(sys, "argv", arguments), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = module.main()
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("no entry for plugin version 9.9.9", stderr.getvalue())

    def test_classify_harness_file_four_classes_are_exclusive(self):
        module = load_module()
        name = "check-docs"
        rel = ".claude/commands/check-docs.md"
        current_body = module.CHECK_DOCS_TEMPLATE
        old_body = current_body + "historical body\n"
        unknown_body = current_body + "unknown body\n"
        current_sha = module._normalized_sha(current_body)
        old_sha = module._normalized_sha(old_body)
        unknown_sha = module._normalized_sha(unknown_body)
        shipped = {
            "current": {name: current_sha},
            "old": {name: old_sha},
        }
        fixtures = (
            ("missing", None),
            ("current", module._markdown_with_stamp(
                current_body, name, "tampered-version", current_sha)),
            ("refreshable", module._markdown_with_stamp(
                old_body, name, "unrelated-version", old_sha)),
            ("not-refreshable", module._markdown_with_stamp(
                unknown_body, name, "current", unknown_sha)),
        )
        observed = []
        for expected, content in fixtures:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as repo:
                if content is not None:
                    write(repo, rel, content)
                result = module.classify_harness_file(
                    repo, rel, name, "current", shipped)
                self.assertEqual(result["class"], expected)
                self.assertEqual(set(result), {"path", "class", "detail"})
                observed.append(result["class"])
        self.assertEqual(set(observed), {
            "missing", "current", "refreshable", "not-refreshable"})
        self.assertEqual(len(observed), len(set(observed)))

    def test_refresh_dry_run_and_check_stamps_all_call_classifier(self):
        module = load_module()
        invocations = (
            ("--harness", "--refresh"),
            ("--harness", "--refresh", "--dry-run"),
            ("--harness", "--check-stamps"),
        )
        for arguments in invocations:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as repo:
                argv = [SCRIPT, "--repo-root", repo, *arguments]
                def forced_current(_repo_root, rel, _name, _version, _shipped):
                    return {"path": rel, "class": "current", "detail": "sentinel"}

                stdout = io.StringIO()
                with mock.patch.object(
                        module, "classify_harness_file",
                        side_effect=forced_current) as classify, \
                        mock.patch.object(sys, "argv", argv), \
                        contextlib.redirect_stdout(stdout), \
                        contextlib.redirect_stderr(io.StringIO()):
                    result = module.main()
                self.assertEqual(result, 0)
                self.assertEqual(classify.call_count, 3)
                out = json.loads(stdout.getvalue())
                if "--check-stamps" in arguments:
                    self.assertIs(out["eligible"], True)
                    self.assertEqual(
                        {(item["class"], item["detail"]) for item in out["files"]},
                        {("current", "sentinel")})
                else:
                    self.assertEqual(out["created"], [])
                    self.assertEqual(len(out["upToDate"]), 3)
                    self.assertFalse(os.path.exists(os.path.join(repo, ".claude")))
                    self.assertFalse(os.path.exists(os.path.join(repo, "scripts")))

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
        self.assertEqual(version, "0.21.0")
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
