#!/usr/bin/env python3
"""Generate the BASE_SHA inventory used by the removed-symbol residue check."""

import json
import os
import re
import sys


BASE_SHA = "749ff0d3b5d4f5fc14f7c42a4364caf921759789"
PATTERNS = {
    "removed-script": r"docaudit_review\.py|code-review-plan\.py",
    "removed-python-symbol": (
        r"\b(?:CODE_REVIEW_STATUS_LINES|CODE_REVIEW_STATES|DEFAULT_CODE_REVIEW_STATUS|"
        r"validate_code_review_contract|classify_review_command|CODE_REVIEW_PLAN|"
        r"CODE_REVIEW_STATE|code_review)\b"
    ),
    "removed-json-symbol": r"\b(?:codeReviewStatus|codeReviewNotRun|codeReview)\b",
    "removed-template": r"\{\{GATE_CODE_REVIEW_STATUS\}\}",
    "removed-source": r"source[^\n]{0,40}code-review",
    "removed-config": r"reviewCommands\.(?:code|required)",
    "removed-config-key": r"[\"'](?:code|required)[\"']\s*:",
    "removed-config-access": (
        r"\b(?:review|review_commands|legacy_review_commands)\.get\("
        r"[\"'](?:code|required)[\"']"
    ),
    "removed-command": r"/code-review",
    "removed-skill": r"skill=code-review",
}


def included_paths(root):
    roots = ("skills", "agents", "tests", ".claude-plugin", "docs")
    for top in roots:
        base = os.path.join(root, top)
        for directory, names, files in os.walk(base):
            relative_directory = os.path.relpath(directory, root).replace(os.sep, "/")
            names[:] = [name for name in names if name != "__pycache__" and not (
                relative_directory == "docs" and name in ("logs", "superpowers")
                or relative_directory == "tests" and name == "data")]
            for name in files:
                path = f"{relative_directory}/{name}"
                if path == "tests/test_release_handoff.py":
                    continue
                yield path
    yield "README.md"


def generate(root):
    matches = []
    compiled = [(symbol, re.compile(pattern, re.I)) for symbol, pattern in PATTERNS.items()]
    for path in sorted(included_paths(root)):
        try:
            with open(os.path.join(root, path), encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except (IsADirectoryError, FileNotFoundError):
            continue
        lines = text.splitlines()
        for number, line in enumerate(lines, 1):
            for symbol, pattern in compiled:
                if symbol == "removed-config-key":
                    continue
                if pattern.search(line):
                    matches.append({"path": path, "line": number, "symbol": symbol,
                                    "text": line})
        review_object = re.compile(
            r"[\"']reviewCommands[\"']\s*:\s*\{(?P<body>[^{}]{0,500})\}", re.I)
        key_pattern = re.compile(PATTERNS["removed-config-key"], re.I)
        for block in review_object.finditer(text):
            for key in key_pattern.finditer(block.group("body")):
                offset = block.start("body") + key.start()
                number = text.count("\n", 0, offset) + 1
                matches.append({"path": path, "line": number,
                                "symbol": "removed-config-key",
                                "text": lines[number - 1]})
    return {"baseSha": BASE_SHA, "patterns": PATTERNS, "matches": matches}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_code_review_remnants.py BASE_WORKTREE")
    sys.stdout.write(json.dumps(generate(sys.argv[1]), ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")))
