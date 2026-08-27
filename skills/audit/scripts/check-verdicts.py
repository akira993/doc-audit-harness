#!/usr/bin/env python3
"""Report Phase-3 evidence completeness without changing any evidence.

This is a completeness preflight only. ``phase3Complete: true`` does not
guarantee that the deterministic gate will pass; the gate performs additional
manifest, HEAD, Phase-4, duplicate, and integrity checks.
"""

import argparse
import json
import os
import sys


VALID_VERDICTS = {"PASS", "WARN", "FAIL"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unique_paths(entries, warnings, source):
    paths = []
    provenance = {}
    if not isinstance(entries, list):
        warnings.append(f"{source}.impacted is not a list")
        return paths, provenance, False

    valid_shape = True
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            path = entry
            prov = "unknown"
        elif isinstance(entry, dict) and isinstance(entry.get("path"), str):
            path = entry["path"]
            prov = entry.get("provenance", "unknown")
        else:
            warnings.append(f"{source}.impacted[{index}] has no string path")
            valid_shape = False
            continue
        if path not in provenance:
            paths.append(path)
            provenance[path] = prov if isinstance(prov, str) else "unknown"
    return paths, provenance, valid_shape


def main():
    ap = argparse.ArgumentParser(description="Report docaudit Phase-3 verdict completeness.")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--impact-json")
    ap.add_argument("--returns", nargs="?", const="__RUN_DIR__",
                    help="validate final workflow returns (default RUN_DIR/returns.json)")
    args = ap.parse_args()
    if args.impact_json is None:
        args.impact_json = os.path.join(args.run_dir, "impact.json")

    warnings = []
    invalid = []
    extra = set()
    duplicates = []
    manifest_ok = True
    impact_ok = True

    try:
        manifest = load_json(os.path.join(args.run_dir, "manifest.json"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        manifest = {}
        manifest_ok = False
        warnings.append(f"manifest.json cannot be read or parsed: {e}")
    if not isinstance(manifest, dict):
        manifest = {}
        manifest_ok = False
        warnings.append("manifest.json is not an object")

    runid = manifest.get("runid")
    if not isinstance(runid, str):
        manifest_ok = False
        warnings.append("manifest.json has no string runid")
    manifest_paths, _, manifest_shape_ok = unique_paths(
        manifest.get("impacted"), warnings, "manifest.json"
    )
    manifest_provenance = manifest.get("provenance")
    if not isinstance(manifest_provenance, dict):
        manifest_provenance = {}
        manifest_ok = False
        warnings.append("manifest.json provenance is not an object")
    manifest_ok = manifest_ok and manifest_shape_ok and isinstance(manifest.get("impacted"), list)
    if isinstance(manifest.get("impacted"), list):
        raw_manifest_paths = []
        for entry in manifest["impacted"]:
            path = entry if isinstance(entry, str) else (
                entry.get("path") if isinstance(entry, dict) else None
            )
            if isinstance(path, str):
                raw_manifest_paths.append(path)
        if len(raw_manifest_paths) != len(set(raw_manifest_paths)):
            manifest_ok = False
            warnings.append("manifest.json impacted paths contain duplicates")

    try:
        impact = load_json(args.impact_json)
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        impact = {}
        impact_ok = False
        warnings.append(f"impact.json cannot be read or parsed: {e}")
    if not isinstance(impact, dict):
        impact = {}
        impact_ok = False
        warnings.append("impact.json is not an object")
    impact_paths, impact_provenance, impact_shape_ok = unique_paths(
        impact.get("impacted"), warnings, "impact.json"
    )
    impact_ok = impact_ok and impact_shape_ok and isinstance(impact.get("impacted"), list)

    manifest_set = set(manifest_paths)
    impact_set = set(impact_paths)
    provenance_mismatch = manifest_provenance != impact_provenance
    manifest_mismatch = (not manifest_ok or not impact_ok or manifest_set != impact_set
                         or provenance_mismatch)
    if manifest_set != impact_set:
        only_manifest = sorted(manifest_set - impact_set)
        only_impact = sorted(impact_set - manifest_set)
        warnings.append(
            "manifest/impact path mismatch "
            f"(manifestOnly={only_manifest}, impactOnly={only_impact})"
        )
    if provenance_mismatch:
        warnings.append("manifest/impact provenance mismatch")

    valid_counts = {}
    valid_records = {}
    verdict_dir = os.path.join(args.run_dir, "verdicts")
    try:
        names = sorted(os.listdir(verdict_dir)) if os.path.isdir(verdict_dir) else []
    except OSError as e:
        names = []
        invalid.append(f"verdicts/: cannot list directory: {e}")

    for name in names:
        if not name.endswith(".json"):
            continue
        filename = f"verdicts/{name}"
        try:
            record = load_json(os.path.join(verdict_dir, name))
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            invalid.append(f"{filename}: invalid JSON: {e}")
            continue
        if not isinstance(record, dict):
            invalid.append(f"{filename}: record is not an object")
            continue
        missing_fields = [key for key in ("runid", "path", "verdict") if key not in record]
        if missing_fields:
            invalid.append(f"{filename}: missing fields {missing_fields}")
            continue

        path = record["path"]
        reasons = []
        if not isinstance(path, str):
            reasons.append("path is not a string")
        elif path not in manifest_set:
            extra.add(path)
            reasons.append("path is not in manifest.impacted")
        if record["runid"] != runid:
            reasons.append("runid does not match manifest")
        verdict = record["verdict"]
        if not isinstance(verdict, str) or verdict not in VALID_VERDICTS:
            reasons.append("verdict is not PASS/WARN/FAIL")
        if reasons:
            invalid.append(f"{filename}: {'; '.join(reasons)}")
            continue
        valid_counts[path] = valid_counts.get(path, 0) + 1
        valid_records[path] = record

    duplicates = sorted(path for path, count in valid_counts.items() if count > 1)
    return_required_paths = manifest.get("dispatch", manifest_paths)
    if not isinstance(return_required_paths, list):
        return_required_paths = manifest_paths
        warnings.append("manifest.dispatch is not a list")
        manifest_ok = False
    missing = [path for path in manifest_paths if valid_counts.get(path, 0) == 0]
    missing_impacted = [
        {"path": path, "provenance": impact_provenance.get(path, "unknown")}
        for path in missing
    ]
    extra_list = sorted(extra)
    return_missing = []
    mismatch = []
    if args.returns is not None:
        returns_path = (os.path.join(args.run_dir, "returns.json")
                        if args.returns == "__RUN_DIR__" else args.returns)
        try:
            returned = load_json(returns_path)
            if not isinstance(returned, list):
                raise ValueError("returns is not an array")
            final = {}
            seen = set()
            for index, item in enumerate(returned):
                if not isinstance(item, dict):
                    raise ValueError(f"returns[{index}] is not an object")
                attempt = item.get("attempt")
                assigned = item.get("assignedPath")
                if (isinstance(attempt, bool) or not isinstance(attempt, int)
                        or not 1 <= attempt <= 3 or not isinstance(assigned, str)):
                    raise ValueError(f"returns[{index}] has invalid attempt/assignedPath")
                if (attempt, assigned) in seen:
                    raise ValueError("returns has duplicate (attempt,assignedPath)")
                seen.add((attempt, assigned))
                if (assigned in return_required_paths
                        and (assigned not in final or attempt > final[assigned]["attempt"])):
                    final[assigned] = item
            for path in return_required_paths:
                if path not in final:
                    return_missing.append(path)
                    continue
                item = final[path]
                disk = valid_records.get(path)
                if (item.get("returnedPath") != path or disk is None
                        or item.get("verdict") != disk.get("verdict")):
                    mismatch.append(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as e:
            invalid.append(f"returns.json: {e}")
            return_missing = list(return_required_paths)

    phase3_complete = not (
        missing or invalid or extra_list or duplicates or manifest_mismatch
        or return_missing or mismatch
    )

    json.dump(
        {
            "phase3Complete": phase3_complete,
            "missing": missing,
            "missingImpacted": missing_impacted,
            "invalid": invalid,
            "extra": extra_list,
            "duplicates": duplicates,
            "warnings": warnings,
            "manifestMismatch": manifest_mismatch,
            "returnMissing": return_missing,
            "mismatch": mismatch,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    main()
