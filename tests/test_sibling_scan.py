import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "sibling-scan.py")
SCRIPT_DIR = os.path.dirname(SCRIPT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True)


class TestSiblingScan(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main"); git(self.repo, "config", "user.email", "t@t.t"); git(self.repo, "config", "user.name", "t")
        os.makedirs(os.path.join(self.repo, "docs"))
        with open(os.path.join(self.repo, "docs", "a.md"), "w") as f: f.write("old `ccc` v1.2.3\n")
        with open(os.path.join(self.repo, "docs", "stale.md"), "w") as f: f.write("old `ccc` v1.2.3\n")
        git(self.repo, "add", "."); git(self.repo, "commit", "-m", "old")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        with open(os.path.join(self.repo, "docs", "a.md"), "w") as f: f.write("new `mdq` v1.2.4\n")
        git(self.repo, "add", "."); git(self.repo, "commit", "-m", "new")

    def scan(self, payload):
        proc = subprocess.run([sys.executable, SCRIPT, "--stdin"], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def payload(self, **more):
        data = {"repoRoot": self.repo, "manifest": {"mode": "incremental", "head": git(self.repo, "rev-parse", "HEAD").stdout.strip(), "baselineSha": self.base, "changedSet": ["docs/a.md"], "docGlobs": ["docs/**/*.md"]}, "returns": [], "phase4": None, "reportPattern": "docs/logs/doc_audit_*.md"}
        data.update(more); return data

    def test_quotes_unicode_title_and_change_set_sources(self):
        out = self.scan(self.payload(returns=[{"verdict": "WARN", "rationale": '`ccc` `mdq` `ax` `both` `--` "a b" "v1" "認証方式" "古い認証方式"'}], phase4={"findings": [{"title": "Stale `認証方式` and old mapping"}]}))
        self.assertIn("ccc", out["phrases"]); self.assertIn("mdq", out["phrases"]); self.assertIn("ax", out["phrases"])
        self.assertNotIn("both", out["phrases"]); self.assertNotIn("a b", out["phrases"])
        self.assertNotIn("--", out["phrases"]); self.assertNotIn("v1", out["phrases"])
        self.assertIn("認証方式", out["phrases"]); self.assertIn("古い認証方式", out["phrases"])
        self.assertIn("Stale `認証方式` and old mapping", out["phrases"])
        self.assertGreater(out["sources"]["changeSet"], 0)
        self.assertIn("v1.2.3", out["phrases"])
        self.assertIn({"phrase": "ccc", "path": "docs/stale.md", "line": 1}, out["matches"])

    def test_unicode_quote_rules_independently(self):
        for rationale, expected in (("`認証方式`", "認証方式"),
                                    ('"認証方式"', "認証方式"),
                                    ('"古い認証方式"', "古い認証方式")):
            with self.subTest(rationale=rationale):
                payload = self.payload(returns=[{"verdict": "WARN", "rationale": rationale}])
                payload["manifest"]["changedSet"] = []
                out = self.scan(payload)
                self.assertIn(expected, out["phrases"])

    def test_match_and_phrase_caps(self):
        with open(os.path.join(self.repo, "docs", "many.md"), "w") as handle:
            handle.write("\n".join(["`ccc`" for _ in range(21)] + [f'`p{i}`' for i in range(205)]))
        returns = [{"verdict": "WARN", "rationale": " ".join(["`ccc`"] + [f'`p{i}`' for i in range(205)])}]
        out = self.scan(self.payload(returns=returns))
        self.assertEqual(len(out["phrases"]), 200); self.assertGreater(out["phraseTruncated"], 0)
        self.assertEqual(out["truncated"]["ccc"], 2); self.assertGreater(out["truncatedTotal"], 2)

    def test_report_is_excluded_and_run_dir_matches_stdin(self):
        os.makedirs(os.path.join(self.repo, "docs", "logs"))
        with open(os.path.join(self.repo, "docs", "logs", "doc_audit_x.md"), "w") as f: f.write("`ccc`\n")
        payload = self.payload(returns=[{"verdict": "WARN", "rationale": "`ccc`"}])
        out = self.scan(payload)
        self.assertNotIn("docs/logs/doc_audit_x.md", [item["path"] for item in out["matches"]])
        run_dir = os.path.join(self.repo, ".claude", "state", "docaudit-run", "r")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "returns.json"), "w") as handle:
            json.dump(payload["returns"], handle)
        with open(os.path.join(run_dir, "manifest.json"), "w") as handle:
            json.dump(payload["manifest"], handle)
        proc = subprocess.run([sys.executable, SCRIPT, "--run-dir", run_dir, "--report-pattern", payload["reportPattern"]], capture_output=True, text=True)
        self.assertEqual(json.loads(proc.stdout), out)

    def test_deleted_document_terms_find_stale_sibling(self):
        os.unlink(os.path.join(self.repo, "docs", "a.md"))
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-m", "delete a")
        out = self.scan(self.payload())
        self.assertIn("ccc", out["phrases"])
        self.assertIn({"phrase": "ccc", "path": "docs/stale.md", "line": 1}, out["matches"])

    def test_added_text_suppression_is_per_origin_file(self):
        repo = tempfile.mkdtemp()
        git(repo, "init", "-b", "main"); git(repo, "config", "user.email", "t@t.t"); git(repo, "config", "user.name", "t")
        os.makedirs(os.path.join(repo, "docs"))
        with open(os.path.join(repo, "docs", "a.md"), "w") as handle:
            handle.write('old "legacy mode"\nbefore `moved-token`\n')
        with open(os.path.join(repo, "docs", "c.md"), "w") as handle:
            handle.write('still "legacy mode"\n')
        git(repo, "add", "."); git(repo, "commit", "-m", "old")
        base = git(repo, "rev-parse", "HEAD").stdout.strip()
        with open(os.path.join(repo, "docs", "a.md"), "w") as handle:
            handle.write('new wording\nafter `moved-token`\n')
        with open(os.path.join(repo, "docs", "b.md"), "w") as handle:
            handle.write('added "legacy mode"\n')
        git(repo, "add", "."); git(repo, "commit", "-m", "move")
        payload = {"repoRoot": repo, "manifest": {"mode": "incremental",
                   "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
                   "baselineSha": base, "changedSet": ["docs/a.md", "docs/b.md"],
                   "docGlobs": ["docs/**/*.md"]}, "returns": [], "phase4": None,
                   "reportPattern": None}
        out = self.scan(payload)
        self.assertIn("legacy mode", out["phrases"])
        self.assertIn({"phrase": "legacy mode", "path": "docs/c.md", "line": 1}, out["matches"])
        self.assertNotIn("moved-token", out["phrases"])

    def test_non_ascii_changed_path_contributes_phrases(self):
        repo = tempfile.mkdtemp()
        git(repo, "init", "-b", "main"); git(repo, "config", "user.email", "t@t.t"); git(repo, "config", "user.name", "t")
        os.makedirs(os.path.join(repo, "docs"))
        with open(os.path.join(repo, "docs", "日本語.md"), "w") as handle:
            handle.write("old `unicode-token`\n")
        with open(os.path.join(repo, "docs", "stale.md"), "w") as handle:
            handle.write("still `unicode-token`\n")
        git(repo, "add", "."); git(repo, "commit", "-m", "old")
        base = git(repo, "rev-parse", "HEAD").stdout.strip()
        with open(os.path.join(repo, "docs", "日本語.md"), "w") as handle:
            handle.write("new wording\n")
        git(repo, "add", "."); git(repo, "commit", "-m", "new")
        payload = {"repoRoot": repo, "manifest": {"mode": "incremental",
                   "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
                   "baselineSha": base, "changedSet": ["docs/日本語.md"],
                   "docGlobs": ["docs/**/*.md"]}, "returns": [], "phase4": None,
                   "reportPattern": None}
        out = self.scan(payload)
        self.assertIn("unicode-token", out["phrases"])
        self.assertIn({"phrase": "unicode-token", "path": "docs/stale.md", "line": 1},
                      out["matches"])

    def test_invalid_utf8_drops_only_change_set_source(self):
        with open(os.path.join(self.repo, "docs", "a.md"), "wb") as handle:
            handle.write(b'new `binary-token` \xff\n')
        with open(os.path.join(self.repo, "docs", "stale.md"), "a") as handle:
            handle.write('still "steady phrase"\n')
        out = self.scan(self.payload(returns=[{
            "verdict": "WARN", "rationale": 'check "steady phrase"'}]))
        self.assertIn("steady phrase", out["phrases"])
        self.assertTrue(any("decode failed" in note for note in out["sources"]["notes"]))
        self.assertEqual(out["sources"]["changeSet"], 0)

    def test_phrase_truncation_counts_distinct_dropped_phrases(self):
        phrases = " ".join(f"`token-{number}`" for number in range(200))
        returns = [{"verdict": "WARN", "rationale": phrases},
                   {"verdict": "WARN", "rationale": "`overflow-token`"},
                   {"verdict": "WARN", "rationale": "`overflow-token`"}]
        payload = self.payload(returns=returns)
        payload["manifest"]["changedSet"] = []
        out = self.scan(payload)
        self.assertEqual(len(out["phrases"]), 200)
        self.assertEqual(out["phraseTruncated"], 1)

    def test_renames_are_scanned_as_delete_and_add(self):
        for edit in (True, False):
            with self.subTest(edit=edit):
                repo = tempfile.mkdtemp()
                git(repo, "init", "-b", "main"); git(repo, "config", "user.email", "t@t.t"); git(repo, "config", "user.name", "t")
                os.makedirs(os.path.join(repo, "docs"))
                with open(os.path.join(repo, "docs", "a.md"), "w") as handle:
                    handle.write("first line\nold `old-term`\n")
                with open(os.path.join(repo, "docs", "c.md"), "w") as handle:
                    handle.write("still `old-term`\n")
                git(repo, "add", "."); git(repo, "commit", "-m", "old")
                base = git(repo, "rev-parse", "HEAD").stdout.strip()
                git(repo, "mv", "docs/a.md", "docs/b.md")
                if edit:
                    with open(os.path.join(repo, "docs", "b.md"), "w") as handle:
                        handle.write("first line changed\nnew wording\n")
                git(repo, "add", "."); git(repo, "commit", "-m", "rename")
                payload = {"repoRoot": repo, "manifest": {"mode": "incremental",
                           "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
                           "baselineSha": base, "changedSet": ["docs/a.md", "docs/b.md"],
                           "docGlobs": ["docs/**/*.md"]}, "returns": [], "phase4": None,
                           "reportPattern": None}
                out = self.scan(payload)
                self.assertTrue(out["phrases"])
                if edit:
                    self.assertIn("old-term", out["phrases"])
                    self.assertIn({"phrase": "old-term", "path": "docs/c.md", "line": 1},
                                  out["matches"])

    def test_clean_full_mode_records_working_copy_limitation(self):
        payload = self.payload()
        payload["manifest"]["mode"] = "full"
        payload["manifest"]["baselineSha"] = payload["manifest"]["head"]
        payload["manifest"]["changedSet"] = []
        out = self.scan(payload)
        self.assertIn("full mode: working-copy diff only", out["sources"]["notes"])
        self.assertEqual(out["sources"]["changeSet"], 0)

    def test_empty_phrases_skip_document_walk(self):
        spec = importlib.util.spec_from_file_location("sibling_scan_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        payload = self.payload()
        payload["manifest"]["changedSet"] = []
        with mock.patch.object(module, "list_doc_files", side_effect=AssertionError("walked")):
            out = module.scan(payload)
        self.assertEqual(out["phrases"], [])
        self.assertEqual(out["matches"], [])

    def test_git_diff_environment_settings_are_neutralized(self):
        for setting in ("external", "color", "noprefix"):
            with self.subTest(setting=setting):
                repo = tempfile.mkdtemp()
                git(repo, "init", "-b", "main"); git(repo, "config", "user.email", "t@t.t"); git(repo, "config", "user.name", "t")
                os.makedirs(os.path.join(repo, "docs"))
                with open(os.path.join(repo, "docs", "a.md"), "w") as handle:
                    handle.write("old `configured-term`\n")
                with open(os.path.join(repo, "docs", "stale.md"), "w") as handle:
                    handle.write("still `configured-term`\n")
                git(repo, "add", "."); git(repo, "commit", "-m", "old")
                base = git(repo, "rev-parse", "HEAD").stdout.strip()
                marker = os.path.join(repo, "external-diff-called")
                if setting == "external":
                    helper = os.path.join(repo, "external-diff.sh")
                    with open(helper, "w") as handle:
                        handle.write("#!/bin/sh\n: > " + shlex.quote(marker) + "\n")
                    os.chmod(helper, 0o755)
                    git(repo, "config", "diff.external", helper)
                elif setting == "color":
                    git(repo, "config", "color.ui", "always")
                else:
                    git(repo, "config", "diff.noprefix", "true")
                with open(os.path.join(repo, "docs", "a.md"), "w") as handle:
                    handle.write("new wording\n")
                git(repo, "add", "docs/a.md"); git(repo, "commit", "-m", "new")
                payload = {"repoRoot": repo, "manifest": {"mode": "incremental",
                           "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
                           "baselineSha": base, "changedSet": ["docs/a.md"],
                           "docGlobs": ["docs/**/*.md"]}, "returns": [], "phase4": None,
                           "reportPattern": None}
                out = self.scan(payload)
                self.assertIn("configured-term", out["phrases"])
                self.assertIn({"phrase": "configured-term", "path": "docs/stale.md", "line": 1},
                              out["matches"])
                if setting == "external":
                    self.assertFalse(os.path.exists(marker))
