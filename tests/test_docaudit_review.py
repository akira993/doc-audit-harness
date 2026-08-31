import ast
import importlib.util
import json
import os
import subprocess
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "skills", "audit", "scripts", "docaudit_review.py")


def load_library():
    spec = importlib.util.spec_from_file_location("docaudit_review", LIB)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocauditReviewTests(unittest.TestCase):
    CASES = (
        ({}, 1, "not-active", "not-configured", None, False, None),
        ({"reviewCommands": None}, 2, "refuse", "invalid-review-config", None, False, None),
        ({"reviewCommands": []}, 2, "refuse", "invalid-review-config", None, False, None),
        ({"reviewCommands": {}}, 3, "not-active", "not-configured", None, False, None),
        ({"reviewCommands": {"security": "/security-review"}}, 3, "not-active", "not-configured", None, False, None),
        ({"reviewCommands": {"required": True}}, 3, "refuse", "invalid-review-config", None, False, None),
        ({"reviewCommands": {"code": None}}, 4, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": ""}}, 5, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "\u3000\t"}}, 5, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review low"}}, 6, "run", "pending", "low", False, None),
        ({"reviewCommands": {"code": "/code-review medium", "required": True}}, 6, "run", "pending", "medium", True, None),
        ({"reviewCommands": {"code": "/code-review high"}}, 6, "run", "pending", "high", False, None),
        ({"reviewCommands": {"code": "/code-review xhigh"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review ultra"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review --fix"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review  high"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review\u3000high"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review"}}, 7, "refuse", "invalid-review-command", None, False, None),
        ({"reviewCommands": {"code": "/code-review-custom"}}, 8, "legacy", "legacy-pending", None, False, "/code-review-custom"),
        ({"reviewCommands": {"code": "/社内レビュー 高"}}, 8, "legacy", "legacy-pending", None, False, "/社内レビュー 高"),
        ({"reviewCommands": {"code": "review\tcommand"}}, 8, "legacy", "legacy-pending", None, False, "review\tcommand"),
        ({"reviewCommands": {"code": "/custom", "required": True}}, 8, "refuse", "invalid-review-config", None, False, None),
        ({"reviewCommands": {"code": "/code-review high", "required": 1}}, 6, "refuse", "invalid-review-config", None, False, None),
    )

    @classmethod
    def tearDownClass(cls):
        print(f"対象 {len(cls.CASES)} 件を検査")

    def test_p1_through_p8_and_boundaries(self):
        classify = load_library().classify_review_command
        for config, p, action, state, effort, required, command in self.CASES:
            with self.subTest(config=config):
                result = classify(config)
                self.assertEqual(result["p"], p)
                self.assertEqual(result["action"], action)
                self.assertEqual(result["state"], state)
                self.assertEqual(result["effort"], effort)
                self.assertIs(result["required"], required)
                self.assertEqual(result["command"], command)
                if action == "refuse":
                    self.assertIn("reviewCommands.code", result["reason"])
                    self.assertIn("docs/ADOPTION.md#code-review-autonomous-execution-and-opt-out", result["reason"])

    def test_library_is_pure_by_ast(self):
        with open(LIB, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}
        imports.update(node.module for node in ast.walk(tree)
                       if isinstance(node, ast.ImportFrom) and node.module)
        self.assertNotIn("sealed_config", imports)
        self.assertNotIn("os", imports)
        calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)]
        self.assertNotIn("open", calls)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("environ", names)

    def test_isolated_import_and_call(self):
        source = (
            "import importlib.util,json;"
            f"s=importlib.util.spec_from_file_location('r',{json.dumps(LIB)});"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            "print(json.dumps(m.classify_review_command({'reviewCommands':{'code':'/code-review high'}}),sort_keys=True))"
        )
        proc = subprocess.run([sys.executable, "-I", "-c", source], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["effort"], "high")

    def test_all_three_consumers_import_the_shared_classifier(self):
        scripts = os.path.join(ROOT, "skills", "audit", "scripts")
        for name in ("code-review-plan.py", "start-run.py", "decide-verdict.py"):
            with self.subTest(name=name), open(os.path.join(scripts, name), encoding="utf-8") as handle:
                source = handle.read()
            self.assertEqual(
                source.count("from docaudit_review import classify_review_command"), 1)


if __name__ == "__main__":
    unittest.main()
