#!/usr/bin/env python3
"""Safely write the report template bound to a sealed-run ledger directory."""

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile

from claim_record import extract_claim_targets
from docaudit_paths import validate_repo_path
from report_tokens import (MAX_PHASE4_BYTES, TokenCountError,
                           read_bounded_regular_file, validate_template_body)


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
MAX_TEMPLATE_BYTES = 2 * 1024 * 1024
PHASE4_TOO_LARGE = "file exceeds byte limit"


def write_all(fd, raw):
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def atomic_receipt(run_dir, value):
    path = os.path.join(run_dir, "report-template.receipt.json")
    raw = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".report-template-receipt.", dir=run_dir)
    try:
        write_all(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(temporary, path)
        directory_fd = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect_existing(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("existing template is not a regular file")
    finally:
        os.close(fd)


def create_template(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def replace_template(run_dir, path, raw):
    inspect_existing(path)
    fd, temporary = tempfile.mkstemp(prefix=".report-template.", dir=run_dir)
    try:
        write_all(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(temporary, path)
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def claim_target_count(repo, run_rel):
    phase4_rel = f"{run_rel}/phase4.json"
    phase4_path = os.path.join(repo, phase4_rel)
    if not os.path.lexists(phase4_path):
        return 0
    validated = validate_repo_path(repo, phase4_rel)
    try:
        raw = read_bounded_regular_file(
            os.path.join(repo, validated), MAX_PHASE4_BYTES)
    except ValueError as exc:
        if str(exc) == PHASE4_TOO_LARGE:
            print(
                "write-template: phase4.json exceeds MAX_PHASE4_BYTES; "
                "claim token count not checked",
                file=sys.stderr,
            )
            return None
        raise
    try:
        phase4 = json.loads(raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"phase4.json is not valid JSON: {exc}") from exc
    return len(extract_claim_targets(phase4)[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        if not RUNID_RE.fullmatch(args.runid):
            raise ValueError("invalid runid")
        repo = os.path.realpath(args.repo_root)
        run_rel = f".claude/state/docaudit-run/{args.runid}"
        validated = validate_repo_path(repo, run_rel, regular_file=False)
        run_dir = os.path.join(repo, validated)
        if not os.path.isdir(run_dir):
            raise ValueError("run directory is not a directory")
        template = os.path.join(run_dir, "report-template.md")

        # Invalidate first. Every invocation makes an older successful receipt unusable.
        atomic_receipt(run_dir, {"failed": True})

        raw = sys.stdin.buffer.read(MAX_TEMPLATE_BYTES + 1)
        if len(raw) > MAX_TEMPLATE_BYTES:
            raise ValueError("template exceeds 2 MiB")
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"report template is not valid UTF-8: {exc}") from exc
        validate_template_body(text, claim_target_count(repo, run_rel))
        if args.replace:
            replace_template(run_dir, template, raw)
        else:
            create_template(template, raw)
        receipt = {
            "bytes": len(raw),
            "failed": False,
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }
        atomic_receipt(run_dir, receipt)
    except (OSError, TokenCountError, ValueError) as exc:
        print(f"write-template: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
