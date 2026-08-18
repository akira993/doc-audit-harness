#!/usr/bin/env python3
"""Atomically write one run-scoped verifier or cache verdict."""

import argparse
import json
import os
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--verdict", required=True, choices=["FAIL", "PASS", "WARN"])
    parser.add_argument("--source", choices=["verifier", "cache"], default="verifier")
    parser.add_argument("--history-runids", default="[]")
    parser.add_argument("--content-sha")
    parser.add_argument("--change-set-sha")
    parser.add_argument("--contract-version")
    args = parser.parse_args()
    verdict_root = os.path.realpath(os.path.join(args.run_dir, "verdicts"))
    out = os.path.realpath(args.out)
    try:
        if not os.path.isabs(args.out) or os.path.commonpath([verdict_root, out]) != verdict_root or out == verdict_root:
            raise ValueError("--out must be an absolute path inside RUN_DIR/verdicts")
        if os.path.lexists(os.path.join(args.run_dir, "verdicts")) and os.path.islink(os.path.join(args.run_dir, "verdicts")):
            raise ValueError("verdicts directory may not be a symlink")
        record = {"runid": args.runid, "path": args.path, "verdict": args.verdict,
                  "rationale": sys.stdin.read()}
        if args.source == "cache":
            runids = json.loads(args.history_runids)
            if (args.verdict != "PASS" or not isinstance(runids, list)
                    or not runids or not all(isinstance(value, str) for value in runids)
                    or not all((args.content_sha, args.change_set_sha, args.contract_version))):
                raise ValueError("cache verdict requires PASS, history runids, and all cache keys")
            record.update({"source": "cache", "historyRunids": runids, "contentSha": args.content_sha,
                           "changeSetSha": args.change_set_sha,
                           "contractVersion": args.contract_version})
        raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        os.makedirs(verdict_root, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".verdict.", dir=verdict_root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, out)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"write-verdict: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
