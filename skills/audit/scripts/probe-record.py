#!/usr/bin/env python3
"""Persist display-only Phase-0 probe output inside one audit run directory."""

import argparse
import json
import os
import re
import stat
import sys
import uuid


RUNID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
SEAMS = {
    "indexing", "mdqHealth", "mdqDegrade", "contextMode", "webExtract",
    "codexReview", "codexReviewState", "symbolGraph", "docGraph",
    "semanticSearch",
}
RECORD_NAME = "phase0-probes.json"

GRAPH = {
    "symbolGraph": ("symbolGraphAvailable", "symbolGraphBin",
                    {"ok", "not-installed", "disabled-by-config", "index-failed",
                     "not-configured", "invalid-config"}, {"ok"}),
    "docGraph": ("docGraphAvailable", "docGraphBin",
                 {"ok", "not-installed", "disabled-by-config", "update-failed",
                  "not-configured", "invalid-config"}, {"ok"}),
    "semanticSearch": ("semanticSearchAvailable", "semanticSearchBin",
                       {"ok", "not-installed", "disabled-by-config", "not-initialized",
                        "index-failed", "not-configured", "invalid-config",
                        "gitignore-modified"}, {"ok"}),
}


class Invalid(ValueError):
    pass


def require_object(value, label):
    if not isinstance(value, dict):
        raise Invalid(label + " must be an object")
    return value


def require(value, key, kind, label):
    if key not in value or not isinstance(value[key], kind):
        raise Invalid(label + "." + key + " has the wrong type")
    return value[key]


def require_nullable_string(value, key, label):
    if key not in value or (value[key] is not None and not isinstance(value[key], str)):
        raise Invalid(label + "." + key + " has the wrong type")
    return value[key]


def validate_probe(seam, value):
    value = require_object(value, seam)
    if seam == "indexing":
        available = require(value, "mdqAvailable", bool, seam)
        reason = require(value, "reason", str, seam)
        if not available and reason == "disabled-by-config":
            return
        if not available and reason in {"not-installed", "invalid-config"}:
            require(value, "bin", str, seam)
            return
        if available and reason == "indexed":
            require(value, "bin", str, seam)
            require(value, "dbDir", str, seam)
            return
        if not available and reason == "index-failed":
            require(value, "rc", int, seam)
            if isinstance(value["rc"], bool):
                raise Invalid(seam + ".rc has the wrong type")
            require(value, "bin", str, seam)
            return
        raise Invalid("invalid indexing availability/reason pair")
    if seam == "mdqHealth":
        for key in ("files", "chunks"):
            number = require(value, key, int, seam)
            if isinstance(number, bool) or number < 0:
                raise Invalid(seam + "." + key + " has the wrong value")
        for key in ("searchSmoke", "healthy"):
            require(value, key, bool, seam)
        status = require(value, "status", str, seam)
        if status not in {"ok", "empty-index", "search-broken", "probe-error"}:
            raise Invalid("invalid mdqHealth status")
        return
    if seam == "mdqDegrade":
        if require(value, "degrade", str, seam) not in {"n/a", "user-approved", "non-interactive"}:
            raise Invalid("invalid mdqDegrade value")
        return
    if seam == "contextMode":
        available = require(value, "contextModeAvailable", bool, seam)
        if "contextModeHealthy" not in value:
            raise Invalid(seam + ".contextModeHealthy has the wrong type")
        healthy = value["contextModeHealthy"]
        status = require(value, "status", str, seam)
        if available:
            if not isinstance(healthy, bool) or status not in {"ok", "degraded", "probe-error"}:
                raise Invalid("invalid contextMode available branch")
        elif healthy is not None or status not in {"disabled-by-config", "not-installed", "probe-error", "invalid-config"}:
            raise Invalid("invalid contextMode unavailable branch")
        return
    if seam == "webExtract":
        available = require(value, "axAvailable", bool, seam)
        require(value, "axBin", str, seam)
        require_nullable_string(value, "axVersion", seam)
        reason = require(value, "reason", str, seam)
        if reason not in {"ok", "not-installed", "disabled-by-config", "invalid-config", "not-configured"} or available != (reason == "ok"):
            raise Invalid("invalid webExtract availability/reason pair")
        return
    if seam == "codexReview":
        available = require(value, "codexReviewAvailable", bool, seam)
        require(value, "codexReviewBin", str, seam)
        require_nullable_string(value, "codexReviewVersion", seam)
        commands = require(value, "probeCommands", list, seam)
        if not all(isinstance(command, str) for command in commands):
            raise Invalid("codexReview.probeCommands has the wrong type")
        reason = require(value, "reason", str, seam)
        require_nullable_string(value, "callerCodexHome", seam)
        if require(value, "callerCodexHomeSource", str, seam) not in {"env", "default", "unknown"}:
            raise Invalid("invalid callerCodexHomeSource")
        if require(value, "callerAuthFile", str, seam) not in {"present", "absent", "unknown"}:
            raise Invalid("invalid callerAuthFile")
        if reason == "not-configured":
            expected = {
                "codexReviewAvailable": False,
                "codexReviewBin": "codex",
                "codexReviewVersion": None,
                "probeCommands": [],
                "reason": "not-configured",
                "callerCodexHome": None,
                "callerCodexHomeSource": "unknown",
                "callerAuthFile": "unknown",
            }
            if value != expected:
                raise Invalid("invalid codexReview not-configured record")
            return
        if reason not in {"ok", "not-installed", "disabled-by-config", "probe-exec-failed", "invalid-config"} or available != (reason == "ok"):
            raise Invalid("invalid codexReview availability/reason pair")
        return
    if seam == "codexReviewState":
        if require(value, "state", str, seam) not in {
                "completed", "execution-failed", "ref-invalid", "skipped-full-run",
                "not-active", "phase4-not-required"}:
            raise Invalid("invalid codexReviewState")
        return
    available_key, bin_key, reasons, ok_reasons = GRAPH[seam]
    available = require(value, available_key, bool, seam)
    require(value, bin_key, str, seam)
    reason = require(value, "reason", str, seam)
    if reason not in reasons or available != (reason in ok_reasons):
        raise Invalid("invalid " + seam + " availability/reason pair")
    if seam == "docGraph":
        require(value, "gitignoreOk", bool, seam)


