#!/usr/bin/env python3
"""Prototype fail-closed Phase-3 dispatcher for one codex exec per dispatched doc."""

import argparse
import concurrent.futures
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile

from docaudit_paths import validate_repo_path


HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(os.path.dirname(HERE), "references",
                      "codex-phase3-verdict.schema.json")
WRITER = os.path.join(HERE, "write-verdict.py")
VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
KILL_GRACE_SECONDS = 0.25
MAX_ATTEMPTS = 3
MAX_CHANGED_PATHS_IN_PROMPT = 100


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dispatch sealed Phase-3 documents through codex exec.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--timeout-seconds", required=True, type=float)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--codex-bin", default="codex")
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be greater than zero")
    if isinstance(args.concurrency, bool) or args.concurrency <= 0:
        parser.error("--concurrency must be a positive integer")
    return args


def load_manifest(run_dir, repo):
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or manifest.get("sealed") is not True:
        raise ValueError("manifest must be a sealed object")
    runid = manifest.get("runid")
    dispatched = manifest.get("dispatch")
    cached = manifest.get("cached")
    changed_set = manifest.get("changedSet")
    if (not isinstance(runid, str) or not runid
            or not isinstance(dispatched, list) or not isinstance(cached, list)
            or not isinstance(changed_set, list)
            or any(not isinstance(path, str) for path in dispatched + cached)
            or any(not isinstance(path, str) for path in changed_set)
            or len(dispatched) != len(set(dispatched))
            or set(dispatched) & set(cached)):
        raise ValueError("manifest dispatch identity is invalid")
    return manifest, [validate_repo_path(repo, path) for path in dispatched]


def load_provenance(run_dir):
    try:
        with open(os.path.join(run_dir, "impact.json"), encoding="utf-8") as handle:
            impacted = json.load(handle).get("impacted", [])
    except (OSError, AttributeError, json.JSONDecodeError):
        return {}
    return {entry["path"]: entry.get("provenance", "unknown")
            for entry in impacted
            if isinstance(entry, dict) and isinstance(entry.get("path"), str)}


def private_directory(codex_root, attempt, path):
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    stem = f"attempt-{attempt:02d}-{digest}"
    number = 1
    while True:
        name = stem if number == 1 else f"{stem}-{number:02d}"
        candidate = os.path.join(codex_root, name)
        try:
            os.mkdir(candidate, 0o700)
            return candidate
        except FileExistsError:
            number += 1


def prompt_for(manifest, repo, path, provenance):
    identity = json.dumps({"runid": manifest["runid"], "path": path},
                          ensure_ascii=False, sort_keys=True)
    head = manifest.get("head")
    if manifest.get("mode") == "full":
        scope = f"""This is a full-corpus audit. There is no diff scope.
Sealed HEAD: {head}

Investigate whether the document at {json.dumps(path, ensure_ascii=False)} accurately describes
the current source and configuration at the sealed HEAD."""
        fail_basis = "the current source"
        pass_basis = "the document accurately describes the current source and configuration"
    else:
        changed_set = manifest.get("changedSet", [])
        shown = changed_set[:MAX_CHANGED_PATHS_IN_PROMPT]
        changed_paths = "\n".join(
            f"- {json.dumps(item, ensure_ascii=False)}" for item in shown)
        if not changed_paths:
            changed_paths = "- (none)"
        scope = f"""Baseline commit: {manifest.get("baselineSha")}
Sealed HEAD: {head}
Sealed changed paths: {len(changed_set)} total; showing {len(shown)}:
{changed_paths}

Investigate whether the document at {json.dumps(path, ensure_ascii=False)} still accurately
describes the source/configuration changes between the baseline and sealed HEAD. The verification
target is the current file content in the sealed worktree. The changed set may include uncommitted
and untracked changes: do not rely only on commit history. Compare the document's claims with the
current content of the listed changed paths."""
        fail_basis = "the changed source"
        pass_basis = "the document is unaffected or already consistent"
    return f"""You are a report-only documentation-impact verifier for exactly one document.
Repository root: {repo}
Expected identity JSON: {identity}
Impact provenance: {provenance}
{scope} Use read-only commands only. Use grep -n and narrowly targeted reads for relevant document and source lines.
Do not use mdq even if it is installed, and do not read unrelated files.

Choose exactly one verdict:
- FAIL: a cited document claim is contradicted by {fail_basis}.
- WARN: there is a concrete, cited staleness or under-specification signal.
- PASS: {pass_basis}.

Return only JSON conforming to the supplied schema. The runid and path must exactly equal the
Expected identity JSON. Give a concise rationale citing file:line and put supporting file:line
references in the evidence array. Do not edit any file.
"""


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=KILL_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.communicate()


