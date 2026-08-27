import json
import fcntl
import os
import stat
import subprocess
import sys
import tempfile
import unittest

from tests.wp12_helpers import RunFixture, git, script, write


class TestOpenRun(unittest.TestCase):
    def test_initial_evidence_seeds_optional_sentinels(self):
        fx = RunFixture(self)
        proc = fx.open()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        evidence = json.loads(proc.stdout)
        self.assertEqual(evidence["preflight"], "none")
        self.assertEqual(evidence["phase4"], "none")

    def test_double_open_release_and_break(self):
        fx = RunFixture(self)
        first = fx.open()
        self.assertEqual(first.returncode, 0, first.stderr)
        second = fx.call("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                         "--runid", "20260818T120001Z-abcdef13")
        self.assertEqual(second.returncode, 4)
        wrong = fx.call("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                        "--release", "--runid", "20260818T120001Z-abcdef13")
        self.assertEqual(wrong.returncode, 4)
        self.assertTrue(os.path.exists(os.path.join(fx.run_base, "lock")))
        released = fx.call("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                           "--release", "--runid", fx.runid)
        self.assertEqual(released.returncode, 0)
        fx.open(runid="20260818T120002Z-abcdef14")
        broken = fx.call("open-run.py", "--run-base", fx.run_base, "--repo-root", fx.repo,
                         "--break-lock")
        self.assertEqual(broken.returncode, 0)
        self.assertTrue(json.loads(broken.stdout)["broken"])

    def test_break_is_refused_while_gate_style_flock_is_held(self):
        fx = RunFixture(self); fx.open()
        lock = os.path.join(fx.run_base, "lock")
        fd = os.open(lock, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            proc = fx.call("open-run.py", "--run-base", fx.run_base,
                           "--repo-root", fx.repo, "--break-lock")
            self.assertEqual(proc.returncode, 4)
        finally:
            os.close(fd)

    def test_previous_report_status_surfaces_only_recovery_states(self):
        for status, expected in (("pending", "pending"), ("failed", "failed"),
                                 ("written-durability-unknown", "written-durability-unknown"),
                                 ("written", None), ("not-requested", None)):
            with self.subTest(status=status):
                fx = RunFixture(self)
                write(fx.last_run, json.dumps({"reportStatus": status}) + "\n")
                proc = fx.open()
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout).get("previousReportStatus"), expected)


class TestEvidence(unittest.TestCase):
    def test_returns_schema_and_evidence_merge(self):
        fx = RunFixture(self)
        fx.open()
        original = dict(fx.evidence)
        value = [{"attempt": 1, "assignedPath": "docs/a.md", "returnedPath": None,
                  "verdict": None, "rationale": None, "suggestion": None}]
        proc = fx.write_evidence("returns", value)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for key in original:
            self.assertEqual(fx.evidence[key], original[key])
        self.assertEqual(fx.evidence["attempt"], 1)
        self.assertRegex(fx.evidence["returns"], r"^sha256:[0-9a-f]{64}$")

    def test_duplicate_and_out_of_range_returns_are_rejected(self):
        fx = RunFixture(self); fx.open()
        bad = [{"attempt": 0, "assignedPath": "docs/a.md", "returnedPath": None,
                "verdict": None, "rationale": None, "suggestion": None}]
        self.assertEqual(fx.write_evidence("returns", bad).returncode, 2)
        item = {"attempt": 1, "assignedPath": "docs/a.md", "returnedPath": None,
                "verdict": None, "rationale": None, "suggestion": None}
        self.assertEqual(fx.write_evidence("returns", [item, item]).returncode, 2)


class TestDispatchConfiguration(unittest.TestCase):
    def test_invalid_minimum_disables_cache_with_warning(self):
        for value in (0, 1, 11):
            with self.subTest(value=value):
                fx = RunFixture(self, config_extra={
                    "verdictCache": {"enabled": True, "minConsecutivePasses": value}})
                fx.open()
                self.assertEqual(fx.plan_start_seal().returncode, 0)
                with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
                    dispatch = json.load(handle)
                self.assertEqual(set(dispatch["dispatch"]), set(fx.docs))
                self.assertTrue(dispatch["warnings"])

    def test_full_alias_resolves_null_baseline_to_head_and_dispatches_all(self):
        fx = RunFixture(self)
        fx.open()
        impact_path = os.path.join(fx.run_dir, "impact.json")
        write(impact_path, json.dumps({"impacted": fx.docs}) + "\n")
        proc = fx.call(
            "plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--config", fx.config_path, "--history", fx.history,
            "--impact-json", impact_path, "--baseline-sha", "null", "--full",
            "--contract-version", "0.10.0", "--evidence", json.dumps(fx.evidence))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            dispatch = json.load(handle)
        self.assertEqual(dispatch["baselineSha"], fx.head)
        self.assertEqual(set(dispatch["dispatch"]), set(fx.docs))
        self.assertEqual(dispatch["cached"], [])


class TestChangeSet(unittest.TestCase):
    def call(self, fx, baseline=None):
        return subprocess.run(
            [sys.executable, script("change-set-sha.py"), "--repo-root", fx.repo,
             "--baseline-sha", baseline or fx.head, "--config", fx.config_path],
            capture_output=True, text=True)

    def test_delete_mode_symlink_and_report_exclusion(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md",
            "docGlobs": ["docs/**/*.md", "*.md"], "diffGlobs": ["docs/**", "src/**"]})
        os.unlink(os.path.join(fx.repo, "src", "app.py"))
        os.chmod(os.path.join(fx.repo, "docs", "a.md"), 0o755)
        os.symlink("a.md", os.path.join(fx.repo, "docs", "link.md"))
        write(os.path.join(fx.repo, "docs", "logs", "doc_audit_2026-08-18.md"), "report\n")
        proc = self.call(fx)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("src/app.py", out["changedSet"])
        self.assertIn("docs/a.md", out["changedSet"])
        self.assertIn("docs/link.md", out["changedSet"])
        self.assertNotIn("docs/logs/doc_audit_2026-08-18.md", out["changedSet"])
        other = self.call(fx, baseline="0" * 40)
        self.assertNotEqual(other.returncode, 0)

    def test_report_exclusion_is_exact_and_ignores_corpus_opt_in(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md",
            "auditReportsInCorpus": True,
            "docGlobs": ["docs/**/*.md", "*.md"]})
        report = "docs/logs/doc_audit_2026-08-18_02.md"
        policy = "docs/logs/doc_audit_policy.md"
        write(os.path.join(fx.repo, report), "report\n")
        write(os.path.join(fx.repo, policy), "policy\n")
        out = json.loads(self.call(fx).stdout)
        self.assertNotIn(report, out["changedSet"])
        self.assertIn(policy, out["changedSet"])

    def test_baseline_is_part_of_digest(self):
        fx = RunFixture(self)
        first = json.loads(self.call(fx).stdout)["changeSetSha"]
        write(os.path.join(fx.repo, "second.txt"), "x\n")
        git(fx.repo, "add", "-A"); git(fx.repo, "commit", "-m", "second")
        second_head = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        second = json.loads(self.call(fx, second_head).stdout)["changeSetSha"]
        self.assertNotEqual(first, second)

    def test_report_without_filename_prefix_is_not_excluded(self):
        fx = RunFixture(self, config_extra={
            "reportPath": "docs/<YYYY-MM-DD>.md",
            "docGlobs": ["docs/**/*.md", "*.md"]})
        write(os.path.join(fx.repo, "docs", "2026-08-18.md"), "report\n")
        proc = self.call(fx)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("docs/2026-08-18.md", json.loads(proc.stdout)["changedSet"])

    def test_claude_worktrees_are_always_excluded(self):
        fx = RunFixture(self)
        write(os.path.join(fx.repo, ".claude", "worktrees", "agent", "copy.py"), "copy\n")
        proc = self.call(fx)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(".claude/worktrees/agent/copy.py",
                         json.loads(proc.stdout)["changedSet"])

    def test_untracked_probe_outputs_are_always_excluded(self):
        fx = RunFixture(self)
        before = json.loads(self.call(fx).stdout)["changeSetSha"]
        for root in (".mdq", ".codegraph", "graphify-out", ".cocoindex_code"):
            write(os.path.join(fx.repo, root, "x"), "generated\n")
        proc = self.call(fx)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        changed = out["changedSet"]
        self.assertEqual(out["changeSetSha"], before)
        self.assertFalse(any(path.startswith("graphify-out/") for path in changed))
        self.assertFalse(any(path.split("/", 1)[0] in {
            ".mdq", ".codegraph", "graphify-out", ".cocoindex_code"} for path in changed))

    def test_dirty_submodule_changes_digest_without_submodule_commit(self):
        fx = RunFixture(self)
        source = tempfile.TemporaryDirectory()
        self.addCleanup(source.cleanup)
        git(source.name, "init", "-b", "main")
        git(source.name, "config", "user.email", "t@example.test")
        git(source.name, "config", "user.name", "Test")
        write(os.path.join(source.name, "tracked.txt"), "clean\n")
        git(source.name, "add", "-A"); git(source.name, "commit", "-m", "sub initial")
        added = subprocess.run(
            ["git", "-c", "protocol.file.allow=always", "-C", fx.repo,
             "submodule", "add", source.name, "vendor/sub"],
            capture_output=True, text=True)
        self.assertEqual(added.returncode, 0, added.stdout + added.stderr)
        git(fx.repo, "add", "-A"); git(fx.repo, "commit", "-m", "add submodule")
        baseline = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        clean = json.loads(self.call(fx, baseline).stdout)["changeSetSha"]
        write(os.path.join(fx.repo, "vendor", "sub", "tracked.txt"), "dirty\n")
        dirty = self.call(fx, baseline)
        self.assertEqual(dirty.returncode, 0, dirty.stderr)
        value = json.loads(dirty.stdout)
        self.assertIn("vendor/sub", value["changedSet"])
        self.assertNotEqual(value["changeSetSha"], clean)


