#!/usr/bin/env python3
"""Enumerate and hash the complete worktree change set from a baseline."""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys

from docaudit_paths import matches_glob
from sealed_config import SealedConfigMismatch, load_sealed_config


PROBE_ROOTS = {".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}


def git(root, *args, check=True, input_bytes=None):
    return subprocess.run(["git", "-C", root, *args], input=input_bytes,
                          capture_output=True, check=check).stdout


def current_mode_blob(root, path):
    full = os.path.join(root, *path.split("/"))
    if not os.path.lexists(full):
        return "0", "0"
    info = os.lstat(full)
    if stat.S_ISLNK(info.st_mode):
        return "120000", os.readlink(full)
    if stat.S_ISDIR(info.st_mode):
        sub_head = git(full, "rev-parse", "HEAD", check=False).decode().strip() or "0"
        status_bytes = git(full, "status", "--porcelain=v2", "--untracked-files=all", check=False)
        diff_bytes = git(full, "diff", "HEAD", "--binary", "--no-ext-diff", check=False)
        dirty = hashlib.sha256(status_bytes + diff_bytes).hexdigest()
        return "160000", sub_head + ":" + dirty
    with open(full, "rb") as handle:
        content = handle.read()
    blob = git(root, "hash-object", "--stdin", input_bytes=content).decode().strip()
    mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
    return mode, blob


def report_pattern(config):
    value = config.get("reportPath")
    globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if not isinstance(value, str) or not value.endswith(".md"):
        return None
    sample = value.replace("<YYYY-MM-DD>", "2000-01-01").replace("[_NN]", "_01")
    if not any(matches_glob(sample, item) for item in globs if isinstance(item, str)):
        return None
    directory, name = os.path.split(value)
    if "<YYYY-MM-DD>" not in name:
        return None
    prefix = name.split("<YYYY-MM-DD>", 1)[0]
    if not prefix:
        return None
    marker = "<YYYY-MM-DD>"
    suffix_marker = "[_NN]"
    suffix_at = None
    if suffix_marker not in value:
        suffix_at = len(value) - len(name) + name.find(marker) + len(marker)
    out = []
    i = 0
    while i < len(value):
        if value.startswith(marker, i):
            out.append("[0-9]{4}-[0-9]{2}-[0-9]{2}")
            i += len(marker)
            if suffix_at == i:
                out.append("(_[0-9]{2,})?")
        elif value.startswith(suffix_marker, i):
            out.append("(_[0-9]{2,})?")
            i += len(suffix_marker)
        else:
            out.append(re.escape(value[i]))
            i += 1
    return "^" + "".join(out) + "$"


def excluded(path, config):
    if path == ".claude/state" or path.startswith(".claude/state/"):
        return True
    if path == ".claude/worktrees" or path.startswith(".claude/worktrees/"):
        return True
    if path.split("/", 1)[0] in PROBE_ROOTS:
        return True
    pattern = report_pattern(config)
    return bool(pattern and re.fullmatch(pattern, path))


def enumerate_changes(root, baseline, config):
    raw = git(root, "diff", "--raw", "-z", "--no-renames", "--abbrev=40",
              "--ignore-submodules=none", baseline, "--", ".")
    fields = raw.split(b"\0")
    changes = {}
    index = 0
    while index + 1 < len(fields) and fields[index]:
        header = fields[index].decode("ascii", "strict")
        path = os.fsdecode(fields[index + 1]).replace(os.sep, "/")
        index += 2
        parts = header[1:].split()
        if len(parts) != 5:
            raise ValueError("unexpected git diff --raw record")
        old_mode, raw_new_mode, old_blob, _raw_new_blob, status_code = parts
        new_mode, new_blob = current_mode_blob(root, path)
        if status_code.startswith("D"):
            new_mode, new_blob = "0", "0"
        changes[path] = (status_code, old_mode, old_blob, new_mode, new_blob)
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    for item in untracked.split(b"\0"):
        if not item:
            continue
        path = os.fsdecode(item).replace(os.sep, "/")
        mode, blob = current_mode_blob(root, path)
        changes[path] = ("?", "0", "0", mode, blob)
    return {path: changes[path] for path in sorted(changes) if not excluded(path, config)}


def calculate(root, baseline, config):
    changes = enumerate_changes(root, baseline, config)
    material = bytearray(baseline.encode("ascii") + b"\0")
    changed_set = []
    entries = []
    for path, (status_code, old_mode, old_blob, new_mode, new_blob) in changes.items():
        changed_set.append(path)
        entries.append({"status": status_code, "path": path, "oldMode": old_mode,
                        "oldBlob": old_blob, "newMode": new_mode, "newBlob": new_blob})
        for value in (status_code, path, old_mode, old_blob, new_mode, new_blob):
            material.extend(value.encode("utf-8", "surrogateescape") + b"\0")
    return "sha256:" + hashlib.sha256(material).hexdigest(), changed_set, entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha", required=True)
    args = parser.parse_args()
    try:
        _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
        digest, changed, entries = calculate(os.path.realpath(args.repo_root), args.baseline_sha, config)
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"change-set-sha: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"changeSetSha": digest, "changedSet": changed, "entries": entries}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
