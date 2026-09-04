#!/usr/bin/env python3
"""Create the complete unsealed run manifest from impact and dispatch plans."""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from docaudit_paths import corpus_settings, list_doc_files, matches_glob, validate_repo_path
from sealed_config import SealedConfigMismatch, load_sealed_config


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
BUILTIN_EXCLUDES = [".claude/state/docaudit-run", ".claude/state/docaudit-history.json",
                    ".claude/state/docaudit-last-run.json", ".claude/state/last-doc-audit.json",
                    ".claude/worktrees", ".mdq", ".codegraph", "graphify-out",
                    ".cocoindex_code"]
VALID_PHASE3_BACKENDS = {"workflow", "codex"}
DEFAULT_PHASE3_CODEX_TIMEOUT_SECONDS = 600
VALID_PROVENANCE = {"mapped", "heuristic", "both", "full", "self", "graphify",
                    "semantic", "regression"}
HEX_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def phase3_settings(config):
    backend = config.get("phase3Backend", "workflow")
    if not isinstance(backend, str) or backend not in VALID_PHASE3_BACKENDS:
        raise ValueError("phase3Backend must be workflow or codex")
    timeout = config.get("phase3CodexTimeoutSeconds",
                         DEFAULT_PHASE3_CODEX_TIMEOUT_SECONDS)
    if (isinstance(timeout, bool) or not isinstance(timeout, int)
            or not 60 <= timeout <= 3600):
        raise ValueError("phase3CodexTimeoutSeconds must be an integer from 60 through 3600")
    return backend, timeout


def report_pattern(config):
    value = config.get("reportPath")
    globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if not isinstance(value, str) or not value.endswith(".md"):
        return None
    sample = value.replace("<YYYY-MM-DD>", "2000-01-01").replace("[_NN]", "_01")
    if not any(matches_glob(sample, item) for item in globs if isinstance(item, str)):
        return None
    directory, name = os.path.split(value)
    marker = "<YYYY-MM-DD>"
    suffix_marker = "[_NN]"
    if marker not in name:
        return None
    prefix = name.split(marker, 1)[0]
    if not prefix:
        return None
    suffix_at = None
    if suffix_marker not in value:
        suffix_at = len(value) - len(name) + name.find(marker) + len(marker)
    out = []
    i = 0
    while i < len(value):
        if value.startswith(marker, i):
            out.append("[0-9]{4}-[0-9]{2}-[0-9]{2}")
            i += len(marker)
            if suffix_at == i:
                out.append("(_[0-9]{2,})?")
        elif value.startswith(suffix_marker, i):
            out.append("(_[0-9]{2,})?")
            i += len(suffix_marker)
        else:
            out.append(re.escape(value[i]))
            i += 1
    return "^" + "".join(out) + "$"


def report_candidate_rule(config, repo, report_date):
    value = config.get("reportPath")
    if value is None:
        return None
    if report_pattern(config) is None:
        raise ValueError("reportPath is not a valid report candidate pattern")
    if value.count("<YYYY-MM-DD>") != 1 or value.count("[_NN]") > 1:
        raise ValueError("reportPath must contain one date marker and at most one suffix marker")
    marker_position = value.index("<YYYY-MM-DD>")
    rendered = value.replace("<YYYY-MM-DD>", report_date)
    if "[_NN]" in rendered:
        prefix, suffix = rendered.split("[_NN]", 1)
    else:
        insertion = marker_position + len(report_date)
        prefix, suffix = rendered[:insertion], rendered[insertion:]
    base = prefix + suffix
    for candidate in (base, prefix + "_02" + suffix):
        validate_repo_path(repo, candidate, must_exist=False)
    return {"base": base, "suffixPrefix": prefix,
            "suffixSuffix": suffix, "suffixStart": 2}


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


