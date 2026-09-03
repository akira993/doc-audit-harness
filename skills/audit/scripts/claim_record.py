#!/usr/bin/env python3
"""Shared runtime contract for run-scoped codex claim records."""

import hashlib
import json
import os
import re
import stat
import unicodedata

from docaudit_paths import normalize_finding_path, validate_repo_path


MAX_CLAIM_RECORD_BYTES = 64 * 1024
CLAIM_STATES = frozenset({"confirmed", "refuted", "unverified", "not-adjudicable"})
AGENT_CLAIM_STATES = frozenset({"confirmed", "refuted", "unverified"})
CLAIM_REASON_BY_STATE = {
    "confirmed": None,
    "refuted": None,
    "unverified": None,
    "not-adjudicable": "path-unresolved",
}
FINDING_ID_RE = re.compile(r"^[0-9a-f]{64}$")
CLAIM_FILENAME_RE = re.compile(r"^[0-9a-f]{64}\.json$")
CLAIM_RECORD_KEYS = frozenset({
    "runid", "findingId", "state", "reason", "rationale",
    "evidenceFile", "evidenceLine",
})


class ClaimRecordError(ValueError):
    """A non-blocking claim-record validation failure with a stable warning code."""

    def __init__(self, message, warning="codexClaimsUnadjudicated"):
        super().__init__(message)
        self.warning = warning


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def claim_finding_id(finding):
    file_value = finding.get("file") if isinstance(finding, dict) else None
    severity = finding.get("severity") if isinstance(finding, dict) else None
    title = finding.get("title") if isinstance(finding, dict) else None
    if not isinstance(file_value, str):
        raise ValueError("claim finding file must be a string")
    if not isinstance(severity, str) or not severity.strip():
        raise ValueError("claim finding severity must be a non-empty string")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("claim finding title must be a non-empty string")
    identity = {
        "file": file_value,
        "severity": severity.strip().upper(),
        "title": unicodedata.normalize("NFC", title).strip(),
    }
    return hashlib.sha256(canonical_bytes(identity)).hexdigest()


def extract_claim_targets(phase4):
    """Return ordered, deduplicated adjudication targets and missing-title count."""
    findings = phase4.get("findings", []) if isinstance(phase4, dict) else []
    if not isinstance(findings, list):
        raise ValueError("phase findings must be an array")
    targets = []
    seen = set()
    missing_titles = 0
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("source") != "codex-review":
            continue
        severity = finding.get("severity")
        if not isinstance(severity, str) or severity.strip().upper() not in {"CRITICAL", "HIGH"}:
            continue
        title = finding.get("title")
        if not isinstance(title, str) or not title.strip():
            missing_titles += 1
            continue
        finding_id = claim_finding_id(finding)
        if finding_id in seen:
            continue
        seen.add(finding_id)
        targets.append({
            "findingId": finding_id,
            "file": finding["file"],
            "severity": severity.strip().upper(),
            "title": unicodedata.normalize("NFC", title).strip(),
        })
    return targets, missing_titles


def encode_claim_record(record):
    raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_CLAIM_RECORD_BYTES:
        raise ClaimRecordError("claim record exceeds its size limit")
    return raw


def read_claim_record(path):
    """Read at most the shared limit plus one byte without following a symlink."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ClaimRecordError(f"claim record cannot be opened: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ClaimRecordError("claim record is not a regular file")
        chunks = []
        remaining = MAX_CLAIM_RECORD_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_CLAIM_RECORD_BYTES:
            raise ClaimRecordError("claim record exceeds its size limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ClaimRecordError(f"claim record is not valid JSON: {exc}") from exc
        return value, raw
    finally:
        os.close(fd)


def _line_exists(repo_root, evidence_file, evidence_line):
    try:
        relative = validate_repo_path(repo_root, evidence_file)
        with open(os.path.join(repo_root, relative), "rb") as handle:
            for number, _line in enumerate(handle, 1):
                if number == evidence_line:
                    return True
    except (OSError, ValueError):
        return False
    return False


def validate_claim_record(record, *, runid, finding_id, repo_root, finding_file,
                          raw_size=None):
    """Validate every planner/writer/gate rule and return the record unchanged."""
    if raw_size is not None and raw_size > MAX_CLAIM_RECORD_BYTES:
        raise ClaimRecordError("claim record exceeds its size limit")
    if not FINDING_ID_RE.fullmatch(finding_id):
        raise ClaimRecordError("claim findingId is invalid")
    if not isinstance(record, dict) or set(record) - CLAIM_RECORD_KEYS:
        raise ClaimRecordError("claim record has an invalid shape")
    if record.get("runid") != runid or record.get("findingId") != finding_id:
        raise ClaimRecordError("claim record runid or findingId does not match")
    state = record.get("state")
    if state not in CLAIM_STATES:
        raise ClaimRecordError("claim record state is invalid")
    if not isinstance(record.get("rationale"), str):
        raise ClaimRecordError("claim record rationale must be a string")
    expected_reason = CLAIM_REASON_BY_STATE[state]
    if expected_reason is None:
        if "reason" in record:
            raise ClaimRecordError("claim record state/reason combination is invalid")
    elif record.get("reason") != expected_reason:
        raise ClaimRecordError("claim record state/reason combination is invalid")
    if state == "not-adjudicable":
        if normalize_finding_path(repo_root, finding_file) is not None:
            raise ClaimRecordError(
                "not-adjudicable finding path now resolves",
                "claimNotAdjudicableRejected",
            )
    if state in {"confirmed", "refuted"}:
        evidence_file = record.get("evidenceFile")
        evidence_line = record.get("evidenceLine")
        if (not isinstance(evidence_file, str)
                or isinstance(evidence_line, bool)
                or not isinstance(evidence_line, int)
                or evidence_line < 1
                or not _line_exists(repo_root, evidence_file, evidence_line)):
            raise ClaimRecordError(
                "claim evidence cannot be resolved", "claimEvidenceUnresolved"
            )
    return record


def load_valid_claim_record(path, *, runid, finding_id, repo_root, finding_file):
    record, raw = read_claim_record(path)
    return validate_claim_record(
        record, runid=runid, finding_id=finding_id, repo_root=repo_root,
        finding_file=finding_file, raw_size=len(raw)
    )
