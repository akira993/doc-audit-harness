#!/usr/bin/env python3
"""Seal a run after detecting Phase-1-to-fan-out drift."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))


def atomic_write(path, raw):
    fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def emit(value, code):
    print(json.dumps(value, sort_keys=True))
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence)
        if os.path.realpath(str(evidence.get("runDir"))) != os.path.realpath(args.run_dir):
            raise ValueError("EVIDENCE runDir mismatch")
        with open(os.path.join(args.run_dir, "manifest.json"), "rb") as handle:
            manifest_raw = handle.read()
        if "sha256:" + hashlib.sha256(manifest_raw).hexdigest() != evidence.get("manifest"):
            raise ValueError("manifest sha does not match EVIDENCE")
        manifest = json.loads(manifest_raw.decode("utf-8"))
        config = os.path.join(os.path.realpath(args.repo_root), ".claude", "doc-audit.json")
        change = subprocess.run(
            [sys.executable, os.path.join(HERE, "change-set-sha.py"),
             "--repo-root", args.repo_root, "--baseline-sha", manifest["baselineSha"],
             "--config", config, "--expect-config-sha", evidence["config"]],
            capture_output=True, text=True)
        if change.returncode == 7:
            if change.stderr:
                print(change.stderr.rstrip(), file=sys.stderr)
            return 7
        if change.returncode:
            raise ValueError(change.stderr.strip() or "change-set-sha failed")
        current_change = json.loads(change.stdout)
        head = subprocess.run(["git", "-C", args.repo_root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        if current_change["changeSetSha"] != manifest.get("changeSetSha"):
            return emit({"sealed": False, "reason": "change-set-drift"}, 5)
        if head != manifest.get("head"):
            return emit({"sealed": False, "reason": "head-drift"}, 5)
        command = [sys.executable, os.path.join(HERE, "tree-digest.py"),
                   "--repo-root", args.repo_root, "--include-head"]
        for item in manifest.get("digestExclude", []):
            command.extend(["--exclude", item])
        digest_proc = subprocess.run(command, capture_output=True, text=True)
        if digest_proc.returncode:
            raise ValueError(digest_proc.stderr.strip() or "tree-digest failed")
        digest = json.loads(digest_proc.stdout)["digest"]
        manifest["worktreeDigest"] = digest
        manifest["sealed"] = True
        raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        atomic_write(os.path.join(args.run_dir, "manifest.json"), raw)
        evidence["digest"] = digest
        evidence["manifest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    except (OSError, KeyError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"seal-run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
