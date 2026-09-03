#!/usr/bin/env python3
"""Validate and atomically write orchestrator-owned evidence."""

import argparse
import hashlib
import json
import os
import sys
import tempfile


VALID_VERDICTS = {"PASS", "WARN", "FAIL"}


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