def validate_record(record):
    record = require_object(record, "record")
    if record.get("schemaVersion") != 1:
        raise Invalid("unsupported schemaVersion")
    seams = require_object(record.get("seams"), "seams")
    if not set(seams).issubset(SEAMS):
        raise Invalid("unknown seam")
    for seam, value in seams.items():
        validate_probe(seam, value)
    return record


def open_run_dir(repo_root, runid):
    if not RUNID_RE.fullmatch(runid):
        raise Invalid("invalid runid")
    repo = os.path.realpath(repo_root)
    fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in (".claude", "state", "docaudit-run", runid):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return repo, fd
    except Exception:
        os.close(fd)
        raise


def validate_evidence(raw, expected_run_dir):
    try:
        evidence = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise Invalid("invalid evidence JSON") from exc
    require_object(evidence, "evidence")
    run_dir = evidence.get("runDir")
    if not isinstance(run_dir, str) or os.path.realpath(run_dir) != os.path.realpath(expected_run_dir):
        raise Invalid("evidence runDir does not match")


def read_record(run_fd):
    try:
        fd = os.open(RECORD_NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=run_fd)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Invalid("probe record is not a regular file")
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        try:
            record = json.loads(b"".join(chunks).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Invalid("invalid probe record JSON") from exc
        return validate_record(record)
    finally:
        os.close(fd)


def write_record(run_fd, record):
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    temporary = ".phase0-probes.%s.tmp" % uuid.uuid4().hex
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=run_fd)
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.replace(temporary, RECORD_NAME, src_dir_fd=run_fd, dst_dir_fd=run_fd)
        os.fsync(run_fd)
    except Exception:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=run_fd)
        except FileNotFoundError:
            pass
        raise


def unknown_rebind():
    return {
        "mdq": {"state": "unknown", "available": None, "reason": None, "bin": None,
                "rootsDefaulted": None,
                "healthy": None, "chunks": None, "status": None, "degrade": None},
        "context-mode": {"state": "unknown", "available": None, "healthy": None, "status": None},
        "ax": {"state": "unknown", "available": None, "reason": None},
        "codex-review": {"state": "unknown", "available": None, "reason": None, "bin": None,
                          "reviewState": None, "callerCodexHomeDisplay": None,
                          "callerCodexHomeSource": None, "callerAuthFile": None},
        "symbol-graph": {"state": "unknown", "available": None, "reason": None, "bin": None},
        "doc-graph": {"state": "unknown", "available": None, "reason": None, "bin": None,
                      "gitignoreOk": None},
        "semantic-search": {"state": "unknown", "available": None, "reason": None, "bin": None},
    }


