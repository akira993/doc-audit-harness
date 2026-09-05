"""Issue #78 contracts for carrying claims-refused Phase-4 records."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture, write


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "audit" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import refused_phase4
import claim_record


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def phase(findings, variant="full", state="completed"):
    return {
        "findings": findings,
        "codexReview": {
            "state": state,
            "promptVariant": variant if state in {"completed", "execution-failed"} else None,
            "carryForwardSha": "none",
        },
    }


def finding(file="docs/a.md", severity="HIGH", title="carried claim"):
    return {"source": "codex-review", "severity": severity,
            "title": f"{title} ({file})", "file": file}


def record(runid="20260818T120000Z-abcdef12", history_sha="none",
           digest="old-digest"):
    return {
        "runid": runid,
        "ts": "2026-08-18T12:00:00+00:00",
        "worktreeDigest": digest,
        "contractVersion": "0.10.0",
        "configSha": "sha256:" + "1" * 64,
        "carryForwardSha": "none",
        "unresolvedFileCount": 0,
        "truncated": False,
        "findings": [{"file": "docs/a.md", "severity": "HIGH"}],
        "gateVerdict": "REFUSED",
        "reason": "codexClaimsUnadjudicated",
        "claimCounts": {"targets": 2, "unadjudicated": 1},
        "historySha": history_sha,
    }


class TestRefusedPhase4Loader(unittest.TestCase):
    def write_record(self, directory, value):
        path = os.path.join(directory, "docaudit-refused-phase4.json")
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        write(path, raw)
        return path, raw

    def test_valid_record_and_all_rejection_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, raw = self.write_record(tmp, record())
            evidence = {"runid": "20260818T120001Z-bcdef123",
                        "history": "none", "refusedPhase4": sha(raw)}
            actual, reason = refused_phase4.load_usable_record(path, evidence)
            self.assertEqual(actual, record())
            self.assertIsNone(reason)

            cases = {
                "sha": (record(), dict(evidence, refusedPhase4="sha256:" + "0" * 64)),
                "shape": ([], evidence),
                "meaning": (dict(record(), gateVerdict="CONSISTENT"), evidence),
                # Keep every numeric boundary explicit so weakening the compound
                # claim-count predicate cannot survive this table.
                "counts-unadjudicated-zero": (
                    dict(record(), claimCounts={"targets": 1, "unadjudicated": 0}),
                    evidence),
                "counts-unadjudicated-over-targets": (
                    dict(record(), claimCounts={"targets": 1, "unadjudicated": 2}),
                    evidence),
                "counts-targets-zero": (
                    dict(record(), claimCounts={"targets": 0, "unadjudicated": 1}),
                    evidence),
                "same-run": (record(runid=evidence["runid"]), evidence),
                "history": (record(history_sha="sha256:" + "2" * 64), evidence),
            }
            for name, (value, base_evidence) in cases.items():
                with self.subTest(name=name):
                    path, case_raw = self.write_record(tmp, value)
                    case_evidence = dict(base_evidence)
                    if name != "sha":
                        case_evidence["refusedPhase4"] = sha(case_raw)
                    actual, reason = refused_phase4.load_usable_record(path, case_evidence)
                    self.assertIsNone(actual)
                    self.assertTrue(reason)
                    if name.startswith("counts-"):
                        self.assertEqual(reason, "claimCounts is invalid")

    def test_absent_symlink_fifo_and_one_mib_boundaries_do_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing")
            self.assertEqual(
                refused_phase4.load_usable_record(
                    missing, {"refusedPhase4": "none"}),
                (None, None))
            exact = os.path.join(tmp, "exact")
            write(exact, b"x" * refused_phase4.MAX_RECORD_BYTES)
            self.assertEqual(len(refused_phase4.read_bounded_regular(exact)),
                             refused_phase4.MAX_RECORD_BYTES)
            write(exact, b"x" * (refused_phase4.MAX_RECORD_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                refused_phase4.read_bounded_regular(exact)
            target = os.path.join(tmp, "target")
            write(target, "{}")
            link = os.path.join(tmp, "link")
            os.symlink(target, link)
            actual, reason = refused_phase4.load_usable_record(
                link, {"refusedPhase4": "sha256:" + "0" * 64})
            self.assertIsNone(actual)
            self.assertTrue(reason)
            fifo = os.path.join(tmp, "fifo")
            os.mkfifo(fifo)
            actual, reason = refused_phase4.load_usable_record(
                fifo, {"refusedPhase4": "sha256:" + "0" * 64})
            self.assertIsNone(actual)
            self.assertIn("regular file", reason)

    def test_short_reads_still_enforce_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "short-read")
            write(path, b"12345")
            real_read = refused_phase4.os.read

            def one_byte(fd, size):
                return real_read(fd, min(size, 1))

            with mock.patch.object(refused_phase4.os, "read", side_effect=one_byte):
                with self.assertRaisesRegex(ValueError, "1 MiB"):
                    refused_phase4.read_bounded_regular(path, limit=4)


class TestRefusedPhase4Planner(unittest.TestCase):
    def run_plan(self, repo, side_value, mutate_evidence=None, history_records=None):
        os.makedirs(os.path.join(repo, ".claude", "state"), exist_ok=True)
        os.makedirs(os.path.join(repo, "docs"), exist_ok=True)
        write(os.path.join(repo, "docs", "a.md"), "# A\n")
        config = os.path.join(repo, "config.json")
        write(config, json.dumps({"codexReview": {"required": True}}))
        history_path = os.path.join(repo, "history.json")
        history_sha = "none"
        if history_records is not None:
            history_raw = (json.dumps({"entries": [], "phase4Runs": history_records},
                                      sort_keys=True) + "\n").encode()
            write(history_path, history_raw)
            history_sha = sha(history_raw)
            if isinstance(side_value, dict):
                side_value = dict(side_value, historySha=history_sha)
        side = os.path.join(repo, ".claude", "state", "docaudit-refused-phase4.json")
        raw = (json.dumps(side_value, sort_keys=True) + "\n").encode()
        write(side, raw)
        evidence = {"runid": "20260818T120001Z-bcdef123", "history": history_sha,
                    "refusedPhase4": sha(raw)}
        if mutate_evidence:
            evidence.update(mutate_evidence)
        return subprocess.run([
            sys.executable, str(SCRIPTS / "codex-review-plan.py"),
            "--mode", "full", "--config", config,
            "--expect-config-sha", sha(Path(config).read_bytes()),
            "--repo-root", repo, "--available", "true", "--baseline-ok", "false",
            "--history", history_path,
            "--expect-history-sha", history_sha, "--worktree-digest", "current-digest",
            "--evidence", json.dumps(evidence),
        ], capture_output=True, text=True)

    def test_valid_record_is_last_carry_candidate(self):
        with tempfile.TemporaryDirectory() as repo:
            older = record(runid="20260818T115959Z-aaaa1111", digest="older-digest")
            older["findings"] = [{"file": "docs/b.md", "severity": "CRITICAL"}]
            os.makedirs(os.path.join(repo, "docs"), exist_ok=True)
            write(os.path.join(repo, "docs", "b.md"), "# B\n")
            proc = self.run_plan(repo, record(), history_records=[older])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["carryForward"], {
            "files": [{"file": "docs/a.md", "severity": "HIGH"}]})
        self.assertNotIn("warnings", result)

    def test_each_invalid_record_is_warned_and_not_carried(self):
        cases = {
            "sha": (record(), {"refusedPhase4": "sha256:" + "0" * 64}),
            "shape": ([], None),
            "meaning": (dict(record(), reason="other"), None),
            "counts-unadjudicated-zero": (
                dict(record(), claimCounts={"targets": 1, "unadjudicated": 0}), None),
            "counts-unadjudicated-over-targets": (
                dict(record(), claimCounts={"targets": 1, "unadjudicated": 2}), None),
            "counts-targets-zero": (
                dict(record(), claimCounts={"targets": 0, "unadjudicated": 1}), None),
            "same-run": (record(runid="20260818T120001Z-bcdef123"), None),
            "history": (record(history_sha="sha256:" + "2" * 64), None),
        }
        for name, (value, evidence_patch) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as repo:
                proc = self.run_plan(repo, value, evidence_patch)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertIsNone(result["carryForward"])
                self.assertEqual(result["carryForwardSha"], "none")
                self.assertTrue(any(item.startswith("refusedPhase4Ignored: ")
                                    for item in result["warnings"]))
                if name.startswith("counts-"):
                    self.assertIn("refusedPhase4Ignored: claimCounts is invalid",
                                  result["warnings"])


class TestRefusedPhase4Gate(unittest.TestCase):
    RUNIDS = (
        "20260818T120000Z-abcdef12", "20260818T120001Z-bcdef123",
        "20260818T120002Z-cdef1234", "20260818T120003Z-def12345",
    )

    def prepare(self, fx, runid, findings, *, mode="full", report=False,
                state="completed"):
        self.assertEqual(fx.open(runid).returncode, 0)
        self.assertEqual(fx.plan_start_seal(mode=mode).returncode, 0)
        variant = "full" if mode == "full" else "diff"
        self.assertEqual(fx.complete(phase4=phase(findings, variant, state)).returncode, 0)
        if report:
            self.assertEqual(fx.write_template().returncode, 0)

    def side_path(self, fx):
        return os.path.join(fx.repo, ".claude", "state", "docaudit-refused-phase4.json")

    def load_decide(self):
        spec = importlib.util.spec_from_file_location(
            "decide_refused_phase4_test", SCRIPTS / "decide-verdict.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_main(self, module, fx, patcher):
        argv = ["decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence)]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(output), patcher:
            code = module.main()
        return code, json.loads(output.getvalue())

    def test_claims_refusal_writes_exact_record_and_preserves_history_anchor(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.prepare(fx, self.RUNIDS[0], [])
        self.assertEqual(fx.gate().returncode, 0)
        history_before = Path(fx.history).read_bytes()
        anchor_before = Path(fx.anchor).read_bytes()

        self.prepare(fx, self.RUNIDS[1], [finding()])
        history_sha = fx.evidence["history"]
        manifest = json.loads(Path(fx.run_dir, "manifest.json").read_text())
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["reason"].startswith("codexClaimsUnadjudicated"))
        self.assertEqual(Path(fx.history).read_bytes(), history_before)
        self.assertEqual(Path(fx.anchor).read_bytes(), anchor_before)
        side = json.loads(Path(self.side_path(fx)).read_text())
        self.assertEqual(side["runid"], self.RUNIDS[1])
        self.assertEqual(set(side), {
            "runid", "ts", "worktreeDigest", "contractVersion", "configSha",
            "carryForwardSha", "unresolvedFileCount", "truncated", "findings",
            "gateVerdict", "reason", "claimCounts", "historySha",
        })
        self.assertEqual(side["worktreeDigest"], manifest["worktreeDigest"])
        self.assertEqual(side["contractVersion"], manifest["contractVersion"])
        self.assertEqual(side["configSha"], fx.evidence["config"])
        self.assertEqual(side["carryForwardSha"], "none")
        self.assertEqual(side["unresolvedFileCount"], 0)
        self.assertFalse(side["truncated"])
        self.assertIsInstance(side["ts"], str)
        self.assertEqual(side["findings"], [{"file": "docs/a.md", "severity": "HIGH"}])
        self.assertEqual(side["historySha"], history_sha)
        self.assertEqual(side["claimCounts"], {"targets": 1, "unadjudicated": 1})
        self.assertEqual((side["gateVerdict"], side["reason"]),
                         ("REFUSED", "codexClaimsUnadjudicated"))

    def test_same_digest_flip_warns_and_success_clears_side(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.prepare(fx, self.RUNIDS[0], [finding()])
        self.assertEqual(fx.gate().returncode, 3)
        refused_digest = json.loads(Path(self.side_path(fx)).read_text())["worktreeDigest"]

        self.prepare(fx, self.RUNIDS[1], [])
        manifest = json.loads(Path(fx.run_dir, "manifest.json").read_text())
        self.assertEqual(manifest["worktreeDigest"], refused_digest)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["counts"]["phase4FlipsUnchangedContent"], 1)
        self.assertIn(
            f"previousRunRefused: {self.RUNIDS[0]} "
            "(codexClaimsUnadjudicated 1 of 1)", result["warnings"])
        self.assertFalse(os.path.exists(self.side_path(fx)))

    def test_side_record_wins_over_history_for_flip_and_is_not_persisted(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.prepare(fx, self.RUNIDS[0], [])
        self.assertEqual(fx.gate().returncode, 0)
        self.prepare(fx, self.RUNIDS[1], [finding(file="docs/a.md")])
        self.assertEqual(fx.gate().returncode, 3)

        current_finding = finding(file="docs/b.md")
        self.prepare(fx, self.RUNIDS[2], [current_finding])
        target = claim_record.extract_claim_targets(phase([current_finding]))[0][0]
        written = fx.call(
            "write-claim.py", "--run-dir", fx.run_dir,
            "--out", os.path.join(fx.run_dir, "claims", target["findingId"] + ".json"),
            "--runid", fx.runid, "--repo-root", fx.repo,
            "--finding-id", target["findingId"], "--state", "refuted",
            "--evidence-file", "docs/b.md", "--evidence-line", "1",
            input_text="checked")
        self.assertEqual(written.returncode, 0, written.stderr)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["counts"]["phase4FlipsUnchangedContent"], 2)
        history = json.loads(Path(fx.history).read_text())
        self.assertNotIn(self.RUNIDS[1], [item["runid"] for item in history["phase4Runs"]])

    def test_three_consecutive_cold_claim_refusals_replace_latest_record(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        for index, runid in enumerate(self.RUNIDS[:3]):
            self.prepare(fx, runid, [finding()])
            proc = fx.gate()
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            result = json.loads(proc.stdout)
            side = json.loads(Path(self.side_path(fx)).read_text())
            self.assertEqual(side["runid"], runid)
            self.assertEqual(side["historySha"], "none")
            if index:
                self.assertTrue(any(item.startswith("previousRunRefused: ")
                                    for item in result["warnings"]))

    def test_corrupt_history_is_quarantined_then_side_uses_none_history(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        write(fx.history, "{broken")
        self.prepare(fx, self.RUNIDS[0], [finding()])
        self.assertEqual(fx.evidence["historyStatus"], "corrupt")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(fx.history))
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))
        self.assertEqual(json.loads(Path(self.side_path(fx)).read_text())["historySha"], "none")
        self.prepare(fx, self.RUNIDS[1], [])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(any(item.startswith("previousRunRefused: ")
                            for item in json.loads(proc.stdout)["warnings"]))

    def test_incremental_or_pre_barrier_refusal_does_not_write_side(self):
        fx = RunFixture(self, config_extra={"codexReview": {}})
        self.prepare(fx, self.RUNIDS[0], [finding()], mode="incremental")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(self.side_path(fx)))

        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.prepare(fx, self.RUNIDS[0], [finding()])
        write(os.path.join(fx.repo, "src", "app.py"), "print('changed')\n")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["reason"], "worktree digest mismatch")
        self.assertFalse(os.path.exists(self.side_path(fx)))

    def test_corrupt_side_is_warning_only_for_nonterminal_and_no_phase4_runs(self):
        cases = (
            ({}, [], "ref-invalid"),
            ({}, [], "not-active"),
        )
        for config, findings, state in cases:
            with self.subTest(state=state):
                fx = RunFixture(self, config_extra=config)
                write(self.side_path(fx), "{broken")
                self.prepare(fx, self.RUNIDS[0], findings, mode="incremental", state=state)
                proc = fx.gate()
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                result = json.loads(proc.stdout)
                self.assertEqual(result["verdict"], "CONSISTENT")
                self.assertTrue(any(item.startswith("refusedPhase4Ignored: ")
                                    for item in result["warnings"]))
                self.assertFalse(any(item.startswith("previousRunRefused: ")
                                     for item in result["warnings"]))
                self.assertEqual(result["counts"]["phase4FlipsUnchangedContent"], 0)

        fx = RunFixture(self)
        write(self.side_path(fx), "{broken")
        self.assertEqual(fx.open(self.RUNIDS[0]).returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(fx.complete(verdicts={}).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_each_invalid_side_is_ignored_by_gate_without_affecting_flip(self):
        cases = {
            "sha": record(),
            "shape": [],
            "meaning": dict(record(), reason="other"),
            "counts-unadjudicated-zero": dict(
                record(), claimCounts={"targets": 1, "unadjudicated": 0}),
            "counts-unadjudicated-over-targets": dict(
                record(), claimCounts={"targets": 1, "unadjudicated": 2}),
            "counts-targets-zero": dict(
                record(), claimCounts={"targets": 0, "unadjudicated": 1}),
            "same-run": record(runid=self.RUNIDS[0]),
            "history": record(history_sha="sha256:" + "2" * 64),
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
                raw = (json.dumps(value, sort_keys=True) + "\n").encode()
                write(self.side_path(fx), raw)
                self.prepare(fx, self.RUNIDS[0], [])
                if name == "sha":
                    write(self.side_path(fx), raw + b" ")
                proc = fx.gate()
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                result = json.loads(proc.stdout)
                self.assertEqual(result["verdict"], "CONSISTENT")
                self.assertEqual(result["counts"]["phase4FlipsUnchangedContent"], 0)
                self.assertTrue(any(item.startswith("refusedPhase4Ignored: ")
                                    for item in result["warnings"]))
                if name.startswith("counts-"):
                    self.assertIn("refusedPhase4Ignored: claimCounts is invalid",
                                  result["warnings"])
                self.assertFalse(any(item.startswith("previousRunRefused: ")
                                     for item in result["warnings"]))

    def test_absent_side_adds_no_warning(self):
        fx = RunFixture(self, config_extra={"codexReview": {"required": True}})
        self.prepare(fx, self.RUNIDS[0], [])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        warnings = json.loads(proc.stdout).get("warnings", [])
        self.assertFalse(any("refusedPhase4" in item or "previousRunRefused" in item
                             for item in warnings))

    def test_write_and_clear_failures_are_stdout_only(self):
        report_config = {
            "codexReview": {"required": True},
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md",
        }
        fx = RunFixture(self, config_extra=report_config)
        self.prepare(fx, self.RUNIDS[0], [finding()])
        self.assertEqual(fx.write_template(
            body=fx.report_template() + "codexClaims: {{GATE_CODEX_CLAIMS}}\n"
        ).returncode, 0)
        module = self.load_decide()
        real_atomic = module.atomic
        atomic_paths = []

        def fail_side(path, value):
            atomic_paths.append(path)
            if path.endswith("/docaudit-refused-phase4.json"):
                raise OSError("injected side write failure")
            return real_atomic(path, value)

        code, result = self.run_main(
            module, fx, mock.patch.object(module, "atomic", side_effect=fail_side))
        self.assertEqual(code, 3)
        self.assertIn("refusedPhase4WriteFailed", result["warnings"], atomic_paths)
        report = Path(fx.repo, result["reportPath"]).read_text()
        self.assertNotIn("refusedPhase4WriteFailed", report)

        fx = RunFixture(self, config_extra=report_config)
        write(self.side_path(fx), (json.dumps(record()) + "\n"))
        self.prepare(fx, self.RUNIDS[1], [])
        self.assertEqual(fx.write_template(
            body=fx.report_template() + "codexClaims: {{GATE_CODEX_CLAIMS}}\n"
        ).returncode, 0)
        module = self.load_decide()
        real_unlink = module.os.unlink

        def fail_clear(path):
            if os.fspath(path).endswith("/docaudit-refused-phase4.json"):
                raise OSError("injected side clear failure")
            return real_unlink(path)

        code, result = self.run_main(
            module, fx, mock.patch.object(module.os, "unlink", side_effect=fail_clear))
        self.assertEqual(code, 0)
        self.assertIn("refusedPhase4ClearFailed", result["warnings"])
        report = Path(fx.repo, result["reportPath"]).read_text()
        self.assertNotIn("refusedPhase4ClearFailed", report)
        self.assertTrue(os.path.exists(self.side_path(fx)))
        self.prepare(fx, self.RUNIDS[2], [])
        self.assertEqual(fx.write_template(
            body=fx.report_template() + "codexClaims: {{GATE_CODEX_CLAIMS}}\n"
        ).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        next_result = json.loads(proc.stdout)
        self.assertTrue(any(item.startswith("refusedPhase4Ignored: ")
                            for item in next_result["warnings"]))
        self.assertFalse(any(item.startswith("previousRunRefused: ")
                             for item in next_result["warnings"]))

    def test_clear_failure_can_reuse_side_when_history_bytes_do_not_change(self):
        fx = RunFixture(self)
        history_raw = (json.dumps(
            {"entries": [], "phase4Runs": []}, ensure_ascii=False,
            sort_keys=True, indent=2) + "\n").encode()
        write(fx.history, history_raw)
        write(self.side_path(fx), json.dumps(
            record(history_sha=sha(history_raw)), sort_keys=True) + "\n")
        self.assertEqual(fx.open(self.RUNIDS[1]).returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(fx.complete(verdicts={}).returncode, 0)
        module = self.load_decide()
        real_unlink = module.os.unlink

        def fail_clear(path):
            if os.fspath(path).endswith("/docaudit-refused-phase4.json"):
                raise OSError("injected side clear failure")
            return real_unlink(path)

        code, result = self.run_main(
            module, fx, mock.patch.object(module.os, "unlink", side_effect=fail_clear))
        self.assertEqual(code, 0)
        self.assertIn("refusedPhase4ClearFailed", result["warnings"])
        self.assertEqual(Path(fx.history).read_bytes(), history_raw)

        self.assertEqual(fx.open(self.RUNIDS[2]).returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        self.assertEqual(fx.complete(verdicts={}).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(any(item.startswith("previousRunRefused: ")
                            for item in json.loads(proc.stdout)["warnings"]))

    def test_side_file_is_a_builtin_digest_exclusion_and_schema_is_documented(self):
        source = Path(SCRIPTS, "start-run.py").read_text()
        self.assertIn('".claude/state/docaudit-refused-phase4.json"', source)
        schema = Path(ROOT, "skills", "audit", "references", "config-schema.md").read_text()
        self.assertIn(".claude/state/docaudit-refused-phase4.json", schema)

    def test_open_run_side_reader_contract(self):
        for name in ("symlink", "fifo", "oversize"):
            with self.subTest(name=name):
                fx = RunFixture(self)
                side = self.side_path(fx)
                os.makedirs(os.path.dirname(side), exist_ok=True)
                if name == "symlink":
                    target = side + ".target"
                    write(target, "{}")
                    os.symlink(target, side)
                elif name == "fifo":
                    os.mkfifo(side)
                else:
                    write(side, b"x" * (refused_phase4.MAX_RECORD_BYTES + 1))
                proc = fx.open(self.RUNIDS[0])
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["refusedPhase4"], "none")
                self.assertIn("refusedPhase4 ignored", proc.stderr)

        fx = RunFixture(self)
        side = self.side_path(fx)
        raw = b"x" * refused_phase4.MAX_RECORD_BYTES
        write(side, raw)
        proc = fx.open(self.RUNIDS[0])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["refusedPhase4"], sha(raw))


if __name__ == "__main__":
    unittest.main()
