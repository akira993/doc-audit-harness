"""End-to-end tests for sealed Phase-4 Codex review execution."""

import base64
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEC = os.path.join(ROOT, "skills", "audit", "scripts", "codex-review-exec.py")
SCHEMA = os.path.join(
    ROOT, "skills", "audit", "references", "codex-review-output.schema.json")
MAX_MANIFEST = 1024 * 1024
MAX_RESULT = 2 * 1024 * 1024
BAD_SHA = "sha256:" + "0" * 64


FAKE_CODEX = r'''#!/usr/bin/env python3
import base64
import json
import os
import signal
import subprocess
import sys
import time


args = sys.argv[1:]
prompt = sys.stdin.buffer.read()


def option(name):
    index = args.index(name)
    return args[index + 1]


output = option("-o")
model = option("-m")
record = {
    "args": args,
    "model": model,
    "output": output,
    "stdinB64": base64.b64encode(prompt).decode("ascii"),
}
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def emit():
    with open(os.environ["FAKE_PAYLOAD"], "rb") as source:
        raw = source.read()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


mode = os.environ.get("FAKE_MODE", "success")
if mode == "success":
    emit()
elif mode == "missing":
    pass
elif mode == "always_fail":
    raise SystemExit(7)
elif mode == "nonzero_valid_then_missing":
    if model == "gpt-5.6-luna":
        emit()
        raise SystemExit(7)
elif mode == "noise":
    os.write(1, b"o" * (4 * 1024 * 1024))
    os.write(2, b"e" * (4 * 1024 * 1024))
    emit()
elif mode == "symlink":
    os.symlink(os.environ["FAKE_SYMLINK_TARGET"], output)
elif mode == "fifo":
    os.mkfifo(output)
elif mode == "timeout_then_success":
    if model == "gpt-5.6-luna":
        child = r"""
import os
import signal
import sys
import time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(1.5)
with open(sys.argv[2], "rb") as source:
    raw = source.read()
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    os.write(fd, raw)
finally:
    os.close(fd)
"""
        subprocess.Popen([sys.executable, "-c", child, output,
                          os.environ["FAKE_PAYLOAD"]])
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(10)
    else:
        emit()
else:
    raise SystemExit(9)
'''


def tagged_sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def valid_result_bytes(size=None):
    prefix = b'{"findings":[{"severity":"low","title":"'
    suffix = b'","file":"docs/a.md"}]}'
    if size is None:
        return prefix + b"checked" + suffix
    padding = size - len(prefix) - len(suffix)
    if padding < 1:
        raise ValueError("requested result size is too small")
    raw = prefix + (b"x" * padding) + suffix
    if len(raw) != size:
        raise AssertionError("result size construction failed")
    return raw


