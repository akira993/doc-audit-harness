#!/usr/bin/env python3
"""Deterministic sealed-run gate and sole history/lastRun/anchor writer."""

import argparse
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile

from docaudit_cache import (cache_qualification, content_sha, json_bytes,
                            parse_history, sha256_bytes, trim_history,
                            validate_min_passes)
from docaudit_paths import validate_repo_path


HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED_EXPECT = {"runid", "runDir", "anchor", "config", "lockIno", "preflight",
                   "dispatch", "cached", "history", "historyStatus", "manifest",
                   "digest", "returns", "attempt", "phase4"}
VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
FAIL_SEVERITIES = {"FAIL", "HIGH", "CRITICAL"}
MAX_TEMPLATE_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_RECEIPT_BYTES = 64 * 1024
TOKEN_COUNTS = {
    "{{GATE_VERDICT}}": 1,
    "{{GATE_REASON}}": 1,
    "{{GATE_COUNTS}}": 1,
    "{{GATE_HISTORY_STATUS}}": 1,
    "{{GATE_WARNINGS}}": 1,
    "{{GATE_SIBLING_SCAN}}": 1,
    "{{GATE_ANCHOR_WRITTEN}}": 1,
    "{{GATE_REPORT_DATE}}": 2,
}
OPTIONAL_TOKENS = frozenset({"{{GATE_REASON}}"})
TOKEN_RE = re.compile(r"\{\{GATE_[A-Z0-9_]+\}\}")
REPORT_WARNING_CODES = frozenset({
    "reportWriteError", "reportTemplateMissing", "reportTemplateInvalid",
    "reportDurabilityUnknown", "reportStatusUpdateFailed", "lockReleaseFailed",
})
BIDI_CONTROLS = frozenset(chr(value) for value in (
    0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)))


class Refused(Exception):
    pass


class TemplateMissing(Exception):
    pass


class TemplateInvalid(Exception):
    pass


def sibling_skipped(reason):
    return {"skipped": reason, "phrases": [], "matches": [],
            "sources": {"findings": 0, "phase4": 0, "changeSet": 0, "notes": [reason]},
            "truncated": {}, "truncatedTotal": 0, "phraseTruncated": 0}


