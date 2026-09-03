#!/usr/bin/env python3
"""Atomically persist one run-scoped codex claim adjudication."""

import argparse
import json
import os
import sys
import tempfile

from claim_record import (AGENT_CLAIM_STATES, FINDING_ID_RE, encode_claim_record,
                          validate_claim_record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--state", required=True, choices=sorted(AGENT_CLAIM_STATES))
    parser.add_argument("--evidence-file")
    parser.add_argument("--evidence-line", type=int)
    args = parser.parse_args()
    run_dir = os.path.realpath(args.run_dir)
    claims_dir = os.path.join(run_dir, "claims")
    out = os.path.realpath(args.out)
    try:
        if not FINDING_ID_RE.fullmatch(args.finding_id):
            raise ValueError("--finding-id must be 64 lowercase hexadecimal characters")
        expected_out = os.path.join(claims_dir, args.finding_id + ".json")
        if not os.path.isabs(args.out) or out != expected_out:
            raise ValueError("--out must be the assigned RUN_DIR/claims/<findingId>.json")
        if os.path.lexists(claims_dir) and os.path.islink(claims_dir):
            raise ValueError("claims directory may not be a symlink")
        record = {
            "runid": args.runid,
            "findingId": args.finding_id,
            "state": args.state,
            "rationale": sys.stdin.read(),
        }
        if args.evidence_file is not None:
            record["evidenceFile"] = args.evidence_file
        if args.evidence_line is not None:
            record["evidenceLine"] = args.evidence_line
        validate_claim_record(
            record, runid=args.runid, finding_id=args.finding_id,
            repo_root=os.path.realpath(args.repo_root), finding_file=""
        )
        raw = encode_claim_record(record)
        os.makedirs(claims_dir, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".claim.", dir=run_dir)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, out)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        with open(out, encoding="utf-8") as handle:
            stored = json.load(handle)
        print(json.dumps(stored, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"write-claim: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
