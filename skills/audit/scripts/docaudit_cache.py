#!/usr/bin/env python3
"""Shared deterministic history/cache rules for plan-dispatch and the gate."""

import hashlib
import json
import os


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
