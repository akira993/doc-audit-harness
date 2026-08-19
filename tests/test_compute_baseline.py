import json, os, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "compute-baseline.sh")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


def write(repo, rel, content="x\n"):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def run_script(repo, config):
    cfg_rel = ".claude/doc-audit.json"
    write(repo, cfg_rel, json.dumps(config))
    git(repo, "add", "-A"); git(repo, "commit", "-m", "cfg")
    p = subprocess.run(["bash", SCRIPT, "--config", os.path.join(repo, cfg_rel), "--repo-root", repo],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class TestComputeBaseline(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        write(self.repo, "README.md", "init\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "init")

    def test_no_anchor_yields_full_mode(self):
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**", "apps/**"]})
        self.assertEqual(out["mode"], "full")

    def test_changed_files_since_anchor(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/a.md", "changed\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertEqual(out["mode"], "incremental")
        self.assertIn("docs/a.md", out["changed"])

    def test_untracked_and_unstaged_included(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/untracked.md", "new\n")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertIn("docs/untracked.md", out["changed"])

    def test_missing_anchor_sha_falls_back_to_full(self):
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": "0000000000000000000000000000000000000000"}))
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": ["docs/**"]})
        self.assertEqual(out["mode"], "full")

    # These tests widen diffGlobs to also cover the anchor state file and the
    # .claude/doc-audit.json config file that run_script() itself commits, so
    # filteredOutCount reflects only the paths the test explicitly adds.
    OVERHEAD_GLOBS = ["docs/**", ".claude/state/**", ".claude/doc-audit.json"]

    def test_paths_outside_diffGlobs_are_reported_filtered_out(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/a.md", "changed\n")
        write(self.repo, "apps/api/index.ts", "changed\n")
        write(self.repo, "package.json", "{}\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": self.OVERHEAD_GLOBS})
        self.assertIn("docs/a.md", out["changed"])
        self.assertNotIn("apps/api/index.ts", out["changed"])
        self.assertEqual(out["filteredOutCount"], 2)
        self.assertEqual(out["filteredOutSample"], ["apps/api/index.ts", "package.json"])

    def test_all_paths_within_diffGlobs_yields_zero_filtered_out(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        write(self.repo, "docs/a.md", "changed\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": self.OVERHEAD_GLOBS})
        self.assertEqual(out["filteredOutCount"], 0)
        self.assertEqual(out["filteredOutSample"], [])

    def test_filteredOutSample_capped_at_five(self):
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json",
              json.dumps({"sha": head, "verdict": "CONSISTENT"}))
        for i in range(6):
            write(self.repo, f"apps/api/file{i}.ts", "changed\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        out = run_script(self.repo, {"anchorPath": ".claude/state/last-doc-audit.json",
                                     "diffGlobs": self.OVERHEAD_GLOBS})
        self.assertEqual(out["filteredOutCount"], 6)
        self.assertEqual(len(out["filteredOutSample"]), 5)

    def test_machinery_paths_are_separate_from_diffglob_filter(self):
        config = {"anchorPath": ".claude/state/last-doc-audit.json", "diffGlobs": ["docs/**", ".claude/**", ".mdq/**", ".codegraph/**", "graphify-out/**", ".cocoindex_code/**"], "docGlobs": ["docs/**/*.md"], "reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>.md"}
        config_path = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(self.repo, ".claude/doc-audit.json", json.dumps(config))
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "config")
        head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        write(self.repo, ".claude/state/last-doc-audit.json", json.dumps({"sha": head}))
        for path in (".claude/state/docaudit-history.json", ".claude/worktrees/a", ".mdq/x", ".codegraph/x", "graphify-out/x", ".cocoindex_code/x", "docs/logs/doc_audit_2026-01-01.md", "docs/kept.md"):
            write(self.repo, path, "changed\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "change")
        proc = subprocess.run(["bash", SCRIPT, "--config", config_path, "--repo-root", self.repo],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["machineryExcludedCount"], 8)
        self.assertLessEqual(len(out["machineryExcludedSample"]), 5)
        self.assertEqual(out["filteredOutCount"], 0)
        self.assertEqual(out["changed"], ["docs/kept.md"])


if __name__ == "__main__":
    unittest.main()
