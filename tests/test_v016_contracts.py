"""Release contracts for docaudit v0.16.0 sealed inputs and Phase-4 history."""

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests import test_codex_review_plan as codex_plan_tests
from tests import test_v016_history_common as history_tests
from tests import test_wp12_contracts as wp12_tests
from tests.wp12_helpers import RunFixture, write


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
SKILL = os.path.join(ROOT, "skills", "audit", "SKILL.md")
BAD_SHA = "sha256:" + "0" * 64


CONSUMER_REGISTRY = (
    ("open-run.py", "required", 2, "config-changed-before-open"),
    ("mdq-index.sh", "required", 7, "sealed-config-mismatch"),
    ("ax-probe.sh", "required", 7, "sealed-config-mismatch"),
    ("codex-probe.sh", "required", 7, "sealed-config-mismatch"),
    ("codegraph-probe.sh", "required", 7, "sealed-config-mismatch"),
    ("graphify-probe.sh", "required", 7, "sealed-config-mismatch"),
    ("cocoindex-probe.sh", "required", 7, "sealed-config-mismatch"),
    ("set-config-key.py", "optional", 7, "sealed-config-mismatch"),
    ("generic-layers.py", "optional", 7, "sealed-config-mismatch"),
    ("check-docs.py", "copy", 7, "sealed-config-mismatch"),
    ("fix-scope.py", "conditional", 7, "sealed-config-mismatch"),
    ("compute-baseline.sh", "required", 7, "sealed-config-mismatch"),
    ("resolve-impact.py", "required", 7, "sealed-config-mismatch"),
    ("impact-supplement.py", "conditional", 7, "sealed-config-mismatch"),
    ("classify-run.py", "required", 7, "sealed-config-mismatch"),
    ("plan-dispatch.py", "required", 7, "sealed-config-mismatch"),
    ("start-run.py", "required", 7, "sealed-config-mismatch"),
    ("seal-run.py", "evidence", 7, "sealed-config-mismatch"),
    ("codex-review-plan.py", "required", 7, "sealed-config-mismatch"),
    ("decide-verdict.py", "evidence", 3, "config-changed"),
    ("change-set-sha.py", "required", 7, "sealed-config-mismatch"),
)

GETTER_REGISTRY = (
    ("phase3Backend", "PHASE3_BACKEND_CONFIG", '"workflow"', True),
    ("contextMode", "CM_CONFIG_JSON", "{}", False),
    ("harness", "HARNESS_CONFIG_JSON", "null", False),
    ("docAuditCommands", "DOC_AUDIT_COMMANDS_JSON", "null", False),
    ("maxImpactedDocs", "MAX_IMPACTED_DOCS", "200", False),
    ("docGlobs", "DOC_GLOBS_JSON", "[]", False),
    ("semanticSearch.minScore", "SEMANTIC_MIN_SCORE", "0.4", False),
    ("boundaryCommand", "BOUNDARY_COMMAND", "null", True),
    ("reviewCommands", "REVIEW_COMMANDS_JSON", "{}", False),
    ("codexReview.model", "CODEX_MODEL_CONFIG", "null", True),
    ("codexReview.timeoutMs", "CODEX_TIMEOUT_MS", "300000", False),
    ("reportPath", "REPORT_PATH_CONFIG", "null", True),
    ("docAuditCommands", "DOC_AUDIT_COMMANDS_P4_JSON", "null", False),
)

SHELL_CONSUMERS = (
    "mdq-index.sh", "ax-probe.sh", "codex-probe.sh", "codegraph-probe.sh",
    "graphify-probe.sh", "cocoindex-probe.sh", "compute-baseline.sh",
)

OBSERVERS = (
    "mdq-index.sh", "ax-probe.sh", "codex-probe.sh", "codegraph-probe.sh",
    "graphify-probe.sh", "cocoindex-probe.sh", "set-config-key.py",
    "generic-layers.py", "check-docs.py", "fix-scope.py", "compute-baseline.sh",
    "resolve-impact.py", "impact-supplement.py", "classify-run.py",
    "plan-dispatch.py", "start-run.py", "seal-run.py", "codex-review-plan.py",
    "sealed_config.py",
)