def report_pattern(config):
    spec = importlib.util.spec_from_file_location("change_set_sha", os.path.join(HERE, "change-set-sha.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.report_pattern(config)


def run_sibling_scan(payload, repo, timeout_s=30):
    try:
        proc = subprocess.run([sys.executable, os.path.join(HERE, "sibling-scan.py"), "--stdin"],
                              input=json.dumps(payload, ensure_ascii=False), capture_output=True,
                              text=True, timeout=timeout_s)
        if proc.returncode:
            return sibling_skipped("sibling scan exited " + str(proc.returncode))
        value = json.loads(proc.stdout)
        if not isinstance(value, dict):
            return sibling_skipped("sibling scan returned invalid JSON")
        return value
    except subprocess.TimeoutExpired:
        return sibling_skipped("sibling scan timed out")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return sibling_skipped("sibling scan failed: " + str(exc))


def run_sibling_step(manifest, returns, phase4, config, repo):
    try:
        scan_manifest = {key: manifest.get(key) for key in
                         ("mode", "head", "baselineSha", "changedSet", "docGlobs")}
        payload = {"repoRoot": repo, "manifest": scan_manifest, "returns": returns,
                   "phase4": phase4, "reportPattern": report_pattern(config)}
        return run_sibling_scan(payload, repo)
    except Exception as exc:
        return sibling_skipped("sibling scan failed: " + str(exc))


def atomic(path, value):
    raw = json_bytes(value)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".docaudit-state.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_json(raw, label):
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refused(f"{label} is not valid JSON: {exc}") from exc
    return value


def read_once(path, label):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        raise Refused(f"{label} cannot be read: {exc}") from exc


def read_state_once(path, label):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            chunks = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            info = os.fstat(fd)
            if os.stat(path, follow_symlinks=False).st_ino != info.st_ino:
                raise Refused(f"{label} was replaced while being read")
            signature = (info.st_ino, info.st_size, info.st_mtime_ns)
            return b"".join(chunks), signature
        finally:
            os.close(fd)
    except OSError as exc:
        raise Refused(f"{label} cannot be read: {exc}") from exc


def state_signature(path):
    info = os.stat(path, follow_symlinks=False)
    return info.st_ino, info.st_size, info.st_mtime_ns


def state_unchanged(path, signature):
    if signature is None:
        return not os.path.exists(path)
    try:
        return state_signature(path) == signature
    except OSError:
        return False


def verify_sha(raw, expected, label):
    actual = sha256_bytes(raw)
    if actual != expected:
        raise Refused(f"{label} sha mismatch")


def validate_returns(value):
    if not isinstance(value, list):
        raise Refused("returns.json must be an array")
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise Refused(f"returns[{index}] is not an object")
        attempt = item.get("attempt")
        assigned = item.get("assignedPath")
        if (isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= 3
                or not isinstance(assigned, str)):
            raise Refused(f"returns[{index}] has invalid attempt/assignedPath")
        if (attempt, assigned) in seen:
            raise Refused("returns contains duplicate (attempt,assignedPath)")
        seen.add((attempt, assigned))
        if item.get("returnedPath") is not None and not isinstance(item.get("returnedPath"), str):
            raise Refused(f"returns[{index}].returnedPath is invalid")
        if item.get("verdict") is not None and item.get("verdict") not in VALID_VERDICTS:
            raise Refused(f"returns[{index}].verdict is invalid")


def findings_fail(value):
    if not isinstance(value, dict):
        raise Refused("phase evidence must be an object")
    findings = value.get("findings", [])
    if not isinstance(findings, list):
        raise Refused("phase findings must be an array")
    blocking = False
    for finding in findings:
        if not isinstance(finding, dict):
            raise Refused("phase finding is not an object")
        raw_severity = finding.get("severity")
        if not isinstance(raw_severity, str) or not raw_severity.strip():
            raise Refused("phase finding severity is missing")
        severity = raw_severity.strip().upper()
        if severity in FAIL_SEVERITIES:
            blocking = True
        elif severity not in {"PASS", "WARN", "MEDIUM", "LOW", "INFO"}:
            raise Refused(f"unknown finding severity: {severity}")
    if value.get("parsed") is False:
        exit_code = value.get("exitCode", value.get("returncode", 0))
        if isinstance(exit_code, int) and exit_code != 0:
            return True
        commands = value.get("commands", [])
        if isinstance(commands, list) and any(isinstance(item, dict) and item.get("exitCode") not in (None, 0)
                                              for item in commands):
            return True
    return blocking


def run_tree_digest(repo, manifest):
    command = [sys.executable, os.path.join(HERE, "tree-digest.py"),
               "--repo-root", repo, "--include-head"]
    for item in manifest.get("digestExclude", []):
        command.extend(["--exclude", item])
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode:
        raise Refused(proc.stderr.strip() or "tree-digest failed")
    return json.loads(proc.stdout)["digest"]


def lock_recheck(fd, lock_path, runid, expected_inode):
    try:
        inode_fd = os.fstat(fd).st_ino
        inode_path = os.stat(lock_path, follow_symlinks=False).st_ino
    except OSError as exc:
        raise Refused(f"lock disappeared or changed: {exc}") from exc
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, 65536)
    holder = parse_json(raw, "lock")
    if inode_fd != inode_path or inode_fd != expected_inode or holder.get("runid") != runid:
        raise Refused("lock inode or runid mismatch")
    return holder


def validate_evidence(value):
    if not isinstance(value, dict):
        raise Refused("EVIDENCE is not an object")
    if REQUIRED_EXPECT - set(value):
        raise Refused("EVIDENCE required keys are missing")
    if not isinstance(value["runid"], str) or not isinstance(value["runDir"], str):
        raise Refused("EVIDENCE run identity has invalid types")
    if (isinstance(value["lockIno"], bool) or not isinstance(value["lockIno"], int)
            or value["lockIno"] <= 0):
        raise Refused("EVIDENCE lockIno has invalid type")
    if (isinstance(value["attempt"], bool) or not isinstance(value["attempt"], int)
            or not 0 <= value["attempt"] <= 3):
        raise Refused("EVIDENCE attempt has invalid type")
    if value["historyStatus"] not in {"absent", "ok", "corrupt"}:
        raise Refused("EVIDENCE historyStatus is invalid")
    sha_fields = {"config", "dispatch", "manifest", "digest", "returns"}
    optional_sha_fields = {"anchor", "preflight", "cached", "history", "phase4"}
    sha_re = re.compile(r"^sha256:[0-9a-f]{64}$")
    for key in sha_fields:
        if not isinstance(value[key], str) or not sha_re.fullmatch(value[key]):
            raise Refused(f"EVIDENCE {key} has invalid type")
    for key in optional_sha_fields:
        if not isinstance(value[key], str) or (value[key] != "none" and not sha_re.fullmatch(value[key])):
            raise Refused(f"EVIDENCE {key} has invalid type")


def validate_report_rule(manifest, repo, runid):
    report_date = manifest.get("reportDate")
    if not isinstance(report_date, str):
        raise Refused("sealed reportDate is missing")
    try:
        parsed = datetime.date.fromisoformat(report_date)
        run_date = datetime.datetime.strptime(runid[:16], "%Y%m%dT%H%M%SZ").date()
    except ValueError as exc:
        raise Refused("sealed reportDate is invalid") from exc
    if parsed.isoformat() != report_date or parsed != run_date:
        raise Refused("sealed reportDate does not match runid UTC date")
    rule = manifest.get("reportCandidateRule")
    if rule is None:
        return None
    if not isinstance(rule, dict) or set(rule) != {
            "base", "suffixPrefix", "suffixSuffix", "suffixStart"}:
        raise Refused("sealed report candidate rule is invalid")
    if (not all(isinstance(rule[key], str) for key in ("base", "suffixPrefix", "suffixSuffix"))
            or not isinstance(rule["suffixStart"], int)
            or isinstance(rule["suffixStart"], bool)
            or rule["suffixStart"] != 2
            or rule["base"] != rule["suffixPrefix"] + rule["suffixSuffix"]
            or report_date not in rule["base"]):
        raise Refused("sealed report candidate rule is invalid")
    try:
        validate_repo_path(repo, rule["base"], must_exist=False)
        validate_repo_path(repo, rule["suffixPrefix"] + "_02" + rule["suffixSuffix"],
                           must_exist=False)
    except ValueError as exc:
        raise Refused(f"sealed report candidate rule is unsafe: {exc}") from exc
    return rule


def read_regular_bounded(path, label, maximum, missing_error):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError as exc:
        raise missing_error(f"{label} is missing") from exc
    except OSError as exc:
        raise TemplateInvalid(f"{label} cannot be safely opened: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise TemplateInvalid(f"{label} is not a regular file")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > maximum:
            raise TemplateInvalid(f"{label} exceeds its size limit")
        return raw
    finally:
        os.close(fd)


def load_report_template(run_dir):
    receipt_raw = read_regular_bounded(
        os.path.join(run_dir, "report-template.receipt.json"), "report receipt",
        MAX_RECEIPT_BYTES, TemplateMissing)
    try:
        receipt = json.loads(receipt_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TemplateInvalid(f"report receipt is invalid: {exc}") from exc
    if not isinstance(receipt, dict) or receipt.get("failed") is not False:
        raise TemplateInvalid("report receipt does not record a successful helper invocation")
    raw = read_regular_bounded(os.path.join(run_dir, "report-template.md"), "report template",
                               MAX_TEMPLATE_BYTES, TemplateMissing)
    expected_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
    if (receipt.get("sha256") != expected_sha or receipt.get("bytes") != len(raw)
            or isinstance(receipt.get("bytes"), bool)):
        raise TemplateInvalid("report receipt does not match the template")
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise TemplateInvalid(f"report template is not valid UTF-8: {exc}") from exc


def safe_json(value):
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if any(char in BIDI_CONTROLS for char in rendered):
        raise TemplateInvalid("report replacement contains a bidirectional control character")
    return (rendered.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def render_report(template, verdict, report_date, *, reason=None, counts=None,
                  history_status=None, warnings=None, sibling=None, anchor_written=False):
    found = TOKEN_RE.findall(template)
    if any(token not in TOKEN_COUNTS for token in found):
        raise TemplateInvalid("report template contains an unknown gate token")
    for token, count in TOKEN_COUNTS.items():
        actual_count = found.count(token)
        if ((token in OPTIONAL_TOKENS and actual_count not in (0, count))
                or (token not in OPTIONAL_TOKENS and actual_count != count)):
            raise TemplateInvalid(f"report template token count is invalid for {token}")
    refused = verdict == "REFUSED"
    values = {
        "{{GATE_VERDICT}}": verdict,
        "{{GATE_REASON}}": safe_json(reason if refused else "n/a"),
        "{{GATE_COUNTS}}": safe_json("n/a" if refused else counts),
        "{{GATE_HISTORY_STATUS}}": safe_json("n/a" if refused else history_status),
        "{{GATE_WARNINGS}}": safe_json(warnings or []),
        "{{GATE_SIBLING_SCAN}}": safe_json("n/a" if refused else sibling),
        "{{GATE_ANCHOR_WRITTEN}}": "true" if anchor_written else "false",
        "{{GATE_REPORT_DATE}}": report_date,
    }
    rendered = TOKEN_RE.sub(lambda match: values[match.group(0)], template)
    raw = rendered.encode("utf-8")
    if len(raw) > MAX_REPORT_BYTES:
        raise TemplateInvalid("rendered report exceeds 4 MiB")
    return raw


def write_all(fd, raw):
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def fsync_directory_fd(fd):
    os.fsync(fd)


def publish_report(repo, run_dir, rule, raw):
    fd, temporary = tempfile.mkstemp(prefix=".report-publication.", dir=run_dir)
    linked = None
    linked_parent_fd = None
    cleanup_error = None
    durability_unknown = False
    try:
        os.fchmod(fd, 0o644)
        write_all(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        number = None
        while True:
            candidate = (rule["base"] if number is None else
                         rule["suffixPrefix"] + f"_{number:02d}" + rule["suffixSuffix"])
            candidate = validate_repo_path(repo, candidate, must_exist=False)
            parent_rel = os.path.dirname(candidate)
            parent = repo if not parent_rel else os.path.join(repo, parent_rel)
            os.makedirs(parent, exist_ok=True)
            if parent_rel:
                validate_repo_path(repo, parent_rel, regular_file=False)
            candidate_parent_fd = os.open(
                parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.link(temporary, os.path.basename(candidate),
                        dst_dir_fd=candidate_parent_fd, follow_symlinks=False)
                linked = candidate
                linked_parent_fd = candidate_parent_fd
                candidate_parent_fd = None
                break
            except FileExistsError:
                number = rule["suffixStart"] if number is None else number + 1
            finally:
                if candidate_parent_fd is not None:
                    os.close(candidate_parent_fd)
        try:
            fsync_directory_fd(linked_parent_fd)
        except OSError:
            durability_unknown = True
    finally:
        if linked_parent_fd is not None:
            os.close(linked_parent_fd)
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        except OSError as exc:
            cleanup_error = exc
    return linked, durability_unknown, cleanup_error


def report_status_update(last_run_path, state):
    atomic(last_run_path, state)


def release_lock(lock_path, lock_inode):
    if os.stat(lock_path, follow_symlinks=False).st_ino != lock_inode:
        raise OSError("lock path no longer names the owned inode")
    os.unlink(lock_path)


def add_warning(warnings, code):
    if code not in warnings:
        warnings.append(code)


def finalize_report(repo, run_dir, rule, report_date, last_run_path, base_state, warnings,
                    verdict, *, reason=None, counts=None, history_status=None,
                    sibling=None, anchor_written=False):
    if rule is None:
        return None, base_state["reportStatus"]
    report_path = None
    status = "failed"
    error_code = None
    try:
        template = load_report_template(run_dir)
        rendered = render_report(
            template, verdict, report_date, reason=reason, counts=counts,
            history_status=history_status, warnings=warnings, sibling=sibling,
            anchor_written=anchor_written)
        report_path, durability_unknown, cleanup_error = publish_report(
            repo, run_dir, rule, rendered)
        if durability_unknown:
            status = "written-durability-unknown"
            add_warning(warnings, "reportDurabilityUnknown")
        else:
            status = "written"
        if cleanup_error is not None:
            add_warning(warnings, "reportWriteError")
    except TemplateMissing:
        error_code = "reportTemplateMissing"
        add_warning(warnings, error_code)
    except TemplateInvalid:
        error_code = "reportTemplateInvalid"
        add_warning(warnings, error_code)
    except (OSError, ValueError):
        error_code = "reportWriteError"
        add_warning(warnings, error_code)
    final_state = dict(base_state, reportStatus=status)
    if report_path is not None:
        final_state["reportPath"] = report_path
    if error_code is not None:
        final_state["reportError"] = error_code
    try:
        report_status_update(last_run_path, final_state)
        persisted_status = status
    except OSError:
        add_warning(warnings, "reportStatusUpdateFailed")
        persisted_status = base_state["reportStatus"]
    return report_path, persisted_status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--anchor-path", required=True)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--expect-json", required=True)
    parser.add_argument("--date")
    args = parser.parse_args()
    repo_input = os.path.abspath(args.repo_root)
    repo = os.path.realpath(repo_input)
    run_dir = os.path.realpath(args.run_dir)
    run_base = os.path.dirname(run_dir)
    lock_path = os.path.join(run_base, "lock")
    state_dir = os.path.join(repo, ".claude", "state")
    history_path = os.path.join(state_dir, "docaudit-history.json")
    last_run_path = os.path.join(state_dir, "docaudit-last-run.json")
    config_path = os.path.abspath(args.config)
    anchor_absolute = (args.anchor_path if os.path.isabs(args.anchor_path)
                       else os.path.join(repo, args.anchor_path))

    def relative_to_repo(path):
        absolute = os.path.abspath(path)
        try:
            if os.path.commonpath([repo_input, absolute]) == repo_input:
                return os.path.relpath(absolute, repo_input).replace(os.sep, "/")
        except ValueError:
            pass
        return os.path.relpath(os.path.realpath(absolute), repo).replace(os.sep, "/")

    try:
        expected_run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", args.runid)
        run_rel = relative_to_repo(args.run_dir)
        validate_repo_path(repo, run_rel, regular_file=False)
        if run_dir != os.path.realpath(expected_run_dir):
            raise ValueError("RUN_DIR is outside the run ledger")
        config_rel = relative_to_repo(config_path)
        config_path = os.path.join(repo, validate_repo_path(repo, config_rel))
        anchor_rel = relative_to_repo(anchor_absolute)
        anchor_path = os.path.join(
            repo, validate_repo_path(repo, anchor_rel, must_exist=False, regular_file=False))
        if os.path.lexists(anchor_path) and not os.path.isfile(anchor_path):
            raise ValueError("anchor must be a regular file when present")
    except ValueError as exc:
        print(json.dumps({"verdict": "REFUSED", "anchorWritten": False,
                          "reason": f"unsafe state path: {exc}"}, sort_keys=True))
        return 3
    lock_fd = None
    owned = False
    history_taint = False
    anchor_taint = False
    config_taint = False
    expected = {}
    lock_inode = None
    holder = {}
    history_signature = None
    anchor_signature = None
    config_signature = None
    identity_ok = False
    report_trusted = False
    report_rule = None
    warnings = []
    try:
        expected = json.loads(args.expect_json)
        validate_evidence(expected)
        if expected.get("runid") != args.runid or os.path.realpath(str(expected.get("runDir"))) != run_dir:
            raise Refused("EVIDENCE run identity mismatch")
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refused("lock is held by another process") from exc
        lock_inode = os.fstat(lock_fd).st_ino
        try:
            path_inode = os.stat(lock_path, follow_symlinks=False).st_ino
        except OSError as exc:
            raise Refused(f"lock path cannot be inspected: {exc}") from exc
        os.lseek(lock_fd, 0, os.SEEK_SET)
        holder = parse_json(os.read(lock_fd, 65536), "lock")
        owned = (holder.get("runid") == args.runid
                 and path_inode == lock_inode
                 and lock_inode == expected["lockIno"])
        if path_inode != lock_inode:
            raise Refused("lock was unlinked/recreated")

        # Every evidence file is read exactly once into this immutable snapshot.
        manifest_raw = read_once(os.path.join(run_dir, "manifest.json"), "manifest.json")
        dispatch_raw = read_once(os.path.join(run_dir, "dispatch.json"), "dispatch.json")
        returns_raw = read_once(os.path.join(run_dir, "returns.json"), "returns.json")
        config_raw, config_signature = read_state_once(config_path, "config")
        manifest = parse_json(manifest_raw, "manifest.json")
        if not isinstance(manifest, dict):
            raise Refused("manifest must be an object")
        identity_mismatch = (holder.get("runid") != args.runid
                             or manifest.get("runid") != args.runid
                             or os.path.basename(run_dir) != args.runid
                             or lock_inode != expected.get("lockIno"))
        identity_ok = not identity_mismatch
        verify_sha(manifest_raw, expected["manifest"], "manifest")
        if manifest.get("sealed") is not True:
            raise Refused("manifest is not sealed")
        report_rule = validate_report_rule(manifest, repo, args.runid)
        verify_sha(dispatch_raw, expected["dispatch"], "dispatch")
        verify_sha(returns_raw, expected["returns"], "returns")
        if sha256_bytes(config_raw) != expected["config"]:
            config_taint = True
            raise Refused("run 中に config が変更された。git diff .claude/doc-audit.json で確認し復元せよ")
        dispatch_doc = parse_json(dispatch_raw, "dispatch.json")
        returns = parse_json(returns_raw, "returns.json")
        config = parse_json(config_raw, "config")
        if not all(isinstance(value, dict) for value in (manifest, dispatch_doc, config)):
            raise Refused("manifest, dispatch, and config must be objects")
        report_trusted = identity_ok
        validate_returns(returns)
        if expected.get("attempt") != max((item["attempt"] for item in returns), default=0):
            raise Refused("EVIDENCE attempt does not match returns")
        history_entries = []
        history_raw = None
        if expected["history"] == "none":
            if os.path.exists(history_path) or expected.get("historyStatus") != "absent":
                history_taint = os.path.exists(history_path)
                raise Refused("history=none sentinel is invalid")
        else:
            history_raw, history_signature = read_state_once(history_path, "history")
            if sha256_bytes(history_raw) != expected["history"]:
                history_taint = True
                raise Refused("history sha mismatch")
            if expected.get("historyStatus") == "ok":
                try:
                    history_entries = parse_history(parse_json(history_raw, "history"))
                except (ValueError, Refused) as exc:
                    history_taint = True
                    raise Refused(f"history is corrupt: {exc}") from exc
            elif expected.get("historyStatus") == "corrupt":
                history_taint = True
            else:
                raise Refused("historyStatus is invalid")

        if expected["anchor"] == "none":
            if os.path.exists(anchor_path):
                anchor_taint = True
                raise Refused("anchor=none sentinel is invalid")
        else:
            anchor_raw, anchor_signature = read_state_once(anchor_path, "anchor")
            if sha256_bytes(anchor_raw) != expected["anchor"]:
                anchor_taint = True
                raise Refused("anchor sha mismatch")

        if identity_mismatch:
            raise Refused("lock/manifest/run directory identity mismatch")

        preflight = None
        preflight_path = os.path.join(run_dir, "preflight.json")
        if expected["preflight"] == "none":
            if manifest.get("preflightRequired") or os.path.exists(preflight_path):
                raise Refused("preflight=none sentinel is invalid")
        else:
            raw = read_once(preflight_path, "preflight.json")
            verify_sha(raw, expected["preflight"], "preflight")
            preflight = parse_json(raw, "preflight.json")

        phase4 = None
        phase4_path = os.path.join(run_dir, "phase4.json")
        if expected["phase4"] == "none":
            if manifest.get("phase4Required") or os.path.exists(phase4_path):
                raise Refused("phase4=none sentinel is invalid")
        else:
            raw = read_once(phase4_path, "phase4.json")
            verify_sha(raw, expected["phase4"], "phase4")
            phase4 = parse_json(raw, "phase4.json")

        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
        if head != manifest.get("head"):
            raise Refused("HEAD does not match sealed manifest")
        digest = run_tree_digest(repo, manifest)
        if digest != manifest.get("worktreeDigest") or digest != expected.get("digest"):
            raise Refused("worktree digest mismatch")
        change_proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "change-set-sha.py"), "--repo-root", repo,
             "--baseline-sha", manifest["baselineSha"], "--config", config_path],
            capture_output=True, text=True)
        if change_proc.returncode:
            raise Refused(change_proc.stderr.strip() or "change-set-sha failed")
        if json.loads(change_proc.stdout).get("changeSetSha") != manifest.get("changeSetSha"):
            raise Refused("changeSetSha mismatch")

        impacted = manifest.get("impacted")
        dispatched = manifest.get("dispatch")
        cached = manifest.get("cached")
        if not all(isinstance(value, list) for value in (impacted, dispatched, cached)):
            raise Refused("manifest path sets are invalid")
        if (manifest.get("mode") == "full" and not impacted
                and not manifest.get("emptyCorpus")):
            raise Refused("full mode requires impacted documents unless the corpus is empty")
        if set(dispatched) | set(cached) != set(impacted) or set(dispatched) & set(cached):
            raise Refused("manifest dispatch/cached partition is invalid")
        for field in ("dispatch", "cached", "changeSetSha", "changedSet", "baselineSha",
                      "contractVersion", "historyStatus"):
            if dispatch_doc.get(field) != manifest.get(field) and field not in {"historyStatus"}:
                raise Refused(f"manifest and dispatch.json differ at {field}")
        if dispatch_doc.get("historyStatus") != expected.get("historyStatus"):
            raise Refused("dispatch historyStatus mismatch")

        verdict_dir = os.path.join(run_dir, "verdicts")
        verdicts = {}
        verdict_raw = {}
        for name in sorted(os.listdir(verdict_dir)) if os.path.isdir(verdict_dir) else []:
            if not name.endswith(".json"):
                continue
            raw = read_once(os.path.join(verdict_dir, name), f"verdicts/{name}")
            record = parse_json(raw, f"verdicts/{name}")
            path = record.get("path") if isinstance(record, dict) else None
            if not isinstance(path, str) or path in verdicts:
                raise Refused("verdict path is invalid or duplicated")
            if record.get("runid") != args.runid or record.get("verdict") not in VALID_VERDICTS:
                raise Refused("verdict runid/value is invalid")
            verdicts[path] = record
            verdict_raw[path] = raw
        if set(verdicts) != set(impacted):
            raise Refused("verdict set does not equal impacted set")
        cached_material = b"".join(verdict_raw[path] for path in sorted(cached))
        if cached:
            if expected["cached"] == "none" or sha256_bytes(cached_material) != expected["cached"]:
                raise Refused("cached verdict aggregate sha mismatch")
        elif expected["cached"] != "none":
            raise Refused("cached sentinel is invalid")

        final_returns = {}
        for item in returns:
            path = item["assignedPath"]
            if path in dispatched and (path not in final_returns or item["attempt"] > final_returns[path]["attempt"]):
                final_returns[path] = item
        for path in dispatched:
            item = final_returns.get(path)
            if (item is None or item.get("returnedPath") != path
                    or item.get("verdict") != verdicts[path]["verdict"]):
                raise Refused(f"final return mismatch for {path}")

        enabled, minimum, warnings = validate_min_passes(config)
        if cached and (not enabled or expected.get("historyStatus") != "ok"):
            raise Refused("cached verdicts are not permitted")
        for path in cached:
            record = verdicts[path]
            if record.get("source") != "cache":
                raise Refused(f"cached verdict source mismatch for {path}")
            current_sha = content_sha(repo, path)
            ok, runids, _reason = cache_qualification(
                history_entries, path, current_sha, manifest["changeSetSha"],
                manifest["contractVersion"], minimum or 2)
            if (not ok or record.get("contentSha") != current_sha
                    or record.get("changeSetSha") != manifest["changeSetSha"]
                    or record.get("contractVersion") != manifest["contractVersion"]
                    or record.get("historyRunids") != runids):
                raise Refused(f"cached verdict is not history-qualified for {path}")

        has_fail = any(record["verdict"] == "FAIL" for record in verdicts.values())
        if preflight is not None:
            has_fail = findings_fail(preflight) or has_fail
        if phase4 is not None:
            has_fail = findings_fail(phase4) or has_fail
        verdict = "NEEDS_FIX" if has_fail else "CONSISTENT"

        # The sibling scan remains inside the lock and precedes the indivisible barrier.
        sibling = run_sibling_step(manifest, returns, phase4, config, repo)

        # Recheck every mutable root as one barrier immediately before state commit.
        lock_recheck(lock_fd, lock_path, args.runid, expected["lockIno"])
        head2 = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                               text=True, check=True).stdout.strip()
        if head2 != head or run_tree_digest(repo, manifest) != digest:
            raise Refused("HEAD/worktree changed before state write")
        if not state_unchanged(history_path, history_signature):
            history_taint = True
            raise Refused("history changed before state write")
        if not state_unchanged(anchor_path, anchor_signature):
            anchor_taint = True
            raise Refused("anchor changed before state write")
        if not state_unchanged(config_path, config_signature):
            config_taint = True
            raise Refused("config changed before state write")
        if history_taint and os.path.exists(history_path):
            os.replace(history_path, history_path + ".tainted-" + args.runid)
            history_entries = []
            history_taint = False
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        existing_keys = {(item["runid"], item["path"]) for item in history_entries}
        additions = []
        for path in impacted:
            if (args.runid, path) in existing_keys:
                raise Refused("history would duplicate (runid,path)")
            additions.append({"runid": args.runid, "path": path,
                              "contentSha": content_sha(repo, path),
                              "changeSetSha": manifest["changeSetSha"],
                              "contractVersion": manifest["contractVersion"],
                              "verdict": verdicts[path]["verdict"], "ts": now})
        atomic(history_path, {"entries": trim_history(history_entries + additions)})
        report_status = "pending" if report_rule is not None else "not-requested"
        last_state = {"runid": args.runid, "verdict": verdict, "ts": now,
                      "reportStatus": report_status}
        atomic(last_run_path, last_state)
        anchor_written = False
        if verdict == "CONSISTENT":
            atomic(anchor_path, {"sha": head, "head": head, "digest": digest,
                                 "runid": args.runid,
                                 "contractVersion": manifest["contractVersion"]})
            anchor_written = True
        counts = {"impacted": len(impacted), "dispatch": len(dispatched),
                  "cached": len(cached)}
        report_path, report_status = finalize_report(
            repo, run_dir, report_rule, manifest["reportDate"], last_run_path,
            last_state, warnings, verdict, counts=counts,
            history_status=expected["historyStatus"], sibling=sibling,
            anchor_written=anchor_written)
        try:
            release_lock(lock_path, lock_inode)
        except OSError:
            add_warning(warnings, "lockReleaseFailed")
        os.close(lock_fd)
        lock_fd = None
        result = {"verdict": verdict, "anchorWritten": anchor_written,
                  "runid": args.runid, "counts": counts,
                  "historyStatus": expected["historyStatus"], "warnings": warnings,
                  "siblingScan": sibling, "reportStatus": report_status}
        if report_path is not None:
            result["reportPath"] = report_path
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, KeyError, json.JSONDecodeError,
            subprocess.CalledProcessError) as exc:
        reason = str(exc)
        # Degrade only state owned by this run; never touch a later run's state.
        report_path = None
        report_status = None
        if owned:
            try:
                if history_taint and os.path.exists(history_path):
                    os.replace(history_path, history_path + ".tainted-" + args.runid)
            except OSError:
                pass
            try:
                if anchor_taint and os.path.exists(anchor_path):
                    os.unlink(anchor_path)
            except OSError:
                pass
            can_report = report_trusted and report_rule is not None and not config_taint
            state_written = False
            if identity_ok:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                recorded_reason = "config-changed" if config_taint else reason
                last_state = {"runid": args.runid, "verdict": "REFUSED",
                              "reason": recorded_reason, "ts": now,
                              "reportStatus": "pending" if can_report else "not-requested"}
                if config_taint:
                    last_state["expectedConfigSha"] = expected.get("config")
                try:
                    atomic(last_run_path, last_state)
                    state_written = True
                    report_status = last_state["reportStatus"]
                except OSError:
                    add_warning(warnings, "reportStatusUpdateFailed")
                if can_report and state_written:
                    report_path, report_status = finalize_report(
                        repo, run_dir, report_rule, manifest["reportDate"], last_run_path,
                        last_state, warnings, "REFUSED", reason=reason,
                        anchor_written=False)
            if lock_fd is not None:
                try:
                    release_lock(lock_path, lock_inode)
                except OSError:
                    add_warning(warnings, "lockReleaseFailed")
        result = {"verdict": "REFUSED", "anchorWritten": False, "reason": reason}
        if warnings:
            result["warnings"] = warnings
        if report_status is not None:
            result["reportStatus"] = report_status
        if report_path is not None:
            result["reportPath"] = report_path
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 3
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