def run_child(args, manifest, provenance, codex_root, attempt, path):
    private = private_directory(codex_root, attempt, path)
    child = os.path.join(private, "out.json")
    command = [
        args.codex_bin, "exec", "-s", "read-only", "--output-schema", SCHEMA,
        "-o", child, "-C", args.repo_root, "-m", args.model,
        "-c", f"model_reasoning_effort={args.effort}", "-",
    ]
    try:
        process = subprocess.Popen(
            command, cwd=args.repo_root, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True, start_new_session=True)
        try:
            process.communicate(
                input=prompt_for(manifest, args.repo_root, path,
                                 provenance.get(path, "unknown")),
                timeout=args.timeout_seconds)
            return {"path": path, "child": child, "exit": process.returncode,
                    "timedOut": False}
        except subprocess.TimeoutExpired:
            terminate_group(process)
            return {"path": path, "child": child, "exit": process.returncode,
                    "timedOut": True}
    except OSError:
        return {"path": path, "child": child, "exit": None, "timedOut": False}


def read_output(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("codex output is not a regular file")
        if info.st_size > MAX_OUTPUT_BYTES:
            raise ValueError("codex output exceeds 2 MiB")
        chunks = []
        remaining = MAX_OUTPUT_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError("codex output exceeds 2 MiB")
    finally:
        os.close(fd)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("codex output is not valid UTF-8 JSON") from exc


def validate_output(value, runid, path):
    required = {"runid", "path", "verdict", "rationale", "evidence"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("codex output does not match the verdict schema")
    if (value.get("runid") != runid or value.get("path") != path
            or value.get("verdict") not in VALID_VERDICTS
            or not isinstance(value.get("rationale"), str)
            or not isinstance(value.get("evidence"), list)
            or not all(isinstance(item, str) for item in value["evidence"])):
        raise ValueError("codex output identity or field type is invalid")
    return value


def verdict_path(run_dir, path):
    name = hashlib.sha256(path.encode("utf-8")).hexdigest() + ".json"
    return os.path.join(run_dir, "verdicts", name)


def publish_verdict(run_dir, runid, path, value):
    proc = subprocess.run(
        [sys.executable, WRITER, "--run-dir", run_dir, "--out",
         verdict_path(run_dir, path), "--runid", runid, "--path", path,
         "--verdict", value["verdict"]],
        input=value["rationale"], capture_output=True, text=True)
    if proc.returncode:
        raise ValueError(proc.stderr.strip() or "write-verdict.py failed")
    try:
        written = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("write-verdict.py returned invalid JSON") from exc
    if (written.get("runid") != runid or written.get("path") != path
            or written.get("verdict") != value["verdict"]
            or written.get("rationale") != value["rationale"]):
        raise ValueError("write-verdict.py returned a mismatched record")


def return_row(attempt, path, value=None):
    if value is None:
        return {"attempt": attempt, "assignedPath": path, "returnedPath": None,
                "verdict": None, "rationale": None, "suggestion": None}
    return {"attempt": attempt, "assignedPath": path, "returnedPath": path,
            "verdict": value["verdict"], "rationale": value["rationale"],
            "suggestion": None}


def atomic_returns(run_dir, returns):
    raw = (json.dumps(returns, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".returns.", dir=run_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, os.path.join(run_dir, "returns.json"))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    args = parse_args()
    try:
        args.repo_root = os.path.realpath(args.repo_root)
        args.run_dir = os.path.realpath(args.run_dir)
        if not os.path.isdir(args.repo_root) or not os.path.isdir(args.run_dir):
            raise ValueError("repo root and run directory must exist")
        manifest, dispatched = load_manifest(args.run_dir, args.repo_root)
        provenance = load_provenance(args.run_dir)
        codex_root = os.path.join(args.run_dir, "codex-out")
        os.makedirs(codex_root, exist_ok=True)
        if os.path.islink(codex_root) or not os.path.isdir(codex_root):
            raise ValueError("codex-out must be a real directory")

        returns = []
        pending = list(dispatched)
        succeeded = set()
        attempts = 0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if not pending:
                break
            attempts = attempt
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=args.concurrency) as executor:
                futures = [executor.submit(
                    run_child, args, manifest, provenance, codex_root, attempt, path)
                    for path in pending]
                executions = [future.result() for future in futures]

            retry = []
            for execution in executions:
                path = execution["path"]
                value = None
                if execution["exit"] == 0 and not execution["timedOut"]:
                    try:
                        candidate = validate_output(
                            read_output(execution["child"]), manifest["runid"], path)
                        publish_verdict(args.run_dir, manifest["runid"], path, candidate)
                        value = candidate
                        succeeded.add(path)
                    except (OSError, ValueError):
                        value = None
                returns.append(return_row(attempt, path, value))
                if value is None:
                    retry.append(path)
            pending = retry

        atomic_returns(args.run_dir, returns)
        result = {"returnsPath": os.path.join(args.run_dir, "returns.json"),
                  "attempts": attempts, "ok": len(succeeded), "failed": len(pending)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"codex-dispatch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
