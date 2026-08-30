"""Focused CT-5 boundary contracts for docaudit v0.16.0 Phase-4 history."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture, write


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from docaudit_cache import parse_history_document  # noqa: E402


def script(name):
    return os.path.join(SCRIPTS, name)


def file_sha(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def load_decide_verdict():
    path = script("decide-verdict.py")
    spec = importlib.util.spec_from_file_location("v016_phase4_decide_verdict", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phase4_record(digest="source", findings=None, **updates):
    record = {
        "runid": "20260818T110000Z-source01",
        "ts": "2026-08-18T11:00:00+00:00",
        "worktreeDigest": digest,
        "contractVersion": "0.16.0",
        "configSha": "sha256:" + "1" * 64,
        "carryForwardSha": "none",
        "unresolvedFileCount": 0,
        "truncated": False,
        "findings": findings or [],
    }
    record.update(updates)
    return record


class TestV016Phase4Contracts(unittest.TestCase):
    maxDiff = None

    def _prepare_full(self, fx, runid=None, contract="0.16.0"):
        opened = fx.open(runid=runid)
        self.assertEqual(opened.returncode, 0, opened.stdout + opened.stderr)
        prepared = fx.plan_start_seal(mode="full", contract=contract)
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)

    def _complete_and_gate(self, fx, findings, carry_sha="none"):
        phase4 = {
            "findings": findings,
            "codexReview": {
                "state": "completed",
                "promptVariant": "full",
                "carryForwardSha": carry_sha,
            },
        }
        completed = fx.complete(phase4=phase4)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        gated = fx.gate()
        self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)
        return json.loads(gated.stdout)

    def _plan_carry_forward(self, fx):
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            digest = json.load(handle)["worktreeDigest"]
        proc = subprocess.run([
            sys.executable, script("codex-review-plan.py"),
            "--mode", "full", "--repo-root", fx.repo,
            "--config", fx.config_path,
            "--expect-config-sha", file_sha(fx.config_path),
            "--available", "true", "--baseline-ok", "true",
            "--history", fx.history,
            "--expect-history-sha", file_sha(fx.history),
            "--worktree-digest", digest,
        ], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout), digest

    def test_ct_5_retains_five_plus_source_guard_and_stable_carry_forward(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        source = phase4_record(findings=[{"file": "docs/a.md", "severity": "HIGH"}])
        write(fx.history, json.dumps({"entries": [], "phase4Runs": [source]}) + "\n")

        carry_shas = []
        current_digest = None
        for index in range(7):
            runid = f"20260818T12000{index}Z-abcdef{index + 12:02d}"
            self._prepare_full(fx, runid=runid)
            planned, digest = self._plan_carry_forward(fx)
            current_digest = digest
            self.assertEqual(planned["carryForward"], {
                "files": [{"file": "docs/a.md", "severity": "HIGH"}],
            })
            carry_shas.append(planned["carryForwardSha"])
            self._complete_and_gate(
                fx,
                [{"source": "codex-review", "file": "docs/b.md",
                  "severity": "LOW", "title": "sample"}],
                planned["carryForwardSha"],
            )
            with open(fx.history, encoding="utf-8") as handle:
                records = json.load(handle)["phase4Runs"]
            self.assertLessEqual(len(records), 6)
            self.assertTrue(any(record["worktreeDigest"] == "source"
                                for record in records))

        self.assertEqual(len(set(carry_shas[1:])), 1)
        self.assertEqual(carry_shas[-1], carry_shas[1])
        with open(fx.history, encoding="utf-8") as handle:
            records = json.load(handle)["phase4Runs"]
        self.assertEqual(len(records), 6)
        self.assertEqual(sum(record["worktreeDigest"] == "source" for record in records), 1)
        self.assertEqual(sum(record["worktreeDigest"] == current_digest
                             for record in records), 5)

    def test_ct_5_truncates_501_findings_and_skips_flip_comparison(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        findings = []
        for index in range(501):
            relative = f"docs/generated-{index:03d}.md"
            write(os.path.join(fx.repo, relative), "generated\n")
            findings.append({"source": "codex-review", "file": relative,
                             "severity": "HIGH", "title": "sample"})

        self._prepare_full(fx)
        result = self._complete_and_gate(fx, findings)
        self.assertEqual(result["counts"]["phase4FlipsUnchangedContent"], 0)
        self.assertTrue(any("findings were truncated; flip comparison skipped" in warning
                            for warning in result["warnings"]))
        with open(fx.history, encoding="utf-8") as handle:
            record = json.load(handle)["phase4Runs"][-1]
        self.assertTrue(record["truncated"])
        self.assertEqual(len(record["findings"]), 500)

    def test_ct_5_gate_degraded_phase4_runs_rebuilds_without_quarantine(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        write(fx.history, json.dumps({"entries": [], "phase4Runs": "invalid"}) + "\n")
        self._prepare_full(fx)
        result = self._complete_and_gate(
            fx, [{"source": "codex-review", "file": "docs/a.md",
                  "severity": "HIGH", "title": "sample"}])
        self.assertTrue(any("phase4Runs ignored" in warning
                            for warning in result["warnings"]))
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        self.assertEqual(len(history["phase4Runs"]), 1)
        self.assertEqual(history["phase4Runs"][0]["runid"], fx.runid)
        self.assertFalse(any(name.startswith("docaudit-history.json.tainted-")
                             for name in os.listdir(os.path.dirname(fx.history))))

    def test_ct_5_round_trip_failure_warns_without_adding_record(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self._prepare_full(fx)
        completed = fx.complete(phase4={
            "findings": [{"source": "codex-review", "file": "docs/a.md",
                          "severity": "HIGH", "title": "sample"}],
            "codexReview": {"state": "completed", "promptVariant": "full",
                            "carryForwardSha": "none"},
        })
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        module = load_decide_verdict()
        argv = [
            script("decide-verdict.py"), "--run-dir", fx.run_dir,
            "--repo-root", fx.repo, "--config", fx.config_path,
            "--anchor-path", fx.anchor_rel, "--runid", fx.runid,
            "--expect-json", json.dumps(fx.evidence), "--date", "2026-08-18",
        ]
        forced = mock.Mock(side_effect=lambda data: (
            data["entries"], [], ["phase4Runs ignored: forced boundary failure"]))
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(module, "parse_history_document", forced), \
                mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = module.main()
        self.assertEqual(status, 0, stdout.getvalue() + stderr.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(any("failed round-trip validation" in warning
                            for warning in result["warnings"]))
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        self.assertEqual(history["phase4Runs"], [])
        self.assertEqual(forced.call_count, 1)

    def test_ct_5_writer_parser_maximum_and_oversize_boundaries(self):
        directory = "界" * 80
        suffix = "file-000-" + "x" * 15
        worst_path = "docs/" + directory + "/" + suffix
        serialized_path = json.dumps(worst_path, ensure_ascii=True,
                                     separators=(",", ":")).encode("utf-8")
        self.assertEqual(len(serialized_path), 512)

        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        findings = []
        for index in range(500):
            suffix = f"file-{index:03d}-" + "x" * 15
            relative = "docs/" + directory + "/" + suffix
            self.assertEqual(len(json.dumps(relative, ensure_ascii=True).encode("utf-8")),
                             512)
            write(os.path.join(fx.repo, relative), "boundary\n")
            findings.append({"source": "codex-review", "file": relative,
                             "severity": "HIGH", "title": "sample"})
        self._prepare_full(fx)
        result = self._complete_and_gate(fx, findings)
        self.assertFalse(any("round-trip" in warning
                             for warning in result.get("warnings", [])))
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        entries, records, warnings = parse_history_document(history)
        self.assertTrue(entries)
        self.assertEqual(len(records[-1]["findings"]), 500)
        self.assertFalse(records[-1]["truncated"])
        self.assertEqual(warnings, [])

        record_513k = copy.deepcopy(records[-1])
        record_513k["padding"] = "x" * (513 * 1024)
        _entries, records, warnings = parse_history_document(
            {"entries": [], "phase4Runs": [record_513k]})
        self.assertEqual(records, [])
        self.assertTrue(any("record 0 exceeds 512 KiB" in warning for warning in warnings))

        large_records = []
        for index in range(3):
            large = phase4_record(digest=f"digest-{index}")
            large["padding"] = "x" * (400 * 1024)
            large_records.append(large)
        _entries, records, warnings = parse_history_document(
            {"entries": [], "phase4Runs": large_records})
        self.assertEqual(records, [])
        self.assertTrue(any("phase4Runs exceeds 1 MiB" in warning for warning in warnings))

    def test_ct_5_unresolved_file_count_is_recorded_and_warned(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self._prepare_full(fx)
        result = self._complete_and_gate(fx, [
            {"source": "codex-review", "file": "docs/a.md",
             "severity": "HIGH", "title": "valid"},
            {"source": "codex-review", "file": "docs\\a.md",
             "severity": "HIGH", "title": "backslash"},
            {"source": "codex-review", "file": "../escape.md",
             "severity": "HIGH", "title": "parent"},
        ])
        self.assertTrue(any("Phase-4 unresolved finding paths: 2" in warning
                            for warning in result["warnings"]))
        with open(fx.history, encoding="utf-8") as handle:
            record = json.load(handle)["phase4Runs"][-1]
        self.assertEqual(record["unresolvedFileCount"], 2)
        self.assertEqual(record["findings"], [
            {"file": "docs/a.md", "severity": "HIGH"},
        ])

    def test_ct_5_flip_requires_matching_contract_and_config(self):
        module = load_decide_verdict()
        base = phase4_record(
            digest="same",
            findings=[{"file": "docs/a.md", "severity": "HIGH"}],
            configSha="sha256:" + "a" * 64,
            carryForwardSha="sha256:" + "c" * 64,
        )
        current = phase4_record(
            digest="same",
            findings=[{"file": "docs/b.md", "severity": "HIGH"}],
            configSha=base["configSha"],
            carryForwardSha=base["carryForwardSha"],
        )
        self.assertEqual(module.phase4_flip_count([base], current), 2)
        different_contract = dict(current, contractVersion="0.16.1")
        self.assertEqual(module.phase4_flip_count([base], different_contract), 0)
        different_config = dict(current, configSha="sha256:" + "b" * 64)
        self.assertEqual(module.phase4_flip_count([base], different_config), 0)


if __name__ == "__main__":
    unittest.main()
