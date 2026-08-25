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

from docaudit_paths import validate_repo_path


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
MAX_TEMPLATE_BYTES = 2 * 1024 * 1024


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
    except (OSError, ValueError) as exc:
        print(f"write-template: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
