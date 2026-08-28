#!/usr/bin/env python3
"""Read a run manifest only after verifying its sealed evidence digest."""

import argparse
import hashlib
import json
import os
import re
import sys


TAGGED_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_manifest(run_dir, evidence, opener=open):
    """Return the manifest parsed from the exact bytes whose digest was checked."""
    if not isinstance(evidence, dict):
        raise ValueError("EVIDENCE must be an object")
    expected = evidence.get("manifest")
    if not isinstance(expected, str) or not TAGGED_SHA_RE.fullmatch(expected):
        raise ValueError("EVIDENCE.manifest must be a sha256 digest")
    path = os.path.join(run_dir, "manifest.json")
    with opener(path, "rb") as handle:
        raw = handle.read()
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("manifest sha does not match EVIDENCE")
    manifest = json.loads(raw)
    if not (isinstance(manifest, dict) and manifest.get("sealed") is True):
        raise ValueError("manifest is not sealed")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence)
        manifest = read_manifest(args.run_dir, evidence)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"read-manifest: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
