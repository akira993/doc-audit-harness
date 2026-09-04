#!/usr/bin/env python3
"""Shared report-template token validation and bounded file reads."""

import os
import re
import stat


TOKEN_COUNTS = {
    "{{GATE_VERDICT}}": 1,
    "{{GATE_REASON}}": 1,
    "{{GATE_COUNTS}}": 1,
    "{{GATE_HISTORY_STATUS}}": 1,
    "{{GATE_WARNINGS}}": 1,
    "{{GATE_SIBLING_SCAN}}": 1,
    "{{GATE_CODEX_CLAIMS}}": 1,
    "{{GATE_ANCHOR_WRITTEN}}": 1,
    "{{GATE_REPORT_DATE}}": 2,
}
OPTIONAL_TOKENS = frozenset({"{{GATE_REASON}}"})
TOKEN_RE = re.compile(r"\{\{GATE_[A-Z0-9_]+\}\}")
MALFORMED_RE = re.compile(r"\{\{[^}]*GATE_[^}]*\}\}")
BIDI_CONTROLS = frozenset(chr(value) for value in (
    0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)))
MAX_PHASE4_BYTES = 2 * 1024 * 1024


class TokenCountError(ValueError):
    """The report template does not satisfy the gate token contract."""


def validate_template_body(text: str, claim_target_count: int) -> None:
    malformed = MALFORMED_RE.findall(text)
    if any(token not in TOKEN_COUNTS for token in malformed):
        raise TokenCountError("report template contains an unknown gate token")

    optional_tokens = set(OPTIONAL_TOKENS)
    if claim_target_count in (None, 0):
        optional_tokens.add("{{GATE_CODEX_CLAIMS}}")
    violations = []
    for token, expected in TOKEN_COUNTS.items():
        actual = text.count(token)
        allowed = (0, expected) if token in optional_tokens else (expected,)
        if actual not in allowed:
            expected_text = f"0 or {expected}" if token in optional_tokens else str(expected)
            violations.append(
                f"report template token count is invalid for {token}; "
                f"expected {expected_text}, found {actual}"
            )
    if violations:
        raise TokenCountError("; ".join(violations))
    if any(char in BIDI_CONTROLS for char in text):
        raise TokenCountError(
            "report template contains a bidirectional control character")


def read_bounded_regular_file(path, limit) -> bytes:
    """Read a regular file without following its final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("file is not a regular file")
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
            raise ValueError("file exceeds byte limit")
        return raw
    finally:
        os.close(fd)
