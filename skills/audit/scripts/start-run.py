#!/usr/bin/env python3
"""start-run.py — open an audit run by writing the evidence manifest.

The manifest is the "expected work" contract that decide-verdict.py later checks
the evidence against. It is derived from the deterministic Phase-2 output
(resolve-impact.py), NOT from anything the orchestrator narrates:

  - impacted : the exact list of doc paths that MUST each get a Phase-3 verdict
  - head     : the commit the verdicts are valid for (defeats replayed evidence)
  - phase4Expected : whether the SKILL Phase-4 gate opens (impacted non-empty OR
                     ssotRecheck non-empty OR mode==full) — so a required Phase 4
                     cannot be silently skipped

It also creates the verdicts/ directory each Phase-3 subagent writes into.

This script is plumbing run by the orchestrator; it is NOT a trust anchor (an
orchestrator with shell access could fake a manifest). Its integrity is the job
of the Layer-3 CI re-derivation. What it buys locally is that the honest path is
turn-key and every downstream omission becomes a hard REFUSE in the gate.
"""
import argparse
import json
import os
import subprocess
import sys
import uuid


def impacted_paths(impacted):
    out = []
    for d in impacted:
        if isinstance(d, str):
            out.append(d)
        elif isinstance(d, dict) and "path" in d:
            out.append(d["path"])
        else:
            sys.exit(f"start-run: malformed impacted entry: {d!r}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Write the docaudit run manifest.")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--impact-json", required=True,
                    help="resolve-impact.py output: a file path, or - for stdin")
    ap.add_argument("--mode", default="incremental", choices=["incremental", "full"])
    ap.add_argument("--runid", default=None, help="override (default: generated)")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.impact_json == "-" else open(args.impact_json).read()
    try:
        impact = json.loads(raw)
    except Exception as e:
        sys.exit(f"start-run: --impact-json is not valid JSON: {e}")

    impacted = impacted_paths(impact.get("impacted", []))
    if len(set(impacted)) != len(impacted):
        sys.exit("start-run: resolve-impact produced duplicate impacted paths")
    ssot_recheck = impact.get("ssotRecheck", [])

    head = subprocess.run(
        ["git", "-C", args.repo_root, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    phase4_expected = bool(impacted) or bool(ssot_recheck) or args.mode == "full"
    runid = args.runid or "run-" + uuid.uuid4().hex[:12]

    # Start clean: stale evidence from a previous run carries a different runid
    # (the gate would REFUSE on it). Clear it so the honest path just works.
    vdir = os.path.join(args.run_dir, "verdicts")
    os.makedirs(vdir, exist_ok=True)
    for name in os.listdir(vdir):
        if name.endswith(".json"):
            os.remove(os.path.join(vdir, name))
    p4 = os.path.join(args.run_dir, "phase4.json")
    if os.path.isfile(p4):
        os.remove(p4)

    manifest = {
        "runid": runid,
        "head": head,
        "mode": args.mode,
        "impacted": impacted,
        "phase4Expected": phase4_expected,
    }
    with open(os.path.join(args.run_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(json.dumps({"runid": runid, "runDir": args.run_dir,
                      "impactedCount": len(impacted), "phase4Expected": phase4_expected},
                     sort_keys=True))


if __name__ == "__main__":
    main()
