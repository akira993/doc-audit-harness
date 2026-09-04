import hashlib, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "resolve-impact.py")


def run(changed, config, repo_root, mode="incremental", history=None, history_path=None):
    """Invoke resolve-impact.py; return parsed JSON stdout."""
    cfg = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(config, cfg); cfg.close()
    with open(cfg.name, "rb") as handle:
        config_sha = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    command = [sys.executable, SCRIPT, "--config", cfg.name, "--repo-root", repo_root,
               "--expect-config-sha", config_sha, "--changed", "-", "--mode", mode]
    history_file = None
    if history is not None:
        history_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        if isinstance(history, str):
            history_file.write(history)
        else:
            json.dump(history, history_file)
        history_file.close()
        command += ["--history", history_file.name]
    elif history_path is not None:
        command += ["--history", history_path]
    p = subprocess.run(
        command,
        input="\n".join(changed), capture_output=True, text=True,
    )
    os.unlink(cfg.name)
    if history_file:
        os.unlink(history_file.name)
    assert p.returncode == 0, f"stderr: {p.stderr}"
    return json.loads(p.stdout)


class TestResolveImpact(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        for rel in ["docs/wcag.md", "DESIGN.md", "docs/other.md", "docs/server-paths.md"]:
            full = os.path.join(self.repo, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write("placeholder\n")

    def base_config(self, **over):
        cfg = {
            "docGlobs": ["docs/**/*.md", "*.md"],
            "impactMap": [
                {"changed": "apps/nc_proto/css/variables.css",
                 "impacts": ["docs/wcag.md", "DESIGN.md"], "note": "color tokens"},
                {"changed": "scripts/*.cron", "impacts": ["docs/server-paths.md"]},
            ],
            "ssotSources": [
                {"name": "nc_version", "liveSource": "occ status",
                 "docsThatCite": ["docs/wcag.md", "DESIGN.md:8"]},
            ],
            "maxImpactedDocs": 50,
        }
        cfg.update(over)
        return cfg

    def history_entry(self, path, verdict="FAIL", runid="r"):
        with open(os.path.join(self.repo, path), "rb") as handle:
            current_sha = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        return {"runid": runid, "path": path, "contentSha": current_sha,
                "changeSetSha": "sha256:y", "contractVersion": "1",
                "verdict": verdict, "ts": "t"}

    def test_exact_path_match_is_mapped(self):
        out = run(["apps/nc_proto/css/variables.css"], self.base_config(), self.repo)
        paths = {d["path"]: d["provenance"] for d in out["impacted"]}
        self.assertIn("docs/wcag.md", paths)
        self.assertIn("DESIGN.md", paths)
        self.assertEqual(paths["docs/wcag.md"], "mapped")

    def test_common_filename_token_not_heuristic_flooded(self):
        # A changed */SKILL.md must NOT heuristic-match docs that merely mention
        # "SKILL.md"/"SKILL" — it is a generic Claude Code convention filename that
        # appears across many dirs (excluded by default to avoid heuristic flooding).
        with open(os.path.join(self.repo, "docs/mentions.md"), "w", encoding="utf-8") as f:
            f.write("see the markdown-query SKILL.md and another SKILL for details\n")
        out = run(["plugins/foo/SKILL.md"], self.base_config(), self.repo)
        self.assertNotIn("docs/mentions.md", [d["path"] for d in out["impacted"]])

    def test_glob_match_is_mapped(self):
        out = run(["scripts/nc_backup_cleanup.cron"], self.base_config(), self.repo)
        paths = [d["path"] for d in out["impacted"]]
        self.assertIn("docs/server-paths.md", paths)

    def test_heuristic_only_doc_tagged_as_gap(self):
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as f:
            f.write("references nc_backup_cleanup script behavior\n")
        out = run(["scripts/nc_backup_cleanup.cron"], self.base_config(), self.repo)
        by = {d["path"]: d["provenance"] for d in out["impacted"]}
        self.assertIn("docs/other.md", by)
        self.assertEqual(by["docs/other.md"], "heuristic")
        self.assertIn("docs/other.md", out.get("mapGapCandidates", []))

    def test_ssot_recheck_triggered_by_docsThatCite(self):
        # docs/wcag.md IS in nc_version's docsThatCite → must trigger recheck.
        out = run(["docs/wcag.md"], self.base_config(), self.repo)
        names = [s["name"] for s in out["ssotRecheck"]]
        self.assertIn("nc_version", names)

    def test_ssot_no_recheck_when_changed_file_unrelated(self):
        # variables.css is NOT in docsThatCite; liveSource "occ status" has no
        # matching repo file path → nc_version must NOT be rechecked.
        out = run(["apps/nc_proto/css/variables.css"], self.base_config(), self.repo)
        names = [s["name"] for s in out["ssotRecheck"]]
        self.assertNotIn("nc_version", names)

    def test_ssot_url_livesource_warned_not_rechecked(self):
        # A URL liveSource is unsupported: it must surface a warning in the output
        # JSON (never silently skipped) and must NOT trigger an ssotRecheck.
        cfg = self.base_config(ssotSources=[
            {"name": "api_status", "liveSource": "https://example.com/api/status",
             "docsThatCite": ["docs/wcag.md"]},
        ])
        out = run(["apps/nc_proto/css/variables.css"], cfg, self.repo)
        self.assertTrue(any("api_status" in w and "URL" in w for w in out["warnings"]),
                        f"warnings: {out['warnings']}")
        self.assertNotIn("api_status", [s["name"] for s in out["ssotRecheck"]])

    def test_nonexistent_mapped_path_dropped_with_warning(self):
        cfg = self.base_config(impactMap=[
            {"changed": "x.css", "impacts": ["docs/missing.md", "docs/wcag.md"]}])
        out = run(["x.css"], cfg, self.repo)
        paths = [d["path"] for d in out["impacted"]]
        self.assertIn("docs/wcag.md", paths)
        self.assertNotIn("docs/missing.md", paths)

    def test_cap_sets_truncated(self):
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("variables.css\n")
        with open(os.path.join(self.repo, "docs/server-paths.md"), "w", encoding="utf-8") as handle:
            handle.write("variables.css\n")
        cfg = self.base_config(maxImpactedDocs=1, impactMap=[])
        out = run(["apps/nc_proto/css/variables.css"], cfg, self.repo)
        self.assertTrue(out["truncated"])
        self.assertEqual(len(out["impacted"]), 1)

    def test_provenance_both(self):
        # docs/other.md is BOTH a mapped impact AND a heuristic hit for special_helper.
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as f:
            f.write("references special_helper behavior\n")
        cfg = self.base_config(impactMap=[
            {"changed": "apps/nc_proto/css/variables.css",
             "impacts": ["docs/wcag.md", "DESIGN.md"], "note": "color tokens"},
            {"changed": "scripts/*.cron", "impacts": ["docs/server-paths.md"]},
            {"changed": "scripts/special_helper.py", "impacts": ["docs/other.md"]},
        ])
        out = run(["scripts/special_helper.py"], cfg, self.repo)
        by = {d["path"]: d["provenance"] for d in out["impacted"]}
        self.assertIn("docs/other.md", by)
        self.assertEqual(by["docs/other.md"], "both")


    def test_node_modules_skipped_in_heuristic(self):
        # A broad docGlobs (**/*.md) must NOT pull node_modules into the heuristic
        # scan (noise + perf). list_doc_files prunes node_modules/.venv/etc.
        nmdir = os.path.join(self.repo, "node_modules", "pkg")
        os.makedirs(nmdir, exist_ok=True)
        with open(os.path.join(nmdir, "doc.md"), "w", encoding="utf-8") as f:
            f.write("this vendored file mentions variables.css inside node_modules\n")
        out = run(["apps/nc_proto/css/variables.css"],
                  self.base_config(docGlobs=["**/*.md"]), self.repo)
        self.assertNotIn("node_modules/pkg/doc.md", [d["path"] for d in out["impacted"]])

    def test_linked_worktree_pruned_from_corpus(self):
        # A linked git worktree (e.g. .claude/worktrees/<feature>/) has a `.git`
        # FILE (a `gitdir: ...` pointer), not a directory, so the name-based
        # `skip` set can't catch it. Its docs must not be double-counted.
        wtdir = os.path.join(self.repo, ".claude", "worktrees", "feature", "docs")
        os.makedirs(wtdir, exist_ok=True)
        with open(os.path.join(self.repo, ".claude", "worktrees", "feature", ".git"),
                   "w", encoding="utf-8") as f:
            f.write("gitdir: /some/parent/.git/worktrees/feature\n")
        with open(os.path.join(wtdir, "dup.md"), "w", encoding="utf-8") as f:
            f.write("placeholder\n")
        out = run(["apps/nc_proto/css/variables.css"],
                  self.base_config(docGlobs=["**/*.md"]), self.repo)
        paths = [d["path"] for d in out["impacted"]]
        self.assertNotIn(".claude/worktrees/feature/docs/dup.md", paths)

    def test_nested_clone_pruned_from_corpus(self):
        # A nested full clone/submodule has a real `.git` DIRECTORY. It must be
        # pruned the same way as a linked worktree's `.git` file.
        clonedir = os.path.join(self.repo, "vendor", "sub", "docs")
        os.makedirs(clonedir, exist_ok=True)
        os.makedirs(os.path.join(self.repo, "vendor", "sub", ".git"), exist_ok=True)
        with open(os.path.join(clonedir, "dup.md"), "w", encoding="utf-8") as f:
            f.write("placeholder\n")
        out = run(["apps/nc_proto/css/variables.css"],
                  self.base_config(docGlobs=["**/*.md"]), self.repo)
        paths = [d["path"] for d in out["impacted"]]
        self.assertNotIn("vendor/sub/docs/dup.md", paths)

    def test_root_docs_included_even_when_root_has_git_dir(self):
        # The walk root itself commonly has a real .git directory (it's the repo
        # being audited). Pruning must only apply to subdirs walked INTO, never
        # exclude the root's own direct docs.
        os.makedirs(os.path.join(self.repo, ".git"), exist_ok=True)
        out = run(["apps/nc_proto/css/variables.css"], self.base_config(), self.repo)
        paths = [d["path"] for d in out["impacted"]]
        self.assertIn("docs/wcag.md", paths)
        self.assertIn("DESIGN.md", paths)

    def test_reports_are_excluded_from_full_corpus_but_policy_remains(self):
        report = "docs/logs/doc_audit_2026-08-25_02.md"
        policy = "docs/logs/doc_audit_policy.md"
        for path in (report, policy):
            full = os.path.join(self.repo, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write("doc\n")
        cfg = self.base_config(reportPath="docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md")
        out = run([], cfg, self.repo, mode="full")
        paths = [item["path"] for item in out["impacted"]]
        self.assertNotIn(report, paths)
        self.assertIn(policy, paths)
        self.assertEqual(out["mapGapCandidates"], [])
        self.assertEqual(out["counts"], {"changed": 0, "impacted": 5, "mapped": 0, "self": 0,
                                         "heuristicOnly": 0, "regression": 0, "docCorpus": 5,
                                         "heuristicSaturation": 0.0, "candidatesBeforeCap": 5})

    def test_reports_are_excluded_from_heuristic_pool_but_mapped_is_unchanged(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        policy = "docs/logs/doc_audit_policy.md"
        for path in (report, policy):
            full = os.path.join(self.repo, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write("report_signal\n")
        cfg = self.base_config(reportPath="docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md")
        out = run(["src/report_signal.py"], cfg, self.repo)
        self.assertEqual(out["impacted"], [{"path": policy, "provenance": "heuristic"}])
        self.assertEqual(out["mapGapCandidates"], [policy])
        self.assertEqual(out["counts"], {"changed": 1, "impacted": 1, "mapped": 0, "self": 0,
                                         "heuristicOnly": 1, "regression": 0, "docCorpus": 5,
                                         "heuristicSaturation": 0.2, "candidatesBeforeCap": 1})

        mapped_cfg = self.base_config(
            reportPath="docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md",
            impactMap=[{"changed": "src/report_signal.py", "impacts": [report]}])
        mapped = run(["src/report_signal.py"], mapped_cfg, self.repo)
        self.assertIn({"path": report, "provenance": "mapped"}, mapped["impacted"])

    def test_corpus_opt_in_true_only_restores_reports(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        full = os.path.join(self.repo, report)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write("report\n")
        base = self.base_config(reportPath="docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md")
        opted_in = run([], dict(base, auditReportsInCorpus=True), self.repo, mode="full")
        self.assertIn(report, [item["path"] for item in opted_in["impacted"]])
        self.assertEqual(opted_in["counts"]["candidatesBeforeCap"], 5)
        for value in ("true", 1, []):
            with self.subTest(value=value):
                out = run([], dict(base, auditReportsInCorpus=value), self.repo, mode="full")
                self.assertNotIn(report, [item["path"] for item in out["impacted"]])
                self.assertEqual(out["counts"]["candidatesBeforeCap"], 4)

    def test_regression_recheck_and_history_sha(self):
        history = {"entries": [self.history_entry("docs/other.md")]}
        out = run([], self.base_config(regressionRecheck={"enabled": True}), self.repo, history=history)
        self.assertIn({"path": "docs/other.md", "provenance": "regression"}, out["impacted"])
        self.assertRegex(out["historySha"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(out["counts"]["regression"], 1)
        self.assertEqual(out["mapGapCandidates"], [])

    def test_invalid_phase4_runs_keeps_regression_entries(self):
        history = {
            "entries": [self.history_entry("docs/other.md")],
            "phase4Runs": "bad",
        }
        out = run([], self.base_config(regressionRecheck={"enabled": True}),
                  self.repo, history=history)
        self.assertIn({"path": "docs/other.md", "provenance": "regression"},
                      out["impacted"])
        self.assertTrue(any("phase4Runs ignored" in item
                            for item in out["warnings"]))

    def test_saturation_and_doc_path_token_opt_out(self):
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("wcag.md\n")
        out = run(["docs/wcag.md"], self.base_config(heuristics={"excludeDocPathTokens": True}), self.repo)
        self.assertNotIn("docs/other.md", [d["path"] for d in out["impacted"]])
        self.assertEqual(out["counts"]["docCorpus"], 4)
        self.assertEqual(out["counts"]["heuristicSaturation"], 0.0)

    def test_empty_corpus_has_zero_saturation_without_warning(self):
        with tempfile.TemporaryDirectory() as repo:
            out = run(["src/signal.py"], self.base_config(docGlobs=["docs/**/*.md"], impactMap=[]), repo)
        self.assertEqual(out["counts"]["docCorpus"], 0)
        self.assertEqual(out["counts"]["heuristicSaturation"], 0.0)
        self.assertEqual(out["warnings"], [])

    def test_nine_of_nine_heuristic_docs_warn_without_minimum(self):
        with tempfile.TemporaryDirectory() as repo:
            for index in range(9):
                path = os.path.join(repo, "docs", f"d{index}.md")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("signal_token\n")
            out = run(["src/signal_token.py"], self.base_config(docGlobs=["docs/**/*.md"], impactMap=[]), repo)
        self.assertEqual(out["counts"]["heuristicSaturation"], 1.0)
        self.assertTrue(any("heuristic saturation: 9/9 docs" in w for w in out["warnings"]))

    def test_saturation_compares_unrounded_ratio(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs"))
            for index in range(2500):
                with open(os.path.join(repo, "docs", f"d{index}.md"), "w", encoding="utf-8") as handle:
                    handle.write("signal_token\n" if index < 1249 else "other\n")
            out = run(["src/signal_token.py"], self.base_config(docGlobs=["docs/**/*.md"], impactMap=[], maxImpactedDocs=2500), repo)
        self.assertEqual(out["counts"]["heuristicSaturation"], 0.5)
        self.assertFalse(any(w.startswith("heuristic saturation:") for w in out["warnings"]))

    def test_doc_path_token_exclusion_true_false_pair(self):
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("wcag.md\n")
        included = run(["docs/wcag.md"], self.base_config(heuristics={"excludeDocPathTokens": False}), self.repo)
        excluded = run(["docs/wcag.md"], self.base_config(heuristics={"excludeDocPathTokens": True}), self.repo)
        self.assertIn("docs/other.md", [d["path"] for d in included["impacted"]])
        self.assertNotIn("docs/other.md", [d["path"] for d in excluded["impacted"]])

    def test_cap_warning_is_in_json(self):
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("variables.css\n")
        out = run(["apps/nc_proto/css/variables.css"], self.base_config(
            maxImpactedDocs=1, impactMap=[{"changed": "apps/nc_proto/css/variables.css",
                                             "impacts": ["docs/wcag.md"]}]), self.repo)
        self.assertIn("1 impacted docs dropped by maxImpactedDocs=1", out["warnings"])

    def test_saturation_warn_ratio_type_table(self):
        cases = [("0.5", True), (True, True), (False, True), (-1, True), (1.5, True),
                 (None, True), ([], True), (0, False), (1, False)]
        for path in ("docs/wcag.md", "DESIGN.md", "docs/other.md", "docs/server-paths.md"):
            with open(os.path.join(self.repo, path), "w", encoding="utf-8") as handle:
                handle.write("signal_token\n")
        for value, invalid in cases:
            with self.subTest(value=value):
                out = run(["src/signal_token.py"], self.base_config(heuristics={"saturationWarnRatio": value}), self.repo)
                invalid_warnings = [w for w in out["warnings"] if "saturationWarnRatio invalid" in w]
                self.assertEqual(bool(invalid_warnings), invalid)
                saturation_warnings = [w for w in out["warnings"] if w.startswith("heuristic saturation:")]
                if type(value) in (int, float) and value == 0:
                    self.assertEqual(saturation_warnings, [])
                if type(value) in (int, float) and value == 1:
                    self.assertTrue(saturation_warnings)

    def test_other_config_type_tables(self):
        for value in ("true", 1, None):
            with self.subTest(key="excludeDocPathTokens", value=value):
                out = run([], self.base_config(heuristics={"excludeDocPathTokens": value}), self.repo)
                self.assertTrue(any("excludeDocPathTokens invalid" in w for w in out["warnings"]))
        for value in ([], "x", {"enabled": "yes"}):
            with self.subTest(key="regressionRecheck", value=value):
                out = run([], self.base_config(regressionRecheck=value), self.repo)
                self.assertTrue(any("regressionRecheck" in w and "invalid" in w for w in out["warnings"]))
                self.assertNotIn("historySha", out)

    def test_regression_provenance_precedence_and_modes(self):
        history = {"entries": [self.history_entry("docs/other.md"), self.history_entry("docs/wcag.md", runid="r2")]}
        mapped = run(["apps/nc_proto/css/variables.css"], self.base_config(regressionRecheck={"enabled": True}), self.repo, history=history)
        self.assertEqual({d["path"]: d["provenance"] for d in mapped["impacted"]}["docs/wcag.md"], "mapped")
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("signal_token\n")
        heuristic = run(["src/signal_token.py"], self.base_config(regressionRecheck={"enabled": True}), self.repo, history=history)
        self.assertEqual({d["path"]: d["provenance"] for d in heuristic["impacted"]}["docs/other.md"], "heuristic")
        self.assertIn("docs/other.md", heuristic["mapGapCandidates"])
        full = run([], self.base_config(regressionRecheck={"enabled": True}), self.repo, mode="full", history=history)
        self.assertNotIn("historySha", full)
        self.assertTrue(all(d["provenance"] == "full" for d in full["impacted"]))

    def test_regression_defaults_missing_and_corrupt_history(self):
        default = run([], self.base_config(regressionRecheck={}, respectGitignore=False), self.repo, history={"entries": []})
        self.assertNotIn("historySha", default)
        self.assertEqual(default["warnings"], [])
        missing = run([], self.base_config(regressionRecheck={"enabled": True}, respectGitignore=False), self.repo,
                      history_path=os.path.join(self.repo, "missing-history.json"))
        self.assertIsNone(missing["historySha"])
        self.assertEqual(missing["warnings"], [])
        raw = "{broken"
        corrupt = run([], self.base_config(regressionRecheck={"enabled": True}), self.repo, history=raw)
        self.assertEqual(corrupt["historySha"], "sha256:" + hashlib.sha256(raw.encode()).hexdigest())
        self.assertTrue(any(w.startswith("regression recheck skipped: history unreadable") for w in corrupt["warnings"]))

    def test_cap_priority_mapped_regression_heuristic(self):
        for name in ("r1", "r2", "h1", "h2"):
            with open(os.path.join(self.repo, "docs", name + ".md"), "w", encoding="utf-8") as handle:
                handle.write("heur_signal\n" if name.startswith("h") else "other\n")
        cfg = self.base_config(maxImpactedDocs=3, regressionRecheck={"enabled": True}, impactMap=[
            {"changed": "src/change.py", "impacts": ["docs/wcag.md", "DESIGN.md"]}])
        history = {"entries": [self.history_entry("docs/r1.md"), self.history_entry("docs/r2.md", runid="r2")]}
        out = run(["src/change.py", "src/heur_signal.py"], cfg, self.repo, history=history)
        self.assertEqual([d["provenance"] for d in out["impacted"]], ["mapped", "mapped", "regression"])
        self.assertTrue(out["truncated"])
        self.assertTrue(any("dropped by maxImpactedDocs=3" in w for w in out["warnings"]))

    def test_changed_document_is_not_regression(self):
        history = {"entries": [self.history_entry("docs/other.md")]}
        with open(os.path.join(self.repo, "docs/other.md"), "w", encoding="utf-8") as handle:
            handle.write("fixed after prior FAIL\n")
        out = run([], self.base_config(regressionRecheck={"enabled": True}), self.repo, history=history)
        self.assertNotIn("docs/other.md", [d["path"] for d in out["impacted"]])
        self.assertEqual(out["counts"]["regression"], 0)

    def test_changed_failures_do_not_displace_heuristics_at_cap(self):
        for name in ("failed1", "failed2", "heur1", "heur2"):
            with open(os.path.join(self.repo, "docs", name + ".md"), "w", encoding="utf-8") as handle:
                handle.write("before\n")
        history = {"entries": [self.history_entry("docs/failed1.md"),
                               self.history_entry("docs/failed2.md", runid="r2")]}
        for name in ("failed1", "failed2"):
            with open(os.path.join(self.repo, "docs", name + ".md"), "w", encoding="utf-8") as handle:
                handle.write("fixed\n")
        for name in ("heur1", "heur2"):
            with open(os.path.join(self.repo, "docs", name + ".md"), "w", encoding="utf-8") as handle:
                handle.write("heur_signal\n")
        cfg = self.base_config(maxImpactedDocs=4, regressionRecheck={"enabled": True}, impactMap=[
            {"changed": "src/change.py", "impacts": ["docs/wcag.md", "DESIGN.md"]}])
        out = run(["src/change.py", "src/heur_signal.py"], cfg, self.repo, history=history)
        self.assertEqual([d["provenance"] for d in out["impacted"]],
                         ["mapped", "mapped", "heuristic", "heuristic"])
        self.assertEqual(out["counts"]["regression"], 0)

    def test_impact_map_source_is_ignored(self):
        base = self.base_config()
        sourced = json.loads(json.dumps(base))
        sourced["impactMap"][0]["source"] = "audit-scope"
        self.assertEqual(run(["apps/nc_proto/css/variables.css"], base, self.repo),
                         run(["apps/nc_proto/css/variables.css"], sourced, self.repo))


if __name__ == "__main__":
    unittest.main()
