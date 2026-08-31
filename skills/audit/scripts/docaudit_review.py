#!/usr/bin/env python3
"""Pure classification for the configured Phase-4 code-review command."""

import json
import re


RUN_RE = re.compile(r"^/code-review (low|medium|high)$")
CODE_REVIEW_NAMESPACE_RE = re.compile(r"^/code-review(?:$|\s)")
ADOPTION_POINTER = "docs/ADOPTION.md#code-review-autonomous-execution-and-opt-out"
REMEDIATION = (
    'set reviewCommands.code to "/code-review <low|medium|high>" or remove '
    f"reviewCommands.code; see {ADOPTION_POINTER}"
)


def _json_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    return "number"


def _quoted(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _result(p, action, state, reason, *, effort=None, required=False, command=None):
    return {
        "p": p,
        "action": action,
        "state": state,
        "effort": effort,
        "required": required if action == "run" else False,
        "command": command,
        "reason": reason,
    }


def _refuse(p, state, subject, value, detail=None):
    prefix = f"invalid {subject} ({_json_type(value)}): {_quoted(value)}"
    if detail:
        prefix += f" ({detail})"
    return _result(p, "refuse", state, f"{prefix}; {REMEDIATION}")


def classify_review_command(config_doc):
    """Classify a parsed JSON config without reading external state."""
    if not isinstance(config_doc, dict):
        raise TypeError("config_doc must be a parsed JSON object")

    if "reviewCommands" not in config_doc:
        return _result(1, "not-active", "not-configured",
                       "reviewCommands is not configured")

    review = config_doc["reviewCommands"]
    if not isinstance(review, dict):
        return _refuse(2, "invalid-review-config", "reviewCommands", review)

    if "code" not in review:
        required = review.get("required", False)
        if not isinstance(required, bool):
            return _refuse(3, "invalid-review-config", "reviewCommands.required", required)
        if required:
            return _refuse(3, "invalid-review-config", "reviewCommands.required", required,
                           "required:true requires a contract /code-review command")
        return _result(3, "not-active", "not-configured",
                       "reviewCommands.code is not configured")

    command = review["code"]
    if not isinstance(command, str):
        return _refuse(4, "invalid-review-command", "reviewCommands.code", command)
    if not command or command.isspace():
        return _refuse(5, "invalid-review-command", "reviewCommands.code", command)

    matched = RUN_RE.fullmatch(command)
    if matched:
        required = review.get("required", False)
        if not isinstance(required, bool):
            return _refuse(6, "invalid-review-config", "reviewCommands.required", required)
        return _result(6, "run", "pending", "configured /code-review command",
                       effort=matched.group(1), required=required)

    if CODE_REVIEW_NAMESPACE_RE.match(command):
        return _refuse(7, "invalid-review-command", "reviewCommands.code", command)

    required = review.get("required", False)
    if not isinstance(required, bool):
        return _refuse(8, "invalid-review-config", "reviewCommands.required", required)
    if required:
        return _refuse(8, "invalid-review-config", "reviewCommands.required", required,
                       "required:true applies only to /code-review <low|medium|high>")
    return _result(8, "legacy", "legacy-pending", "project-specific review command",
                   command=command)
