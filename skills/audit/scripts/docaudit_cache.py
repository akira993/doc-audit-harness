#!/usr/bin/env python3
"""Shared deterministic history/cache rules for plan-dispatch and the gate."""

import hashlib
import json
import os
import re
import unicodedata


VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
VALID_BACKENDS = {"workflow", "codex"}
CODEX_REVIEW_STATES = ("completed", "execution-failed", "ref-invalid",
                       "skipped-full-run", "not-active")
HISTORY_FIELDS = {
    "runid": str,
    "path": str,
    "contentSha": str,
    "changeSetSha": str,
    "contractVersion": str,
    "verdict": str,
    "ts": str,
}
PHASE4_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
PHASE4_RUN_FIELDS = {
    "runid": str,
    "ts": str,
    "worktreeDigest": str,
    "contractVersion": str,
    "configSha": str,
    "carryForwardSha": str,
    "unresolvedFileCount": int,
    "truncated": bool,
    "findings": list,
}
PHASE4_RUN_LIMIT = 6
PHASE4_FINDING_LIMIT = 500
PHASE4_FILE_BYTES = 512
PHASE4_RECORD_BYTES = 512 * 1024
PHASE4_RUNS_BYTES = 1024 * 1024


def sha256_bytes(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def content_sha(repo_root, path):
    with open(os.path.join(repo_root, *path.split("/")), "rb") as handle:
        return sha256_bytes(handle.read())


def validate_min_passes(config):
    cache = config.get("verdictCache", {})
    enabled = cache.get("enabled", True)
    value = cache.get("minConsecutivePasses", 2)
    if not enabled:
        return False, None, []
    if isinstance(value, bool) or not isinstance(value, int) or not 2 <= value <= 10:
        return False, None, ["verdictCache.minConsecutivePasses must be an integer from 2 through 10; cache disabled"]
    return True, value, []


def parse_history(data):
    if isinstance(data, dict):
        entries = data.get("entries")
    else:
        entries = data
    if not isinstance(entries, list):
        raise ValueError("history entries must be a list")
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"history entry {index} is not an object")
        for field, typ in HISTORY_FIELDS.items():
            if not isinstance(entry.get(field), typ):
                raise ValueError(f"history entry {index} has invalid {field}")
        if entry["verdict"] not in VALID_VERDICTS:
            raise ValueError(f"history entry {index} has invalid verdict")
        backend = entry.get("backend", "workflow")
        if not isinstance(backend, str) or backend not in VALID_BACKENDS:
            raise ValueError(f"history entry {index} has invalid backend")
        key = (entry["runid"], entry["path"])
        if key in seen:
            raise ValueError("history contains duplicate (runid,path)")
        seen.add(key)
    return entries


def _canonical_size(value):
    return len(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8"))


def _validate_phase4_path(path):
    if not isinstance(path, str) or not path:
        raise ValueError("finding file must be a non-empty string")
    if (path.startswith(("./", "/", "//"))
            or re.match(r"^[A-Za-z]:", path)
            or "\\" in path or '"' in path
            or any(unicodedata.category(char) == "Cc" for char in path)):
        raise ValueError("finding file is not a canonical repository path")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError("finding file is not a canonical repository path")
    if _canonical_size(path) > PHASE4_FILE_BYTES:
        raise ValueError("finding file exceeds 512 serialized bytes")


def _validate_phase4_runs(phase4_runs):
    if not isinstance(phase4_runs, list):
        raise ValueError("phase4Runs must be a list")
    if len(phase4_runs) > PHASE4_RUN_LIMIT:
        raise ValueError("phase4Runs exceeds 6 records")
    if _canonical_size(phase4_runs) > PHASE4_RUNS_BYTES:
        raise ValueError("phase4Runs exceeds 1 MiB")
    for record_index, record in enumerate(phase4_runs):
        if not isinstance(record, dict):
            raise ValueError(f"phase4Runs record {record_index} is not an object")
        for field, expected_type in PHASE4_RUN_FIELDS.items():
            value = record.get(field)
            if expected_type is int:
                valid = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid = isinstance(value, expected_type)
            if not valid:
                raise ValueError(
                    f"phase4Runs record {record_index} has invalid {field}")
        if _canonical_size(record) > PHASE4_RECORD_BYTES:
            raise ValueError(
                f"phase4Runs record {record_index} exceeds 512 KiB")
        findings = record["findings"]
        if len(findings) > PHASE4_FINDING_LIMIT:
            raise ValueError(
                f"phase4Runs record {record_index} exceeds 500 findings")
        for finding_index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                raise ValueError(
                    f"phase4Runs record {record_index} finding {finding_index} is not an object")
            _validate_phase4_path(finding.get("file"))
            if finding.get("severity") not in PHASE4_SEVERITIES:
                raise ValueError(
                    f"phase4Runs record {record_index} finding {finding_index} has invalid severity")


def parse_history_document(data):
    """Return ``(entries, phase4_runs, warnings)`` for every valid history.

    Invalid deterministic entries remain a corrupt-history error.  Invalid
    Phase-4 sampling records degrade independently so deterministic cache data
    remains usable.
    """
    entries = parse_history(data)
    if isinstance(data, list) or "phase4Runs" not in data:
        return entries, [], []
    phase4_runs = data["phase4Runs"]
    try:
        _validate_phase4_runs(phase4_runs)
    except ValueError as exc:
        return entries, [], [f"phase4Runs ignored: {exc}"]
    return entries, phase4_runs, []


def cache_qualification(entries, path, current_content_sha, change_set_sha,
                        contract_version, minimum, backend="workflow"):
    if not isinstance(backend, str) or backend not in VALID_BACKENDS:
        return False, [], "backend-invalid"
    recent = [entry for entry in entries if entry["path"] == path][-minimum:]
    if len(recent) != minimum:
        return False, [], "history-insufficient"
    if len({entry["runid"] for entry in recent}) != minimum:
        return False, [], "history-runid-duplicate"
    expected = (current_content_sha, change_set_sha, contract_version, backend)
    for entry in recent:
        actual = (entry["contentSha"], entry["changeSetSha"], entry["contractVersion"],
                  entry.get("backend", "workflow"))
        if entry["verdict"] != "PASS" or actual != expected:
            return False, [], "history-key-mismatch"
    return True, [entry["runid"] for entry in recent], None


def trim_history(entries, per_path=20):
    paths = sorted({entry["path"] for entry in entries})
    kept = []
    for path in paths:
        kept.extend([entry for entry in entries if entry["path"] == path][-per_path:])
    return kept


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
