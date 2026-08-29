#!/usr/bin/env python3
"""Choose the deterministic Phase-4 codex-review action."""

import argparse
import json

from docaudit_cache import CODEX_REVIEW_STATES


def parse_bool(value):
    return value == "true"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["incremental", "full"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--available", required=True, choices=["true", "false"])
    parser.add_argument("--available-reason", default="not-installed")
    parser.add_argument("--baseline-ok", required=True, choices=["true", "false"])
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)
    configured = "codexReview" in config
    codex_config = config.get("codexReview", {})
    if not isinstance(codex_config, dict):
        codex_config = {}
    required_value = codex_config.get("required", False)
    required = required_value is True
    invalid_required = not isinstance(required_value, bool)

    if not configured:
        result = {"action": "not-active", "state": "not-active",
                  "promptVariant": None, "reason": "not-configured"}
    elif not parse_bool(args.available):
        result = {"action": "not-active", "state": "not-active",
                  "promptVariant": None, "reason": args.available_reason}
    elif args.mode == "full" and required:
        result = {"action": "run", "state": None, "promptVariant": "full",
                  "reason": "ready"}
    elif args.mode == "full":
        result = {"action": "skip", "state": "skipped-full-run",
                  "promptVariant": None, "reason": "full-run-without-required"}
    elif parse_bool(args.baseline_ok):
        result = {"action": "run", "state": None, "promptVariant": "diff",
                  "reason": "ready"}
    else:
        result = {"action": "skip", "state": "ref-invalid",
                  "promptVariant": None, "reason": "baseline-ref-invalid"}

    if invalid_required:
        result["reason"] = "codexReview.required must be boolean"
    if result["state"] is not None and result["state"] not in CODEX_REVIEW_STATES:
        raise AssertionError("codex-review plan emitted an unknown state")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
