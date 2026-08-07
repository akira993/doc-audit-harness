"""Tests for the Phase-3 Workflow template and its verdict persistence command."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "skills" / "audit" / "references" / "workflow-template.js"
WRITE_VERDICT = ROOT / "skills" / "audit" / "scripts" / "write-verdict.py"
TEMPLATE_ENV = "DOCAUDIT_WORKFLOW_TEMPLATE"
HELPERS_BEGIN = "// BEGIN PERSIST HELPERS"
HELPERS_END = "// END PERSIST HELPERS"
TERMINATION_WARNING = (
    "Calling the structured-output tool ends this run immediately. Complete STEP A first.\n"
    "No steps execute after STEP B."
)


def template_path():
    return Path(os.environ.get(TEMPLATE_ENV, DEFAULT_TEMPLATE))


def read_template():
    return template_path().read_text(encoding="utf-8")


def extract_helpers(source):
    """Return the marked pure-helper source without brace-counting regexes."""
    start = source.index(HELPERS_BEGIN)
    end = source.index(HELPERS_END, start)
    return source[start:end]


class TestWorkflowTemplate(unittest.TestCase):
    def setUp(self):
        # Node is required for this test; absence is a failure, never a silent skip.
        found = subprocess.run(
            ["/bin/sh", "-c", "command -v node"],
            capture_output=True,
            text=True,
        )
        if found.returncode != 0 or not found.stdout.strip():
            self.fail(
                "Node.js is required to parse and execute workflow-template.js, "
                "but `command -v node` could not find it"
            )
        self.node = found.stdout.strip().splitlines()[-1]
        self.source = read_template()

    def run_node(self, program, env=None):
        proc = subprocess.run(
            [self.node, "-e", program],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def build_persist_cmd(self, scripts_dir, run_dir, run_id, doc_path):
        helpers = extract_helpers(self.source)
        program = helpers + """
const values = JSON.parse(process.env.DOCAUDIT_TEST_VALUES)
process.stdout.write(buildPersistCmd(values[0], values[1], values[2], values[3]))
"""
        env = os.environ.copy()
        env["DOCAUDIT_TEST_VALUES"] = json.dumps(
            [str(scripts_dir), str(run_dir), run_id, doc_path]
        )
        return self.run_node(program, env=env)

    @staticmethod
    def render_command(command, verdict, rationale):
        if not rationale.endswith("\n"):
            raise AssertionError("test rationale must include its exact final newline")
        command = command.replace("<PASS|WARN|FAIL>", verdict, 1)
        return command.replace("<rationale>\n", rationale, 1)

    def test_parses_as_async_function_body(self):
        # The DSL has top-level await/return, so plain `node --check` is incorrect.
        source = self.source.replace("export ", "", 1)
        program = """
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
new AsyncFunction(process.env.DOCAUDIT_TEMPLATE_SOURCE)
"""
        env = os.environ.copy()
        env["DOCAUDIT_TEMPLATE_SOURCE"] = source
        self.run_node(program, env=env)

    def test_static_invariants(self):
        self.assertTrue("STEP A" in self.source, "STEP A marker is missing")
        self.assertTrue("STEP B" in self.source, "STEP B marker is missing")
        step_a = self.source.index("STEP A")
        step_b = self.source.index("STEP B")
        self.assertLess(step_a, step_b)
        self.assertIn(TERMINATION_WARNING, self.source)
        self.assertIn("write-verdict.py", self.source)
        self.assertIn("DOCAUDIT_EOF_", self.source)
        self.assertIn(
            "${buildPersistCmd(scriptsDir, runDir, runId, d.path)}", self.source
        )
        self.assertIn("typeof a === 'string'", self.source)
        self.assertIn("JSON.parse(a)", self.source)
        self.assertIn("const scriptsDir = a.scriptsDir", self.source)
        self.assertIn("if (!runId || !runDir || !scriptsDir)", self.source)
        self.assertIn("agentType: 'docaudit:doc-impact-verifier'", self.source)

    def test_slug_is_injective_for_underscore_and_separator_and_bounded(self):
        helpers = extract_helpers(self.source)
        program = helpers + """
const values = JSON.parse(process.env.DOCAUDIT_TEST_VALUES)
process.stdout.write(JSON.stringify(values.map(slug)))
"""
        long_a = "docs/" + "a" * 220 + ".md"
        long_b = "docs/" + "a" * 219 + "b.md"
        env = os.environ.copy()
        env["DOCAUDIT_TEST_VALUES"] = json.dumps(
            ["a/b.md", "a__b.md", "a\\b.md", long_a, long_b, long_a]
        )
        values = json.loads(self.run_node(program, env=env))
        self.assertEqual(values[0], "a__b.md")
        self.assertEqual(values[1], "a_5f_5fb.md")
        self.assertEqual(values[2], "a__b.md")
        self.assertNotEqual(values[0], values[1])
        self.assertLessEqual(len(values[3]), 200)
        self.assertRegex(values[3], r"_[0-9a-f]{16}$")
        self.assertNotEqual(values[3], values[4])
        self.assertEqual(values[3], values[5])

    def test_generated_command_resists_shell_metacharacters(self):
        self.assertTrue(WRITE_VERDICT.is_file(), f"missing helper: {WRITE_VERDICT}")
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            scripts_dir = temp_path / "scripts dir's"
            scripts_dir.mkdir()
            shutil.copy2(WRITE_VERDICT, scripts_dir / "write-verdict.py")
            run_dir = temp_path / "run dir's"
            (run_dir / "verdicts").mkdir(parents=True)
            doc_path = "docs/$(touch PWNED).md"
            rationale = (
                "literal $(touch RATIONALE_PWNED) and quotes ' \"\n"
                "EOF\n"
                "final line\n"
            )
            command = self.build_persist_cmd(
                scripts_dir, run_dir, "run-adversarial", doc_path
            )
            command = self.render_command(command, "WARN", rationale)

            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            files = list((run_dir / "verdicts").glob("*.json"))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["path"], doc_path)
            self.assertEqual(record["verdict"], "WARN")
            self.assertEqual(record["rationale"], rationale)
            self.assertEqual(json.loads(proc.stdout), record)
            self.assertFalse((temp_path / "PWNED").exists())
            self.assertFalse((temp_path / "RATIONALE_PWNED").exists())

    def test_run_delimiter_self_injection_leaves_valid_truncated_json(self):
        # A doc cannot know the future RUNID. Supplying this exact delimiter is an
        # agent self-injection, in the same trust class as residual risk 1.
        self.assertTrue(WRITE_VERDICT.is_file(), f"missing helper: {WRITE_VERDICT}")
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            scripts_dir = temp_path / "scripts"
            scripts_dir.mkdir()
            shutil.copy2(WRITE_VERDICT, scripts_dir / "write-verdict.py")
            run_dir = temp_path / "run"
            (run_dir / "verdicts").mkdir(parents=True)
            run_id = "run-self-injection"
            delimiter = f"DOCAUDIT_EOF_{run_id}"
            rationale = f"kept before delimiter\n{delimiter}\n# harmless tail\n"
            command = self.build_persist_cmd(
                scripts_dir, run_dir, run_id, "docs/self.md"
            )
            command = self.render_command(command, "PASS", rationale)

            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            files = list((run_dir / "verdicts").glob("*.json"))
            self.assertEqual(len(files), 1)
            record = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["runid"], run_id)
            self.assertEqual(record["path"], "docs/self.md")
            self.assertEqual(record["verdict"], "PASS")
            self.assertEqual(record["rationale"], "kept before delimiter\n")


if __name__ == "__main__":
    unittest.main()
