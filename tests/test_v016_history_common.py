import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from docaudit_cache import parse_history_document  # noqa: E402
from docaudit_paths import normalize_finding_path  # noqa: E402


CODEX_PLAN = os.path.join(SCRIPTS, "codex-review-plan.py")


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def history_entry():
    return {
        "runid": "r0", "path": "docs/a.md", "contentSha": "sha256:c",
        "changeSetSha": "sha256:s", "contractVersion": "1",
        "verdict": "PASS", "ts": "t",
    }


def phase4_record(digest="old", findings=None):
    return {
        "runid": "r1", "ts": "t", "worktreeDigest": digest,
        "contractVersion": "1", "configSha": "sha256:c",
        "carryForwardSha": "none", "unresolvedFileCount": 0,
        "truncated": False, "findings": findings or [],
    }


class TestHistoryDocument(unittest.TestCase):
    def test_old_array_and_new_document_always_return_three_values(self):
        entry = history_entry()
        self.assertEqual(parse_history_document([entry]), ([entry], [], []))
        record = phase4_record(findings=[{"file": "docs/a.md", "severity": "HIGH"}])
        record["futureField"] = {"accepted": True}
        self.assertEqual(
            parse_history_document({"entries": [entry], "phase4Runs": [record]}),
            ([entry], [record], []))

    def test_invalid_phase4_runs_degrades_without_losing_entries(self):
        entry = history_entry()
        entries, records, warnings = parse_history_document({
            "entries": [entry],
            "phase4Runs": [phase4_record(findings=[
                {"file": "../escape.md", "severity": "HIGH"},
            ])],
        })
        self.assertEqual(entries, [entry])
        self.assertEqual(records, [])
        self.assertTrue(warnings)

    def test_invalid_entries_remain_corrupt(self):
        with self.assertRaises(ValueError):
            parse_history_document({"entries": "bad", "phase4Runs": []})


class TestNormalizeFindingPath(unittest.TestCase):
    def test_normalization_and_rejection_table(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs"))
            for name in ("a.md", "spec:10"):
                with open(os.path.join(repo, "docs", name), "w", encoding="utf-8") as handle:
                    handle.write("x\n")
            cases = {
                "docs/a.md": "docs/a.md",
                "./docs/a.md": "docs/a.md",
                "docs/a.md:10": "docs/a.md",
                "docs/a.md:10:2": "docs/a.md",
                "docs/spec:10": "docs/spec:10",
                "docs\\a.md": None,
                "C:/docs/a.md": None,
                "../docs/a.md": None,
                'docs/"a.md': None,
            }
            for value, expected in cases.items():
                with self.subTest(value=value):
                    self.assertEqual(normalize_finding_path(repo, value), expected)


class TestCarryForward(unittest.TestCase):
    def test_full_plan_returns_only_current_safe_files(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs"))
            for name in ("a.md", "b.md", "with space.md"):
                with open(os.path.join(repo, "docs", name), "w", encoding="utf-8") as handle:
                    handle.write("x\n")
            os.symlink("a.md", os.path.join(repo, "docs", "link.md"))
            config_raw = json.dumps({"codexReview": {"required": True}}).encode("utf-8")
            config_path = os.path.join(repo, "config.json")
            with open(config_path, "wb") as handle:
                handle.write(config_raw)
            findings = [
                {"file": "docs/b.md", "severity": "LOW"},
                {"file": "docs/a.md", "severity": "HIGH"},
                {"file": "docs/link.md", "severity": "CRITICAL"},
                {"file": "docs/missing.md", "severity": "HIGH"},
                {"file": "docs/with space.md", "severity": "MEDIUM"},
            ]
            history_raw = json.dumps({
                "entries": [], "phase4Runs": [phase4_record("old", findings)],
            }).encode("utf-8")
            history_path = os.path.join(repo, "history.json")
            with open(history_path, "wb") as handle:
                handle.write(history_raw)
            proc = subprocess.run([
                sys.executable, CODEX_PLAN, "--mode", "full",
                "--repo-root", repo,
                "--config", config_path, "--expect-config-sha", sha(config_raw),
                "--available", "true", "--baseline-ok", "true",
                "--history", history_path, "--expect-history-sha", sha(history_raw),
                "--worktree-digest", "current",
            ], capture_output=True, text=True, cwd=repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            expected = {"files": [
                {"file": "docs/a.md", "severity": "HIGH"},
                {"file": "docs/b.md", "severity": "LOW"},
            ]}
            self.assertEqual(result["carryForward"], expected)
            canonical = json.dumps(
                expected, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            self.assertEqual(result["carryForwardSha"], sha(canonical))

    def test_history_mismatch_is_exit_seven(self):
        with tempfile.TemporaryDirectory() as repo:
            config_raw = b'{"codexReview":{}}'
            config_path = os.path.join(repo, "config.json")
            history_path = os.path.join(repo, "history.json")
            with open(config_path, "wb") as handle:
                handle.write(config_raw)
            with open(history_path, "wb") as handle:
                handle.write(b'{"entries":[]}')
            proc = subprocess.run([
                sys.executable, CODEX_PLAN, "--mode", "incremental",
                "--repo-root", repo,
                "--config", config_path, "--expect-config-sha", sha(config_raw),
                "--available", "true", "--baseline-ok", "true",
                "--history", history_path, "--expect-history-sha", "none",
                "--worktree-digest", "current",
            ], capture_output=True, text=True, cwd=repo)
            self.assertEqual(proc.returncode, 7)
            self.assertIn("sealed-history-mismatch", proc.stderr)

    def test_invalid_phase4_runs_returns_warning_and_no_carry_forward(self):
        with tempfile.TemporaryDirectory() as repo:
            config_raw = b'{"codexReview":{"required":true}}'
            history_raw = b'{"entries":[],"phase4Runs":"bad"}'
            config_path = os.path.join(repo, "config.json")
            history_path = os.path.join(repo, "history.json")
            with open(config_path, "wb") as handle:
                handle.write(config_raw)
            with open(history_path, "wb") as handle:
                handle.write(history_raw)
            proc = subprocess.run([
                sys.executable, CODEX_PLAN, "--mode", "full",
                "--repo-root", repo,
                "--config", config_path, "--expect-config-sha", sha(config_raw),
                "--available", "true", "--baseline-ok", "true",
                "--history", history_path, "--expect-history-sha", sha(history_raw),
                "--worktree-digest", "current",
            ], capture_output=True, text=True, cwd=repo)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertIsNone(result["carryForward"])
            self.assertEqual(result["carryForwardSha"], "none")
            self.assertTrue(any("phase4Runs ignored" in item
                                for item in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
