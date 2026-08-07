#!/usr/bin/env python3
"""Compute a deterministic SHA-256 digest of a repository worktree.

The digest covers filtered ``git status --porcelain`` output, filtered
``git diff HEAD`` output, and the ordered path/content-hash list of untracked
files.  This helper is read-only; it never changes the repository.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys


def run_git(repo_root, *args):
    return subprocess.run(
        ["git", "-C", repo_root, *args],
        capture_output=True,
        check=True,
    ).stdout


def normalize_exclude(value):
    value = value.replace("\\", "/").strip()
    if value in ("", ".") or value.startswith("/"):
        raise ValueError(f"invalid repo-relative exclude: {value!r}")
    value = value.rstrip("/")
    if not value:
        raise ValueError("invalid repo-relative exclude")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"invalid repo-relative exclude: {value!r}")
    return "/".join(parts)


def excluded(path, excludes):
    return any(path == prefix or path.startswith(prefix + "/") for prefix in excludes)


def porcelain_path(line):
    """Return the path(s) represented by one ordinary porcelain line."""
    if len(line) < 4:
        return []
    value = line[3:]
    if b" -> " in value:
        old, new = value.split(b" -> ", 1)
        return [os.fsdecode(old), os.fsdecode(new)]
    return [os.fsdecode(value)]


def filtered_status(raw, excludes):
    lines = raw.splitlines(keepends=True)
    kept = []
    for line in lines:
        text = line.rstrip(b"\r\n")
        paths = porcelain_path(text)
        if paths and all(excluded(path, excludes) for path in paths):
            continue
        kept.append(line)
    return b"".join(kept)


def filtered_diff(repo_root, excludes):
    args = ["diff", "--no-ext-diff", "--no-textconv", "HEAD", "--", "."]
    args.extend(":!" + prefix for prefix in excludes)
    return run_git(repo_root, *args)


def untracked_hash_list(repo_root, excludes):
    raw = run_git(repo_root, "ls-files", "--others", "--exclude-standard")
    lines = raw.splitlines()
    entries = []
    for path_bytes in lines:
        path = os.fsdecode(path_bytes)
        if excluded(path, excludes):
            continue
        full = os.path.join(repo_root, *path.split("/"))
        if os.path.islink(full):
            target = os.fsencode(os.readlink(full))
            entries.append(
                path.encode("utf-8", "surrogateescape") + b"\tSYMLINK\0" +
                len(target).to_bytes(8, "big") + target + b"\n"
            )
            continue
        if os.path.isdir(full):
            continue
        with open(full, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
        entries.append(path.encode("utf-8", "surrogateescape") + b"\t" +
                       content_hash.encode("ascii") + b"\n")
    return b"".join(entries)


def compute(repo_root, excludes):
    status = filtered_status(run_git(repo_root, "status", "--porcelain"), excludes)
    diff = filtered_diff(repo_root, excludes)
    untracked = untracked_hash_list(repo_root, excludes)
    digest = hashlib.sha256(status + diff + untracked).hexdigest()
    return "sha256:" + digest


def main():
    ap = argparse.ArgumentParser(description="Compute a deterministic worktree digest.")
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--exclude", action="append", default=[],
                    help="repo-relative path prefix to exclude (repeatable)")
    args = ap.parse_args()
    try:
        repo_root = os.path.realpath(args.repo_root)
        excludes = [normalize_exclude(value) for value in args.exclude]
        digest = compute(repo_root, excludes)
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        print(f"tree-digest: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"digest": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