def file_sha(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def script(name):
    return os.path.join(SCRIPTS, name)


def run(name, *args, input_text=None, cwd=None, env=None):
    command = (["bash", script(name)] if name.endswith(".sh")
               else [sys.executable, script(name)])
    return subprocess.run(command + list(args), input=input_text, capture_output=True,
                          text=True, cwd=cwd, env=env)


def load_module(name):
    path = script(name)
    spec = importlib.util.spec_from_file_location("v016_" + name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestV016Contracts(unittest.TestCase):
    maxDiff = None

    def test_ct_1_registry_equivalence(self):
        with open(SKILL, encoding="utf-8") as handle:
            skill = handle.read()

        flag_files = set()
        for name in os.listdir(SCRIPTS):
            if not (name.endswith(".py") or name.endswith(".sh")):
                continue
            with open(script(name), encoding="utf-8") as handle:
                source = handle.read()
            if (re.search(r'add_argument\("--expect-config-sha"', source)
                    or re.search(r'--expect-config-sha\)', source)):
                flag_files.add(name)
        expected_flags = {name for name, mode, _code, _token in CONSUMER_REGISTRY
                          if mode in {"required", "conditional", "optional"}}
        expected_flags.discard("check-docs.py")
        expected_flags.add("import-audit-scope.py")
        self.assertEqual(flag_files, expected_flags)

        call_lines = [line for line in skill.splitlines()
                      if ('--expect-config-sha "$CONFIG_SHA"' in line
                          or '--expect-config-sha "$PRECHECK_CONFIG_SHA"' in line)]
        cfg_lines = [line for line in skill.splitlines() if '"$CFG"' in line]
        exemptions = [line for line in cfg_lines if "CONFIG_SHA" not in line]
        self.assertEqual(len(call_lines), 22)
        self.assertEqual(len(exemptions), 3)
        self.assertIn("ANCHOR_PATH=", exemptions[0])
        self.assertTrue(any("import-audit-scope.py" in line and "--check" in line
                            for line in exemptions))
        self.assertTrue(any("decide-verdict.py" in line for line in exemptions))
        for line in cfg_lines:
            classified = (line in exemptions
                          or '--expect-config-sha "$CONFIG_SHA"' in line
                          or ('sealed_config.py' in line
                              and '--expect-sha "$CONFIG_SHA"' in line))
            self.assertTrue(classified, line)

        for key, variable, default, raw in GETTER_REGISTRY:
            prefix = (f'{variable}="$(python3 "$SD/scripts/sealed_config.py" '
                      f'--config "$CFG" --expect-sha "$CONFIG_SHA" --get {key} ')
            matches = [line for line in skill.splitlines() if prefix in line]
            self.assertEqual(len(matches), 1, (key, variable, matches))
            rendered_default = ({'"workflow"': "'\"workflow\"'",
                                 "{}": "'{}'", "[]": "'[]'"}.get(default, default))
            self.assertIn("--default " + rendered_default,
                          matches[0])
            self.assertEqual("--raw" in matches[0], raw)
            assignments = re.findall(rf'(?m)^.*\b{re.escape(variable)}=', skill)
            self.assertEqual(len(assignments), 1, variable)
        phase4 = skill.split("## Phase 4 —", 1)[1].split("## Phase 5", 1)[0]
        review_assignment = phase4.index('REVIEW_COMMANDS_JSON="$(python3')
        normalized_phase4 = " ".join(phase4.split())
        security_instruction = (
            "Normalize any `/security-audit ...` request to `/security-review`, then run "
            "`reviewCommands.security` exactly as before."
        )
        self.assertEqual(normalized_phase4.count(security_instruction), 1)
        self.assertLess(review_assignment, phase4.index("3. Normalize any", review_assignment))

        for name in SHELL_CONSUMERS:
            with open(script(name), encoding="utf-8") as handle:
                source = handle.read()
            self.assertEqual(source.count("sealed_config.py"), 1, name)
            self.assertNotIn("json.load(open", source, name)

        with open(script("decide-verdict.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        observed = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "OBSERVERS"
                    for target in node.targets):
                observed = ast.literal_eval(node.value)
        self.assertEqual(observed, OBSERVERS)
        counts = (len(call_lines), len(exemptions), len(GETTER_REGISTRY),
                  len(CONSUMER_REGISTRY), len(observed))
        self.assertEqual(counts, (22, 3, 13, 21, 19))
        print("call sites 22／exempt 3／getters 13／scripts 21／observers 19")

    def _base_args(self, fx, impact_path):
        good = file_sha(fx.config_path)
        history = fx.history
        return {
            "mdq-index.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                             "--repo-root", fx.repo],
            "ax-probe.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                            "--repo-root", fx.repo],
            "codex-probe.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                               "--repo-root", fx.repo],
            "codegraph-probe.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                                   "--repo-root", fx.repo],
            "graphify-probe.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                                  "--repo-root", fx.repo],
            "cocoindex-probe.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                                   "--repo-root", fx.repo],
            "generic-layers.py": ["--config", fx.config_path, "--expect-config-sha", good,
                                  "--repo-root", fx.repo],
            "fix-scope.py": ["--config", fx.config_path, "--expect-config-sha", good,
                             "--repo-root", fx.repo, "--paths", "-"],
            "compute-baseline.sh": ["--config", fx.config_path, "--expect-config-sha", good,
                                    "--repo-root", fx.repo],
            "resolve-impact.py": ["--config", fx.config_path, "--expect-config-sha", good,
                                  "--repo-root", fx.repo, "--changed", "-", "--mode", "full"],
            "impact-supplement.py": ["--impact-json", impact_path, "--changed", "-",
                                     "--repo-root", fx.repo, "--config", fx.config_path,
                                     "--expect-config-sha", good],
            "classify-run.py": ["--repo-root", fx.repo, "--config", fx.config_path,
                                "--expect-config-sha", good, "--impact-json", impact_path,
                                "--baseline-sha", fx.head, "--mode", "incremental"],
            "codex-review-plan.py": ["--mode", "incremental", "--repo-root", fx.repo,
                                     "--config", fx.config_path,
                                     "--expect-config-sha", good, "--available", "false",
                                     "--baseline-ok", "true", "--history", history,
                                     "--expect-history-sha", "none",
                                     "--worktree-digest", "sha256:" + "1" * 64],
            "change-set-sha.py": ["--repo-root", fx.repo, "--baseline-sha", fx.head,
                                  "--config", fx.config_path, "--expect-config-sha", good],
        }

    def test_ct_2_all_consumer_match_mismatch_pairs(self):
        checked = set()
        mismatch_contract = {
            name: (code, token) for name, _mode, code, token in CONSUMER_REGISTRY
        }
        fx = RunFixture(self)
        impact_path = os.path.join(fx.repo, "impact-pair.json")
        write(impact_path, json.dumps({"impacted": []}) + "\n")
        args_by_name = self._base_args(fx, impact_path)

        for name in (*SHELL_CONSUMERS, "generic-layers.py", "fix-scope.py",
                     "resolve-impact.py", "impact-supplement.py", "classify-run.py",
                     "codex-review-plan.py", "change-set-sha.py"):
            with self.subTest(name=name, seal="match"):
                proc = run(name, *args_by_name[name], input_text="")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            bad_args = [BAD_SHA if item == file_sha(fx.config_path) else item
                        for item in args_by_name[name]]
            with self.subTest(name=name, seal="mismatch"):
                proc = run(name, *bad_args, input_text="")
                expected_code, expected_token = mismatch_contract[name]
                self.assertEqual(proc.returncode, expected_code,
                                 proc.stdout + proc.stderr)
                self.assertIn(expected_token, proc.stderr)
            checked.add(name)

        with tempfile.TemporaryDirectory() as temp:
            config = os.path.join(temp, "config.json")
            write(config, "{}\n")
            good = file_sha(config)
            match = run("set-config-key.py", "--config", config, "--expect-config-sha", good,
                        "--set", "probe=1")
            self.assertEqual(match.returncode, 0, match.stdout + match.stderr)
            mismatch = run("set-config-key.py", "--config", config,
                           "--expect-config-sha", BAD_SHA, "--set", "probe=2")
            expected_code, expected_token = mismatch_contract["set-config-key.py"]
            self.assertEqual(mismatch.returncode, expected_code)
            self.assertIn(expected_token, mismatch.stderr)
        checked.add("set-config-key.py")

        copied = os.path.join(fx.repo, "scripts", "check-docs.py")
        os.makedirs(os.path.dirname(copied), exist_ok=True)
        shutil.copyfile(script("generic-layers.py"), copied)
        copy_args = ["--config", fx.config_path, "--repo-root", fx.repo]
        no_flag = subprocess.run([sys.executable, copied, *copy_args], capture_output=True, text=True)
        self.assertEqual(no_flag.returncode, 0, no_flag.stdout + no_flag.stderr)
        match = subprocess.run([sys.executable, copied, *copy_args,
                                "--expect-config-sha", file_sha(fx.config_path)],
                               capture_output=True, text=True)
        self.assertEqual(match.returncode, 0, match.stdout + match.stderr)
        mismatch = subprocess.run([sys.executable, copied, *copy_args,
                                   "--expect-config-sha", BAD_SHA],
                                  capture_output=True, text=True)
        expected_code, expected_token = mismatch_contract["check-docs.py"]
        self.assertEqual(mismatch.returncode, expected_code)
        self.assertIn(expected_token, mismatch.stderr)
        checked.add("check-docs.py")

        wrong_open = run("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                         "--anchor-path", fx.anchor_rel, "--runid", fx.runid,
                         "--expect-config-sha", BAD_SHA)
        expected_code, expected_token = mismatch_contract["open-run.py"]
        self.assertEqual(wrong_open.returncode, expected_code)
        self.assertIn(expected_token, wrong_open.stderr)
        self.assertEqual(fx.open().returncode, 0)
        checked.add("open-run.py")

        good = file_sha(fx.config_path)
        classify = run("classify-run.py", *args_by_name["classify-run.py"])
        self.assertEqual(classify.returncode, 0, classify.stdout + classify.stderr)
        plan_args = ["--run-dir", fx.run_dir, "--runid", fx.runid, "--repo-root", fx.repo,
                     "--config", fx.config_path, "--expect-config-sha", good,
                     "--history", fx.history, "--impact-json", impact_path,
                     "--baseline-sha", fx.head, "--mode", "incremental",
                     "--contract-version", "0.16.0", "--evidence", json.dumps(fx.evidence)]
        planned = run("plan-dispatch.py", *plan_args)
        self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
        fx.evidence = json.loads(planned.stdout)
        checked.add("plan-dispatch.py")
        start_args = ["--run-dir", fx.run_dir, "--runid", fx.runid, "--repo-root", fx.repo,
                      "--impact-json", impact_path,
                      "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
                      "--run-class", "light", "--mode", "incremental",
                      "--config", fx.config_path, "--expect-config-sha", good,
                      "--evidence", json.dumps(fx.evidence)]
        started = run("start-run.py", *start_args)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        fx.evidence = json.loads(started.stdout)
        checked.add("start-run.py")
        sealed = run("seal-run.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                     "--evidence", json.dumps(fx.evidence))
        self.assertEqual(sealed.returncode, 0, sealed.stdout + sealed.stderr)
        fx.evidence = json.loads(sealed.stdout)
        checked.add("seal-run.py")
        checked.add("classify-run.py")

        bad_evidence = dict(fx.evidence, config=BAD_SHA)
        bad_plan = list(plan_args)
        bad_plan[bad_plan.index(good)] = BAD_SHA
        bad_plan[-1] = json.dumps(dict(json.loads(plan_args[-1]), config=BAD_SHA))
        proc = run("plan-dispatch.py", *bad_plan)
        expected_code, expected_token = mismatch_contract["plan-dispatch.py"]
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        self.assertIn(expected_token, proc.stderr)
        bad_start = list(start_args)
        bad_start[bad_start.index(good)] = BAD_SHA
        bad_start[-1] = json.dumps(bad_evidence)
        proc = run("start-run.py", *bad_start)
        expected_code, expected_token = mismatch_contract["start-run.py"]
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        self.assertIn(expected_token, proc.stderr)

        with open(fx.config_path, "a", encoding="utf-8") as handle:
            handle.write(" ")
        proc = run("seal-run.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                   "--evidence", json.dumps(fx.evidence))
        expected_code, expected_token = mismatch_contract["seal-run.py"]
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        self.assertIn(expected_token, proc.stderr)

        gate_ok = RunFixture(self)
        self.assertEqual(gate_ok.open().returncode, 0)
        self.assertEqual(gate_ok.plan_start_seal().returncode, 0)
        self.assertEqual(gate_ok.complete().returncode, 0)
        self.assertEqual(gate_ok.gate().returncode, 0)
        checked.add("decide-verdict.py")
        gate_bad = RunFixture(self)
        self.assertEqual(gate_bad.open().returncode, 0)
        self.assertEqual(gate_bad.plan_start_seal().returncode, 0)
        self.assertEqual(gate_bad.complete().returncode, 0)
        with open(gate_bad.config_path, "a", encoding="utf-8") as handle:
            handle.write(" ")
        refused = gate_bad.gate()
        expected_code, expected_token = mismatch_contract["decide-verdict.py"]
        self.assertEqual(refused.returncode, expected_code,
                         refused.stdout + refused.stderr)
        self.assertEqual(json.loads(refused.stdout)["reason"], "config-changed")
        self.assertIn(expected_token, refused.stdout)

        expected = {name for name, _mode, _code, _token in CONSUMER_REGISTRY}
        self.assertEqual(checked, expected)
        print(f"対象 {len(checked)} 本を検査")

    def test_ct_2_shell_consumers_accept_large_sealed_config_via_stdin(self):
        fx = RunFixture(self)
        fx.config.update({
            "impactMap": [
                {"changed": f"src/generated/{index:05d}.py",
                 "impacts": ["docs/a.md"], "note": "x" * 96}
                for index in range(2400)
            ],
            "indexing": {"enabled": False},
            "webExtract": {"enabled": False},
            "codexReview": {"enabled": False},
            "symbolGraph": {"enabled": False},
            "docGraph": {"enabled": False},
            "semanticSearch": {"enabled": False},
        })
        rendered = json.dumps(fx.config, ensure_ascii=False, indent=2) + "\n"
        self.assertGreater(len(rendered.encode("utf-8")), 300 * 1024)
        write(fx.config_path, rendered)
        impact_path = os.path.join(fx.repo, "impact-large-config.json")
        write(impact_path, json.dumps({"impacted": []}) + "\n")
        args_by_name = self._base_args(fx, impact_path)

        for name in SHELL_CONSUMERS:
            with self.subTest(name=name):
                proc = run(name, *args_by_name[name], input_text="")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIsInstance(json.loads(proc.stdout), dict)

    def test_ct_2b_sitecustomize_hooks_builtins_and_os_open(self):
        with tempfile.TemporaryDirectory() as temp:
            config = os.path.join(temp, "config.json")
            log = os.path.join(temp, "opens.log")
            write(config, "{}\n")
            hook = textwrap.dedent(r'''
                import builtins, json, os, sys
                _builtins_open = builtins.open
                _os_open = os.open
                _target = os.environ.get("DOCAUDIT_COUNT_PATH")
                _log = os.environ.get("DOCAUDIT_COUNT_LOG")
                def _record(kind, path):
                    try: same = os.path.realpath(os.fspath(path)) == os.path.realpath(_target)
                    except Exception: same = False
                    if same:
                        with _builtins_open(_log, "a", encoding="utf-8") as handle:
                            handle.write(json.dumps({"kind":kind,"argv":sys.argv}) + "\n")
                def counted_open(path, *args, **kwargs):
                    handle = _builtins_open(path, *args, **kwargs)
                    _record("builtins.open", path)
                    return handle
                def counted_os_open(path, *args, **kwargs):
                    fd = _os_open(path, *args, **kwargs)
                    _record("os.open", path)
                    return fd
                builtins.open = counted_open
                os.open = counted_os_open
            ''')
            write(os.path.join(temp, "sitecustomize.py"), hook)
            env = dict(os.environ, PYTHONPATH=temp, DOCAUDIT_COUNT_PATH=config,
                       DOCAUDIT_COUNT_LOG=log)
            probe = subprocess.run([
                sys.executable, "-c",
                "import os; f=open(os.environ['DOCAUDIT_COUNT_PATH']); f.close(); "
                "fd=os.open(os.environ['DOCAUDIT_COUNT_PATH'], os.O_RDONLY); os.close(fd)"],
                capture_output=True, text=True, env=env)
            self.assertEqual(probe.returncode, 0, probe.stderr)
            sealed = run("sealed_config.py", "--config", config, "--expect-sha",
                         file_sha(config), "--print", env=env)
            self.assertEqual(sealed.returncode, 0, sealed.stderr)
            with open(log, encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle]
            self.assertIn("builtins.open", {item["kind"] for item in events})
            self.assertIn("os.open", {item["kind"] for item in events})
            sealed_events = [item for item in events if "sealed_config.py" in " ".join(item["argv"])]
            self.assertEqual([item["kind"] for item in sealed_events], ["os.open"])
            self.assertIn("builtins.open = counted_open", hook)
            self.assertIn("os.open = counted_os_open", hook)

    def test_ct_2b_all_consumer_read_counts_and_child_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            log = os.path.join(temp, "opens.log")
            hook = textwrap.dedent(r'''
                import builtins, json, os, sys
                _builtins_open = builtins.open
                _os_open = os.open
                _target = os.environ.get("DOCAUDIT_COUNT_PATH")
                _log = os.environ.get("DOCAUDIT_COUNT_LOG")
                _swap_for = os.environ.get("DOCAUDIT_SWAP_FOR")
                _swap_bytes = os.environ.get("DOCAUDIT_SWAP_BYTES")
                _swap_done = os.environ.get("DOCAUDIT_SWAP_DONE")
                def _record(kind, path):
                    try: same = os.path.realpath(os.fspath(path)) == os.path.realpath(_target)
                    except Exception: same = False
                    if not same:
                        return
                    with _builtins_open(_log, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"kind":kind,"argv":sys.argv}) + "\n")
                    if (_swap_for and os.path.basename(sys.argv[0]) == _swap_for
                            and _swap_bytes and _swap_done):
                        try:
                            marker = _os_open(_swap_done, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        except FileExistsError:
                            return
                        os.close(marker)
                        replacement = _target + ".ct2b-swap"
                        fd = _os_open(replacement, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                        try: os.write(fd, _swap_bytes.encode("utf-8"))
                        finally: os.close(fd)
                        os.replace(replacement, _target)
                def counted_open(path, *args, **kwargs):
                    handle = _builtins_open(path, *args, **kwargs)
                    _record("builtins.open", path)
                    return handle
                def counted_os_open(path, *args, **kwargs):
                    fd = _os_open(path, *args, **kwargs)
                    _record("os.open", path)
                    return fd
                builtins.open = counted_open
                os.open = counted_os_open
            ''')
            write(os.path.join(temp, "sitecustomize.py"), hook)

            def counted_env(config_path, **extra):
                value = dict(os.environ, PYTHONPATH=temp,
                             DOCAUDIT_COUNT_PATH=config_path,
                             DOCAUDIT_COUNT_LOG=log)
                value.update(extra)
                return value

            def execute(name, args, config_path, input_text="", env_extra=None):
                write(log, "")
                env = counted_env(config_path, **(env_extra or {}))
                proc = run(name, *args, input_text=input_text, env=env)
                with open(log, encoding="utf-8") as handle:
                    events = [json.loads(line) for line in handle]
                return proc, events

            def assert_child_sha(events, expected_sha):
                children = [item for item in events
                            if os.path.basename(item["argv"][0]) == "change-set-sha.py"]
                self.assertEqual(len(children), 1, events)
                argv = children[0]["argv"]
                position = argv.index("--expect-config-sha")
                self.assertEqual(argv[position + 1], expected_sha)

            fx = RunFixture(self)
            impact_path = os.path.join(fx.repo, "impact-count.json")
            write(impact_path, json.dumps({"impacted": []}) + "\n")
            args_by_name = self._base_args(fx, impact_path)
            direct = (*SHELL_CONSUMERS, "generic-layers.py", "fix-scope.py",
                      "resolve-impact.py", "impact-supplement.py",
                      "codex-review-plan.py", "change-set-sha.py")
            measured = set()
            for name in direct:
                with self.subTest(name=name, kind="direct"):
                    proc, events = execute(name, args_by_name[name], fx.config_path)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertEqual(len(events), 1, events)
                measured.add(name)

            config = os.path.join(temp, "set-config.json")
            write(config, "{}\n")
            proc, events = execute(
                "set-config-key.py",
                ["--config", config, "--expect-config-sha", file_sha(config),
                 "--set", "probe=1"], config)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 1, events)
            with open(config, encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["probe"], 1)
            measured.add("set-config-key.py")

            copied = os.path.join(fx.repo, "scripts", "check-docs.py")
            os.makedirs(os.path.dirname(copied), exist_ok=True)
            shutil.copyfile(script("generic-layers.py"), copied)
            write(log, "")
            proc = subprocess.run(
                [sys.executable, copied, "--config", fx.config_path,
                 "--expect-config-sha", file_sha(fx.config_path),
                 "--repo-root", fx.repo], capture_output=True, text=True,
                env=counted_env(fx.config_path))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            with open(log, encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle]
            self.assertEqual(len(events), 1, events)
            measured.add("check-docs.py")

            good = file_sha(fx.config_path)
            open_args = ["--run-base", fx.run_base, "--repo-root", fx.repo,
                         "--anchor-path", fx.anchor_rel, "--runid", fx.runid,
                         "--expect-config-sha", good]
            proc, events = execute("open-run.py", open_args, fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 1, events)
            fx.evidence = json.loads(proc.stdout)
            fx.run_dir = fx.evidence["runDir"]
            measured.add("open-run.py")

            proc, events = execute(
                "classify-run.py", args_by_name["classify-run.py"], fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 2, events)
            assert_child_sha(events, good)
            measured.add("classify-run.py")

            plan_args = ["--run-dir", fx.run_dir, "--runid", fx.runid,
                         "--repo-root", fx.repo, "--config", fx.config_path,
                         "--expect-config-sha", good, "--history", fx.history,
                         "--impact-json", impact_path, "--baseline-sha", fx.head,
                         "--mode", "incremental", "--contract-version", "0.16.0",
                         "--evidence", json.dumps(fx.evidence)]
            proc, events = execute("plan-dispatch.py", plan_args, fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 2, events)
            assert_child_sha(events, good)
            fx.evidence = json.loads(proc.stdout)
            measured.add("plan-dispatch.py")

            start_args = ["--run-dir", fx.run_dir, "--runid", fx.runid,
                          "--repo-root", fx.repo, "--impact-json", impact_path,
                          "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
                          "--run-class", "light", "--mode", "incremental",
                          "--config", fx.config_path, "--expect-config-sha", good,
                          "--evidence", json.dumps(fx.evidence)]
            proc, events = execute("start-run.py", start_args, fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 1, events)
            fx.evidence = json.loads(proc.stdout)
            measured.add("start-run.py")

            seal_args = ["--run-dir", fx.run_dir, "--repo-root", fx.repo,
                         "--evidence", json.dumps(fx.evidence)]
            proc, events = execute("seal-run.py", seal_args, fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 1, events)
            assert_child_sha(events, good)
            fx.evidence = json.loads(proc.stdout)
            measured.add("seal-run.py")

            self.assertEqual(fx.complete(verdicts={}).returncode, 0)
            gate_args = ["--run-dir", fx.run_dir, "--repo-root", fx.repo,
                         "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                         "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                         "--date", "2026-08-18"]
            proc, events = execute("decide-verdict.py", gate_args, fx.config_path)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(len(events), 2, events)
            assert_child_sha(events, good)
            measured.add("decide-verdict.py")

            expected = {name for name, _mode, _code, _token in CONSUMER_REGISTRY}
            self.assertEqual(measured, expected)

            raced = RunFixture(self)
            raced_impact = os.path.join(raced.repo, "impact-race.json")
            write(raced_impact, json.dumps({"impacted": []}) + "\n")
            raced_args = self._base_args(raced, raced_impact)["classify-run.py"]
            raced_good = raced_args[raced_args.index("--expect-config-sha") + 1]
            proc, events = execute(
                "classify-run.py", raced_args, raced.config_path,
                env_extra={"DOCAUDIT_SWAP_FOR": "classify-run.py",
                           "DOCAUDIT_SWAP_BYTES": '{"docGlobs":[]}\n',
                           "DOCAUDIT_SWAP_DONE": os.path.join(temp, "swap.done")})
            self.assertEqual(proc.returncode, 7, proc.stdout + proc.stderr)
            self.assertIn("sealed-config-mismatch", proc.stderr)
            self.assertEqual(len(events), 2, events)
            assert_child_sha(events, raced_good)

    def test_ct_3_toctou_taint_acceptance_flow(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        with open(fx.config_path, "rb") as handle:
            original = handle.read()
        with open(fx.config_path, "ab") as handle:
            handle.write(b" ")
        mismatch = run("mdq-index.sh", "--config", fx.config_path,
                       "--expect-config-sha", fx.evidence["config"],
                       "--repo-root", fx.repo)
        self.assertEqual(mismatch.returncode, 7)
        write(fx.config_path, original)
        tainted = fx.call(
            "decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
            "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
            "--taint-observed", "config", "--observed-by", "mdq-index.sh")
        self.assertEqual(tainted.returncode, 3, tainted.stdout + tainted.stderr)
        refused = fx.open(runid="20260818T120001Z-abcdef13")
        self.assertEqual(refused.returncode, 6, refused.stdout + refused.stderr)
        accepted = fx.open(runid="20260818T120001Z-abcdef13", accept=True)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        released = fx.call("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                           "--release", "--runid", fx.runid)
        self.assertEqual(released.returncode, 0, released.stdout + released.stderr)
        reopened = fx.open(runid="20260818T120002Z-abcdef14")
        self.assertEqual(reopened.returncode, 0, reopened.stdout + reopened.stderr)

        with open(SKILL, encoding="utf-8") as handle:
            skill = handle.read()
        stopping = skill.index("If any top-level consumer returns exit 7")
        seal_release = skill.index("Any other non-zero exit, except exit 7")
        self.assertLess(stopping, seal_release)
        seal_branch = skill[seal_release:skill.index("report `seal-run:`", seal_release)]
        for token in ("sealed-config-mismatch",
                      "--taint-observed config --observed-by seal-run.py",
                      "must not release"):
            self.assertIn(token, seal_branch)

    def test_ct_3_gate_child_detects_post_parent_config_swap(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        with tempfile.TemporaryDirectory() as temp:
            hook = textwrap.dedent(r'''
                import builtins, json, os, sys
                _builtins_open = builtins.open
                _os_open = os.open
                _target = os.environ["DOCAUDIT_COUNT_PATH"]
                _log = os.environ["DOCAUDIT_COUNT_LOG"]
                _done = os.environ["DOCAUDIT_SWAP_DONE"]
                _swap = os.environ["DOCAUDIT_SWAP_BYTES"].encode("utf-8")
                def _maybe_swap():
                    if os.path.basename(sys.argv[0]) != "change-set-sha.py": return
                    try:
                        marker = _os_open(_done, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    except FileExistsError:
                        return
                    os.close(marker)
                    replacement = _target + ".ct3-swap"
                    fd = _os_open(replacement, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    try: os.write(fd, _swap)
                    finally: os.close(fd)
                    os.replace(replacement, _target)
                def _same(path):
                    try: return os.path.realpath(os.fspath(path)) == os.path.realpath(_target)
                    except Exception: return False
                def _record(kind, path):
                    if not _same(path): return
                    with _builtins_open(_log, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"kind":kind,"argv":sys.argv}) + "\n")
                def counted_open(path, *args, **kwargs):
                    handle = _builtins_open(path, *args, **kwargs)
                    _record("builtins.open", path)
                    return handle
                def counted_os_open(path, *args, **kwargs):
                    fd = _os_open(path, *args, **kwargs)
                    _record("os.open", path)
                    return fd
                builtins.open = counted_open
                os.open = counted_os_open
                _maybe_swap()
            ''')
            write(os.path.join(temp, "sitecustomize.py"), hook)
            log = os.path.join(temp, "opens.log")
            write(log, "")
            changed = dict(fx.config, ct3Race=True)
            env = dict(
                os.environ, PYTHONPATH=temp, DOCAUDIT_COUNT_PATH=fx.config_path,
                DOCAUDIT_COUNT_LOG=log,
                DOCAUDIT_SWAP_DONE=os.path.join(temp, "swap.done"),
                DOCAUDIT_SWAP_BYTES=json.dumps(changed, sort_keys=True) + "\n")
            proc = subprocess.run(
                [sys.executable, script("decide-verdict.py"),
                 "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                 "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                 "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                 "--date", "2026-08-18"],
                capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["reason"], "config-changed")
            with open(fx.last_run, encoding="utf-8") as handle:
                last_run = json.load(handle)
            self.assertTrue(last_run["configAcceptanceRequired"])
            self.assertEqual(last_run["expectedConfigSha"], fx.evidence["config"])
            self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))
            with open(log, encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle]
            self.assertTrue(any(os.path.basename(item["argv"][0]) == "change-set-sha.py"
                                for item in events))

    def test_ct_3b_taint_nonownership_is_non_mutating(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        lock = os.path.join(fx.run_base, "lock")
        with open(lock, "rb") as handle:
            before = handle.read()
        history_existed = os.path.exists(fx.history)
        history_before = None
        if history_existed:
            with open(fx.history, "rb") as handle:
                history_before = handle.read()
        cases = [
            ("20260818T120009Z-abcdef99", fx.run_dir, fx.evidence),
            (fx.runid, fx.run_dir + "-wrong", fx.evidence),
            (fx.runid, fx.run_dir, dict(fx.evidence, lockIno=fx.evidence["lockIno"] + 1)),
        ]
        for runid, run_dir, evidence in cases:
            with self.subTest(runid=runid, run_dir=run_dir):
                proc = fx.call(
                    "decide-verdict.py", "--run-dir", run_dir, "--repo-root", fx.repo,
                    "--runid", runid, "--expect-json", json.dumps(evidence),
                    "--taint-observed", "config", "--observed-by", "mdq-index.sh")
                self.assertEqual(proc.returncode, 3)
                with open(lock, "rb") as handle:
                    self.assertEqual(handle.read(), before)
                self.assertFalse(os.path.exists(fx.last_run))
                self.assertEqual(os.path.exists(fx.history), history_existed)
                if history_existed:
                    with open(fx.history, "rb") as handle:
                        self.assertEqual(handle.read(), history_before)

        missing = RunFixture(self)
        self.assertEqual(missing.open().returncode, 0)
        missing_lock = os.path.join(missing.run_base, "lock")
        os.unlink(missing_lock)
        proc = missing.call(
            "decide-verdict.py", "--run-dir", missing.run_dir,
            "--repo-root", missing.repo, "--runid", missing.runid,
            "--expect-json", json.dumps(missing.evidence),
            "--taint-observed", "config", "--observed-by", "mdq-index.sh")
        self.assertEqual(proc.returncode, 3)
        self.assertFalse(os.path.exists(missing.last_run))
        self.assertFalse(os.path.exists(missing.history))

        held = RunFixture(self)
        self.assertEqual(held.open().returncode, 0)
        held_lock = os.path.join(held.run_base, "lock")
        write(held.history, json.dumps({"entries": [], "phase4Runs": []}) + "\n")
        with open(held_lock, "rb") as handle:
            held_lock_before = handle.read()
        with open(held.history, "rb") as handle:
            held_history_before = handle.read()
        locker = subprocess.Popen(
            [sys.executable, "-c", textwrap.dedent('''
                import fcntl, os, sys
                fd = os.open(sys.argv[1], os.O_RDWR)
                fcntl.flock(fd, fcntl.LOCK_EX)
                print("ready", flush=True)
                sys.stdin.readline()
                os.close(fd)
            '''), held_lock], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: locker.poll() is None and locker.kill())
        self.assertEqual(locker.stdout.readline().strip(), "ready")
        try:
            proc = held.call(
                "decide-verdict.py", "--run-dir", held.run_dir,
                "--repo-root", held.repo, "--runid", held.runid,
                "--expect-json", json.dumps(held.evidence),
                "--taint-observed", "config", "--observed-by", "mdq-index.sh")
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("lock is held by another process", proc.stdout)
            with open(held_lock, "rb") as handle:
                self.assertEqual(handle.read(), held_lock_before)
            with open(held.history, "rb") as handle:
                self.assertEqual(handle.read(), held_history_before)
            self.assertFalse(os.path.exists(held.last_run))
        finally:
            locker.communicate("\n", timeout=5)

    def test_ct_4_and_4c_open_run_recovery_suite(self):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(wp12_tests.TestOpenRun)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        self.assertTrue(result.wasSuccessful(), stream.getvalue())

    def test_ct_4b_harness_compatibility_contract(self):
        with open(SKILL, encoding="utf-8") as handle:
            skill = handle.read()
        self.assertIn("Only a stamp exactly equal to `0.19.0`", skill)
        self.assertIn("older, future, missing, invalid, or modified", skill)
        self.assertIn("do not run the copy", skill)
        self.assertIn("--expect-config-sha \"$CONFIG_SHA\"", skill)

    def test_ct_4d_plan_dispatch_history_mismatch_funnel(self):
        with open(script("plan-dispatch.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("sealed-history-mismatch: expected", source)
        self.assertIn("return 7", source)
        with open(SKILL, encoding="utf-8") as handle:
            skill = handle.read()
        self.assertIn("--taint-observed history --observed-by plan-dispatch.py", skill)

        fx = RunFixture(self)
        write(fx.history, json.dumps({"entries": [], "phase4Runs": []}) + "\n")
        self.assertEqual(fx.open().returncode, 0)
        impact_path = os.path.join(fx.run_dir, "impact-history-mismatch.json")
        write(impact_path, json.dumps({"impacted": [], "historySha": BAD_SHA}) + "\n")
        proc = fx.call(
            "plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--config", fx.config_path,
            "--expect-config-sha", fx.evidence["config"], "--history", fx.history,
            "--impact-json", impact_path, "--baseline-sha", fx.head,
            "--mode", "incremental", "--contract-version", "0.16.0",
            "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 7, proc.stdout + proc.stderr)
        self.assertIn("sealed-history-mismatch", proc.stderr)
        tainted = fx.call(
            "decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
            "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
            "--taint-observed", "history", "--observed-by", "plan-dispatch.py")
        self.assertEqual(tainted.returncode, 3, tainted.stdout + tainted.stderr)
        self.assertFalse(os.path.exists(fx.history))
        quarantined = [name for name in os.listdir(os.path.dirname(fx.history))
                       if name.startswith("docaudit-history.json.tainted-")]
        self.assertEqual(len(quarantined), 1)
        with open(fx.last_run, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["reason"], "history-changed")

    def test_ct_5b_complete_phase4_eligibility_table(self):
        module = load_module("decide-verdict.py")
        valid = {
            ("full", "full", "completed"): True,
            ("full", "full", "execution-failed"): False,
            ("full", None, "skipped-full-run"): False,
            ("full", None, "not-active"): False,
            ("incremental", "diff", "completed"): False,
            ("incremental", "diff", "execution-failed"): False,
            ("incremental", None, "ref-invalid"): False,
            ("incremental", None, "not-active"): False,
        }
        with tempfile.TemporaryDirectory() as repo:
            for (mode, variant, state), eligible in valid.items():
                with self.subTest(mode=mode, variant=variant, state=state):
                    phase4 = {"findings": [], "codexReview": {
                        "state": state, "promptVariant": variant,
                        "carryForwardSha": "none"}}
                    got, _codex, _normalized, _unresolved = module.validate_phase4_contract(
                        repo, {"mode": mode}, phase4)
                    self.assertEqual(got, eligible)
            invalid = [
                {"state": "completed", "carryForwardSha": "none"},
                {"state": "completed", "promptVariant": "diff"},
                {"state": "completed", "promptVariant": "full",
                 "carryForwardSha": 1},
                {"state": "future", "promptVariant": "diff", "carryForwardSha": "none"},
                {"state": "completed", "promptVariant": None, "carryForwardSha": "none"},
                {"state": "not-active", "promptVariant": "full", "carryForwardSha": "none"},
                {"state": "completed", "promptVariant": "full", "carryForwardSha": "none"},
            ]
            modes = ["full", "incremental", "full", "incremental", "incremental",
                     "full", "incremental"]
            for codex, mode in zip(invalid, modes):
                with self.subTest(invalid=codex, mode=mode):
                    with self.assertRaises(module.Refused):
                        module.validate_phase4_contract(
                            repo, {"mode": mode}, {"findings": [], "codexReview": codex})

    def test_ct_5_history_path_and_carry_contract_suites(self):
        suite = unittest.TestSuite()
        for case in (history_tests.TestHistoryDocument,
                     history_tests.TestNormalizeFindingPath,
                     history_tests.TestCarryForward):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        self.assertTrue(result.wasSuccessful(), stream.getvalue())

    def test_ct_5_gate_records_and_measures_four_key_flips(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})

        def full_phase(file_name, carry_sha="none"):
            return {
                "findings": [{"source": "codex-review", "file": file_name,
                              "severity": "HIGH", "title": "sample"}],
                "codexReview": {"state": "completed", "promptVariant": "full",
                                "carryForwardSha": carry_sha},
            }

        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode="full", contract="0.16.0").returncode, 0)
        self.assertEqual(fx.complete(phase4=full_phase("./docs/a.md")).returncode, 0)
        first = fx.gate()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(json.loads(first.stdout)["counts"]["phase4FlipsUnchangedContent"], 0)
        with open(fx.history, encoding="utf-8") as handle:
            first_history = json.load(handle)
        self.assertEqual(first_history["phase4Runs"][0]["findings"],
                         [{"file": "docs/a.md", "severity": "HIGH"}])

        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode="full", contract="0.16.0").returncode, 0)
        self.assertEqual(fx.complete(phase4=full_phase("docs/b.md:10")).returncode, 0)
        second = fx.gate()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        second_result = json.loads(second.stdout)
        self.assertEqual(second_result["counts"]["phase4FlipsUnchangedContent"], 2)
        self.assertTrue(any("Phase-4 instability: 2 file(s)" in warning
                            for warning in second_result["warnings"]))
        with open(fx.history, encoding="utf-8") as handle:
            second_history = json.load(handle)
        self.assertEqual(len(second_history["phase4Runs"]), 2)

        self.assertEqual(fx.open(runid="20260818T120002Z-abcdef14").returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode="full", contract="0.16.0").returncode, 0)
        different_carry = "sha256:" + "2" * 64
        self.assertEqual(
            fx.complete(phase4=full_phase("docs/a.md", different_carry)).returncode, 0)
        third = fx.gate()
        self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
        self.assertEqual(json.loads(third.stdout)["counts"]["phase4FlipsUnchangedContent"], 0)

    def test_ct_6_codex_review_plan_suite(self):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            codex_plan_tests.TestCodexReviewPlan)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        self.assertTrue(result.wasSuccessful(), stream.getvalue())

    def test_ct_6_history_mismatch_taint_quarantine_and_cold_start(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.assertEqual(fx.open().returncode, 0)
        history = {
            "entries": [],
            "phase4Runs": [{
                "runid": "20260817T120000Z-abcdef11", "ts": "2026-08-17T12:00:00Z",
                "worktreeDigest": "sha256:" + "1" * 64,
                "contractVersion": "0.16.0", "configSha": fx.evidence["config"],
                "carryForwardSha": "none", "unresolvedFileCount": 0,
                "truncated": False,
                "findings": [{"file": "docs/a.md", "severity": "HIGH"}],
            }],
        }
        write(fx.history, json.dumps(history, sort_keys=True) + "\n")
        args = [
            "--mode", "full", "--repo-root", fx.repo,
            "--config", fx.config_path, "--expect-config-sha", fx.evidence["config"],
            "--available", "true", "--baseline-ok", "true",
            "--history", fx.history, "--expect-history-sha", BAD_SHA,
            "--worktree-digest", "sha256:" + "2" * 64,
        ]
        mismatch = run("codex-review-plan.py", *args, cwd=fx.repo)
        self.assertEqual(mismatch.returncode, 7, mismatch.stdout + mismatch.stderr)
        self.assertIn("sealed-history-mismatch", mismatch.stderr)
        tainted = fx.call(
            "decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
            "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
            "--taint-observed", "history", "--observed-by", "codex-review-plan.py")
        self.assertEqual(tainted.returncode, 3, tainted.stdout + tainted.stderr)
        self.assertFalse(os.path.exists(fx.history))
        state_dir = os.path.dirname(fx.history)
        self.assertEqual(len([name for name in os.listdir(state_dir)
                              if name.startswith("docaudit-history.json.tainted-")]), 1)
        self.assertEqual(
            fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        cold_args = list(args)
        cold_args[cold_args.index(BAD_SHA)] = "none"
        cold = run("codex-review-plan.py", *cold_args, cwd=ROOT)
        self.assertEqual(cold.returncode, 0, cold.stdout + cold.stderr)
        cold_result = json.loads(cold.stdout)
        self.assertIsNone(cold_result["carryForward"])
        self.assertEqual(cold_result["carryForwardSha"], "none")

    def test_ct_7_document_contracts(self):
        paths = [
            "docs/ADOPTION.md", "docs/ADOPTION.ja.md", "README.md",
            "skills/audit/SKILL.md", "skills/audit/references/config-schema.md",
        ]
        texts = {}
        for relative in paths:
            with open(os.path.join(ROOT, relative), encoding="utf-8") as handle:
                texts[relative] = handle.read()
        joined = "\n".join(texts.values())
        for token in ("phase4FlipsUnchangedContent", "--expect-config-sha",
                      "sealed-config-mismatch", "configAcceptanceRequired"):
            self.assertIn(token, joined)
        self.assertIn("entire plugin tree", texts["docs/ADOPTION.md"])
        self.assertIn("plugin tree 全体", texts["docs/ADOPTION.ja.md"])
        self.assertIn("older, future, missing, invalid, or modified", texts["skills/audit/SKILL.md"])
        self.assertIn("repository-writer level", joined)


if __name__ == "__main__":
    unittest.main()