class CodexReviewExecFixture:
    def __init__(self, case, *, run_class="light", model=None, timeout_ms=2000):
        self.case = case
        self.temp = tempfile.TemporaryDirectory()
        case.addCleanup(self.temp.cleanup)
        self.repo = os.path.join(self.temp.name, "repo")
        self.runid = "20260905T120000Z-c0decafe"
        self.run_dir = os.path.join(
            self.repo, ".claude", "state", "docaudit-run", self.runid)
        self.control = os.path.join(self.temp.name, "control")
        os.makedirs(self.run_dir)
        os.makedirs(self.control)
        self.fake = os.path.join(self.control, "codex")
        with open(self.fake, "w", encoding="utf-8") as handle:
            handle.write(FAKE_CODEX)
        os.chmod(self.fake, 0o755)
        self.log = os.path.join(self.control, "calls.jsonl")
        self.payload_path = os.path.join(self.control, "payload.bin")
        self.symlink_target = os.path.join(self.control, "symlink-target.json")
        self.config_path = os.path.join(self.control, "doc-audit.json")
        self.manifest_path = os.path.join(self.run_dir, "manifest.json")
        self.prompt_path = os.path.join(self.run_dir, "codex-review-prompt.txt")
        self.result_path = os.path.join(self.run_dir, "codex-review-result.json")
        self.prompt = "PROMPT sentinel\n二行目\n".encode("utf-8")
        self.payload = valid_result_bytes()
        self._write(self.prompt_path, self.prompt)
        self.set_payload(self.payload)
        self.config = {"codexReview": {"bin": self.fake, "timeoutMs": timeout_ms}}
        if model is not None:
            self.config["codexReview"]["model"] = model
        self.evidence = {
            "runid": self.runid,
            "runDir": self.run_dir,
            "config": "",
            "manifest": "",
            "codexReviewResult": "none",
        }
        self.write_config()
        self.manifest = {
            "sealed": True,
            "runid": self.runid,
            "runClass": run_class,
            "excludeDocGlobs": [],
            "respectGitignore": True,
        }
        self.write_manifest()

    @staticmethod
    def _write(path, raw):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(raw)

    def set_payload(self, raw):
        self.payload = raw
        self._write(self.payload_path, raw)

    def write_config(self):
        raw = json_bytes(self.config)
        self._write(self.config_path, raw)
        self.config_sha = tagged_sha(raw)
        if hasattr(self, "evidence"):
            self.evidence["config"] = self.config_sha

    def write_manifest(self, raw=None):
        raw = json_bytes(self.manifest) if raw is None else raw
        self._write(self.manifest_path, raw)
        self.manifest_raw = raw
        self.evidence["manifest"] = tagged_sha(raw)

    def prepare_other_run_dir(self, path, manifest=None, prompt=None):
        os.makedirs(path, exist_ok=True)
        raw = json_bytes(self.manifest if manifest is None else manifest)
        self._write(os.path.join(path, "manifest.json"), raw)
        self._write(os.path.join(path, "codex-review-prompt.txt"),
                    self.prompt if prompt is None else prompt)
        return raw

    def run(self, *, mode="success", evidence=None, expect_config_sha=None,
            run_dir=None, repo_root=None, timeout=8):
        selected_evidence = self.evidence if evidence is None else evidence
        env = os.environ.copy()
        env.update({
            "FAKE_MODE": mode,
            "FAKE_LOG": self.log,
            "FAKE_PAYLOAD": self.payload_path,
            "FAKE_SYMLINK_TARGET": self.symlink_target,
        })
        command = [
            sys.executable, EXEC,
            "--run-dir", self.run_dir if run_dir is None else run_dir,
            "--repo-root", self.repo if repo_root is None else repo_root,
            "--config", self.config_path,
            "--expect-config-sha", (self.config_sha if expect_config_sha is None
                                      else expect_config_sha),
            "--evidence", json.dumps(selected_evidence, ensure_ascii=False),
        ]
        return subprocess.run(
            command, capture_output=True, text=True, env=env, timeout=timeout)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def diagnostic(self, proc):
        lines = proc.stderr.splitlines()
        self.case.assertEqual(len(lines), 1, proc.stderr)
        return json.loads(lines[0])


