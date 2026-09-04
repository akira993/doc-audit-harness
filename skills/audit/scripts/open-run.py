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
import stat
import sys
import tempfile
import time

from docaudit_paths import validate_repo_path


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_MANIFEST = os.path.join(HERE, "..", "..", "..", ".claude-plugin", "plugin.json")


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def plugin_engine_version():
    try:
        with open(PLUGIN_MANIFEST, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read plugin engine version: {exc}") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version:
        raise ValueError("plugin manifest has no version")
    return version


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
        value = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(value, dict):
        return None
    marker = value.get("historyQuarantineFailed")
    if marker is not None and not isinstance(marker, bool):
        return None
    return value


def read_last_run(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return "absent", None
    except OSError:
        return "unreadable", None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return "unreadable", None
        raw = os.read(fd, 65537)
        if len(raw) > 65536:
            return "unreadable", None
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "unreadable", None
    finally:
        os.close(fd)
    if not isinstance(value, dict):
        return "unreadable", None
    for key in ("configAcceptanceRequired", "historyQuarantineFailed"):
        if key in value and not isinstance(value[key], bool):
            return "unreadable", None
    return "valid", value


def report_status(value):
    status = value.get("reportStatus") if isinstance(value, dict) else None
    if status in {"pending", "failed", "written-durability-unknown"}:
        return status
    return None


def atomic_state(path, value):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".docaudit-state.", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def merge_quarantine_marker(last_run_path):
    state, value = read_last_run(last_run_path)
    if state == "unreadable":
        return False
    merged = dict(value) if state == "valid" else {}
    merged["historyQuarantineFailed"] = True
    try:
        atomic_state(last_run_path, merged)
    except OSError:
        return False
    return True


def release(lock_path, last_run_path, runid, breaking=False):
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
            return emit({"released": False, "reason": "lock-replaced",
                         "holder": holder or {"invalid": True}}, 4)
        if holder is None:
            return emit({"released": False, "reason": "lock-invalid",
                         "holder": {"invalid": True}}, 4)
        if not breaking and holder.get("runid") != runid:
            return emit({"released": False, "reason": "runid-mismatch", "holder": holder}, 4)
        if holder.get("historyQuarantineFailed") is True:
            merge_quarantine_marker(last_run_path)
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
    parser.add_argument("--expect-config-sha")
    parser.add_argument("--skill-version")
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
    last_run_path = os.path.join(repo, ".claude", "state", "docaudit-last-run.json")
    if args.break_lock:
        return release(lock_path, last_run_path, None, breaking=True)
    if args.release:
        if not args.runid or not RUNID_RE.match(args.runid):
            print("open-run: --release requires a valid --runid", file=sys.stderr)
            return 2
        return release(lock_path, last_run_path, args.runid)

    if not args.skill_version:
        print("open-run: normal open requires --skill-version", file=sys.stderr)
        return 2
    try:
        engine_version = plugin_engine_version()
    except ValueError as exc:
        print(f"open-run: {exc}", file=sys.stderr)
        return 2
    if args.skill_version != engine_version:
        print(
            f"open-run: skill version {args.skill_version} does not match plugin engine "
            f"version {engine_version}; the plugin changed under this session — start a new "
            "session and rerun the audit",
            file=sys.stderr,
        )
        return 2
    if not args.expect_config_sha:
        print("open-run: normal open requires --expect-config-sha", file=sys.stderr)
        return 2

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
        config_fd = os.open(config_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            if not stat.S_ISREG(os.fstat(config_fd).st_mode):
                raise OSError("config is not a regular file")
            chunks = []
            while True:
                chunk = os.read(config_fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            config_bytes = b"".join(chunks)
        finally:
            os.close(config_fd)
    except OSError as exc:
        print(f"open-run: cannot read config: {exc}", file=sys.stderr)
        return 2
    config_sha = sha(config_bytes)
    if config_sha != args.expect_config_sha:
        print("config-changed-before-open", file=sys.stderr)
        return 2
    try:
        config = json.loads(config_bytes.decode("utf-8"))
        if not isinstance(config, dict):
            raise ValueError("config top level must be an object")
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"open-run: invalid config: {exc}", file=sys.stderr)
        return 2
    anchor_absolute = (args.anchor_path if os.path.isabs(args.anchor_path)
                       else os.path.join(repo, args.anchor_path))
    anchor_rel = os.path.relpath(os.path.abspath(anchor_absolute), repo).replace(os.sep, "/")
    try:
        anchor_rel = validate_repo_path(
            repo, anchor_rel, must_exist=False, regular_file=False)
        configured_anchor = validate_repo_path(
            repo, config.get("anchorPath"), must_exist=False, regular_file=False)
        if anchor_rel != configured_anchor:
            raise ValueError("anchor-path-mismatch")
        anchor = os.path.join(repo, anchor_rel)
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

    if os.path.lexists(lock_path):
        try:
            existing_fd = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                existing = read_holder(existing_fd) or {"invalid": True}
            finally:
                os.close(existing_fd)
        except OSError:
            existing = {"invalid": True}
        return emit({"locked": True, "holder": existing}, 4)

    last_run_state, last_run = read_last_run(last_run_path)
    if last_run_state == "unreadable" and not args.accept_config:
        return emit({"opened": False, "reason": "last-run-unreadable"}, 6)
    acceptance_required = False
    if last_run_state == "valid":
        if last_run.get("configAcceptanceRequired") is True:
            acceptance_required = True
        elif ("configAcceptanceRequired" not in last_run
              and last_run.get("verdict") == "REFUSED"
              and last_run.get("reason") == "config-changed"
              and last_run.get("expectedConfigSha") != config_sha):
            acceptance_required = True
    if acceptance_required and not args.accept_config:
        return emit({"opened": False, "reason": "config-change-unaccepted",
                     "expectedConfigSha": last_run.get("expectedConfigSha")}, 6)

    prior_status = report_status(last_run)
    quarantine_pending = (
        last_run_state == "valid"
        and last_run.get("historyQuarantineFailed") is True
    ) or last_run_state == "unreadable"
    holder = {"runid": runid, "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    raw = (json.dumps(holder, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        return emit({"locked": True, "holder": {"invalid": True}}, 4)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, raw)
        os.fsync(fd)
        inode = os.fstat(fd).st_ino

        history_path = os.path.join(repo, ".claude", "state", "docaudit-history.json")
        if quarantine_pending and os.path.lexists(history_path):
            quarantine_path = history_path + f".tainted-{runid}-{int(time.time())}"
            try:
                os.replace(history_path, quarantine_path)
            except OSError as exc:
                raise RuntimeError("history-quarantine-pending") from exc
            if os.path.lexists(history_path):
                raise RuntimeError("history-quarantine-pending")

        updated_last_run = None
        if last_run_state == "unreadable":
            updated_last_run = {
                "configAcceptanceRequired": False,
                "historyQuarantineFailed": False,
            }
        elif last_run_state == "valid" and (
                args.accept_config or last_run.get("historyQuarantineFailed") is True):
            updated_last_run = dict(last_run)
            if args.accept_config:
                updated_last_run["configAcceptanceRequired"] = False
            if last_run.get("historyQuarantineFailed") is True:
                updated_last_run["historyQuarantineFailed"] = False
        if updated_last_run is not None:
            atomic_state(last_run_path, updated_last_run)

        run_dir = os.path.join(run_base, runid)
        os.mkdir(run_dir, 0o700)
    except Exception as exc:
        try:
            if os.fstat(fd).st_ino == os.lstat(lock_path).st_ino:
                os.unlink(lock_path)
        except OSError:
            pass
        if isinstance(exc, RuntimeError) and str(exc) == "history-quarantine-pending":
            print("history-quarantine-pending", file=sys.stderr)
        else:
            print(f"open-run: {exc}", file=sys.stderr)
        return 2
    finally:
        os.close(fd)
    result = {"runid": runid, "runDir": run_dir, "anchor": anchor_sha,
              "config": config_sha, "lockIno": inode,
              "preflight": "none", "phase4": "none", "engineVersion": engine_version}
    if prior_status is not None:
        result["previousReportStatus"] = prior_status
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
