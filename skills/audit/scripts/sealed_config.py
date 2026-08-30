#!/usr/bin/env python3
"""Read a JSON config once and verify its sealed SHA-256 before use."""

import argparse
import hashlib
import json
import os
import re
import sys


SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_MISSING = object()


class SealedConfigMismatch(Exception):
    """The bytes read from config do not match the expected seal."""

    def __init__(self, expected_sha, observed_sha):
        super().__init__(expected_sha, observed_sha)
        self.expected_sha = expected_sha
        self.observed_sha = observed_sha

    def __str__(self):
        return (f"sealed-config-mismatch: expected {self.expected_sha} "
                f"observed {self.observed_sha}")


def load_sealed_config(path, expected_sha, with_signature=False):
    """Return verified bytes and JSON, optionally with the read fd's signature."""
    if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
        raise ValueError("expected config sha must be sha256:<64 lowercase hex>")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        observed_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        signature = None
        if with_signature:
            info = os.fstat(fd)
            try:
                path_info = os.lstat(path)
            except OSError as exc:
                raise SealedConfigMismatch(expected_sha, observed_sha) from exc
            if path_info.st_ino != info.st_ino:
                raise SealedConfigMismatch(expected_sha, observed_sha)
            signature = (info.st_ino, info.st_size, info.st_mtime_ns)
    finally:
        os.close(fd)
    if observed_sha != expected_sha:
        raise SealedConfigMismatch(expected_sha, observed_sha)
    doc = json.loads(raw.decode("utf-8"))
    if with_signature:
        return raw, doc, signature
    return raw, doc


def dotted_get(value, dotted_key):
    parts = dotted_key.split(".")
    if not dotted_key or any(not part for part in parts):
        raise ValueError("--get requires a non-empty dotted key")
    current = value
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-sha", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--print", dest="print_config", action="store_true")
    action.add_argument("--get")
    parser.add_argument("--default")
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()

    try:
        if not SHA_RE.fullmatch(args.expect_sha):
            raise ValueError("--expect-sha must be sha256:<64 lowercase hex>")
        if args.print_config and (args.default is not None or args.raw):
            raise ValueError("--default and --raw require --get")
        default = _MISSING if args.default is None else json.loads(args.default)
        _raw, doc = load_sealed_config(args.config, args.expect_sha)
        if args.print_config:
            value = doc
        else:
            value = dotted_get(doc, args.get)
            if value is _MISSING:
                value = None if default is _MISSING else default
        if args.raw:
            if value is None:
                output = ""
            elif isinstance(value, str):
                output = value
            else:
                raise ValueError("--raw value must be a string or null")
            sys.stdout.buffer.write((output + "\n").encode("utf-8"))
        else:
            rendered = json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n"
            sys.stdout.buffer.write(rendered.encode("ascii"))
        return 0
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"sealed-config: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
