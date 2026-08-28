"""Contracts for the S1a portion of docaudit v0.13.2."""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_SCOPE = os.path.join(ROOT, "skills", "audit", "scripts", "fix-scope.py")
SHARED_DOC_GLOBS = ["docs/**/*.md", "*.md"]


def read_repo_file(relative):
    with open(os.path.join(ROOT, *relative.split("/")), encoding="utf-8") as handle:
        return handle.read()


class TestFixScopeDefaults(unittest.TestCase):
    def run_fix_scope(self, config, paths):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = temp.name
        for relative in paths:
            target = os.path.join(root, *relative.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8"):
                pass
        config_path = os.path.join(root, "doc-audit.json")
        paths_path = os.path.join(root, "paths.txt")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        with open(paths_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(paths) + "\n")
        proc = subprocess.run(
            [sys.executable, FIX_SCOPE, "--repo-root", root, "--config", config_path,
             "--paths", paths_path],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_omitted_doc_globs_uses_shared_default_and_denies_agent_files(self):
        """DoD (2): omission uses shared globs while built-in denies win."""
        paths = [
            "docs/a.md", "README.md", "SECURITY.md", "src/app.py", "docs/logs/x.md",
            "AGENTS.md", "CLAUDE.md", "docs/CLAUDE.md",
        ]
        out = self.run_fix_scope({}, paths)
        self.assertEqual(out["allowed"], ["README.md", "SECURITY.md", "docs/a.md"])
        denied = {item["path"]: item["reason"] for item in out["denied"]}
        self.assertEqual(denied, {
            "src/app.py": "path does not match docGlobs",
            "docs/logs/x.md": "built-in protected path",
            "AGENTS.md": "agent instruction file",
            "CLAUDE.md": "agent instruction file",
            "docs/CLAUDE.md": "agent instruction file",
        })

    def test_explicit_doc_globs_still_denies_agent_files(self):
        """DoD (2): explicit broad globs cannot bypass case-insensitive basename deny."""
        first = self.run_fix_scope(
            {"docGlobs": ["**/*.md"]},
            ["AGENTS.md", "docs/CLAUDE.md", "docs/a.md"],
        )
        self.assertEqual(first["allowed"], ["docs/a.md"])
        self.assertEqual(
            {item["path"]: item["reason"] for item in first["denied"]},
            {"AGENTS.md": "agent instruction file",
             "docs/CLAUDE.md": "agent instruction file"},
        )
        second = self.run_fix_scope(
            {"docGlobs": ["**/*.md"]}, ["docs/claude.md"])
        self.assertEqual(second["allowed"], [])
        self.assertEqual(second["denied"], [
            {"path": "docs/claude.md", "reason": "agent instruction file"},
        ])

    def test_doc_globs_default_is_shared_across_eleven_call_sites(self):
        """DoD (3): seven known consumers expose exactly eleven shared literal defaults."""
        targets = [
            "skills/audit/scripts/resolve-impact.py",
            "skills/audit/scripts/start-run.py",
            "skills/audit/scripts/generic-layers.py",
            "skills/audit/scripts/change-set-sha.py",
            "skills/audit/scripts/impact-supplement.py",
            "skills/audit/scripts/import-audit-scope.py",
            "skills/audit/scripts/fix-scope.py",
        ]
        found = []
        for relative in targets:
            tree = ast.parse(read_repo_file(relative), filename=relative)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get"
                        and len(node.args) >= 2
                        and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == "docGlobs"):
                    continue
                try:
                    default = ast.literal_eval(node.args[1])
                except (ValueError, TypeError):
                    continue
                self.assertEqual(default, SHARED_DOC_GLOBS, relative)
                found.append(relative)
        # Expected distribution: resolve/start/generic/import=2 each; change/impact/fix=1 each.
        self.assertEqual(len(found), 11)
        self.assertEqual(set(found), set(targets))


class TestV0132S1aContracts(unittest.TestCase):
    def test_builtin_deny_documented_in_five_places(self):
        """DoD (4): all five built-in deny descriptions name both agent files and casing."""
        schema = read_repo_file("skills/audit/references/config-schema.md")
        skill = read_repo_file("skills/audit/SKILL.md")
        adoption = read_repo_file("docs/ADOPTION.md")
        adoption_ja = read_repo_file("docs/ADOPTION.ja.md")
        schema_row = next(line for line in schema.splitlines()
                          if line.startswith("| `protectedGlobs` |"))
        schema_preflight = schema.split("### Pre-flight, cache, and run class", 1)[1].split("\n### ", 1)[0]
        phase05 = skill.split("## Phase 0.5", 1)[1].split("\n## Phase 1", 1)[0]
        adoption_row = next(line for line in adoption.splitlines()
                            if line.startswith("| `protectedGlobs` |"))
        adoption_ja_row = next(line for line in adoption_ja.splitlines()
                               if line.startswith("| `protectedGlobs` |"))
        places = [schema_row, schema_preflight, phase05, adoption_row, adoption_ja_row]
        self.assertEqual(len(places), 5)
        for index, place in enumerate(places):
            with self.subTest(place=index):
                self.assertIn("CLAUDE.md", place)
                self.assertIn("AGENTS.md", place)
                self.assertTrue(
                    "case-insensitive" in place
                    or "case-insensitively" in place
                    or "大文字小文字を区別しない" in place,
                    place,
                )

    def test_doc_globs_rows_no_longer_say_fail_closed(self):
        """DoD (4): schema and adoption rows describe one shared pre-flight default."""
        for relative in (
                "skills/audit/references/config-schema.md",
                "docs/ADOPTION.md",
                "docs/ADOPTION.ja.md"):
            row = next(line for line in read_repo_file(relative).splitlines()
                       if line.startswith("| `docGlobs` |"))
            normalized = row.lower().replace("-", ".")
            self.assertNotIn("fail.closed", normalized, relative)
            self.assertNotIn("rejects every path", normalized, relative)
            self.assertNotIn("全パスを拒否", row, relative)
            self.assertIn("pre-flight fix", row, relative)
            self.assertTrue("same default" in row or "同じ既定" in row, row)

    def test_phase3_three_stop_branches_release_the_run(self):
        """DoD (5): all three seal/read stop branches fully release the active run."""
        skill = read_repo_file("skills/audit/SKILL.md")
        phase3 = skill.split("## Phase 3", 1)[1].split("\n## ", 1)[0]
        lines = phase3.splitlines()
        fixed_phrases = [
            "Exit 5 means",
            "Any other non-zero exit",
            "If `read-manifest.py` fails",
        ]
        for phrase in fixed_phrases:
            start = next(i for i, line in enumerate(lines) if phrase in line)
            nearby = lines[start:start + 4]
            release = next((line for line in nearby if '--release --runid "$RUNID"' in line), None)
            self.assertIsNotNone(release, phrase)
            for required in (
                    '--run-base "$RUN_BASE"',
                    '--repo-root "$CLAUDE_PROJECT_DIR"',
                    '--anchor-path "$ANCHOR_PATH"'):
                self.assertIn(required, release)
        self.assertGreaterEqual(phase3.count('--release --runid "$RUNID"'), 3)
        other_start = phase3.index("Any other non-zero exit")
        other_end = phase3.index("Immediately verify", other_start)
        other_branch = phase3[other_start:other_end]
        self.assertIn("without calling `read-manifest.py`", other_branch)
        self.assertIn("do not launch either verifier backend", other_branch)
        self.assertIn("`seal-run:` stderr", other_branch)


if __name__ == "__main__":
    unittest.main()
