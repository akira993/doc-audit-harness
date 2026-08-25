#!/usr/bin/env python3
"""Search documentation siblings for potentially stale phrases."""

import argparse
import json
import os
import re
import subprocess
import sys

from docaudit_paths import list_doc_files


QUOTE_RE = re.compile(r'"([^"\n\r]{2,200})"|`([^`\n\r]{2,80})`')
SEMVER_RE = re.compile(r'\bv?\d+\.\d+\.\d+\b')
STOPLIST = {"mapped", "heuristic", "both", "full", "skill", "graphify", "semantic",
            "pass", "warn", "fail", "consistent", "needs_fix", "needs fix", "true",
            "false", "null", "none"}


def blank_result(reason=None):
    result = {"phrases": [], "matches": [],
              "sources": {"findings": 0, "phase4": 0, "changeSet": 0, "notes": []},
              "truncated": {}, "truncatedTotal": 0, "phraseTruncated": 0}
    if reason:
        result["skipped"] = reason
        result["sources"]["notes"].append(reason)
    return result


def valid_common(phrase):
    phrase = phrase.strip()
    if not phrase or any(ord(char) < 32 or ord(char) == 127 for char in phrase):
        return False
    if phrase.casefold() in STOPLIST or not any(char.isalnum() for char in phrase):
        return False
    return True


def valid_quote(phrase, kind):
    if not valid_common(phrase):
        return False
    if kind == "backtick":
        allowed = set("._/@:#<>=()- ")
        return (2 <= len(phrase) <= 80 and any(char.isalnum() for char in phrase)
                and all(char.isalnum() or char in allowed for char in phrase))
    words = re.findall(r"[^\W_]+", phrase, flags=re.UNICODE)
    non_ascii = any(char.isalnum() and not char.isascii() for char in phrase)
    alnums = sum(char.isalnum() for char in phrase)
    return (6 <= len(phrase) <= 200 and len(words) >= 2) or (non_ascii and alnums >= 2 and 4 <= len(phrase) <= 200)


def valid_title(phrase):
    return valid_common(phrase) and 6 <= len(phrase) <= 200 and sum(char.isalnum() for char in phrase) >= 2


def quote_phrases(text):
    if not isinstance(text, str):
        return []
    result = []
    for match in QUOTE_RE.finditer(text):
        phrase, kind = (match.group(1), "double") if match.group(1) is not None else (match.group(2), "backtick")
        phrase = phrase.strip()
        if valid_quote(phrase, kind):
            result.append(phrase)
    return result


def diff_candidates(repo, manifest, notes):
    paths = [path for path in manifest.get("changedSet", []) if isinstance(path, str)]
    baseline = manifest.get("baselineSha")
    if isinstance(baseline, str) and baseline == manifest.get("head"):
        notes.append("full mode: working-copy diff only")
    if not paths or not isinstance(baseline, str):
        return []
    try:
        proc = subprocess.run(["git", "-c", "core.quotePath=false", "-c", "color.ui=never",
                               "-C", repo, "diff", "--no-ext-diff", "--no-textconv",
                               "--no-color", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/",
                               baseline, "--", *paths],
                              capture_output=True, text=False, check=False)
    except OSError as exc:
        notes.append(f"change-set diff failed: {exc}")
        return []
    if proc.returncode:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        notes.append("change-set diff failed: " + (detail or str(proc.returncode)))
        return []
    try:
        diff_text = proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        notes.append(f"change-set diff decode failed: {exc}")
        return []
    added, removed, current = {}, [], None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("--- a/"):
            current = line[6:]
        elif line.startswith("+++ b/"):
            current = line[6:]
        elif current and line.startswith("+") and not line.startswith("+++"):
            added.setdefault(current, []).append(line[1:])
        elif current and line.startswith("-") and not line.startswith("---"):
            removed.append((current, line[1:]))
    candidates = []
    for path, text in removed:
        normalized_added = " ".join(added.get(path, [])).split()
        added_text = " ".join(normalized_added)
        for phrase in quote_phrases(text):
            if " ".join(phrase.split()) not in added_text:
                candidates.append(phrase)
        for phrase in SEMVER_RE.findall(text):
            if " ".join(phrase.split()) not in added_text:
                candidates.append(phrase)
    return candidates


def scan(payload):
    repo = payload.get("repoRoot")
    manifest = payload.get("manifest")
    if not isinstance(repo, str) or not isinstance(manifest, dict):
        raise ValueError("payload requires repoRoot and manifest")
    result = blank_result()
    grouped = {"findings": [], "phase4": [], "changeSet": []}
    for item in payload.get("returns", []):
        if not isinstance(item, dict) or item.get("verdict") not in {"FAIL", "WARN"}:
            continue
        for field in ("rationale", "suggestion"):
            grouped["findings"].extend(quote_phrases(item.get(field)))
    phase4 = payload.get("phase4")
    if isinstance(phase4, dict):
        for finding in phase4.get("findings", []):
            title = finding.get("title") if isinstance(finding, dict) else None
            if isinstance(title, str):
                grouped["phase4"].extend(quote_phrases(title))
                if valid_title(title.strip()):
                    grouped["phase4"].append(title.strip())
    grouped["changeSet"] = diff_candidates(repo, manifest, result["sources"]["notes"])
    phrases, seen = [], set()
    for source in ("findings", "phase4", "changeSet"):
        for phrase in grouped[source]:
            if phrase in seen:
                continue
            seen.add(phrase)
            if len(phrases) >= 200:
                result["phraseTruncated"] += 1
                continue
            phrases.append(phrase)
            result["sources"][source] += 1
    result["phrases"] = sorted(phrases)
    if not result["phrases"]:
        return result
    report_pattern = payload.get("reportPattern")
    docs = []
    for path in list_doc_files(repo, manifest.get("docGlobs", []), result["sources"]["notes"]):
        if path.startswith(".claude/state/") or (isinstance(report_pattern, str)
                                                   and re.fullmatch(report_pattern, path)):
            continue
        docs.append(path)
    counts = {}
    for path in docs:
        with open(os.path.join(repo, path), encoding="utf-8", errors="ignore") as handle:
            for number, line in enumerate(handle, 1):
                for phrase in result["phrases"]:
                    if phrase in line:
                        count = counts.get(phrase, 0)
                        counts[phrase] = count + 1
                        if count >= 20:
                            result["truncated"][phrase] = result["truncated"].get(phrase, 0) + 1
                            result["truncatedTotal"] += 1
                        else:
                            result["matches"].append({"phrase": phrase, "path": path, "line": number})
    return result


def load_run_dir(run_dir, report_pattern):
    with open(os.path.join(run_dir, "returns.json"), encoding="utf-8") as handle:
        returns = json.load(handle)
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    phase_path = os.path.join(run_dir, "phase4.json")
    phase4 = json.load(open(phase_path, encoding="utf-8")) if os.path.exists(phase_path) else None
    return {"repoRoot": os.path.realpath(os.path.join(run_dir, "..", "..", "..", "..")),
            "manifest": manifest, "returns": returns, "phase4": phase4, "reportPattern": report_pattern}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-dir")
    group.add_argument("--stdin", action="store_true")
    parser.add_argument("--report-pattern")
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin) if args.stdin else load_run_dir(args.run_dir, args.report_pattern)
        print(json.dumps(scan(payload), ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sibling-scan: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
