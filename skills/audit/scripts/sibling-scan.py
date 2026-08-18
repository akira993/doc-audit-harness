#!/usr/bin/env python3
"""Search documentation siblings for quoted phrases from failed returns."""

import argparse
import json
import os
import re
import sys

from docaudit_paths import list_doc_files


QUOTE_RE = re.compile(r'(?:"([^"]{4,200})"|`([^`]{4,200})`)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        with open(os.path.join(args.run_dir, "returns.json"), encoding="utf-8") as handle:
            returns = json.load(handle)
        with open(os.path.join(args.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        phrases = set()
        for item in returns:
            if item.get("verdict") not in {"FAIL", "WARN"}:
                continue
            for field in ("rationale", "suggestion"):
                value = item.get(field)
                if not isinstance(value, str):
                    continue
                for match in QUOTE_RE.finditer(value):
                    phrases.add(next(group for group in match.groups() if group is not None))
        repo = os.path.realpath(os.path.join(args.run_dir, "..", "..", "..", ".."))
        matches = []
        for path in list_doc_files(repo, manifest.get("docGlobs", [])):
            with open(os.path.join(repo, path), encoding="utf-8", errors="ignore") as handle:
                for number, line in enumerate(handle, 1):
                    for phrase in sorted(phrases):
                        if phrase in line:
                            matches.append({"phrase": phrase, "path": path, "line": number})
        print(json.dumps({"phrases": sorted(phrases), "matches": matches}, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sibling-scan: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