class TestImpactAndClassification(unittest.TestCase):
    def test_full_impact_ignores_cap_and_drops_unsafe_mapping(self):
        fx = RunFixture(self, config_extra={"maxImpactedDocs": 1,
            "impactMap": [{"changed": "src/**", "impacts": ["../outside.md"]}]})
        changed = os.path.join(fx.repo, "changed.txt")
        write(changed, "src/app.py\n")
        proc = subprocess.run([sys.executable, script("resolve-impact.py"),
                               "--config", fx.config_path, "--changed", changed,
                               "--repo-root", fx.repo, "--mode", "full"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(len(out["impacted"]), 2)
        self.assertTrue(all(item["provenance"] == "full" for item in out["impacted"]))
        self.assertFalse(out["truncated"])

    def test_unsafe_mapped_and_symlink_docs_are_dropped_with_warnings(self):
        fx = RunFixture(self, config_extra={
            "impactMap": [{"changed": "src/**", "impacts": ["../outside.md"]}]})
        outside = tempfile.NamedTemporaryFile()
        self.addCleanup(outside.close)
        os.symlink(outside.name, os.path.join(fx.repo, "docs", "outside.md"))
        changed = os.path.join(fx.repo, "changed.txt")
        write(changed, "src/app.py\n")
        proc = subprocess.run([sys.executable, script("resolve-impact.py"),
                               "--config", fx.config_path, "--changed", changed,
                               "--repo-root", fx.repo, "--mode", "incremental"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertNotIn("../outside.md", [item["path"] for item in out["impacted"]])
        self.assertNotIn("docs/outside.md", [item["path"] for item in out["impacted"]])
        self.assertTrue(any("unsafe" in warning for warning in out["warnings"]))

    def classify(self, fx, mode="incremental", last=None, baseline=None):
        impact = os.path.join(fx.repo, "impact.json")
        write(impact, json.dumps({"impacted": [{"path": "docs/a.md"}]}) + "\n")
        args = [sys.executable, script("classify-run.py"), "--repo-root", fx.repo,
                "--config", fx.config_path, "--impact-json", impact,
                "--baseline-sha", baseline or fx.head, "--mode", mode]
        if last: args += ["--last-run", last]
        return subprocess.run(args, capture_output=True, text=True)

    def test_sensitive_filename_full_and_last_run_boundaries(self):
        fx = RunFixture(self)
        write(os.path.join(fx.repo, "src", "ordinary.py"), "one\ntwo\n")
        self.assertEqual(json.loads(self.classify(fx).stdout)["runClass"], "light")
        write(os.path.join(fx.repo, "src", "auth.py"), "x\n")
        out = json.loads(self.classify(fx).stdout)
        self.assertEqual(out["runClass"], "standard")
        self.assertIn("src/auth.py", out["sensitivePaths"])
        full = self.classify(fx, mode="full", baseline="null")
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertEqual(json.loads(full.stdout)["runClass"], "standard")
        last = os.path.join(fx.repo, "last.json")
        write(last, json.dumps({"verdict": "NEEDS_FIX"}))
        self.assertIn("last-run", json.loads(self.classify(fx, last=last).stdout)["reasons"])

    def test_untracked_diff_line_and_byte_limits_are_inclusive_boundaries(self):
        fx = RunFixture(self, config_extra={"models": {"light": {
            "maxChanged": 10, "maxImpacted": 15, "maxDiffLines": 0,
            "maxDiffBytes": 1, "sensitiveTokens": []}}})
        write(os.path.join(fx.repo, "src", "ordinary.py"), "two bytes\n")
        out = json.loads(self.classify(fx).stdout)
        self.assertEqual(out["runClass"], "standard")
        self.assertIn("diff-lines", out["reasons"])
        self.assertIn("diff-bytes", out["reasons"])

    def test_deleted_file_uses_old_blob_size_for_diff_bytes(self):
        fx = RunFixture(self, config_extra={"models": {"light": {
            "maxChanged": 10, "maxImpacted": 15, "maxDiffLines": 200,
            "maxDiffBytes": 0, "sensitiveTokens": []}}})
        old_size = int(git(fx.repo, "cat-file", "-s", f"{fx.head}:src/app.py").stdout.strip())
        os.unlink(os.path.join(fx.repo, "src", "app.py"))
        impact = os.path.join(fx.repo, ".claude", "state", "classification-impact.json")
        write(impact, json.dumps({"impacted": []}) + "\n")
        proc = subprocess.run(
            [sys.executable, script("classify-run.py"), "--repo-root", fx.repo,
             "--config", fx.config_path, "--impact-json", impact,
             "--baseline-sha", fx.head, "--mode", "incremental"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["diffBytes"], old_size)
        self.assertIn("diff-bytes", out["reasons"])

    def test_retired_exclude_globs_cannot_shrink_changed_set(self):
        fx = RunFixture(self, config_extra={"models": {"light": {
            "maxChanged": 1, "maxImpacted": 15, "maxDiffLines": 200,
            "maxDiffBytes": 65536, "sensitiveTokens": [],
            "excludeGlobs": ["src/**"]}}})
        write(os.path.join(fx.repo, "src", "ordinary.py"), "changed\n")
        out = json.loads(self.classify(fx).stdout)
        self.assertEqual(out["changedCount"], 2)
        self.assertEqual(out["runClass"], "standard")
        self.assertIn("changed-count", out["reasons"])


class TestRegressionSealedChainIntegration(unittest.TestCase):
    @staticmethod
    def history_entry(path, runid):
        return {"runid": runid, "path": path, "contentSha": "sha256:old-content",
                "changeSetSha": "sha256:old-change", "contractVersion": "0.10.0",
                "backend": "workflow", "verdict": "FAIL", "ts": "2026-08-17T00:00:00Z"}

    def run_chain(self, fx, changed):
        impact_path = os.path.join(fx.run_dir, "impact.json")
        resolved = fx.call(
            "resolve-impact.py", "--config", fx.config_path, "--changed", "-",
            "--repo-root", fx.repo, "--mode", "incremental", "--history", fx.history,
            input_text="\n".join(changed) + "\n")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        write(impact_path, resolved.stdout)

        supplemented = fx.call(
            "impact-supplement.py", "--impact-json", impact_path, "--changed", "-",
            "--change-summary", "S4a integration", "--repo-root", fx.repo,
            "--max-impacted-docs", str(fx.config["maxImpactedDocs"]),
            "--doc-globs", ",".join(fx.config["docGlobs"]), "--config", fx.config_path,
            input_text="\n".join(changed) + "\n")
        self.assertEqual(supplemented.returncode, 0, supplemented.stderr)

        planned = fx.call(
            "plan-dispatch.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--config", fx.config_path, "--history", fx.history,
            "--impact-json", impact_path, "--baseline-sha", fx.head,
            "--mode", "incremental", "--contract-version", "0.10.0",
            "--evidence", json.dumps(fx.evidence))
        self.assertEqual(planned.returncode, 0, planned.stderr)
        fx.evidence = json.loads(planned.stdout)

        started = fx.call(
            "start-run.py", "--run-dir", fx.run_dir, "--runid", fx.runid,
            "--repo-root", fx.repo, "--impact-json", impact_path,
            "--dispatch-json", os.path.join(fx.run_dir, "dispatch.json"),
            "--run-class", "standard", "--mode", "incremental",
            "--config", fx.config_path, "--evidence", json.dumps(fx.evidence))
        self.assertEqual(started.returncode, 0, started.stderr)
        fx.evidence = json.loads(started.stdout)

        sealed = fx.call("seal-run.py", "--run-dir", fx.run_dir,
                         "--repo-root", fx.repo, "--evidence", json.dumps(fx.evidence))
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        fx.evidence = json.loads(sealed.stdout)

        with open(impact_path, encoding="utf-8") as handle:
            impact = json.load(handle)
        with open(os.path.join(fx.run_dir, "dispatch.json"), encoding="utf-8") as handle:
            dispatch = json.load(handle)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        for path in manifest["impacted"]:
            verdict = fx.write_verdict(path, "PASS")
            self.assertEqual(verdict.returncode, 0, verdict.stderr)
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "PASS", "rationale": "checked", "suggestion": None}
                   for path in manifest["dispatch"]]
        written = fx.write_evidence("returns", returns)
        self.assertEqual(written.returncode, 0, written.stderr)
        if manifest["phase4Required"]:
            phase4 = fx.write_evidence("phase4", {"findings": []})
            self.assertEqual(phase4.returncode, 0, phase4.stderr)
        gated = fx.gate()
        self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)
        return impact, dispatch, manifest, json.loads(gated.stdout)

    def test_regression_document_traverses_the_complete_sealed_chain(self):
        fx = RunFixture(self, docs=("docs/regression.md",), config_extra={
            "regressionRecheck": {"enabled": True}})
        write(fx.history, json.dumps({"entries": [
            self.history_entry("docs/regression.md", "old-run")]} ) + "\n")
        self.assertEqual(fx.open().returncode, 0)

        impact, dispatch, manifest, gate = self.run_chain(fx, ["src/unrelated.py"])

        expected = {"docs/regression.md": "regression"}
        self.assertEqual({item["path"]: item["provenance"]
                          for item in impact["impacted"]}, expected)
        self.assertEqual(dispatch["dispatch"], ["docs/regression.md"])
        self.assertEqual(dispatch["cached"], [])
        self.assertEqual(manifest["provenance"], expected)
        self.assertEqual(gate["verdict"], "CONSISTENT")

    def test_cap_keeps_mapped_before_regression_before_heuristic_end_to_end(self):
        docs = ("docs/m1.md", "docs/m2.md", "docs/r1.md", "docs/r2.md",
                "docs/h1.md", "docs/h2.md")
        fx = RunFixture(self, docs=docs, config_extra={
            "maxImpactedDocs": 3,
            "regressionRecheck": {"enabled": True},
            "impactMap": [{"changed": "src/change.py",
                           "impacts": ["docs/m1.md", "docs/m2.md"]}],
        })
        for path in ("docs/h1.md", "docs/h2.md"):
            write(os.path.join(fx.repo, path), "signal_token\n")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-m", "prepare integration corpus")
        fx.head = git(fx.repo, "rev-parse", "HEAD").stdout.strip()
        write(fx.history, json.dumps({"entries": [
            self.history_entry("docs/r1.md", "old-r1"),
            self.history_entry("docs/r2.md", "old-r2"),
        ]}) + "\n")
        self.assertEqual(fx.open().returncode, 0)

        impact, dispatch, manifest, gate = self.run_chain(
            fx, ["src/change.py", "src/signal_token.py"])

        self.assertEqual(impact["counts"]["candidatesBeforeCap"], 6)
        self.assertEqual([item["provenance"] for item in impact["impacted"]],
                         ["mapped", "mapped", "regression"])
        self.assertTrue(impact["truncated"])
        self.assertEqual(impact["counts"]["mapped"], 2)
        self.assertEqual(impact["counts"]["regression"], 1)
        self.assertEqual(impact["counts"]["heuristicOnly"], 0)
        self.assertEqual(dispatch["cached"], [])
        self.assertEqual(set(dispatch["dispatch"]), set(manifest["impacted"]))
        self.assertEqual(manifest["provenance"], {
            item["path"]: item["provenance"] for item in impact["impacted"]})
        self.assertEqual(gate["verdict"], "CONSISTENT")


class TestFixScopeAndConfig(unittest.TestCase):
    def test_allow_deny_and_verify_outside_change(self):
        fx = RunFixture(self)
        write(os.path.join(fx.repo, "docs", "logs", "audit.md"), "protected\n")
        proc = subprocess.run([sys.executable, script("fix-scope.py"), "--repo-root", fx.repo,
                               "--config", fx.config_path, "--paths", "-"],
                              input="docs/a.md\ndocs/logs/audit.md\n", capture_output=True, text=True)
        out = json.loads(proc.stdout)
        self.assertEqual(out["allowed"], ["docs/a.md"])
        self.assertEqual(out["denied"][0]["path"], "docs/logs/audit.md")
        allowed = os.path.join(fx.repo, "allowed.json")
        snap = os.path.join(fx.repo, "snapshot.json")
        write(allowed, json.dumps({"allowed": out["allowed"]}))
        snapshot = subprocess.run([sys.executable, script("fix-scope.py"), "--repo-root", fx.repo,
                                   "--snapshot", "--allowed", allowed], capture_output=True, text=True)
        write(snap, snapshot.stdout)
        write(os.path.join(fx.repo, "src", "app.py"), "outside\n")
        verify = subprocess.run([sys.executable, script("fix-scope.py"), "--repo-root", fx.repo,
                                 "--verify", snap, "--allowed", allowed], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 3)
        self.assertIn("src/app.py", json.loads(verify.stdout)["outsideChanges"])

    def test_set_config_updates_multiple_keys_once(self):
        fx = RunFixture(self)
        write(fx.config_path, json.dumps({"zeta": 1, "harness": {"state": "unset"},
                                         "alpha": 2}, indent=2) + "\n")
        proc = subprocess.run([sys.executable, script("set-config-key.py"),
                               "--config", fx.config_path, "--set", 'harness={"state":"declined"}',
                               "--set", 'docAuditCommands={"format":"/check"}'],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(fx.config_path, encoding="utf-8") as handle:
            config = json.load(handle)
        self.assertEqual(config["harness"]["state"], "declined")
        self.assertEqual(config["docAuditCommands"]["format"], "/check")
        self.assertEqual(list(config), ["zeta", "harness", "alpha", "docAuditCommands"])

    def test_verify_detects_mode_change_outside_allowed_files(self):
        fx = RunFixture(self)
        allowed = os.path.join(fx.repo, "allowed.json")
        snapshot_path = os.path.join(fx.repo, ".claude", "state", "snapshot.json")
        write(allowed, json.dumps({"allowed": ["docs/a.md"]}))
        snapshot = subprocess.run(
            [sys.executable, script("fix-scope.py"), "--repo-root", fx.repo,
             "--snapshot", "--allowed", allowed], capture_output=True, text=True)
        self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
        write(snapshot_path, snapshot.stdout)
        outside = os.path.join(fx.repo, "src", "app.py")
        os.chmod(outside, os.stat(outside).st_mode | stat.S_IXUSR)
        verify = subprocess.run(
            [sys.executable, script("fix-scope.py"), "--repo-root", fx.repo,
             "--verify", snapshot_path, "--allowed", allowed],
            capture_output=True, text=True)
        self.assertEqual(verify.returncode, 3, verify.stdout + verify.stderr)
        self.assertIn("src/app.py", json.loads(verify.stdout)["outsideChanges"])


class TestSiblingScan(unittest.TestCase):
    def scan(self, returns):
        fx = RunFixture(self, docs=("docs/a.md",))
        self.assertEqual(fx.open().returncode, 0)
        write(os.path.join(fx.run_dir, "manifest.json"), json.dumps({
            "docGlobs": ["docs/**/*.md", "*.md"]}) + "\n")
        write(os.path.join(fx.run_dir, "returns.json"), json.dumps(returns) + "\n")
        proc = subprocess.run([sys.executable, script("sibling-scan.py"),
                               "--run-dir", fx.run_dir], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_pass_quotes_are_ignored_but_warn_quotes_are_scanned(self):
        out = self.scan([
            {"verdict": "PASS", "rationale": 'ignore "pass phrase"', "suggestion": None},
            {"verdict": "WARN", "rationale": 'check "warn phrase"',
             "suggestion": "also `code phrase`"},
        ])
        self.assertEqual(out["phrases"], ["code phrase", "warn phrase"])
        self.assertNotIn("pass phrase", out["phrases"])

    def test_apostrophes_and_single_quotes_are_ignored(self):
        out = self.scan([{"verdict": "FAIL",
                          "rationale": "What's noisy and 'single phrase'",
                          "suggestion": None}])
        self.assertEqual(out["phrases"], [])
        self.assertEqual(out["matches"], [])


class TestOutputContracts(unittest.TestCase):
    def test_generic_text_and_exit_code(self):
        fx = RunFixture(self, docs=("docs/a.md",))
        write(os.path.join(fx.repo, "docs", "a.md"), "[broken](missing.md)\n")
        proc = subprocess.run([sys.executable, script("generic-layers.py"), "--layer", "all",
                               "--format", "text", "--exit-code", "--config", fx.config_path,
                               "--repo-root", fx.repo], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("HIT FAIL docs/a.md:1", proc.stdout)
        self.assertIn("SUMMARY pass=", proc.stdout)
        self.assertIn("VERDICT NEEDS FIX", proc.stdout)

    def test_digest_rejects_broad_excludes(self):
        fx = RunFixture(self)
        for value in ("docs", "**"):
            proc = subprocess.run([sys.executable, script("tree-digest.py"),
                                   "--repo-root", fx.repo, "--exclude", value],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
