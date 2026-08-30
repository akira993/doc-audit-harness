"""Run lifecycle tests for the v0.10 run ledger contract."""

import hashlib
import json
import os
import unittest

from tests.wp12_helpers import RunFixture, git, write


class TestStartRun(unittest.TestCase):
    def plan_only(self, fx, impact):
        impact_path = os.path.join(fx.run_dir, "impact.json")
        write(impact_path, json.dumps(impact) + "\n")
        proc = fx.call(
            "plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--config", fx.config_path,
            "--history", fx.history, "--impact-json", impact_path,
            "--baseline-sha", fx.head, "--mode", "incremental",
            "--contract-version", "0.10.0", "--evidence", json.dumps(fx.evidence),
            "--expect-config-sha", fx.evidence["config"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        fx.evidence = json.loads(proc.stdout)
        return impact_path

    def start_only(self, fx, impact_path):
        return fx.call(
            "start-run.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--impact-json", impact_path,
            "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
            "--run-class", "standard", "--mode", "incremental",
            "--config", fx.config_path, "--expect-config-sha", fx.evidence["config"],
            "--evidence", json.dumps(fx.evidence))

    def configure_scope(self, fx, metadata=None):
        scope_rel = ".claude/audit-scope.json"
        scope_raw = b'{"src/**/*.py":["docs/a.md"]}\n'
        write(os.path.join(fx.repo, scope_rel), scope_raw)
        base = {"path": scope_rel, "sha256": hashlib.sha256(scope_raw).hexdigest(),
                "rules": 1, "importedAt": "2026-08-27T00:00:00Z"}
        if metadata:
            base.update(metadata)
        fx.config["auditScope"] = base
        write(fx.config_path, json.dumps(fx.config, indent=2) + "\n")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-m", "configure audit scope")
        fx.head = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        return scope_rel, scope_raw

    def test_phase3_backend_defaults_to_workflow_without_codex_timeout(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["phase3Backend"], "workflow")
        self.assertNotIn("phase3CodexTimeoutSeconds", manifest)

    def test_explicit_workflow_does_not_seal_codex_timeout(self):
        fx = RunFixture(self, config_extra={"phase3Backend": "workflow",
                                             "phase3CodexTimeoutSeconds": 900})
        self.assertEqual(fx.open().returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["phase3Backend"], "workflow")
        self.assertNotIn("phase3CodexTimeoutSeconds", manifest)

    def test_codex_backend_seals_default_and_explicit_timeout(self):
        for configured, expected in ((None, 600), (60, 60), (3600, 3600)):
            with self.subTest(timeout=configured):
                extra = {"phase3Backend": "codex"}
                if configured is not None:
                    extra["phase3CodexTimeoutSeconds"] = configured
                fx = RunFixture(self, config_extra=extra)
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal()
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
                    manifest = json.load(handle)
                self.assertEqual(manifest["phase3Backend"], "codex")
                self.assertEqual(manifest["phase3CodexTimeoutSeconds"], expected)

    def test_invalid_phase3_backend_is_rejected_at_start_run(self):
        for value in ("other", "", True, 1, None, []):
            with self.subTest(value=value):
                fx = RunFixture(self, config_extra={"phase3Backend": value})
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("phase3Backend", proc.stderr)

    def test_invalid_phase3_codex_timeout_is_rejected_at_start_run(self):
        for value in (59, 3601, True, 60.0, "600", None):
            with self.subTest(value=value):
                fx = RunFixture(self, config_extra={"phase3Backend": "codex",
                                                     "phase3CodexTimeoutSeconds": value})
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("phase3CodexTimeoutSeconds", proc.stderr)
        fx = RunFixture(self, config_extra={"phase3Backend": "workflow",
                                             "phase3CodexTimeoutSeconds": 59})
        self.assertEqual(fx.open().returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("phase3CodexTimeoutSeconds", proc.stderr)

    def test_manifest_has_complete_contract_and_preserves_verdict_directory(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        marker = os.path.join(fx.run_dir, "verdicts", "keep.txt")
        write(marker, "keep")
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        for field in ("runid", "head", "mode", "baselineSha", "changedSet",
                      "changeSetSha", "impacted", "dispatch", "cached", "runClass",
                      "phase4Required", "preflightRequired", "contractVersion",
                      "digestExclude", "sealed", "worktreeDigest", "reportDate",
                      "reportCandidateRule", "provenance", "auditScopeSha"):
            self.assertIn(field, manifest)
        self.assertTrue(manifest["sealed"])
        self.assertEqual(manifest["provenance"], {
            "docs/a.md": "mapped", "docs/b.md": "mapped"})
        self.assertIsNone(manifest["auditScopeSha"])
        self.assertTrue(os.path.exists(marker))

    def test_impact_provenance_change_after_plan_dispatch_is_rejected(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        impact_path = self.plan_only(fx, {
            "impacted": [{"path": "docs/a.md", "provenance": "mapped"}]})
        write(impact_path, json.dumps({
            "impacted": [{"path": "docs/a.md", "provenance": "heuristic"}]}) + "\n")
        proc = self.start_only(fx, impact_path)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("impact.json changed after plan-dispatch", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(fx.run_dir, "manifest.json")))

    def test_dispatch_without_impact_sha_is_rejected(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        impact_path = self.plan_only(fx, {
            "impacted": [{"path": "docs/a.md", "provenance": "mapped"}]})
        dispatch_path = os.path.join(fx.run_dir, "dispatch.json")
        with open(dispatch_path, encoding="utf-8") as handle:
            dispatch = json.load(handle)
        dispatch.pop("impactSha")
        raw = (json.dumps(dispatch, ensure_ascii=False, sort_keys=True, indent=2)
               + "\n").encode("utf-8")
        write(dispatch_path, raw)
        fx.evidence["dispatch"] = "sha256:" + hashlib.sha256(raw).hexdigest()
        proc = self.start_only(fx, impact_path)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("impactSha", proc.stderr)

    def test_unknown_impact_provenance_is_rejected(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        impact_path = self.plan_only(fx, {
            "impacted": [{"path": "docs/a.md", "provenance": "unknown"}]})
        proc = self.start_only(fx, impact_path)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("invalid impact provenance", proc.stderr)

    def test_valid_audit_scope_sha_and_provenance_are_sealed(self):
        fx = RunFixture(self)
        _scope_rel, scope_raw = self.configure_scope(fx)
        self.assertEqual(fx.open().returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["auditScopeSha"],
                         "sha256:" + hashlib.sha256(scope_raw).hexdigest())
        with open(os.path.join(fx.run_dir, "impact.json"), encoding="utf-8") as handle:
            impact = json.load(handle)
        self.assertEqual(manifest["provenance"], {
            entry["path"]: entry["provenance"] for entry in impact["impacted"]})

    def test_audit_scope_sha_drift_is_rejected(self):
        fx = RunFixture(self)
        scope_rel, _scope_raw = self.configure_scope(fx)
        self.assertEqual(fx.open().returncode, 0)
        write(os.path.join(fx.repo, scope_rel), b'{"changed":[]}\n')
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("audit-scope drift", proc.stderr)

    def test_audit_scope_metadata_type_contract_is_rejected(self):
        cases = (
            ({"path": None}, "auditScope.path invalid"),
            ({"path": "../scope.json"}, "auditScope.path invalid"),
            ({"sha256": "bad"}, "auditScope.sha256 invalid"),
            ({"rules": True}, "auditScope.rules invalid"),
            ({"rules": -1}, "auditScope.rules invalid"),
            ({"rules": 1.0}, "auditScope.rules invalid"),
            ({"importedAt": None}, "auditScope.importedAt invalid"),
        )
        for metadata, reason in cases:
            with self.subTest(metadata=metadata):
                fx = RunFixture(self)
                self.configure_scope(fx, metadata)
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn(reason, proc.stderr)

        for value in (None, [], "scope"):
            with self.subTest(value=value):
                fx = RunFixture(self, config_extra={"auditScope": value})
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal()
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("auditScope must be an object", proc.stderr)

    def test_report_date_and_explicit_suffix_rule_are_sealed_from_runid_utc(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs/audit_<YYYY-MM-DD>_final[_NN].md"})
        self.assertEqual(fx.open(runid="20261231T235959Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["reportDate"], "2026-12-31")
        self.assertEqual(manifest["reportCandidateRule"], {
            "base": "docs/logs/audit_2026-12-31_final.md",
            "suffixPrefix": "docs/logs/audit_2026-12-31_final",
            "suffixSuffix": ".md", "suffixStart": 2})

    def test_implicit_suffix_is_inserted_immediately_after_utc_date(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs/audit_<YYYY-MM-DD>_final.md"})
        self.assertEqual(fx.open(runid="20270101T000000Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            rule = json.load(handle)["reportCandidateRule"]
        self.assertEqual(rule["base"], "docs/logs/audit_2027-01-01_final.md")
        self.assertEqual(rule["suffixPrefix"], "docs/logs/audit_2027-01-01")
        self.assertEqual(rule["suffixSuffix"], "_final.md")

    def test_implicit_suffix_uses_marker_when_same_date_appears_earlier(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/2026-08-18/audit_<YYYY-MM-DD>.md"})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            rule = json.load(handle)["reportCandidateRule"]
        self.assertEqual(rule["base"], "docs/2026-08-18/audit_2026-08-18.md")
        self.assertEqual(rule["suffixPrefix"],
                         "docs/2026-08-18/audit_2026-08-18")
        self.assertEqual(rule["suffixSuffix"], ".md")

    def test_explicit_suffix_directory_position_is_preserved(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs[_NN]/audit_<YYYY-MM-DD>.md"})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            rule = json.load(handle)["reportCandidateRule"]
        self.assertEqual(rule["base"], "docs/logs/audit_2026-08-18.md")
        self.assertEqual(rule["suffixPrefix"], "docs/logs")
        self.assertEqual(rule["suffixSuffix"], "/audit_2026-08-18.md")

    def test_invalid_calendar_runid_is_rejected_before_manifest_write(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open(runid="20260230T120000Z-abcdef12").returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("invalid UTC calendar", proc.stderr)

    def test_invalid_report_candidate_pattern_is_rejected(self):
        fx = RunFixture(self, config_extra={"reportPath": "docs/logs/audit.md"})
        self.assertEqual(fx.open().returncode, 0)
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("reportPath", proc.stderr)

    def test_full_uses_head_as_baseline(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(mode="full")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["baselineSha"], fx.head)
        self.assertEqual(manifest["mode"], "full")

    def test_full_rejects_empty_impact_when_corpus_exists(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(impacted=[], mode="full")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("full mode requires impacted", proc.stderr)

    def test_report_only_full_corpus_is_empty_by_default(self):
        report = "docs/logs/doc_audit_2026-08-25_02.md"
        config = {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
        fx = RunFixture(self, docs=(report,), config_extra=config)
        fx.open()
        proc = fx.plan_start_seal(impacted=[], mode="full")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertTrue(manifest["emptyCorpus"])
        self.assertEqual(manifest["impacted"], [])

    def test_report_corpus_opt_in_true_only_restores_nonempty_corpus(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        base = {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
        values = ((True, 2), ("true", 0), (1, 0), ([], 0))
        for value, expected_returncode in values:
            with self.subTest(value=value):
                fx = RunFixture(self, docs=(report,),
                                config_extra=dict(base, auditReportsInCorpus=value))
                fx.open()
                proc = fx.plan_start_seal(impacted=[], mode="full")
                self.assertEqual(proc.returncode, expected_returncode, proc.stdout + proc.stderr)
                if expected_returncode:
                    self.assertIn("full mode requires impacted", proc.stderr)

    def test_policy_document_keeps_full_corpus_nonempty(self):
        docs = ("docs/logs/doc_audit_2026-08-25.md", "docs/logs/doc_audit_policy.md")
        fx = RunFixture(self, docs=docs, config_extra={
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"})
        fx.open()
        proc = fx.plan_start_seal(impacted=[], mode="full")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("full mode requires impacted", proc.stderr)

    def test_manifest_uses_default_doc_globs_and_excludes_claude_worktrees(self):
        fx = RunFixture(self)
        fx.config.pop("docGlobs")
        write(fx.config_path, json.dumps(fx.config, indent=2) + "\n")
        git(fx.repo, "add", fx.config_path)
        git(fx.repo, "commit", "-m", "use default document globs")
        fx.head = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        fx.open()
        proc = fx.plan_start_seal()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["docGlobs"], ["docs/**/*.md", "*.md"])
        self.assertIn(".claude/worktrees", manifest["digestExclude"])

    def test_preflight_requires_phase4_even_when_incremental_impact_is_empty(self):
        fx = RunFixture(self, config_extra={"harness": {"state": "integrated"}})
        fx.open()
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertTrue(manifest["preflightRequired"])
        self.assertTrue(manifest["phase4Required"])
        fx.write_evidence("preflight", {"state": "integrated", "findings": [],
                                         "userDecision": None, "parsed": True})
        fx.write_evidence("returns", [])
        fx.evidence["phase4"] = "none"
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("phase4=none", json.loads(proc.stdout)["reason"])

    def test_open_rejects_invalid_runid(self):
        fx = RunFixture(self)
        proc = fx.open(runid="../escape")
        self.assertEqual(proc.returncode, 2)

    def test_start_rejects_unsafe_impacted_path(self):
        fx = RunFixture(self)
        fx.open()
        proc = fx.plan_start_seal(impacted=["../outside.md"])
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(proc.stderr)

    def test_seal_detects_new_path_after_dispatch(self):
        fx = RunFixture(self)
        fx.open()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        write(impact_path, json.dumps({
            "impacted": [{"path": "docs/a.md", "provenance": "mapped"}]}) + "\n")
        proc = fx.call("plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
                       "--repo-root", fx.repo, "--config", fx.config_path,
                       "--history", fx.history, "--impact-json", impact_path,
                       "--baseline-sha", fx.head, "--mode", "incremental",
                       "--contract-version", "0.10.0", "--evidence", json.dumps(fx.evidence),
                       "--expect-config-sha", fx.evidence["config"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        fx.evidence = json.loads(proc.stdout)
        proc = fx.call("start-run.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
                       "--repo-root", fx.repo, "--impact-json", impact_path,
                       "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
                       "--run-class", "standard", "--mode", "incremental",
                       "--config", fx.config_path, "--expect-config-sha", fx.evidence["config"],
                       "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        fx.evidence = json.loads(proc.stdout)
        write(os.path.join(fx.repo, "new.py"), "new\n")
        proc = fx.call("seal-run.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                       "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["reason"], "change-set-drift")


class TestCodexRequiredPhase4(unittest.TestCase):
    def test_required_forces_phase4_with_no_impacted_documents_in_both_modes(self):
        for mode in ("incremental", "full"):
            with self.subTest(mode=mode):
                fx = RunFixture(self, docs=(),
                                config_extra={"codexReview": {"required": True}})
                self.assertEqual(fx.open().returncode, 0)
                proc = fx.plan_start_seal(impacted=[], mode=mode)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                with open(os.path.join(fx.run_dir, "manifest.json"),
                          encoding="utf-8") as handle:
                    manifest = json.load(handle)
                self.assertTrue(manifest["phase4Required"])

    def test_non_object_codex_review_preserves_optional_phase4_behavior(self):
        for value in ([], "x"):
            for mode, expected in (("incremental", False), ("full", True)):
                with self.subTest(codexReview=value, mode=mode):
                    fx = RunFixture(self, docs=(), config_extra={"codexReview": value})
                    self.assertEqual(fx.open().returncode, 0)
                    proc = fx.plan_start_seal(impacted=[], mode=mode)
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    with open(os.path.join(fx.run_dir, "manifest.json"),
                              encoding="utf-8") as handle:
                        manifest = json.load(handle)
                    self.assertIs(manifest["phase4Required"], expected)


class TestEndToEnd(unittest.TestCase):
    def test_incremental_empty_impact_is_consistent_and_advances_anchor(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal(impacted=[]).returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["mode"], "incremental")
        self.assertEqual(manifest["changedSet"], [])
        self.assertEqual(manifest["impacted"], [])
        self.assertFalse(manifest["phase4Required"])
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(fx.anchor, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["sha"], fx.head)

    def test_consistent_run_writes_compatible_anchor(self):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(fx.anchor, encoding="utf-8") as handle:
            anchor = json.load(handle)
        self.assertEqual(anchor["sha"], fx.head)
        self.assertEqual(anchor["head"], fx.head)
        self.assertFalse(os.path.exists(os.path.join(fx.run_base, "lock")))

    def test_failed_doc_yields_needs_fix_without_anchor(self):
        fx = RunFixture(self)
        fx.open(); fx.plan_start_seal()
        fx.complete({"docs/a.md": "FAIL", "docs/b.md": "PASS"})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "NEEDS_FIX")
        self.assertFalse(os.path.exists(fx.anchor))

    def test_empty_corpus_cold_start_is_consistent(self):
        fx = RunFixture(self, docs=())
        fx.open(); fx.plan_start_seal(impacted=[])
        fx.complete(verdicts={})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")


if __name__ == "__main__":
    unittest.main()
