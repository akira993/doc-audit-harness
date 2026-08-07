#!/usr/bin/env python3
"""Write one run-scoped Phase-3 verdict and echo the stored JSON."""

import argparse
import json
import os
import sys


VALID_VERDICTS = {"PASS", "WARN", "FAIL"}


def main():
    ap = argparse.ArgumentParser(description="Write one docaudit Phase-3 verdict.")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runid", required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--verdict", required=True, choices=sorted(VALID_VERDICTS))
    args = ap.parse_args()

    if not os.path.isabs(args.out):
        sys.exit("write-verdict: --out must be an absolute path")

    verdict_root = os.path.join(os.path.realpath(args.run_dir), "verdicts")
    out = os.path.realpath(args.out)
    try:
        contained = os.path.commonpath([verdict_root, out]) == verdict_root
    except ValueError:
        contained = False
    if not contained or out == verdict_root:
        sys.exit("write-verdict: --out must be inside RUN_DIR/verdicts/")

    rationale = sys.stdin.read()
    record = {
        "runid": args.runid,
        "path": args.path,
        "verdict": args.verdict,
        "rationale": rationale,
    }

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(out, encoding="utf-8") as f:
        stored = json.load(f)
    print(json.dumps(stored, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
