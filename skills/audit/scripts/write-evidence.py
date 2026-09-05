#!/usr/bin/env python3
"""Validate and atomically write orchestrator-owned evidence."""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile

from codex_review_output import derive_findings, validate_result


VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
MAX_CODEX_RESULT_BYTES = 2 * 1024 * 1024
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def validate_returns(value):
    if not isinstance(value, list):
        raise ValueError("returns must be an array")
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"returns[{index}] must be an object")
        attempt = item.get("attempt")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= 3:
            raise ValueError(f"returns[{index}].attempt must be 1..3")
        if not isinstance(item.get("assignedPath"), str):
            raise ValueError(f"returns[{index}].assignedPath is required")
        for field in ("returnedPath", "rationale", "suggestion"):
            if item.get(field) is not None and not isinstance(item.get(field), str):
                raise ValueError(f"returns[{index}].{field} must be string or null")
        if item.get("verdict") is not None and item.get("verdict") not in VALID_VERDICTS:
            raise ValueError(f"returns[{index}].verdict is invalid")
        key = (attempt, item["assignedPath"])
        if key in seen:
            raise ValueError("duplicate (attempt,assignedPath)")
        seen.add(key)


def validate(name, value):
    if name == "returns":
        validate_returns(value)
        return
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    if name == "preflight":
        required = {"state": str, "findings": list, "userDecision": (str, type(None)), "parsed": bool}
        for key, typ in required.items():
            if not isinstance(value.get(key), typ):
                raise ValueError(f"preflight.{key} is invalid")
    elif name == "phase4":
        if not isinstance(value.get("findings", []), list):
            raise ValueError("phase4.findings must be an array")


def read_regular_bounded(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("codex-review result is not a regular file")
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
            raise ValueError("codex-review result exceeds 2 MiB")
        return raw
    finally:
        os.close(fd)


def merge_codex_findings(run_dir, evidence, value):
    findings = value.setdefault("findings", [])
    if any(isinstance(item, dict) and item.get("source") == "codex-review"
           for item in findings):
        raise ValueError("codex-review findings are derived, not supplied")
    seal = evidence.get("codexReviewResult")
    if not isinstance(seal, str) or (seal not in {"none", "failed"}
                                     and not SHA_RE.fullmatch(seal)):
        raise ValueError("codexReviewResult missing or invalid")
    codex = value.get("codexReview")
    state = codex.get("state") if isinstance(codex, dict) else None
    if SHA_RE.fullmatch(seal):
        if state != "completed":
            raise ValueError("codexReviewResult does not match codexReview.state")
        try:
            raw = read_regular_bounded(
                os.path.join(run_dir, "codex-review-result.json"),
                MAX_CODEX_RESULT_BYTES,
            )
        except OSError as exc:
            raise ValueError(f"codex-review result cannot be read: {exc}") from exc
        if "sha256:" + hashlib.sha256(raw).hexdigest() != seal:
            raise ValueError("codexReviewResult sha mismatch")
        try:
            result = json.loads(raw.decode("utf-8"))
            validate_result(result)
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("codexReviewResult invalid") from exc
        findings.extend(derive_findings(result))
    elif seal == "failed":
        if state != "execution-failed":
            raise ValueError("codexReviewResult does not match codexReview.state")
    elif state in {"completed", "execution-failed"}:
        raise ValueError("codexReviewResult does not match codexReview.state")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--name", required=True, choices=["preflight", "returns", "phase4"])
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    if not args.stdin:
        parser.error("--stdin is required")
    try:
        evidence = json.loads(args.evidence)
        if not isinstance(evidence, dict):
            raise ValueError("--evidence must be an object")
        if os.path.realpath(str(evidence.get("runDir"))) != os.path.realpath(args.run_dir):
            raise ValueError("EVIDENCE runDir mismatch")
        value = json.load(sys.stdin)
        validate(args.name, value)
        if args.name == "phase4":
            merge_codex_findings(args.run_dir, evidence, value)
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        os.makedirs(args.run_dir, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{args.name}.", dir=args.run_dir)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, os.path.join(args.run_dir, args.name + ".json"))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        evidence[args.name] = "sha256:" + hashlib.sha256(raw).hexdigest()
        if args.name == "returns":
            evidence["attempt"] = max((item["attempt"] for item in value), default=0)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"write-evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