def impact_provenance(impact, paths):
    provenance = {}
    for entry in impact.get("impacted", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        value = entry.get("provenance")
        if value not in VALID_PROVENANCE:
            raise ValueError(f"invalid impact provenance: {entry['path']}={value}")
        provenance[entry["path"]] = value
    if set(provenance) != set(paths) or len(provenance) != len(paths):
        raise ValueError("impact provenance keys do not equal impacted")
    return provenance


def audit_scope_sha(config, repo):
    if "auditScope" not in config:
        return None
    value = config["auditScope"]
    if not isinstance(value, dict):
        raise ValueError("auditScope must be an object")
    path = value.get("path")
    expected = value.get("sha256")
    rules = value.get("rules")
    imported_at = value.get("importedAt")
    try:
        normalized = validate_repo_path(repo, path, must_exist=False)
    except ValueError as exc:
        raise ValueError(f"auditScope.path invalid: {exc}") from exc
    if not isinstance(expected, str) or not HEX_SHA_RE.fullmatch(expected):
        raise ValueError("auditScope.sha256 invalid")
    if isinstance(rules, bool) or not isinstance(rules, int) or rules < 0:
        raise ValueError("auditScope.rules invalid")
    if not isinstance(imported_at, str):
        raise ValueError("auditScope.importedAt invalid")
    try:
        normalized = validate_repo_path(repo, normalized)
    except ValueError as exc:
        raise ValueError(f"auditScope.path invalid: {exc}") from exc
    with open(os.path.join(repo, normalized), "rb") as handle:
        raw = handle.read()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("audit-scope drift")
    return "sha256:" + actual


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
    parser.add_argument("--expect-config-sha", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    try:
        if not RUNID_RE.match(args.runid) or os.path.basename(os.path.realpath(args.run_dir)) != args.runid:
            raise ValueError("runid is invalid or does not match RUN_DIR basename")
        try:
            run_time = datetime.datetime.strptime(args.runid[:16], "%Y%m%dT%H%M%SZ").replace(
                tzinfo=datetime.timezone.utc)
        except ValueError as exc:
            raise ValueError("runid contains an invalid UTC calendar timestamp") from exc
        report_date = run_time.date().isoformat()
        evidence = json.loads(args.evidence)
        if (not isinstance(evidence, dict) or evidence.get("runid") != args.runid
                or os.path.realpath(str(evidence.get("runDir"))) != os.path.realpath(args.run_dir)):
            raise ValueError("EVIDENCE run identity mismatch")
        if evidence.get("config") != args.expect_config_sha:
            raise ValueError("--expect-config-sha does not match EVIDENCE config")
        repo = os.path.realpath(args.repo_root)
        expected_run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", args.runid)
        if os.path.realpath(args.run_dir) != os.path.realpath(expected_run_dir):
            raise ValueError("RUN_DIR is outside the run ledger")
        with open(args.dispatch_json, "rb") as handle:
            dispatch_raw = handle.read()
        if "sha256:" + hashlib.sha256(dispatch_raw).hexdigest() != evidence.get("dispatch"):
            raise ValueError("dispatch sha does not match EVIDENCE")
        dispatch = json.loads(dispatch_raw.decode("utf-8"))
        expected_impact_sha = dispatch.get("impactSha")
        if not isinstance(expected_impact_sha, str):
            raise ValueError("dispatch impactSha is missing")
        with open(args.impact_json, "rb") as handle:
            impact_raw = handle.read()
        if "sha256:" + hashlib.sha256(impact_raw).hexdigest() != expected_impact_sha:
            raise ValueError("impact.json changed after plan-dispatch")
        impact = json.loads(impact_raw)
        _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
        phase3_backend, phase3_codex_timeout = phase3_settings(config)
        report_rule = report_candidate_rule(config, repo, report_date)
        paths = impacted_paths(impact, repo)
        provenance = impact_provenance(impact, paths)
        sealed_audit_scope_sha = audit_scope_sha(config, repo)
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
        codex_review = config.get("codexReview", {})
        if not isinstance(codex_review, dict):
            codex_review = {}
        phase4_required = (bool(paths) or bool(impact.get("ssotRecheck"))
                           or args.mode == "full" or preflight_required
                           or bool(codex_review.get("required") is True))
        digest_exclude = list(dict.fromkeys(BUILTIN_EXCLUDES + list(config.get("digestExclude", []))))
        doc_globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
        exclude_globs, respect_gitignore = corpus_settings(config)
        corpus = list_doc_files(repo, doc_globs, exclude_globs=exclude_globs,
                                respect_gitignore=respect_gitignore)
        if config.get("auditReportsInCorpus") is not True:
            report_rx = report_pattern(config)
            corpus = [path for path in corpus
                      if not (report_rx and re.fullmatch(report_rx, path))]
        if args.mode == "full" and not paths and corpus:
            raise ValueError("full mode requires impacted documents unless the corpus is empty")
        manifest = {"runid": args.runid, "head": head, "mode": args.mode,
                    "baselineSha": baseline, "changedSet": dispatch["changedSet"],
                    "changeSetSha": dispatch.get("changeSetSha"), "impacted": paths,
                    "provenance": provenance, "auditScopeSha": sealed_audit_scope_sha,
                    "dispatch": dispatch["dispatch"], "cached": dispatch["cached"],
                    "runClass": args.run_class, "phase4Required": phase4_required,
                    "preflightRequired": preflight_required,
                    "contractVersion": dispatch.get("contractVersion"),
                    "digestExclude": digest_exclude, "sealed": False,
                    "emptyCorpus": not corpus, "docGlobs": doc_globs,
                    "excludeDocGlobs": exclude_globs,
                    "respectGitignore": respect_gitignore,
                    "reportDate": report_date, "reportCandidateRule": report_rule}
        manifest["phase3Backend"] = phase3_backend
        if phase3_backend == "codex":
            manifest["phase3CodexTimeoutSeconds"] = phase3_codex_timeout
        if not isinstance(manifest["changeSetSha"], str) or not isinstance(manifest["contractVersion"], str):
            raise ValueError("dispatch cache contract fields are missing")
        raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        os.makedirs(os.path.join(args.run_dir, "verdicts"), exist_ok=True)
        atomic_write(os.path.join(args.run_dir, "manifest.json"), raw)
        impact_target = os.path.join(args.run_dir, "impact.json")
        if os.path.realpath(args.impact_json) != os.path.realpath(impact_target):
            atomic_write(impact_target, impact_raw)
        evidence["manifest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"start-run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
