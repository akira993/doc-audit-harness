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
        out = run(["apps/nc_proto/css/variables.css"], self.base_config(), self.repo)
        names = [s["name"] for s in out["ssotRecheck"]]
        self.assertIn("nc_version", names)

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


if __name__ == "__main__":
    unittest.main()
