#!/usr/bin/env python3
"""Classify a run as light or standard from deterministic thresholds."""

import argparse
import json
import os
import subprocess
import sys

from sealed_config import SealedConfigMismatch, load_sealed_config


DEFAULT_TOKENS = ["auth", "security", "permission", "access-control", "iam", "crypto",
                  "billing", "session", "token", "oauth", "acl", "rbac", "secret", ".env"]


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha", required=True)
    parser.add_argument("--impact-json", required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--mode", required=True, choices=["incremental", "full"])
    parser.add_argument("--last-run")
    args = parser.parse_args()
    try:
        _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
        with open(args.impact_json, encoding="utf-8") as handle:
            impact = json.load(handle)
        light = config.get("models", {}).get("light", {})
        thresholds = {"maxChanged": 10, "maxImpacted": 15, "maxDiffLines": 200,
                      "maxDiffBytes": 65536}
        thresholds.update({key: light[key] for key in thresholds if key in light})
        tokens = light.get("sensitiveTokens", DEFAULT_TOKENS)
        effective_baseline = args.baseline_sha
        if args.mode == "full":
            effective_baseline = git(args.repo_root, "rev-parse", "HEAD").strip()
        untracked = git(args.repo_root, "ls-files", "--others", "--exclude-standard").splitlines()
        change_proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "change-set-sha.py"),
             "--repo-root", args.repo_root, "--baseline-sha", effective_baseline,
             "--config", args.config, "--expect-config-sha", args.expect_config_sha],
            capture_output=True, text=True)
        if change_proc.returncode:
            if change_proc.returncode == 7:
                print(change_proc.stderr.rstrip(), file=sys.stderr)
                return 7
            raise ValueError(change_proc.stderr.strip() or "change-set-sha failed")
        change_data = json.loads(change_proc.stdout)
        changed = change_data["changedSet"]
        numstat = git(args.repo_root, "diff", "--numstat", "--no-renames", effective_baseline)
        diff_lines = 0
        for line in numstat.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3 and parts[2] in changed:
                for value in parts[:2]:
                    if value.isdigit():
                        diff_lines += int(value)
        for path in untracked:
            if path not in changed:
                continue
            full = os.path.join(args.repo_root, path)
            if os.path.isfile(full) and not os.path.islink(full):
                with open(full, "rb") as handle:
                    diff_lines += len(handle.read().splitlines())
        diff_bytes = 0
        for path in changed:
            full = os.path.join(args.repo_root, path)
            if os.path.islink(full):
                diff_bytes += len(os.fsencode(os.readlink(full)))
            elif os.path.isfile(full):
                diff_bytes += os.path.getsize(full)
        for entry in change_data.get("entries", []):
            if (isinstance(entry, dict) and str(entry.get("status", "")).startswith("D")
                    and isinstance(entry.get("oldBlob"), str) and entry["oldBlob"] != "0"):
                size = git(args.repo_root, "cat-file", "-s", entry["oldBlob"]).strip()
                if not size.isdigit():
                    raise ValueError("deleted blob size is invalid")
                diff_bytes += int(size)
        impacted_count = len(impact.get("impacted", []))
        last_verdict = None
        last_run_path = args.last_run or os.path.join(
            os.path.realpath(args.repo_root), ".claude", "state", "docaudit-last-run.json")
        if os.path.isfile(last_run_path):
            with open(last_run_path, encoding="utf-8") as handle:
                last_verdict = json.load(handle).get("verdict")
        sensitive = [path for path in changed
                     if any(str(token).lower() in path.lower() for token in tokens)]
        reasons = []
        if args.mode != "incremental": reasons.append("full-mode")
        if light.get("enabled", True) is False: reasons.append("disabled")
        if len(changed) > thresholds["maxChanged"]: reasons.append("changed-count")
        if impacted_count > thresholds["maxImpacted"]: reasons.append("impacted-count")
        if diff_lines > thresholds["maxDiffLines"]: reasons.append("diff-lines")
        if diff_bytes > thresholds["maxDiffBytes"]: reasons.append("diff-bytes")
        if last_verdict not in (None, "CONSISTENT"): reasons.append("last-run")
        if sensitive: reasons.append("sensitive-path")
        result = {"runClass": "light" if not reasons else "standard",
                  "changedCount": len(changed), "impactedCount": impacted_count,
                  "diffLines": diff_lines, "diffBytes": diff_bytes,
                  "sensitivePaths": sensitive, "reasons": reasons}
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"classify-run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