def display(value):
    if value is None:
        return "(null)"
    return json.dumps(value[:200])[1:-1]


def make_rebind(record):
    result = unknown_rebind()
    if record is None:
        return result
    seams = record["seams"]
    indexing = seams.get("indexing")
    degrade = seams.get("mdqDegrade")
    if indexing is not None and degrade is not None:
        available = indexing["mdqAvailable"]
        health = seams.get("mdqHealth")
        if not available or health is not None:
            result["mdq"] = {
                "state": "complete", "available": available, "reason": indexing["reason"],
                "bin": indexing.get("bin"), "healthy": health.get("healthy") if health else None,
                "chunks": health.get("chunks") if health else None,
                "status": health.get("status") if health else None,
                "degrade": degrade["degrade"],
                "rootsDefaulted": indexing.get("rootsDefaulted"),
            }
    context = seams.get("contextMode")
    if context is not None:
        result["context-mode"] = {"state": "complete", "available": context["contextModeAvailable"],
                                  "healthy": context["contextModeHealthy"], "status": context["status"]}
    ax = seams.get("webExtract")
    if ax is not None:
        result["ax"] = {"state": "complete", "available": ax["axAvailable"], "reason": ax["reason"]}
    codex = seams.get("codexReview")
    review_state = seams.get("codexReviewState", {}).get("state")
    result["codex-review"]["reviewState"] = review_state
    if codex is not None:
        result["codex-review"] = {
            "state": "complete", "available": codex["codexReviewAvailable"],
            "reason": codex["reason"], "bin": codex["codexReviewBin"],
            "reviewState": review_state,
            "callerCodexHomeDisplay": display(codex["callerCodexHome"]),
            "callerCodexHomeSource": codex["callerCodexHomeSource"],
            "callerAuthFile": codex["callerAuthFile"],
        }
    symbol = seams.get("symbolGraph")
    if symbol is not None:
        result["symbol-graph"] = {"state": "complete", "available": symbol["symbolGraphAvailable"],
                                  "reason": symbol["reason"], "bin": symbol["symbolGraphBin"]}
    doc = seams.get("docGraph")
    if doc is not None:
        result["doc-graph"] = {"state": "complete", "available": doc["docGraphAvailable"],
                               "reason": doc["reason"], "bin": doc["docGraphBin"],
                               "gitignoreOk": doc["gitignoreOk"]}
    semantic = seams.get("semanticSearch")
    if semantic is not None:
        result["semantic-search"] = {"state": "complete", "available": semantic["semanticSearchAvailable"],
                                      "reason": semantic["reason"], "bin": semantic["semanticSearchBin"]}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--seam", choices=sorted(SEAMS))
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--read", action="store_true")
    args = parser.parse_args()
    if args.read == bool(args.seam) or (args.seam and not args.stdin):
        parser.error("use --read, or --seam NAME --stdin")
    try:
        repo, run_fd = open_run_dir(args.repo_root, args.runid)
        try:
            validate_evidence(args.evidence, os.path.join(repo, ".claude", "state", "docaudit-run", args.runid))
            record = read_record(run_fd)
            if args.read:
                print(json.dumps({"schemaVersion": 1, "seams": {} if record is None else record["seams"],
                                  "rebind": make_rebind(record)}, sort_keys=True, separators=(",", ":")))
                return 0
            try:
                probe = json.loads(sys.stdin.buffer.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise Invalid("invalid stdin JSON") from exc
            validate_probe(args.seam, probe)
            if record is None:
                record = {"schemaVersion": 1, "seams": {}}
            record["seams"][args.seam] = probe
            validate_record(record)
            write_record(run_fd, record)
            print(json.dumps(record, sort_keys=True, separators=(",", ":")))
            return 0
        finally:
            os.close(run_fd)
    except (Invalid, OSError) as exc:
        print("probe-record: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
