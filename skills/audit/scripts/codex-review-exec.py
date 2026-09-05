#!/usr/bin/env python3
"""Run the sealed Phase-4 codex review and publish only a validated result."""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile

from codex_review_output import validate_result
from sealed_config import load_sealed_config


HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(os.path.dirname(HERE), "references", "codex-review-output.schema.json")
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_IO_BYTES = 2 * 1024 * 1024
KILL_GRACE_SECONDS = 0.25
RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _load_manifest_reader():
    spec = importlib.util.spec_from_file_location(
        "read_manifest", os.path.join(HERE, "read-manifest.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_manifest


read_manifest = _load_manifest_reader()


def tagged_sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def read_regular_bounded(path, maximum):
    fd = os.open(
        path,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0),
    )
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not a regular file")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > maximum:
            raise ValueError("size limit exceeded")
        return raw
    finally:
        os.close(fd)


def manifest_opener(expected_path, raw):
    def opener(path, mode="rb"):
        if os.path.realpath(path) != os.path.realpath(expected_path) or mode != "rb":
            raise ValueError("unexpected manifest read")
        return io.BytesIO(raw)
    return opener


def private_directory(run_dir, attempt):
    stem = f"codex-review-attempt-{attempt:02d}"
    number = 1
    while True:
        name = stem if number == 1 else f"{stem}-{number:02d}"
        candidate = os.path.join(run_dir, name)
        try:
            os.mkdir(candidate, 0o700)
            return candidate
        except FileExistsError:
            number += 1


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.communicate()


def run_attempt(binary, repo, run_dir, prompt, model, timeout_seconds, attempt):
    private = private_directory(run_dir, attempt)
    output = os.path.join(private, "out.json")
    # Keep `exec` before `-C`; this is not `codex exec review`, and no --base is used.
    command = [
        binary, "exec", "-C", repo, "-s", "read-only", "-m", model,
        "-c", "model_reasoning_effort=medium", "--output-schema", SCHEMA,
        "-o", output, "-",
    ]
    diagnostic = {
        "attempt": attempt,
        "model": model,
        "exit": None,
        "timedOut": False,
        "outputPresent": False,
        "schemaValid": False,
        "reason": None,
    }
    try:
        process = subprocess.Popen(
            command, cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            process.communicate(input=prompt, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            diagnostic["timedOut"] = True
            terminate_group(process)
        diagnostic["exit"] = process.returncode
    except OSError as exc:
        diagnostic["reason"] = f"execution failed: {exc}"
        return None, diagnostic

    diagnostic["outputPresent"] = os.path.lexists(output)
    if diagnostic["timedOut"]:
        diagnostic["reason"] = "timeout"
        return None, diagnostic
    if diagnostic["exit"] != 0:
        diagnostic["reason"] = "non-zero exit"
        return None, diagnostic
    try:
        raw = read_regular_bounded(output, MAX_IO_BYTES)
        value = json.loads(raw.decode("utf-8"))
        validate_result(value)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        diagnostic["reason"] = f"invalid output: {exc}"
        return None, diagnostic
    diagnostic["schemaValid"] = True
    diagnostic["reason"] = "accepted"
    return raw, diagnostic


def publish_result(run_dir, raw):
    fd, temporary = tempfile.mkstemp(prefix=".codex-review-result.", dir=run_dir)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, os.path.join(run_dir, "codex-review-result.json"))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha", required=True)
    parser.add_argument("--evidence", required=True)
    return parser.parse_args()


def load_inputs(args):
    evidence = json.loads(args.evidence)
    if not isinstance(evidence, dict):
        raise ValueError("EVIDENCE must be an object")
    if not SHA_RE.fullmatch(args.expect_config_sha):
        raise ValueError("expected config sha is invalid")
    if args.expect_config_sha != evidence.get("config"):
        raise ValueError("EVIDENCE config mismatch")
    evidence_run_dir = evidence.get("runDir")
    if not isinstance(evidence_run_dir, str):
        raise ValueError("EVIDENCE runDir is invalid")
    run_dir = os.path.realpath(args.run_dir)
    if run_dir != os.path.realpath(evidence_run_dir):
        raise ValueError("EVIDENCE runDir mismatch")
    manifest_path = os.path.join(run_dir, "manifest.json")
    manifest_raw = read_regular_bounded(manifest_path, MAX_MANIFEST_BYTES)
    manifest = read_manifest(
        run_dir, evidence, opener=manifest_opener(manifest_path, manifest_raw))
    runid = manifest.get("runid") if isinstance(manifest, dict) else None
    if not isinstance(runid, str) or not RUNID_RE.fullmatch(runid):
        raise ValueError("manifest runid is invalid")
    if evidence.get("runid") != runid:
        raise ValueError("EVIDENCE runid mismatch")
    repo = os.path.realpath(args.repo_root)
    ledger_run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", runid)
    if run_dir != os.path.realpath(ledger_run_dir):
        raise ValueError("run directory is outside the run ledger")
    prompt = read_regular_bounded(
        os.path.join(run_dir, "codex-review-prompt.txt"), MAX_IO_BYTES)
    _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    codex_config = config.get("codexReview", {})
    if not isinstance(codex_config, dict):
        raise ValueError("codexReview config must be an object")
    binary = codex_config.get("bin", "codex")
    if not isinstance(binary, str) or not binary:
        raise ValueError("codexReview.bin must be a non-empty string")
    configured_model = codex_config.get("model")
    explicit = isinstance(configured_model, str) and bool(configured_model)
    if configured_model is not None and not isinstance(configured_model, str):
        raise ValueError("codexReview.model must be a string or null")
    run_class = manifest.get("runClass")
    if run_class not in {"light", "standard"}:
        raise ValueError("manifest runClass is invalid")
    model = configured_model if explicit else {
        "light": "gpt-5.6-luna", "standard": "gpt-5.6-terra",
    }[run_class]
    timeout_ms = codex_config.get("timeoutMs", 300000)
    if (isinstance(timeout_ms, bool) or not isinstance(timeout_ms, (int, float))
            or timeout_ms <= 0):
        raise ValueError("codexReview.timeoutMs must be positive")
    return evidence, repo, run_dir, prompt, binary, model, explicit, run_class, timeout_ms / 1000


def emit_diagnostic(state, attempts=None, reason=None):
    value = {"state": state, "attempts": attempts or []}
    if reason is not None:
        value["reason"] = reason
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=sys.stderr)


def main():
    args = parse_args()
    try:
        (evidence, repo, run_dir, prompt, binary, model, explicit,
         run_class, timeout_seconds) = load_inputs(args)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        emit_diagnostic("engine-error", reason=str(exc))
        return 2

    attempts = []
    models = [model]
    if not explicit and run_class == "light":
        models.append("gpt-5.6-terra")
    accepted = None
    for number, attempt_model in enumerate(models, 1):
        raw, diagnostic = run_attempt(
            binary, repo, run_dir, prompt, attempt_model, timeout_seconds, number)
        diagnostic["modelSource"] = "explicit" if explicit else "default"
        attempts.append(diagnostic)
        if raw is not None:
            accepted = raw
            break

    if accepted is None:
        evidence["codexReviewResult"] = "failed"
        emit_diagnostic("execution-failed", attempts=attempts)
        print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        return 0
    try:
        publish_result(run_dir, accepted)
    except OSError as exc:
        emit_diagnostic("engine-error", attempts=attempts, reason=str(exc))
        return 2
    evidence["codexReviewResult"] = tagged_sha(accepted)
    emit_diagnostic("completed", attempts=attempts)
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
