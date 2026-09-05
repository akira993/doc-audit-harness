"""Validate the optional Phase-4 record retained by a claims-refused run."""

import hashlib
import json
import os
import re
import stat

from docaudit_cache import _validate_phase4_runs


MAX_RECORD_BYTES = 1024 * 1024
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_bounded_regular(path, limit=MAX_RECORD_BYTES):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not a regular file")
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > limit:
            raise ValueError("exceeds 1 MiB")
        return raw
    finally:
        os.close(fd)


def _sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def load_usable_record(path, evidence):
    """Return ``(record, None)`` or ``(None, reason)`` without raising."""
    expected_sha = evidence.get("refusedPhase4") if isinstance(evidence, dict) else None
    if expected_sha == "none" and not os.path.lexists(path):
        return None, None
    try:
        raw = read_bounded_regular(path)
        if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise ValueError("evidence sha is missing")
        if _sha(raw) != expected_sha:
            raise ValueError("sha mismatch")
        record = json.loads(raw.decode("utf-8"))
        _validate_phase4_runs([record])
        if record.get("gateVerdict") != "REFUSED":
            raise ValueError("gateVerdict is not REFUSED")
        if record.get("reason") != "codexClaimsUnadjudicated":
            raise ValueError("reason is not codexClaimsUnadjudicated")
        counts = record.get("claimCounts")
        if not isinstance(counts, dict):
            raise ValueError("claimCounts is not an object")
        targets = counts.get("targets")
        unadjudicated = counts.get("unadjudicated")
        if (isinstance(targets, bool) or not isinstance(targets, int)
                or isinstance(unadjudicated, bool) or not isinstance(unadjudicated, int)
                or not 0 < unadjudicated <= targets):
            raise ValueError("claimCounts is invalid")
        history_sha = record.get("historySha")
        if (not isinstance(history_sha, str)
                or (history_sha != "none" and not SHA_RE.fullmatch(history_sha))):
            raise ValueError("historySha is invalid")
        if record.get("runid") == evidence.get("runid"):
            raise ValueError("record runid matches current run")
        if history_sha != evidence.get("history"):
            raise ValueError("historySha does not match current history")
        return record, None
    except Exception as exc:
        return None, str(exc) or exc.__class__.__name__
