import json
import os
import subprocess
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "harness-command-kind.py")


class TestHarnessCommandKind(unittest.TestCase):
    def test_classification_table(self):
        commands = ["/check-docs --only format", "doc-lint", "make docs-check", "npm run docs",
                    "uv run x", "./scripts/x", "/usr/local/bin/x", "x/y",
                    "doc-lint\t--foo", "/", "/ --foo", "", "   "]
        proc = subprocess.run([sys.executable, SCRIPT, *commands], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([item["kind"] for item in json.loads(proc.stdout)], [
            "model-driven", "model-driven", "script-backed", "script-backed", "script-backed",
            "script-backed", "script-backed", "script-backed", "script-backed", "script-backed",
            "script-backed", "invalid", "invalid"])

    def test_stdin_json_and_lines(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"], input='["doc-lint", null]',
                              capture_output=True, text=True)
        result = json.loads(proc.stdout)
        self.assertEqual([item["kind"] for item in result], ["model-driven", "invalid"])
        self.assertTrue(all("layer" not in item for item in result))
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"], input="doc-lint\nmake docs\n",
                              capture_output=True, text=True)
        self.assertEqual([item["kind"] for item in json.loads(proc.stdout)], ["model-driven", "script-backed"])

    def test_stdin_json_object_emits_fixed_layers(self):
        mapping = {"format": "/check-docs --only format", "existence": None,
                   "semantic": "doc-lint"}
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"], input=json.dumps(mapping),
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual([item["layer"] for item in result],
                         ["format", "existence", "semantic"])
        self.assertEqual([item["kind"] for item in result],
                         ["model-driven", "invalid", "model-driven"])
        self.assertIsNone(result[1]["command"])

    def test_stdin_json_object_fills_missing_layer(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"],
                              input=json.dumps({"format": "doc-lint", "semantic": "doc-lint",
                                                "extra": "ignored"}),
                              capture_output=True, text=True)
        result = json.loads(proc.stdout)
        self.assertEqual(result[1], {"layer": "existence", "command": None, "kind": "invalid"})
        self.assertEqual(len(result), 3)

    def test_stdin_null_emits_three_invalid_layers(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"], input="null",
                              capture_output=True, text=True)
        result = json.loads(proc.stdout)
        self.assertEqual([item["layer"] for item in result],
                         ["format", "existence", "semantic"])
        self.assertEqual([item["kind"] for item in result], ["invalid", "invalid", "invalid"])
        self.assertTrue(all(item["command"] is None for item in result))
