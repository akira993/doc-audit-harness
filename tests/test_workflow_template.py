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
STANDARD_AGENT = ROOT / "agents" / "doc-impact-verifier.md"
LIGHT_AGENT = ROOT / "agents" / "doc-impact-verifier-light.md"
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

    def run_template(self, verifier_model, outcomes, parallel_null_indexes=None, impacted=None):
        source = self.source.replace("export ", "", 1)
        program = r"""
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const source = process.env.DOCAUDIT_TEMPLATE_SOURCE
const input = JSON.parse(process.env.DOCAUDIT_TEMPLATE_ARGS)
const outcomes = JSON.parse(process.env.DOCAUDIT_TEMPLATE_OUTCOMES)
const parallelNullIndexes = new Set(
  JSON.parse(process.env.DOCAUDIT_PARALLEL_NULL_INDEXES)
)
const agentTypes = []
const prompts = []
let index = 0
const execute = new AsyncFunction('args', 'phase', 'parallel', 'agent', source)
;(async () => {
  const result = await execute(
    JSON.stringify(input),
    () => {},
    async (tasks) => {
      const values = await Promise.all(tasks.map((task) => task()))
      return values.map((value, i) => parallelNullIndexes.has(i) ? null : value)
    },
    async (_prompt, opts) => {
      prompts.push(_prompt)
      agentTypes.push(opts.agentType)
      const value = outcomes[index]
      index += 1
      return value
    },
  )
  process.stdout.write(JSON.stringify({ result, agentTypes, prompts }))
})().catch((error) => {
  process.stderr.write(String(error.stack || error))
  process.exitCode = 1
})
"""
        env = os.environ.copy()
        env["DOCAUDIT_TEMPLATE_SOURCE"] = source
        input_value = {
            "repoRoot": "/repo",
            "changeSummary": "changed",
            "impacted": impacted or [
                {"path": "docs/a.md", "provenance": "mapped"},
                {"path": "docs/b.md", "provenance": "heuristic"},
            ],
            "runId": "20260818T000000Z-1234abcd",
            "runDir": "/repo/.claude/state/docaudit-run/20260818T000000Z-1234abcd",
            "scriptsDir": "/plugin/skills/audit/scripts",
        }
        if verifier_model is not None:
            input_value["verifierModel"] = verifier_model
        env["DOCAUDIT_TEMPLATE_ARGS"] = json.dumps(input_value)
        env["DOCAUDIT_TEMPLATE_OUTCOMES"] = json.dumps(outcomes)
        env["DOCAUDIT_PARALLEL_NULL_INDEXES"] = json.dumps(
            parallel_null_indexes or []
        )
        return json.loads(self.run_node(program, env=env))

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
        self.assertIn("'docaudit:doc-impact-verifier-light'", self.source)
        self.assertIn("'docaudit:doc-impact-verifier'", self.source)
        self.assertIn("verifierModel === 'haiku'", self.source)
        self.assertIn("assignedPath: d.path", self.source)
        self.assertNotIn("results.filter(Boolean)", self.source)
        self.assertNotIn("--source", extract_helpers(self.source))

    def test_verifier_model_selects_namespaced_agent_type(self):
        outcomes = [
            {"path": "docs/a.md", "verdict": "PASS", "rationale": "ok"},
            {"path": "docs/b.md", "verdict": "WARN", "rationale": "check"},
        ]
        light = self.run_template("haiku", outcomes)
        self.assertEqual(
            light["agentTypes"],
            ["docaudit:doc-impact-verifier-light"] * 2,
        )
        standard = self.run_template("sonnet", outcomes)
        self.assertEqual(
            standard["agentTypes"],
            ["docaudit:doc-impact-verifier"] * 2,
        )
        defaulted = self.run_template(None, outcomes)
        self.assertEqual(
            defaulted["agentTypes"],
            ["docaudit:doc-impact-verifier"] * 2,
        )

    def test_self_provenance_prompt_uses_current_source(self):
        executed = self.run_template(
            "sonnet", [{"path": "docs/a.md", "verdict": "PASS", "rationale": "ok"}],
            impacted=[{"path": "docs/a.md", "provenance": "self"}],
        )
        prompt = executed["prompts"][0]
        self.assertIn("current source", prompt)
        self.assertNotIn("still ACCURATELY describes the changed source", prompt)

    def test_null_return_is_retained_with_assigned_path(self):
        executed = self.run_template(
            "sonnet",
            [None, {"path": "docs/b.md", "verdict": "PASS", "rationale": "ok"}],
        )
        self.assertEqual(
            executed["result"][0],
            {
                "assignedPath": "docs/a.md",
                "returnedPath": None,
                "verdict": None,
                "rationale": None,
                "suggestion": None,
            },
        )
        self.assertEqual(executed["result"][1]["assignedPath"], "docs/b.md")
        self.assertEqual(executed["result"][1]["returnedPath"], "docs/b.md")

    def test_parallel_null_element_is_filled_with_assigned_path(self):
        executed = self.run_template(
            "sonnet",
            [
                {"path": "docs/a.md", "verdict": "PASS", "rationale": "ok"},
                {"path": "docs/b.md", "verdict": "PASS", "rationale": "ok"},
            ],
            parallel_null_indexes=[0],
        )
        self.assertEqual(
            executed["result"][0],
            {
                "assignedPath": "docs/a.md",
                "returnedPath": None,
                "verdict": None,
                "rationale": None,
                "suggestion": None,
            },
        )
        self.assertEqual(executed["result"][1]["assignedPath"], "docs/b.md")
        self.assertEqual(executed["result"][1]["returnedPath"], "docs/b.md")

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


class TestVerifierAgentDefinitions(unittest.TestCase):
    @staticmethod
    def split_definition(path):
        raw = path.read_bytes()
        parts = raw.split(b"---\n", 2)
        if len(parts) != 3 or parts[0] != b"":
            raise AssertionError(f"invalid front matter in {path}")
        fields = {}
        for line in parts[1].decode("utf-8").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        return fields, parts[2]

    def test_frontmatter_models_and_names(self):
        standard, _ = self.split_definition(STANDARD_AGENT)
        light, _ = self.split_definition(LIGHT_AGENT)
        self.assertEqual(standard["name"], "doc-impact-verifier")
        self.assertEqual(standard["model"], "sonnet")
        self.assertEqual(light["name"], "doc-impact-verifier-light")
        self.assertEqual(light["model"], "haiku")
        self.assertTrue(light["description"].startswith(standard["description"]))
        self.assertIn("Haiku", light["description"])

    def test_agent_bodies_are_byte_identical(self):
        _, standard_body = self.split_definition(STANDARD_AGENT)
        _, light_body = self.split_definition(LIGHT_AGENT)
        self.assertEqual(light_body, standard_body)

    def test_agent_documents_all_current_provenance_values(self):
        _, body = self.split_definition(STANDARD_AGENT)
        text = body.decode("utf-8")
        for value in ("mapped", "heuristic", "both", "full", "self", "regression", "graphify", "semantic"):
            self.assertIn(f"`{value}`", text)
        self.assertIn("`full` means a\n   full-corpus run and is not an impactMap-gap candidate", text)


if __name__ == "__main__":
    unittest.main()
