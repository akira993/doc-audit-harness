"""Contracts for the S1a portion of docaudit v0.13.2."""

import ast
import hashlib
import json
import os
import re
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
        with open(config_path, "rb") as handle:
            config_sha = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        with open(paths_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(paths) + "\n")
        proc = subprocess.run(
            [sys.executable, FIX_SCOPE, "--repo-root", root, "--config", config_path,
             "--expect-config-sha", config_sha, "--paths", paths_path],
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
    def test_v0132_behavior_changes_paragraph(self):
        """DoD (17): both §7 paragraphs preserve the five fixed behavior statements."""
        expected = {
            "docs/ADOPTION.md": (
                "v0.13.2 behavior changes:",
                (
                    'omitted docGlobs now defaults to ["docs/**/*.md","*.md"] for pre-flight fix classification; CLAUDE.md and AGENTS.md are always denied (case-insensitive)',
                    "an absent docGraph / semanticSearch / symbolGraph key reports not-configured and never runs the tool; an invalid key reports invalid-config",
                    "CocoIndex counts as initialized only when .cocoindex_code/settings.yml exists; a .gitignore change during ccc index reports gitignore-modified and is never reverted by the audit",
                    "any seal-run.py or read-manifest.py failure releases the run and stops; read-manifest.py rejects an unsealed manifest",
                    "configs that relied on auto-detection must add the key via /docaudit:init",
                ),
            ),
            "docs/ADOPTION.ja.md": (
                "v0.13.2 の挙動変更:",
                (
                    'docGlobs を省略した場合、pre-flight fix の分類は ["docs/**/*.md","*.md"] を既定とする。CLAUDE.md と AGENTS.md は大文字小文字を区別せず常に拒否される',
                    "docGraph / semanticSearch / symbolGraph のキーが無い場合は not-configured を報告し tool を一切起動しない。キーが不正な場合は invalid-config を報告する",
                    "CocoIndex は .cocoindex_code/settings.yml が存在する場合のみ初期化済みとみなす。ccc index の実行中に .gitignore が変化した場合は gitignore-modified を報告し、監査は復元しない",
                    "seal-run.py または read-manifest.py が失敗した場合は run を解放して停止する。read-manifest.py は未 seal の manifest を拒否する",
                    "自動検出に頼っていた config は /docaudit:init でキーを追加するまで not-configured になる",
                ),
            ),
        }
        for path, (heading, sentences) in expected.items():
            paragraphs = [part for part in re.split(r"\n\s*\n", read_repo_file(path)) if heading in part]
            self.assertEqual(len(paragraphs), 1, f"{path}: v0.13.2 paragraphs={len(paragraphs)}")
            normalized = " ".join(paragraphs[0].split()).replace("`", "")
            for sentence in sentences:
                self.assertIn(sentence, normalized)

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


class TestV0132S1bContracts(unittest.TestCase):
    def _phase0_block(self, start, end):
        skill = read_repo_file("skills/audit/SKILL.md")
        return skill.split(start, 1)[1].split(end, 1)[0]

    def test_probe_reason_enumerations_match_fixed_sets(self):
        """DoD (9): probe reason enumerations are complete and exact in both documents."""
        skill_blocks = {
            "webExtract": self._phase0_block("Then probe **ax**", "Then probe **codex**"),
            "codexReview": self._phase0_block("Then probe **codex**", "Then probe **codegraph**"),
            "symbolGraph": self._phase0_block("Then probe **codegraph**", "Then probe **graphify**"),
            "docGraph": self._phase0_block("Then probe **graphify**", "Then probe **CocoIndex**"),
            "semanticSearch": self._phase0_block("Then probe **CocoIndex**", "**Harness question"),
        }
        schema = read_repo_file("skills/audit/references/config-schema.md")
        schema_blocks = {
            "symbolGraph": schema.split("## codegraph", 1)[1].split("## graphify", 1)[0],
            "docGraph": schema.split("## graphify", 1)[1].split("## CocoIndex", 1)[0],
            "semanticSearch": schema.split("## CocoIndex", 1)[1].split("## Generic", 1)[0],
        }
        expected = {
            "webExtract": {"ok", "not-installed", "disabled-by-config", "not-configured", "invalid-config"},
            "codexReview": {"ok", "not-installed", "disabled-by-config", "probe-exec-failed", "not-configured", "invalid-config"},
            "symbolGraph": {"ok", "not-installed", "disabled-by-config", "index-failed", "not-configured", "invalid-config"},
            "docGraph": {"ok", "not-installed", "disabled-by-config", "update-failed", "not-configured", "invalid-config"},
            "semanticSearch": {"ok", "not-installed", "disabled-by-config", "not-initialized", "index-failed", "not-configured", "invalid-config", "gitignore-modified"},
        }
        for seam, reasons in expected.items():
            with self.subTest(document="skill", seam=seam):
                listed = re.search(r"\(`reason` ∈\s*([^)]*)\)\.?\s*Bind",
                                   skill_blocks[seam])
                self.assertIsNotNone(listed)
                self.assertEqual(set(re.findall(r"`([a-z-]+)`", listed.group(1))), reasons)
            if seam in schema_blocks:
                with self.subTest(document="schema", seam=seam):
                    self.assertEqual(set(re.findall(r"`([a-z-]+)`", schema_blocks[seam].split("Its probe reasons are", 1)[1])), reasons)

    def test_phase5_status_lines_map_each_reason_to_one_branch(self):
        """DoD (10): every Phase-5 reason has one exclusive user-facing branch."""
        skill = read_repo_file("skills/audit/SKILL.md")
        blocks = {
            "symbol-graph": skill.split("**symbol-graph status line**", 1)[1].split("**doc-graph status line**", 1)[0],
            "doc-graph": skill.split("**doc-graph status line**", 1)[1].split("**semanticSearch status line**", 1)[0],
            "semanticSearch": skill.split("**semanticSearch status line**", 1)[1].split("**harness status line**", 1)[0],
        }
        expected_counts = {"symbol-graph": "6-state", "doc-graph": "6-state (7 messages)", "semanticSearch": "8-state"}
        required = {
            "symbol-graph": {"not-configured": ("💡", "not configured"), "invalid-config": ("⚠", "is invalid"), "not-installed": ("💡", "install:"), "disabled-by-config": ("💡", "disabled"), "index-failed": ("⚠", "failed"), "ok": ("✓ symbol-graph: active (", "")},
            "doc-graph": {"not-configured": ("💡", "not configured"), "invalid-config": ("⚠", "is invalid"), "not-installed": ("💡", "install:"), "disabled-by-config": ("💡", "disabled"), "update-failed": ("⚠", "failed"), "ok": ("✓ doc-graph: active (", "")},
            "semanticSearch": {"not-configured": ("💡", "not configured"), "invalid-config": ("⚠", "is invalid"), "not-installed": ("💡", "install:"), "disabled-by-config": ("💡", "disabled"), "not-initialized": ("💡", "isn't indexed yet"), "index-failed": ("⚠", "failed"), "gitignore-modified": ("⚠", "changed while ccc index ran"), "ok": ("✓ semanticSearch: active (", "")},
        }
        for seam, mapping in required.items():
            with self.subTest(seam=seam):
                block = blocks[seam]
                self.assertIn(expected_counts[seam], block)
                lines = [line for line in block.splitlines() if line.startswith("- `") and "→" in line]
                for reason, (glyph, phrase) in mapping.items():
                    matches = [line for line in lines if reason in line.split("→", 1)[0]]
                    self.assertEqual(len(matches), 2 if seam == "doc-graph" and reason == "ok" else 1, reason)
                    for line in matches:
                        right = line.split("→", 1)[1]
                        if seam == "doc-graph" and reason == "ok" and "active but" in right:
                            self.assertIn("⚠ doc-graph: active but", right)
                        else:
                            self.assertIn(glyph, right)
                        if phrase:
                            self.assertIn(phrase, right)
                self.assertNotIn("AVAILABLE` false", block)
        self.assertNotIn("install:", next(line for line in blocks["doc-graph"].splitlines() if "not-configured" in line).split("→", 1)[1])
        self.assertNotIn("installed", next(line for line in blocks["semanticSearch"].splitlines() if "not-configured" in line).split("→", 1)[1])
        self.assertIn("⚠ doc-graph: active but", blocks["doc-graph"])

    def test_phase0_binds_reason_from_each_probe_json(self):
        """DoD (10b): each Phase-0 reason is read from its matching saved probe JSON."""
        skill = read_repo_file("skills/audit/SKILL.md")
        for variable, script in (("SYMBOL_GRAPH", "codegraph-probe.sh"), ("DOC_GRAPH", "graphify-probe.sh"), ("SEMANTIC_SEARCH", "cocoindex-probe.sh")):
            with self.subTest(variable=variable):
                self.assertIn(f'{variable}_PROBE_JSON="$(bash "$SD/scripts/{script}"', skill)
                match = re.search(rf'{variable}_REASON=.*?\["reason"\].*?"\${variable}_PROBE_JSON"', skill)
                self.assertIsNotNone(match)

    def test_init_skill_marks_five_omit_rules_as_not_configured(self):
        """DoD (11): all five key-gated OMIT rules name not-configured."""
        init = read_repo_file("skills/init/SKILL.md")
        self.assertEqual(init.count("not-configured"), 5)
        documented = set()
        for paragraph in re.split(r"\n\s*\n", init):
            if "not-configured" in paragraph:
                seams = set(re.findall(
                    r"webExtract|codexReview|symbolGraph|docGraph|semanticSearch",
                    paragraph,
                ))
                self.assertTrue(seams, paragraph)
                documented.update(seams)
        self.assertEqual(documented, {
            "webExtract", "codexReview", "symbolGraph", "docGraph",
            "semanticSearch",
        })

    def test_settings_yml_marker_documented_in_five_files(self):
        """DoD (14): all five documents tie not-initialized to settings.yml."""
        files = ("skills/audit/SKILL.md", "skills/init/SKILL.md", "skills/audit/references/config-schema.md", "docs/ADOPTION.md", "docs/ADOPTION.ja.md")
        for relative in files:
            with self.subTest(relative=relative):
                text = read_repo_file(relative)
                self.assertIn(".cocoindex_code/settings.yml", text)
                self.assertTrue(any(".cocoindex_code/settings.yml" in paragraph and "not-initialized" in paragraph
                                    for paragraph in re.split(r"\n\s*\n", text)), relative)
                self.assertIsNone(re.search(r"\.cocoindex_code/`?\s+(?:already exists|不在|present)(?![^\n]*settings\.yml)", text), relative)

    def test_three_seams_no_longer_documented_as_auto_used(self):
        """§0-4 B1: the three worktree-writing seams are documented as key-gated."""
        terms = ("symbolGraph", "docGraph", "semanticSearch", "codegraph", "graphify", "CocoIndex", "ccc")
        forbidden = ("conditional-force", "auto-used when installed", "導入済みなら自動使用")
        for relative in ("skills/audit/references/config-schema.md", "docs/ADOPTION.md", "docs/ADOPTION.ja.md", "skills/init/SKILL.md"):
            text = read_repo_file(relative)
            paragraphs = []
            for paragraph in re.split(r"\n\s*\n", text):
                if paragraph.lstrip().startswith("|"):
                    paragraphs.extend(paragraph.splitlines())
                elif "\n- " in paragraph:
                    paragraphs.extend(paragraph.split("\n- "))
                else:
                    paragraphs.append(paragraph)
            for paragraph in paragraphs:
                normalized = " ".join(paragraph.split())
                if any(term in normalized for term in terms):
                    self.assertFalse(any(term in normalized for term in forbidden), (relative, normalized))

    def test_semantic_search_schema_describes_probe_validation_and_phase2_min_score(self):
        """DoD (12): schema assigns minScore validation to the probe and use to Phase 2."""
        schema = read_repo_file("skills/audit/references/config-schema.md")
        row = next(line for line in schema.splitlines() if line.startswith("| `semanticSearch` |"))
        self.assertIn("the probe validates `enabled`/`bin`/`minScore`; Phase 2 uses `minScore`", row)


if __name__ == "__main__":
    unittest.main()
