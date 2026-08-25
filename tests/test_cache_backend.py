"""Backend compatibility matrix for deterministic verdict caching."""

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from docaudit_cache import cache_qualification, parse_history  # noqa: E402

MISSING = object()


class TestCacheBackend(unittest.TestCase):
    def entries(self, backend_marker):
        entries = []
        for number in range(2):
            entry = {
                "runid": f"20260818T12000{number}Z-abcdef1{number}",
                "path": "docs/a.md",
                "contentSha": "sha256:content",
                "changeSetSha": "sha256:changes",
                "contractVersion": "0.10.0",
                "verdict": "PASS",
                "ts": "2026-08-18T12:00:00+00:00",
            }
            if backend_marker is not MISSING:
                entry["backend"] = backend_marker
            entries.append(entry)
        return entries

    def qualifies(self, entries, backend):
        return cache_qualification(
            entries, "docs/a.md", "sha256:content", "sha256:changes",
            "0.10.0", 2, backend)

    def test_old_history_without_backend_is_not_corrupt(self):
        entries = self.entries(MISSING)
        self.assertEqual(parse_history({"entries": entries}), entries)

    def test_explicit_workflow_hits_old_history_key(self):
        ok, runids, reason = self.qualifies(self.entries(MISSING), "workflow")
        self.assertTrue(ok)
        self.assertEqual(len(runids), 2)
        self.assertIsNone(reason)

    def test_codex_to_codex_hits(self):
        self.assertTrue(self.qualifies(self.entries("codex"), "codex")[0])

    def test_codex_history_to_workflow_misses(self):
        ok, runids, reason = self.qualifies(self.entries("codex"), "workflow")
        self.assertFalse(ok)
        self.assertEqual(runids, [])
        self.assertEqual(reason, "history-key-mismatch")

    def test_workflow_history_to_codex_misses(self):
        ok, runids, reason = self.qualifies(self.entries("workflow"), "codex")
        self.assertFalse(ok)
        self.assertEqual(runids, [])
        self.assertEqual(reason, "history-key-mismatch")

    def test_invalid_backend_is_rejected(self):
        for value in ("other", True, 1, None, []):
            with self.subTest(value=value):
                entries = self.entries(value)
                with self.assertRaisesRegex(ValueError, "invalid backend"):
                    parse_history({"entries": entries})
        ok, runids, reason = self.qualifies(self.entries("workflow"), "other")
        self.assertFalse(ok)
        self.assertEqual(runids, [])
        self.assertEqual(reason, "backend-invalid")


if __name__ == "__main__":
    unittest.main()
