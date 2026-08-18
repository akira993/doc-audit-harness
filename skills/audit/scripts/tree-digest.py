#!/usr/bin/env python3
"""Compute a fail-closed deterministic worktree digest."""

import argparse
import hashlib
import json
import os
import subprocess
import sys


KNOWN_ROOTS = {".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, check=True).stdout


def normalize(value):
    value = value.replace("\\", "/").rstrip("/")
    if not value or value.startswith("/") or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError(f"invalid exclude: {value!r}")
    if any(char in value for char in "*?["):
        raise ValueError("digest excludes may not contain globs")
    if not (value == ".claude/state" or value.startswith(".claude/state/")
            or value == ".claude/worktrees" or value.startswith(".claude/worktrees/")
            or value.split("/", 1)[0] in KNOWN_ROOTS):
        raise ValueError(f"digest exclude is not allowlisted: {value}")
    return value


def is_excluded(path, excludes):
    path = path.replace(os.sep, "/")
    return any(path == item or path.startswith(item + "/") for item in excludes)


def compute(root, excludes, include_head=False):
    status_lines = git(root, "status", "--porcelain", "--untracked-files=all").splitlines(True)
    status = bytearray()
    for line in status_lines:
        text = line.rstrip(b"\r\n")
        value = os.fsdecode(text[3:]) if len(text) >= 4 else ""
        paths = value.split(" -> ")
        if paths and all(is_excluded(path, excludes) for path in paths):
            continue
        status.extend(line)
    command = ["diff", "--no-ext-diff", "--no-textconv", "HEAD", "--", "."]
    command.extend(":!" + item for item in excludes)
    diff = git(root, *command)
    untracked = bytearray()
    for raw_path in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if not raw_path:
            continue
        path = os.fsdecode(raw_path)
        if is_excluded(path, excludes):
            continue
        full = os.path.join(root, path)
        if os.path.islink(full):
            content = os.fsencode(os.readlink(full))
        elif os.path.isfile(full):
            with open(full, "rb") as handle:
                content = handle.read()
        else:
            continue
        untracked.extend(raw_path + b"\0" + hashlib.sha256(content).digest())
    head = git(root, "rev-parse", "HEAD").strip() + b"\0" if include_head else b""
    return "sha256:" + hashlib.sha256(head + bytes(status) + diff + bytes(untracked)).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--include-head", action="store_true")
    args = parser.parse_args()
    try:
        digest = compute(os.path.realpath(args.repo_root), [normalize(item) for item in args.exclude], args.include_head)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"tree-digest: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"digest": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
