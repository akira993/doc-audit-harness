#!/usr/bin/env python3
"""Choose the deterministic Phase-4 codex-review action."""

import argparse
import hashlib
import json
import os
import sys

from docaudit_cache import (CODEX_REVIEW_STATES, parse_history_document,
                            sha256_bytes)
from docaudit_paths import validate_repo_path
from sealed_config import SealedConfigMismatch, load_sealed_config
from refused_phase4 import load_usable_record


SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
SAFE_ASCII_PATH_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/@+-")


def parse_bool(value):
    return value == "true"


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def load_history(path, expected_sha):
    raw = None
    if os.path.isfile(path):
        with open(path, "rb") as handle:
            raw = handle.read()
    observed_sha = sha256_bytes(raw) if raw is not None else "none"
    if observed_sha != expected_sha:
        raise RuntimeError(
            f"sealed-history-mismatch: expected {expected_sha} observed {observed_sha}")
    if raw is None:
        return [], []
    try:
        _entries, phase4_runs, warnings = parse_history_document(
            json.loads(raw.decode("utf-8")))
        return phase4_runs, warnings
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"carry-forward skipped: history corrupt ({exc})"]


def carry_forward(repo_root, phase4_runs, worktree_digest):
    source = next((
        record for record in reversed(phase4_runs)
        if record["worktreeDigest"] != worktree_digest
    ), None)
    if source is None:
        return None, "none"
    files = []
    for finding in sorted(
            source["findings"],
            key=lambda item: (SEVERITY_RANK[item["severity"]], item["file"])):
        path = finding["file"]
        if not all(char in SAFE_ASCII_PATH_CHARS or ord(char) >= 128
                   for char in path):
            continue
        try:
            path = validate_repo_path(repo_root, path)
        except ValueError:
            continue
        files.append({"file": path, "severity": finding["severity"]})
        if len(files) == 50:
            break
    if not files:
        return None, "none"
    value = {"files": files}
    return value, "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["incremental", "full"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--available", required=True, choices=["true", "false"])
    parser.add_argument("--available-reason", default="not-installed")
    parser.add_argument("--baseline-ok", required=True, choices=["true", "false"])
    parser.add_argument("--history", required=True)
    parser.add_argument("--expect-history-sha", required=True)
    parser.add_argument("--worktree-digest", required=True)
    parser.add_argument("--evidence")
    args = parser.parse_args()

    try:
        _config_raw, config = load_sealed_config(
            args.config, args.expect_config_sha)
        phase4_runs, history_warnings = load_history(
            args.history, args.expect_history_sha)
        refused_record = None
        refused_warning = None
        if args.evidence is not None:
            evidence = json.loads(args.evidence)
            if not isinstance(evidence, dict) or evidence.get("history") != args.expect_history_sha:
                raise RuntimeError("sealed-history-mismatch: EVIDENCE.history differs")
            refused_record, refused_reason = load_usable_record(
                os.path.join(args.repo_root, ".claude", "state",
                             "docaudit-refused-phase4.json"),
                evidence)
            if refused_reason is not None:
                refused_warning = "refusedPhase4Ignored: " + refused_reason
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"codex-review-plan: {exc}", file=sys.stderr)
        return 2
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
    carry_value, carry_sha = None, "none"
    if result["action"] == "run" and result["promptVariant"] == "full":
        carry_records = (phase4_runs + [refused_record]
                         if refused_record is not None else phase4_runs)
        carry_value, carry_sha = carry_forward(
            args.repo_root, carry_records, args.worktree_digest)
    result["carryForward"] = carry_value
    result["carryForwardSha"] = carry_sha
    plan_warnings = list(history_warnings)
    if refused_warning is not None:
        plan_warnings.append(refused_warning)
    if plan_warnings:
        result["warnings"] = plan_warnings
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
