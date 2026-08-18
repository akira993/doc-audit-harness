#!/usr/bin/env python3
"""Plan deterministic dispatches and materialize cache verdicts."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from docaudit_cache import (cache_qualification, content_sha, json_bytes,
                            parse_history, sha256_bytes, validate_min_passes)
from docaudit_paths import validate_repo_path


HERE = os.path.dirname(os.path.abspath(__file__))


def atomic_write(path, raw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dispatch.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def paths_from_impact(value):
    if not isinstance(value, dict) or not isinstance(value.get("impacted"), list):
        raise ValueError("impact.impacted must be an array")
    paths = []
    for item in value["impacted"]:
        path = item if isinstance(item, str) else item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str):
            raise ValueError("invalid impacted entry")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate impacted path")
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--impact-json", required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    parser.add_argument("--full", action="store_true",
                        help="force full mode (alias for callers propagating /audit --full)")
    parser.add_argument("--contract-version", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence)
        if (not isinstance(evidence, dict) or evidence.get("runid") != args.runid
                or os.path.realpath(str(evidence.get("runDir"))) != os.path.realpath(args.run_dir)):
            raise ValueError("--evidence run identity mismatch")
        with open(args.config, "rb") as handle:
            config_raw = handle.read()
        if sha256_bytes(config_raw) != evidence.get("config"):
            raise ValueError("config changed after open-run")
        config = json.loads(config_raw.decode("utf-8"))
        with open(args.impact_json, encoding="utf-8") as handle:
            impacted = paths_from_impact(json.load(handle))
        mode = "full" if args.full else args.mode
        baseline_sha = args.baseline_sha
        if mode == "full":
            baseline_sha = subprocess.run(
                ["git", "-C", args.repo_root, "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True).stdout.strip()
        command = [sys.executable, os.path.join(HERE, "change-set-sha.py"),
                   "--repo-root", args.repo_root, "--baseline-sha", baseline_sha,
                   "--config", args.config]
        changed_proc = subprocess.run(command, capture_output=True, text=True)
        if changed_proc.returncode:
            raise ValueError(changed_proc.stderr.strip() or "change-set-sha failed")
        changed = json.loads(changed_proc.stdout)
        history_raw = None
        history_status = "absent"
        entries = []
        if os.path.isfile(args.history):
            with open(args.history, "rb") as handle:
                history_raw = handle.read()
            try:
                entries = parse_history(json.loads(history_raw.decode("utf-8")))
                history_status = "ok"
            except (UnicodeError, ValueError, json.JSONDecodeError):
                history_status = "corrupt"
                entries = []
        enabled, minimum, warnings = validate_min_passes(config)
        if history_status != "ok" or mode == "full":
            enabled = False
        dispatch = []
        cached = []
        cached_bytes = {}
        verdict_dir = os.path.join(args.run_dir, "verdicts")
        os.makedirs(verdict_dir, exist_ok=True)
        for path in impacted:
            path = validate_repo_path(args.repo_root, path)
            doc_sha = content_sha(args.repo_root, path)
            qualified, runids, _reason = cache_qualification(
                entries, path, doc_sha, changed["changeSetSha"], args.contract_version,
                minimum or 2)
            if not enabled or not qualified:
                dispatch.append(path)
                continue
            name = hashlib.sha256(path.encode("utf-8")).hexdigest() + ".json"
            out = os.path.join(verdict_dir, name)
            writer = subprocess.run(
                [sys.executable, os.path.join(HERE, "write-verdict.py"),
                 "--run-dir", args.run_dir, "--out", out, "--runid", args.runid,
                 "--path", path, "--verdict", "PASS", "--source", "cache",
                 "--history-runids", json.dumps(runids), "--content-sha", doc_sha,
                 "--change-set-sha", changed["changeSetSha"],
                 "--contract-version", args.contract_version],
                input="reused from deterministic PASS history\n", capture_output=True, text=True)
            if writer.returncode:
                raise ValueError(writer.stderr.strip() or "write-verdict failed")
            record = json.loads(writer.stdout)
            raw = json_bytes(record)
            cached_bytes[path] = raw
            cached.append(path)
        dispatch_doc = {"dispatch": dispatch, "cached": cached,
                        "changeSetSha": changed["changeSetSha"],
                        "changedSet": changed["changedSet"], "baselineSha": baseline_sha,
                        "minConsecutivePasses": minimum, "contractVersion": args.contract_version,
                        "historyStatus": history_status, "warnings": warnings}
        raw = json_bytes(dispatch_doc)
        atomic_write(os.path.join(args.run_dir, "dispatch.json"), raw)
        cached_material = b"".join(cached_bytes[path] for path in sorted(cached_bytes))
        evidence.update({"dispatch": sha256_bytes(raw),
                         "cached": sha256_bytes(cached_material) if cached else "none",
                         "history": sha256_bytes(history_raw) if history_raw is not None else "none",
                         "historyStatus": history_status})
        evidence["counts"] = {"dispatch": len(dispatch), "cached": len(cached)}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"plan-dispatch: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
