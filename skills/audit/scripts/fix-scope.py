#!/usr/bin/env python3
"""Authorize pre-flight fixes and detect changes outside the approved set."""

import argparse
import hashlib
import json
import os
import stat
import sys

from docaudit_paths import matches_glob, validate_repo_path


DENIED_PARTS = {"adr", "decisions", "logs"}


def load_allowed(path):
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    value = value.get("allowed") if isinstance(value, dict) else value
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("allowed file must contain an array")
    return set(value)


def snapshot(root):
    result = {}
    generated_roots = {".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}
    for dirpath, dirs, files in os.walk(root, followlinks=False):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirs[:] = [name for name in dirs if name != ".git"
                  and not os.path.islink(os.path.join(dirpath, name))
                  and not (rel_dir == "." and name in generated_roots)
                  and not (rel_dir == ".claude" and name == "state")]
        for name in files:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith(".git/"):
                continue
            mode = stat.S_IMODE(os.lstat(full).st_mode)
            if os.path.islink(full):
                raw = b"L\0" + str(mode).encode("ascii") + b"\0" + os.fsencode(os.readlink(full))
            else:
                with open(full, "rb") as handle:
                    raw = b"F\0" + str(mode).encode("ascii") + b"\0" + handle.read()
            result[rel] = hashlib.sha256(raw).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config")
    parser.add_argument("--paths")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--verify")
    parser.add_argument("--allowed")
    args = parser.parse_args()
    try:
        root = os.path.realpath(args.repo_root)
        if args.snapshot:
            if not args.allowed:
                raise ValueError("--snapshot requires --allowed")
            allowed = sorted(load_allowed(args.allowed))
            print(json.dumps({"allowed": allowed, "tree": snapshot(root)}, sort_keys=True))
            return 0
        if args.verify:
            if not args.allowed:
                raise ValueError("--verify requires --allowed")
            with open(args.verify, encoding="utf-8") as handle:
                before = json.load(handle).get("tree")
            if not isinstance(before, dict):
                raise ValueError("snapshot is invalid")
            allowed = load_allowed(args.allowed)
            after = snapshot(root)
            changed = sorted(path for path in set(before) | set(after)
                             if before.get(path) != after.get(path) and path not in allowed)
            print(json.dumps({"verified": not changed, "outsideChanges": changed}, sort_keys=True))
            return 0 if not changed else 3
        if not args.config or not args.paths:
            raise ValueError("classification requires --config and --paths")
        with open(args.config, encoding="utf-8") as handle:
            config = json.load(handle)
        raw = sys.stdin.read() if args.paths == "-" else open(args.paths, encoding="utf-8").read()
        allowed = []
        denied = []
        # Intentionally fail closed: omitted docGlobs rejects every pre-flight fix path.
        doc_globs = config.get("docGlobs", [])
        protected = config.get("protectedGlobs", [])
        for original in [line.strip() for line in raw.splitlines() if line.strip()]:
            reason = None
            try:
                path = validate_repo_path(root, original)
            except ValueError as exc:
                path = original
                reason = str(exc)
            lower_parts = path.lower().split("/")
            if reason is None and (lower_parts[0] == ".claude" or any(part in DENIED_PARTS for part in lower_parts)):
                reason = "built-in protected path"
            if reason is None and not any(matches_glob(path, pattern) for pattern in doc_globs):
                reason = "path does not match docGlobs"
            if reason is None and any(matches_glob(path.lower(), str(pattern).lower()) for pattern in protected):
                reason = "path matches protectedGlobs"
            if reason is None:
                allowed.append(path)
            else:
                denied.append({"path": original, "reason": reason})
        print(json.dumps({"allowed": sorted(set(allowed)), "denied": denied}, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"fix-scope: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
