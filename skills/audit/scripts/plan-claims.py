#!/usr/bin/env python3
"""Plan unresolved codex-review claims after Phase-4 evidence is fixed."""

import argparse
import json
import os
import sys
import tempfile

from claim_record import (ClaimRecordError, encode_claim_record, extract_claim_targets,
                          load_valid_claim_record, validate_claim_record)
from docaudit_paths import normalize_finding_path


def atomic_claim(run_dir, claims_dir, finding_id, record):
    raw = encode_claim_record(record)
    os.makedirs(claims_dir, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".claim.", dir=run_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, os.path.join(claims_dir, finding_id + ".json"))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--phase4-json", required=True)
    args = parser.parse_args()
    run_dir = os.path.realpath(args.run_dir)
    repo = os.path.realpath(args.repo_root)
    claims_dir = os.path.join(run_dir, "claims")
    try:
        if os.path.lexists(claims_dir) and os.path.islink(claims_dir):
            raise ValueError("claims directory may not be a symlink")
        with open(args.phase4_json, encoding="utf-8") as handle:
            phase4 = json.load(handle)
        targets, _missing_titles = extract_claim_targets(phase4)
        pending = []
        for target in targets:
            finding_id = target["findingId"]
            record_path = os.path.join(claims_dir, finding_id + ".json")
            if os.path.exists(record_path):
                try:
                    load_valid_claim_record(
                        record_path, runid=args.runid, finding_id=finding_id,
                        repo_root=repo, finding_file=target["file"]
                    )
                    continue
                except ClaimRecordError:
                    pass
            if normalize_finding_path(repo, target["file"]) is None:
                record = {
                    "runid": args.runid,
                    "findingId": finding_id,
                    "state": "not-adjudicable",
                    "reason": "path-unresolved",
                    "rationale": "The finding path does not resolve to a regular non-symlink repository file.",
                }
                validate_claim_record(
                    record, runid=args.runid, finding_id=finding_id,
                    repo_root=repo, finding_file=target["file"]
                )
                atomic_claim(run_dir, claims_dir, finding_id, record)
            else:
                pending.append(target)
        print(json.dumps(pending, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plan-claims: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
