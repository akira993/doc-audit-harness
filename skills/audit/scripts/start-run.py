#!/usr/bin/env python3
"""Create the complete unsealed run manifest from impact and dispatch plans."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from docaudit_paths import list_doc_files, validate_repo_path


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
BUILTIN_EXCLUDES = [".claude/state/docaudit-run", ".claude/state/docaudit-history.json",
                    ".claude/state/docaudit-last-run.json", ".claude/state/last-doc-audit.json",
                    ".claude/worktrees", ".mdq", ".codegraph", "graphify-out",
                    ".cocoindex_code"]


def atomic_write(path, raw):
    fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def impacted_paths(impact, repo):
    entries = impact.get("impacted")
    if not isinstance(entries, list):
        raise ValueError("impact.impacted must be an array")
    paths = []
    for entry in entries:
        path = entry if isinstance(entry, str) else entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str):
            raise ValueError("malformed impacted entry")
        paths.append(validate_repo_path(repo, path))
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate impacted paths")
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--impact-json", required=True)
    parser.add_argument("--dispatch-json", required=True)
    parser.add_argument("--run-class", required=True, choices=["light", "standard"])
    parser.add_argument("--mode", required=True, choices=["incremental", "full"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    try:
        if not RUNID_RE.match(args.runid) or os.path.basename(os.path.realpath(args.run_dir)) != args.runid:
            raise ValueError("runid is invalid or does not match RUN_DIR basename")
        evidence = json.loads(args.evidence)
        if (not isinstance(evidence, dict) or evidence.get("runid") != args.runid
                or os.path.realpath(str(evidence.get("runDir"))) != os.path.realpath(args.run_dir)):
            raise ValueError("EVIDENCE run identity mismatch")
        repo = os.path.realpath(args.repo_root)
        expected_run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", args.runid)
        if os.path.realpath(args.run_dir) != os.path.realpath(expected_run_dir):
            raise ValueError("RUN_DIR is outside the run ledger")
        with open(args.impact_json, encoding="utf-8") as handle:
            impact = json.load(handle)
        with open(args.dispatch_json, "rb") as handle:
            dispatch_raw = handle.read()
        if "sha256:" + hashlib.sha256(dispatch_raw).hexdigest() != evidence.get("dispatch"):
            raise ValueError("dispatch sha does not match EVIDENCE")
        dispatch = json.loads(dispatch_raw.decode("utf-8"))
        with open(args.config, "rb") as handle:
            config_raw = handle.read()
        if "sha256:" + hashlib.sha256(config_raw).hexdigest() != evidence.get("config"):
            raise ValueError("config changed after open-run")
        config = json.loads(config_raw.decode("utf-8"))
        paths = impacted_paths(impact, repo)
        for field in ("dispatch", "cached", "changedSet"):
            if not isinstance(dispatch.get(field), list):
                raise ValueError(f"dispatch.{field} must be an array")
        if set(dispatch["dispatch"]) | set(dispatch["cached"]) != set(paths):
            raise ValueError("dispatch union cached does not equal impacted")
        if set(dispatch["dispatch"]) & set(dispatch["cached"]):
            raise ValueError("dispatch and cached overlap")
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        baseline = head if args.mode == "full" else dispatch.get("baselineSha")
        if not isinstance(baseline, str):
            raise ValueError("baselineSha is missing")
        harness = config.get("harness", {})
        state = harness.get("state") if isinstance(harness, dict) else None
        commands = config.get("docAuditCommands")
        preflight_required = state in {"installed", "integrated", "adjusted"} or (
            state in {None, "existing-untouched"} and bool(commands))
        if state == "installed":
            generated = [".claude/commands/check-docs.md",
                         ".claude/skills/doc-lint/SKILL.md", "scripts/check-docs.py"]
            if not all(os.path.isfile(os.path.join(repo, path)) for path in generated):
                preflight_required = False
        phase4_required = (bool(paths) or bool(impact.get("ssotRecheck"))
                           or args.mode == "full" or preflight_required)
        digest_exclude = list(dict.fromkeys(BUILTIN_EXCLUDES + list(config.get("digestExclude", []))))
        doc_globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
        corpus = list_doc_files(repo, doc_globs)
        if args.mode == "full" and not paths and corpus:
            raise ValueError("full mode requires impacted documents unless the corpus is empty")
        manifest = {"runid": args.runid, "head": head, "mode": args.mode,
                    "baselineSha": baseline, "changedSet": dispatch["changedSet"],
                    "changeSetSha": dispatch.get("changeSetSha"), "impacted": paths,
                    "dispatch": dispatch["dispatch"], "cached": dispatch["cached"],
                    "runClass": args.run_class, "phase4Required": phase4_required,
                    "preflightRequired": preflight_required,
                    "contractVersion": dispatch.get("contractVersion"),
                    "digestExclude": digest_exclude, "sealed": False,
                    "emptyCorpus": not corpus, "docGlobs": doc_globs}
        if not isinstance(manifest["changeSetSha"], str) or not isinstance(manifest["contractVersion"], str):
            raise ValueError("dispatch cache contract fields are missing")
        raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        os.makedirs(os.path.join(args.run_dir, "verdicts"), exist_ok=True)
        atomic_write(os.path.join(args.run_dir, "manifest.json"), raw)
        impact_target = os.path.join(args.run_dir, "impact.json")
        if os.path.realpath(args.impact_json) != os.path.realpath(impact_target):
            with open(args.impact_json, "rb") as handle:
                impact_raw = handle.read()
            atomic_write(impact_target, impact_raw)
        evidence["manifest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"start-run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