class TestCodexReviewExec(unittest.TestCase):
    maxDiff = None

    def assert_call_contract(self, fixture, call, model):
        args = call["args"]
        output = call["output"]
        self.assertEqual(call["model"], model)
        self.assertEqual(args, [
            "exec", "-C", os.path.realpath(fixture.repo),
            "-s", "read-only", "-m", model,
            "-c", "model_reasoning_effort=medium",
            "--output-schema", SCHEMA, "-o", output, "-",
        ])
        self.assertEqual(base64.b64decode(call["stdinB64"]), fixture.prompt)
        self.assertEqual(os.path.basename(output), "out.json")
        self.assertEqual(os.path.dirname(output), os.path.realpath(os.path.dirname(output)))
        real_run_dir = os.path.realpath(fixture.run_dir)
        self.assertEqual(os.path.commonpath([real_run_dir, output]), real_run_dir)
        self.assertNotIn("review", args)
        self.assertNotIn("--base", args)

    def assert_attempt_shape(self, attempt):
        self.assertEqual(set(attempt), {
            "attempt", "model", "modelSource", "exit", "timedOut",
            "outputPresent", "schemaValid", "reason",
        })

    def assert_engine_rejected(self, fixture, proc, before_evidence, before_calls=0):
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(fixture.evidence, before_evidence)
        self.assertEqual(len(fixture.calls()), before_calls)
        diagnostic = fixture.diagnostic(proc)
        self.assertEqual(diagnostic["state"], "engine-error")
        self.assertIsInstance(diagnostic.get("reason"), str)

    def assert_execution_failed(self, fixture, proc, attempts=None):
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        output = json.loads(proc.stdout)
        self.assertEqual(output["codexReviewResult"], "failed")
        diagnostic = fixture.diagnostic(proc)
        self.assertEqual(diagnostic["state"], "execution-failed")
        if attempts is not None:
            self.assertEqual(len(diagnostic["attempts"]), attempts)
        for item in diagnostic["attempts"]:
            self.assert_attempt_shape(item)
        return diagnostic

    def test_success_preserves_noncanonical_result_bytes_and_seals_sha(self):
        fixture = CodexReviewExecFixture(self)
        raw = ('{\n  "findings" : [ { "severity" : "high", '
               '"title" : "要確認", "file" : "docs/案内.md" } ]\n}\n').encode("utf-8")
        fixture.set_payload(raw)
        proc = fixture.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(fixture.result_path, "rb") as handle:
            self.assertEqual(handle.read(), raw)
        self.assertEqual(json.loads(proc.stdout)["codexReviewResult"], tagged_sha(raw))
        diagnostic = fixture.diagnostic(proc)
        self.assertEqual(diagnostic["state"], "completed")
        self.assertEqual(len(diagnostic["attempts"]), 1)
        self.assert_attempt_shape(diagnostic["attempts"][0])
        self.assertTrue(diagnostic["attempts"][0]["schemaValid"])
        calls = fixture.calls()
        self.assertEqual(len(calls), 1)
        self.assert_call_contract(fixture, calls[0], "gpt-5.6-luna")
        mode = stat.S_IMODE(os.stat(os.path.dirname(calls[0]["output"])).st_mode)
        self.assertEqual(mode, 0o700)
        self.assertFalse(any(name.startswith(".codex-review-result.")
                             for name in os.listdir(fixture.run_dir)))

    def test_nonzero_valid_first_attempt_is_not_reused_by_empty_retry(self):
        fixture = CodexReviewExecFixture(self)
        proc = fixture.run(mode="nonzero_valid_then_missing")
        diagnostic = self.assert_execution_failed(fixture, proc, attempts=2)
        calls = fixture.calls()
        self.assertEqual([item["model"] for item in calls],
                         ["gpt-5.6-luna", "gpt-5.6-terra"])
        self.assertTrue(os.path.isfile(calls[0]["output"]))
        self.assertFalse(os.path.exists(calls[1]["output"]))
        self.assertFalse(os.path.exists(fixture.result_path))
        self.assertEqual(diagnostic["attempts"][0]["exit"], 7)
        self.assertTrue(diagnostic["attempts"][0]["outputPresent"])
        self.assertFalse(diagnostic["attempts"][1]["outputPresent"])

    def test_timeout_kills_grandchild_and_retry_cannot_be_contaminated(self):
        fixture = CodexReviewExecFixture(self, timeout_ms=500)
        proc = fixture.run(mode="timeout_then_success")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        diagnostic = fixture.diagnostic(proc)
        self.assertEqual(diagnostic["state"], "completed")
        self.assertEqual(len(diagnostic["attempts"]), 2)
        self.assertTrue(diagnostic["attempts"][0]["timedOut"])
        self.assertFalse(diagnostic["attempts"][1]["timedOut"])
        calls = fixture.calls()
        self.assertEqual([item["model"] for item in calls],
                         ["gpt-5.6-luna", "gpt-5.6-terra"])
        time.sleep(1.8)
        self.assertFalse(os.path.exists(calls[0]["output"]))
        self.assertTrue(os.path.isfile(calls[1]["output"]))
        with open(fixture.result_path, "rb") as handle:
            self.assertEqual(handle.read(), fixture.payload)

    def test_invalid_utf8_and_json_degrade_without_publication(self):
        cases = (b"\xff", b'{"findings":[')
        for raw in cases:
            with self.subTest(raw=raw):
                fixture = CodexReviewExecFixture(self, run_class="standard")
                fixture.set_payload(raw)
                proc = fixture.run()
                self.assert_execution_failed(fixture, proc, attempts=1)
                self.assertFalse(os.path.exists(fixture.result_path))

    def test_result_schema_boundaries_are_rejected(self):
        invalid = {
            "top_level_extra": {"findings": [], "extra": True},
            "finding_extra": {"findings": [{"severity": "low", "title": "t",
                                                "file": "docs/a.md", "extra": True}]},
            "empty_title": {"findings": [{"severity": "low", "title": "",
                                             "file": "docs/a.md"}]},
            "missing_file": {"findings": [{"severity": "low", "title": "t"}]},
            "wrong_severity": {"findings": [{"severity": "warning", "title": "t",
                                                "file": "docs/a.md"}]},
            "findings_not_array": {"findings": {}},
            "top_level_array": [],
            "top_level_null": None,
        }
        for name, value in invalid.items():
            with self.subTest(name=name):
                fixture = CodexReviewExecFixture(self, run_class="standard")
                fixture.set_payload(json_bytes(value))
                proc = fixture.run()
                diagnostic = self.assert_execution_failed(fixture, proc, attempts=1)
                self.assertTrue(diagnostic["attempts"][0]["outputPresent"])
                self.assertFalse(diagnostic["attempts"][0]["schemaValid"])
                self.assertFalse(os.path.exists(fixture.result_path))

    def test_explicit_model_failure_has_no_retry(self):
        fixture = CodexReviewExecFixture(self, model="review-model")
        proc = fixture.run(mode="always_fail")
        diagnostic = self.assert_execution_failed(fixture, proc, attempts=1)
        self.assertEqual(diagnostic["attempts"][0]["modelSource"], "explicit")
        calls = fixture.calls()
        self.assertEqual([item["model"] for item in calls], ["review-model"])
        self.assert_call_contract(fixture, calls[0], "review-model")

    def test_standard_default_failure_has_no_retry(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        proc = fixture.run(mode="always_fail")
        diagnostic = self.assert_execution_failed(fixture, proc, attempts=1)
        self.assertEqual(diagnostic["attempts"][0]["modelSource"], "default")
        self.assertEqual([item["model"] for item in fixture.calls()],
                         ["gpt-5.6-terra"])

    def test_light_default_failure_retries_once_with_terra(self):
        fixture = CodexReviewExecFixture(self)
        proc = fixture.run(mode="always_fail")
        diagnostic = self.assert_execution_failed(fixture, proc, attempts=2)
        self.assertEqual([item["modelSource"] for item in diagnostic["attempts"]],
                         ["default", "default"])
        self.assertEqual([item["model"] for item in fixture.calls()],
                         ["gpt-5.6-luna", "gpt-5.6-terra"])

    def test_empty_model_is_default_and_retries_once(self):
        fixture = CodexReviewExecFixture(self, model="")
        proc = fixture.run(mode="always_fail")
        diagnostic = self.assert_execution_failed(fixture, proc, attempts=2)
        self.assertEqual([item["modelSource"] for item in diagnostic["attempts"]],
                         ["default", "default"])
        self.assertEqual([item["model"] for item in fixture.calls()],
                         ["gpt-5.6-luna", "gpt-5.6-terra"])

    def test_large_stdout_and_stderr_do_not_block(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        proc = fixture.run(mode="noise", timeout=5)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(fixture.diagnostic(proc)["state"], "completed")
        self.assertEqual(len(fixture.calls()), 1)

    def test_result_size_limit_accepts_exactly_two_mib(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        raw = valid_result_bytes(MAX_RESULT)
        fixture.set_payload(raw)
        proc = fixture.run(timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["codexReviewResult"], tagged_sha(raw))
        self.assertEqual(os.path.getsize(fixture.result_path), MAX_RESULT)

    def test_result_size_limit_rejects_two_mib_plus_one(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        fixture.set_payload(valid_result_bytes(MAX_RESULT + 1))
        proc = fixture.run(timeout=10)
        self.assert_execution_failed(fixture, proc, attempts=1)
        self.assertFalse(os.path.exists(fixture.result_path))

    def test_result_with_501_findings_is_accepted(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        result = {"findings": [
            {"severity": "low", "title": "finding %d" % index,
             "file": "docs/a.md"}
            for index in range(501)
        ]}
        raw = json_bytes(result)
        fixture.set_payload(raw)
        proc = fixture.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["codexReviewResult"], tagged_sha(raw))

    def test_existing_attempt_directory_is_never_reused(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        occupied = os.path.join(fixture.run_dir, "codex-review-attempt-01")
        os.mkdir(occupied, 0o700)
        sentinel = os.path.join(occupied, "out.json")
        fixture._write(sentinel, b"sentinel")
        proc = fixture.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        output = fixture.calls()[0]["output"]
        self.assertNotEqual(os.path.dirname(output), occupied)
        with open(sentinel, "rb") as handle:
            self.assertEqual(handle.read(), b"sentinel")

    def test_same_run_reexecution_allocates_a_fresh_attempt_directory(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        first = fixture.run()
        second = fixture.run()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        outputs = [item["output"] for item in fixture.calls()]
        self.assertEqual(len(outputs), 2)
        self.assertNotEqual(os.path.dirname(outputs[0]), os.path.dirname(outputs[1]))
        self.assertTrue(all(os.path.isfile(path) for path in outputs))

    def test_missing_output_and_missing_binary_are_execution_failures(self):
        missing = CodexReviewExecFixture(self, run_class="standard")
        self.assert_execution_failed(missing, missing.run(mode="missing"), attempts=1)
        self.assertFalse(os.path.exists(missing.result_path))

        binary = CodexReviewExecFixture(self)
        binary.config["codexReview"]["bin"] = os.path.join(binary.control, "absent-codex")
        binary.write_config()
        proc = binary.run()
        diagnostic = self.assert_execution_failed(binary, proc, attempts=2)
        self.assertEqual(binary.calls(), [])
        self.assertTrue(all(item["exit"] is None for item in diagnostic["attempts"]))

    def test_identity_four_conditions_fail_before_codex_and_preserve_evidence(self):
        cases = []

        config = CodexReviewExecFixture(self)
        cases.append(("config_sha", config, {}, {"expect_config_sha": BAD_SHA}))

        evidence_dir = CodexReviewExecFixture(self)
        changed = copy.deepcopy(evidence_dir.evidence)
        changed["runDir"] = os.path.join(evidence_dir.temp.name, "different")
        os.makedirs(changed["runDir"])
        cases.append(("evidence_run_dir", evidence_dir, changed, {}))

        ledger = CodexReviewExecFixture(self)
        outside = os.path.join(ledger.repo, "outside", ledger.runid)
        raw = ledger.prepare_other_run_dir(outside)
        changed = copy.deepcopy(ledger.evidence)
        changed["runDir"] = outside
        changed["manifest"] = tagged_sha(raw)
        cases.append(("outside_ledger", ledger, changed, {"run_dir": outside}))

        runid = CodexReviewExecFixture(self)
        changed = copy.deepcopy(runid.evidence)
        changed["runid"] = "20260905T120000Z-deadbeef"
        cases.append(("evidence_runid", runid, changed, {}))

        for name, fixture, evidence, kwargs in cases:
            with self.subTest(name=name):
                selected = fixture.evidence if not evidence else evidence
                before = copy.deepcopy(fixture.evidence)
                proc = fixture.run(evidence=selected, **kwargs)
                self.assert_engine_rejected(fixture, proc, before)

    def test_identity_type_boundaries_fail_closed(self):
        cases = []
        for value in (None, []):
            fixture = CodexReviewExecFixture(self)
            evidence = copy.deepcopy(fixture.evidence)
            evidence["runDir"] = value
            cases.append(("evidence_run_dir_%r" % (value,), fixture, evidence, {}))

        for value in (None, []):
            fixture = CodexReviewExecFixture(self)
            fixture.manifest["runid"] = value
            fixture.write_manifest()
            evidence = copy.deepcopy(fixture.evidence)
            evidence["runid"] = value
            cases.append(("manifest_runid_%r" % (value,), fixture, evidence, {}))

        invalid = CodexReviewExecFixture(self)
        bad_runid = "not-a-run"
        bad_dir = os.path.join(invalid.repo, ".claude", "state", "docaudit-run", bad_runid)
        manifest = dict(invalid.manifest, runid=bad_runid)
        raw = invalid.prepare_other_run_dir(bad_dir, manifest=manifest)
        evidence = copy.deepcopy(invalid.evidence)
        evidence.update({"runid": bad_runid, "runDir": bad_dir, "manifest": tagged_sha(raw)})
        cases.append(("invalid_runid", invalid, evidence, {"run_dir": bad_dir}))

        config_sha = CodexReviewExecFixture(self)
        evidence = copy.deepcopy(config_sha.evidence)
        evidence["config"] = "bad"
        cases.append(("malformed_equal_config_sha", config_sha, evidence,
                      {"expect_config_sha": "bad"}))

        manifest_sha = CodexReviewExecFixture(self)
        evidence = copy.deepcopy(manifest_sha.evidence)
        evidence["manifest"] = "bad"
        cases.append(("malformed_manifest_sha", manifest_sha, evidence, {}))

        for name, fixture, evidence, kwargs in cases:
            with self.subTest(name=name):
                before = copy.deepcopy(fixture.evidence)
                proc = fixture.run(evidence=evidence, **kwargs)
                self.assert_engine_rejected(fixture, proc, before)

    def test_manifest_safe_reader_contract(self):
        for kind in ("symlink", "fifo", "limit", "over"):
            with self.subTest(kind=kind):
                fixture = CodexReviewExecFixture(self, run_class="standard")
                if kind == "symlink":
                    target = os.path.join(fixture.control, "manifest-target.json")
                    fixture._write(target, fixture.manifest_raw)
                    os.unlink(fixture.manifest_path)
                    os.symlink(target, fixture.manifest_path)
                elif kind == "fifo":
                    os.unlink(fixture.manifest_path)
                    os.mkfifo(fixture.manifest_path)
                else:
                    prefix = (
                        '{"sealed":true,"runid":"%s","runClass":"standard",'
                        '"excludeDocGlobs":[],"respectGitignore":true,"padding":"'
                        % fixture.runid).encode("ascii")
                    suffix = b'"}'
                    size = MAX_MANIFEST + (1 if kind == "over" else 0)
                    raw = prefix + b"x" * (size - len(prefix) - len(suffix)) + suffix
                    self.assertEqual(len(raw), size)
                    fixture.write_manifest(raw)
                before = copy.deepcopy(fixture.evidence)
                proc = fixture.run(timeout=5)
                if kind == "limit":
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertEqual(len(fixture.calls()), 1)
                else:
                    self.assert_engine_rejected(fixture, proc, before)

    def test_prompt_safe_reader_contract(self):
        for kind in ("symlink", "fifo", "limit", "over"):
            with self.subTest(kind=kind):
                fixture = CodexReviewExecFixture(self, run_class="standard")
                if kind == "symlink":
                    target = os.path.join(fixture.control, "prompt-target.txt")
                    fixture._write(target, fixture.prompt)
                    os.unlink(fixture.prompt_path)
                    os.symlink(target, fixture.prompt_path)
                elif kind == "fifo":
                    os.unlink(fixture.prompt_path)
                    os.mkfifo(fixture.prompt_path)
                else:
                    size = MAX_RESULT + (1 if kind == "over" else 0)
                    fixture.prompt = b"p" * size
                    fixture._write(fixture.prompt_path, fixture.prompt)
                before = copy.deepcopy(fixture.evidence)
                proc = fixture.run(timeout=5)
                if kind == "limit":
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertEqual(base64.b64decode(fixture.calls()[0]["stdinB64"]),
                                     fixture.prompt)
                else:
                    self.assert_engine_rejected(fixture, proc, before)

    def test_result_safe_reader_rejects_symlink_and_fifo_without_hanging(self):
        for mode in ("symlink", "fifo"):
            with self.subTest(mode=mode):
                fixture = CodexReviewExecFixture(self, run_class="standard")
                fixture._write(fixture.symlink_target, fixture.payload)
                proc = fixture.run(mode=mode, timeout=5)
                diagnostic = self.assert_execution_failed(fixture, proc, attempts=1)
                self.assertTrue(diagnostic["attempts"][0]["outputPresent"])
                self.assertFalse(os.path.isfile(fixture.result_path))

    def test_missing_prompt_is_engine_error(self):
        fixture = CodexReviewExecFixture(self)
        os.unlink(fixture.prompt_path)
        before = copy.deepcopy(fixture.evidence)
        self.assert_engine_rejected(fixture, fixture.run(), before)

    def test_publication_failure_is_engine_error_not_execution_failure(self):
        fixture = CodexReviewExecFixture(self, run_class="standard")
        os.mkdir(fixture.result_path)
        before = copy.deepcopy(fixture.evidence)
        proc = fixture.run()
        self.assertEqual(len(fixture.calls()), 1)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(fixture.evidence, before)
        diagnostic = fixture.diagnostic(proc)
        self.assertEqual(diagnostic["state"], "engine-error")
        self.assertEqual(len(diagnostic["attempts"]), 1)


if __name__ == "__main__":
    unittest.main()
