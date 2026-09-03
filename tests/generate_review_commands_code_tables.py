#!/usr/bin/env python3
"""Generate the sealed v0.18 reviewCommands.code characterization and expectations."""

import importlib.util
import itertools
import json
import os
import sys


BASE_SHA = "749ff0d3b5d4f5fc14f7c42a4364caf921759789"


def derive_expected(parent_name, code_name, required_name, security):
    object_parent = parent_name == "object"
    return {
        "outcome": "REFUSED" if parent_name not in ("missing", "object") else "PASS",
        "warnings": int(object_parent and (code_name != "missing" or required_name != "missing")),
        "securityStartsWhenPhase4Required": int(object_parent and security),
        "securityStartsWhenPhase4NotRequired": 0,
    }


def generate(base_worktree):
    source = os.path.join(base_worktree, "skills", "audit", "scripts", "docaudit_review.py")
    spec = importlib.util.spec_from_file_location("base_docaudit_review", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    missing = object()
    parents = (("missing", missing), ("null", None), ("boolean", True),
               ("string", "x"), ("number", 1), ("array", []), ("object", {}))
    codes = (("missing", missing), ("null", None), ("boolean", True), ("number", 1),
             ("empty", ""), ("whitespace", "   "), ("code", "/code-review"),
             ("high", "/code-review high"), ("xhigh", "/code-review xhigh"),
             ("custom", "/custom"), ("array", []), ("object", {}))
    requireds = (("missing", missing), ("true", True), ("false", False), ("null", None),
                 ("number", 1), ("string", "yes"), ("array", []), ("object", {}))
    rows = []
    for (parent_name, parent), (code_name, code), (required_name, required), security in itertools.product(
            parents, codes, requireds, (False, True)):
        config = {}
        if parent_name != "missing":
            if parent_name == "object":
                review = {}
                if code_name != "missing":
                    review["code"] = code
                if required_name != "missing":
                    review["required"] = required
                if security:
                    review["security"] = "/security-review"
                config["reviewCommands"] = review
            else:
                config["reviewCommands"] = parent
        result = module.classify_review_command(config)
        rows.append({
            "shape": [parent_name, code_name, required_name,
                      "present" if security else "absent"],
            "config": config,
            "baseline": [result["p"], result["action"], result["state"]],
            "expected": derive_expected(parent_name, code_name, required_name, security),
        })
    return {"baseSha": BASE_SHA, "rows": rows}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_review_commands_code_tables.py BASE_WORKTREE")
    sys.stdout.write(json.dumps(generate(sys.argv[1]), ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")))
