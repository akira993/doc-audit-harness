import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "resolve-impact.py")


def run(changed, config, repo_root):
    """Invoke resolve-impact.py; return parsed JSON stdout."""
    cfg = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(config, cfg); cfg.close()
    p = subprocess.run(
        [sys.executable, SCRIPT, "--config", cfg.name, "--repo-root", repo_root, "--changed", "-"],
        input="\n".join(changed), capture_output=True, text=True,
    )
    os.unlink(cfg.name)
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
        cfg = self.base_config(maxImpactedDocs=1)
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


if __name__ == "__main__":
    unittest.main()
