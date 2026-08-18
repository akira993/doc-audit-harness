#!/usr/bin/env python3
"""Open, release, or explicitly break a docaudit run lock."""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import secrets
import sys

from docaudit_paths import validate_repo_path


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def emit(value, code=0):
    print(json.dumps(value, sort_keys=True))
    return code


def within_repo(repo, path):
    lexical_repo = os.path.abspath(repo)
    absolute = os.path.abspath(path)
    try:
        if os.path.commonpath([lexical_repo, absolute]) != lexical_repo:
            raise ValueError("run-base must be inside repo-root")
    except ValueError as exc:
        raise ValueError("run-base must be inside repo-root") from exc
    current = lexical_repo
    rel = os.path.relpath(absolute, lexical_repo)
    if rel == ".":
        raise ValueError("run-base cannot be repo-root")
    for part in rel.split(os.sep):
        if part in ("", ".", ".."):
            raise ValueError("invalid run-base")
        current = os.path.join(current, part)
        if os.path.lexists(current) and os.path.islink(current):
            raise ValueError("run-base may not contain symlinks")
    real_repo = os.path.realpath(lexical_repo)
    resolved = os.path.realpath(absolute)
    if os.path.commonpath([real_repo, resolved]) != real_repo:
        raise ValueError("run-base resolves outside repo-root")
    return absolute


def read_holder(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, 65536)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"invalid": True}


def release(lock_path, runid, breaking=False):
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        return emit({"released": False, "reason": "lock-missing"}, 0 if breaking else 4)
    except OSError as exc:
        print(f"open-run: cannot safely open lock: {exc}", file=sys.stderr)
        return 4
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return emit({"released": False, "reason": "gate-running", "holder": read_holder(fd)}, 4)
        before = os.fstat(fd).st_ino
        try:
            after = os.stat(lock_path, follow_symlinks=False).st_ino
        except FileNotFoundError:
            return emit({"released": False, "reason": "lock-replaced"}, 4)
        holder = read_holder(fd)
        if before != after:
            return emit({"released": False, "reason": "lock-replaced", "holder": holder}, 4)
        if not breaking and holder.get("runid") != runid:
            return emit({"released": False, "reason": "runid-mismatch", "holder": holder}, 4)
        os.unlink(lock_path)
        return emit({"released": True, "broken": breaking, "holder": holder})
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-base", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--anchor-path", default=".claude/state/last-doc-audit.json")
    parser.add_argument("--runid")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--break-lock", action="store_true")
    parser.add_argument("--accept-config", action="store_true")
    args = parser.parse_args()
    if args.release and args.break_lock:
        parser.error("--release and --break-lock are mutually exclusive")
    try:
        run_base = within_repo(args.repo_root, args.run_base)
        repo = os.path.realpath(args.repo_root)
        if os.path.realpath(run_base) != os.path.join(
                repo, ".claude", "state", "docaudit-run"):
            raise ValueError("run-base must be .claude/state/docaudit-run")
        os.makedirs(run_base, exist_ok=True)
    except (OSError, ValueError) as exc:
        print(f"open-run: {exc}", file=sys.stderr)
        return 2
    lock_path = os.path.join(run_base, "lock")
    if args.break_lock:
        return release(lock_path, None, breaking=True)
    if args.release:
        if not args.runid or not RUNID_RE.match(args.runid):
            print("open-run: --release requires a valid --runid", file=sys.stderr)
            return 2
        return release(lock_path, args.runid)

    runid = args.runid or (datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4))
    if not RUNID_RE.match(runid):
        print("open-run: invalid runid", file=sys.stderr)
        return 2
    try:
        config_path = os.path.join(repo, validate_repo_path(repo, ".claude/doc-audit.json"))
    except ValueError as exc:
        print(f"open-run: invalid config path: {exc}", file=sys.stderr)
        return 2
    try:
        with open(config_path, "rb") as handle:
            config_bytes = handle.read()
    except OSError as exc:
        print(f"open-run: cannot read config: {exc}", file=sys.stderr)
        return 2
    config_sha = sha(config_bytes)
    last_run_path = os.path.join(repo, ".claude", "state", "docaudit-last-run.json")
    if os.path.isfile(last_run_path) and not args.accept_config:
        try:
            with open(last_run_path, encoding="utf-8") as handle:
                last_run = json.load(handle)
        except (OSError, json.JSONDecodeError):
            last_run = {}
        if (last_run.get("verdict") == "REFUSED"
                and last_run.get("reason") == "config-changed"
                and last_run.get("expectedConfigSha") != config_sha):
            return emit({"opened": False, "reason": "config-change-unaccepted",
                         "expectedConfigSha": last_run.get("expectedConfigSha")}, 6)
    anchor_absolute = (args.anchor_path if os.path.isabs(args.anchor_path)
                       else os.path.join(repo, args.anchor_path))
    anchor_rel = os.path.relpath(os.path.abspath(anchor_absolute), repo).replace(os.sep, "/")
    try:
        anchor = os.path.join(
            repo, validate_repo_path(repo, anchor_rel, must_exist=False, regular_file=False))
        if os.path.lexists(anchor) and not os.path.isfile(anchor):
            raise ValueError("anchor must be a regular file when present")
    except ValueError as exc:
        print(f"open-run: invalid anchor path: {exc}", file=sys.stderr)
        return 2
    if os.path.isfile(anchor):
        with open(anchor, "rb") as handle:
            anchor_sha = sha(handle.read())
    else:
        anchor_sha = "none"
    holder = {"runid": runid, "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    raw = (json.dumps(holder, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        try:
            existing_fd = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                existing = read_holder(existing_fd)
            finally:
                os.close(existing_fd)
        except Exception:
            existing = {"invalid": True}
        return emit({"locked": True, "holder": existing}, 4)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, raw)
        os.fsync(fd)
        inode = os.fstat(fd).st_ino
        run_dir = os.path.join(run_base, runid)
        os.mkdir(run_dir, 0o700)
    except Exception as exc:
        try:
            os.unlink(lock_path)
        except OSError:
            pass
        print(f"open-run: {exc}", file=sys.stderr)
        return 2
    finally:
        os.close(fd)
    return emit({"runid": runid, "runDir": run_dir, "anchor": anchor_sha,
                 "config": config_sha, "lockIno": inode,
                 "preflight": "none", "phase4": "none"})


if __name__ == "__main__":
    sys.exit(main())
