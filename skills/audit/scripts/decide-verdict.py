#!/usr/bin/env python3
"""decide-verdict.py — the deterministic verdict gate and the SOLE anchor writer.

Trust is moved off the orchestrator LLM and into this program. The verdict is
DERIVED from on-disk evidence; it is NEVER passed in (there is deliberately no
--verdict argument — the old hand-off path is gone). The audit anchor is written
to disk if and ONLY if:

  1. every integrity check below passes, AND
  2. the derived verdict is CONSISTENT.

Any missing / incomplete / internally-inconsistent / stale / tampered evidence
=> REFUSED (exit 3), and the anchor is NOT written. Because this program is the
only thing that advances the anchor, an orchestrator that skips it (or skips the
verification phases) simply leaves the anchor unmoved — which is visible in git,
exactly the signal that exposed the original incident.

Local scope (closed here, each covered by a test):
  - hand-fed verdict (no --verdict arg exists)
  - skipped Phase 3 / partially-run Phase 3 (evidence count/set mismatch)
  - FAIL hidden by omitting a doc, or diluted by a duplicate/extra record
  - replayed stale evidence (manifest.head != current HEAD)
  - missing Phase 4 evidence when Phase 4 was required
  - malformed evidence (unparseable line, unknown verdict/severity)

Out of local scope (the residual forgery class — an orchestrator with shell
access can author arbitrary local files): deliberately fabricating a fully
self-consistent, runid-stamped evidence set. That is raised in difficulty here
(it is no longer lazy omission) and is closed by the independent CI re-derivation
(Layer 3), which recomputes the verdict from committed evidence and compares the
evidenceDigest stamped into the anchor below.
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

EXIT_DECIDED = 0   # verdict computed (CONSISTENT or NEEDS_FIX); see stdout
EXIT_USAGE = 2     # argparse / usage error
EXIT_REFUSED = 3   # evidence missing/inconsistent/stale/tampered — anchor NOT written

VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
FAIL_SEVERITIES = {"FAIL", "HIGH", "CRITICAL"}
NONFAIL_SEVERITIES = {"PASS", "WARN", "MEDIUM", "LOW", "INFO"}


def emit(obj, code):
    print(json.dumps(obj, sort_keys=True))
    sys.exit(code)


def refuse(reason):
    emit({"verdict": "REFUSED", "anchorWritten": False, "reason": reason}, EXIT_REFUSED)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Deterministic docaudit verdict gate + sole anchor writer.")
    ap.add_argument("--run-dir", required=True, help="evidence directory for this audit run")
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--anchor-path", required=True, help="anchor path relative to repo-root")
    ap.add_argument("--date", default=None, help="override date (YYYY-MM-DD); default = today")
    args = ap.parse_args()

    rd = args.run_dir

    # --- manifest: the "expected work" contract produced at run start ----------
    mpath = os.path.join(rd, "manifest.json")
    if not os.path.isfile(mpath):
        refuse("manifest.json missing — no run was started")
    try:
        manifest = load_json(mpath)
    except Exception as e:
        refuse(f"manifest.json unparseable: {e}")
    for k in ("runid", "head", "impacted", "mode", "phase4Expected"):
        if k not in manifest:
            refuse(f"manifest missing required field: {k}")
    runid = manifest["runid"]
    mode = manifest["mode"]
    impacted = manifest["impacted"]
    if not isinstance(impacted, list):
        refuse("manifest.impacted is not a list")
    impacted_set = set(impacted)
    if len(impacted_set) != len(impacted):
        refuse("manifest.impacted contains duplicate paths")

    # --- head match: a verdict is only valid for the tree it was produced on ---
    try:
        head = subprocess.run(
            ["git", "-C", args.repo_root, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception as e:
        refuse(f"git HEAD unreadable: {e}")
    if head != manifest["head"]:
        refuse(f"HEAD {head} != manifest.head {manifest['head']} (stale or replayed evidence)")

    # --- Phase 3 verdict records (one runid-stamped file per impacted doc) ------
    # Each Phase-3 verifier subagent writes its own file under verdicts/, so
    # parallel subagents never collide on a shared file.
    vdir = os.path.join(rd, "verdicts")
    records = []
    if os.path.isdir(vdir):
        for name in sorted(os.listdir(vdir)):
            if not name.endswith(".json"):
                continue
            try:
                r = load_json(os.path.join(vdir, name))
            except Exception:
                refuse(f"verdicts/{name} is not valid JSON")
            for k in ("runid", "path", "verdict"):
                if k not in r:
                    refuse(f"verdicts/{name} missing field: {k}")
            if r["runid"] != runid:
                refuse(f"verdicts/{name} runid {r['runid']!r} != run {runid!r} (foreign/forged record)")
            if r["verdict"] not in VALID_VERDICTS:
                refuse(f"verdicts/{name} has invalid verdict {r['verdict']!r}")
            records.append(r)

    paths = [r["path"] for r in records]
    if len(paths) != len(set(paths)):
        refuse("duplicate verdict record for the same path")
    if set(paths) != impacted_set:
        missing = sorted(impacted_set - set(paths))
        extra = sorted(set(paths) - impacted_set)
        refuse(f"verdict set != impacted set (missing={missing} extra={extra})")

    # --- Phase 4 evidence (reviews + delegated layers; main-loop produced) ------
    # Required when the SKILL global gate would have opened Phase 4. Derived
    # locally (not blindly trusted from the flag) for the dangerous cases.
    phase4_required = bool(manifest["phase4Expected"]) or len(impacted) > 0 or mode == "full"
    phase4_fail = False
    p4path = os.path.join(rd, "phase4.json")
    if os.path.isfile(p4path):
        try:
            p4 = load_json(p4path)
        except Exception as e:
            refuse(f"phase4.json unparseable: {e}")
        for finding in p4.get("findings", []):
            sev = str(finding.get("severity", "")).upper()
            if sev in FAIL_SEVERITIES:
                phase4_fail = True
            elif sev in NONFAIL_SEVERITIES:
                pass
            else:
                refuse(f"phase4 finding has unknown severity {sev!r} (cannot classify)")
    elif phase4_required:
        refuse("Phase 4 was required (impacted/ssotRecheck/full) but phase4.json is missing")

    # --- derive verdict (machine aggregation; WARN never blocks) ----------------
    phase3_fail = any(r["verdict"] == "FAIL" for r in records)
    has_fail = phase3_fail or phase4_fail
    verdict = "NEEDS_FIX" if has_fail else "CONSISTENT"

    evidence_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            {
                "manifest": manifest,
                "verdicts": sorted(records, key=lambda r: r["path"]),
                "phase4_fail": phase4_fail,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()

    if verdict != "CONSISTENT":
        emit(
            {
                "verdict": verdict,
                "anchorWritten": False,
                "runid": runid,
                "phase3Fail": phase3_fail,
                "phase4Fail": phase4_fail,
                "evidenceDigest": evidence_digest,
            },
            EXIT_DECIDED,
        )

    # --- CONSISTENT: write the anchor (this program is the sole writer) ---------
    date = args.date or datetime.date.today().isoformat()
    dest = os.path.join(args.repo_root, args.anchor_path)
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    anchor = {
        "sha": head,
        "date": date,
        "verdict": "CONSISTENT",
        "tool": "docaudit",
        "mode": mode,
        "runid": runid,
        "evidenceDigest": evidence_digest,
        "phase3Count": len(records),
        "phase4Expected": bool(manifest["phase4Expected"]),
    }
    with open(dest, "w") as f:
        json.dump(anchor, f, indent=2)
        f.write("\n")
    emit(
        {
            "verdict": "CONSISTENT",
            "anchorWritten": True,
            "runid": runid,
            "anchorPath": args.anchor_path,
            "evidenceDigest": evidence_digest,
        },
        EXIT_DECIDED,
    )


if __name__ == "__main__":
    main()
