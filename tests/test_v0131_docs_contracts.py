"""Contracts for the v0.13.1 documentation release."""

import ast
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {".claude/state", ".claude/worktrees", ".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}
DOCS = (("skills/audit/references/config-schema.md", "Accepted `digestExclude` prefixes:", "the run is not sealed"),
        ("docs/ADOPTION.md", "Accepted `digestExclude` prefixes:", "the run is not sealed"),
        ("docs/ADOPTION.ja.md", "`digestExclude` で受理されるプレフィックス:", "run は seal されない"))


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def fences(text):
    return re.findall(r"```[^\n]*\n(.*?)```", text, re.S)


class TestV0131DocsContracts(unittest.TestCase):
    def test_a_digest_exclude_contract(self):
        spec = importlib.util.spec_from_file_location("tree_digest", ROOT / "skills/audit/scripts/tree-digest.py")
        tree_digest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tree_digest)
        for path, marker, unsealed in DOCS:
            lines = [line for line in read(path).splitlines() if marker in line]
            self.assertEqual(len(lines), 1, f"{path}: marker lines={len(lines)}")
            cell = lines[0].split(marker, 1)[1].split("|", 1)[0]
            values = re.findall(r"`([^`]+)`", cell)
            self.assertEqual(len(values), 6, f"{path}: extracted prefixes={len(values)}")
            self.assertEqual(len(set(values)), 6, f"{path}: distinct prefixes={len(set(values))}")
            self.assertEqual(set(values), EXPECTED, f"{path}: prefixes={values}")
            for value in values:
                tree_digest.normalize(value)
            for bad in (".claude/state/**", ".claude/worktrees/*"):
                with self.assertRaises(ValueError, msg=f"{path}: rejected glob={bad}"):
                    tree_digest.normalize(bad)
            for term in ("tree-digest.py", "seal-run.py", "exit 2", unsealed):
                self.assertIn(term, lines[0], f"{path}: contract term={term!r}, marker lines={len(lines)}")

    def test_b_generic_layers_commands_always_use_config(self):
        lines = [line for line in read("skills/audit/SKILL.md").splitlines() if "generic-layers.py" in line]
        self.assertGreaterEqual(len(lines), 3, f"generic-layers.py lines={len(lines)}")
        self.assertTrue(all("--config" in line for line in lines), f"generic-layers.py lines={len(lines)}")

    def test_c_appendix_file_map_matches_files(self):
        actual = {str(path.relative_to(ROOT)) for directory in (ROOT / "skills/audit/scripts", ROOT / "skills/audit/references")
                  for path in directory.iterdir() if path.is_file() and path.suffix != ".pyc" and path.name != "__pycache__"}
        self.assertEqual(len(actual), 43, f"implementation paths={len(actual)}")
        for doc in ("docs/ADOPTION.md", "docs/ADOPTION.ja.md"):
            appendix = [block for block in fences(read(doc)) if "├── skills/audit/scripts/" in block]
            self.assertEqual(len(appendix), 1, f"{doc}: appendix fences={len(appendix)}")
            documented = set(re.findall(r"(skills/audit/(?:scripts|references)/[^\s`]+)", appendix[0]))
            self.assertTrue(documented, f"{doc}: documented paths={len(documented)}")
            self.assertFalse(actual - documented, f"{doc}: missing paths={sorted(actual - documented)}")
            self.assertFalse(documented - actual, f"{doc}: extra paths={sorted(documented - actual)}")

    def test_d_readme_mode_flags_match_each_skill(self):
        modes_section = read("README.md").split("## Modes", 1)[1]
        modes = {name: next(line for line in modes_section.splitlines() if line.lstrip().startswith(f"/docaudit:{name}"))
                 for name in ("audit", "init")}
        self.assertEqual(len(modes), 2, f"README mode lines={len(modes)}")
        for mode, skill in (("audit", "skills/audit/SKILL.md"), ("init", "skills/init/SKILL.md")):
            frontmatter = read(skill).split("---", 2)[1]
            expected = set(re.findall(r"--[\w-]+", next(line for line in frontmatter.splitlines() if line.startswith("argument-hint:"))))
            actual = set(re.findall(r"--[\w-]+", modes[mode]))
            self.assertTrue(expected, f"{mode}: skill flags={len(expected)}")
            self.assertEqual(actual, expected, f"{mode}: README flags={len(actual)}, skill flags={len(expected)}")

    def test_f_example_matches_schema_and_fixed_defaults(self):
        example = json.loads(read("docs/examples/doc-audit.example.json"))
        keys = set(example) - {"_note"}
        table = read("skills/audit/references/config-schema.md").split("| key | type | required | meaning |", 1)[1].split("\n\n", 1)[0]
        schema = set(re.findall(r"^\| `([^`]+)` \|", table, re.M))
        self.assertEqual(len(schema), 32, f"schema keys={len(schema)}")
        self.assertTrue(keys, f"example keys={len(keys)}")
        self.assertTrue(keys <= schema, f"example keys={len(keys)}, schema keys={len(schema)}, extra={sorted(keys - schema)}")
        self.assertEqual(example["phase3Backend"], "workflow")
        self.assertEqual(example["regressionRecheck"], {"enabled": False})
        self.assertEqual(example["codexReview"], {"enabled": True, "bin": "codex", "required": False})
        self.assertEqual(example["models"], {"light": {"enabled": True, "maxChanged": 10, "maxImpacted": 15, "maxDiffLines": 200, "maxDiffBytes": 65536}})
        self.assertNotIn("auditScope", keys)

    def test_g_refresh_paragraph_versions(self):
        target = {"0.10.1", "0.11.0", "0." "12.0", "0.13.0", "0.13.1", json.loads(read(".claude-plugin/plugin.json"))["version"]}
        for path, needle in (("docs/ADOPTION.md", "templates can be updated directly to"), ("docs/ADOPTION.ja.md", "へ直接更新できる")):
            paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", read(path)) if needle in part]
            self.assertEqual(len(paragraphs), 1, f"{path}: refresh paragraphs={len(paragraphs)}")
            versions = set(re.findall(r"\b\d+\.\d+\.\d+\b", paragraphs[0]))
            self.assertEqual(versions, target, f"{path}: refresh versions={sorted(versions)}")

    def test_h_adoption_structures_stay_parallel(self):
        en, ja = read("docs/ADOPTION.md"), read("docs/ADOPTION.ja.md")
        def headings(text):
            outside = re.sub(r"```.*?```", "", text, flags=re.S)
            return re.findall(r"^(#+) ", outside, re.M)
        self.assertEqual(headings(en), headings(ja), f"heading counts={len(headings(en))}/{len(headings(ja))}")
        self.assertEqual(headings(en).count("##"), 15, f"level-two headings={headings(en).count('##')}")
        def section_keys(text):
            section = text.split("## 5.", 1)[1].split("## 6.", 1)[0]
            return re.findall(r"^\| `([^`]+)` \|", section, re.M)
        en_keys, ja_keys = section_keys(en), section_keys(ja)
        self.assertEqual(en_keys, ja_keys, f"section-5 keys={len(en_keys)}/{len(ja_keys)}")
        self.assertEqual(len(en_keys), 26, f"section-5 keys={len(en_keys)}")
        self.assertTrue({"layerGlobs", "frontMatterOverrides", "auditReportsInCorpus"} <= set(en_keys), f"section-5 keys={len(en_keys)}")
        en_tree = [line for block in fences(en) for line in block.splitlines() if "├" in line or "└" in line]
        ja_tree = [line for block in fences(ja) for line in block.splitlines() if "├" in line or "└" in line]
        self.assertEqual(en_tree, ja_tree, f"tree lines={len(en_tree)}/{len(ja_tree)}")
        self.assertEqual(len(en_tree), 52, f"tree lines={len(en_tree)}")

    def test_i_severity_documentation_matches_python(self):
        tree = ast.parse(read("skills/audit/scripts/decide-verdict.py"))
        fails = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "FAIL_SEVERITIES" for target in node.targets) and isinstance(node.value, ast.Set)]
        nonblocking = [node.comparators[0] for node in ast.walk(tree) if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "severity" and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn) and isinstance(node.comparators[0], ast.Set)]
        self.assertEqual(len(fails), 1, f"FAIL_SEVERITIES sets={len(fails)}")
        self.assertEqual(len(nonblocking), 1, f"severity NotIn sets={len(nonblocking)}")
        fail_values = {item.value for item in fails[0].elts}
        nonblocking_values = {item.value for item in nonblocking[0].elts}
        self.assertEqual(len(fail_values), 3, f"FAIL_SEVERITIES values={len(fail_values)}")
        self.assertEqual(len(nonblocking_values), 5, f"severity NotIn values={len(nonblocking_values)}")
        for path, header, catchall in (("docs/ADOPTION.md", "| severity | gate effect |", "any other value"), ("docs/ADOPTION.ja.md", "| severity | gate への効果 |", "上記以外の値")):
            lines = read(path).splitlines(); starts = [i for i, line in enumerate(lines) if line == header]
            self.assertEqual(len(starts), 1, f"{path}: severity tables={len(starts)}")
            table = []
            for line in lines[starts[0] + 2:]:
                if not line.startswith("|"):
                    break
                table.append(line)
            self.assertEqual(len(table), 9, f"{path}: severity data rows={len(table)}")
            rows = [([part.strip() for part in line.split("|")[1:-1]]) for line in table]
            severities = [re.findall(r"`([^`]+)`", row[0]) for row in rows if row[0] != catchall]
            flat = [value for group in severities for value in group]
            self.assertEqual(len(flat), 8, f"{path}: severity values={len(flat)}")
            self.assertEqual(len(set(flat)), 8, f"{path}: distinct severity values={len(set(flat))}")
            mapping = {re.findall(r"`([^`]+)`", row[0])[0]: re.match(r"`([^`]+)`", row[1]).group(1) for row in rows if row[0] != catchall}
            catch = [row for row in rows if row[0] == catchall]
            self.assertEqual(len(catch), 1, f"{path}: catch-all rows={len(catch)}")
            self.assertIn("unknown finding severity", catch[0][1])
            self.assertEqual(re.match(r"`([^`]+)`", catch[0][1]).group(1), "REFUSED")
            self.assertEqual({key for key, value in mapping.items() if value == "blocking"}, fail_values)
            self.assertEqual({key for key, value in mapping.items() if value == "non-blocking"}, nonblocking_values)
