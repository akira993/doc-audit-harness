import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
sys.path.insert(0, SCRIPTS)


def module(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return path


def tagged_sha(path):
    with open(path, "rb") as handle:
        return "sha256:" + hashlib.sha256(handle.read()).hexdigest()


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def run_script(name, args, *, input_text=None, env=None):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name + ".py"), *args],
                          input=input_text, text=True, capture_output=True, env=env)


def make_exec(path, body):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)


class TestV020Contracts(unittest.TestCase):
    def make_repo(self, *, git=True, config=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = temp.name
        for rel, body in {
            "docs/public.md": "# public\nneedle\n",
            "docs/private.md": "# private\nneedle\n",
            "docs/report-2026-09-04.md": "# report\n",
            "src/change.py": "pass\n",
        }.items():
            write(repo, rel, body)
        cfg = config or {"docGlobs": ["docs/**/*.md"], "impactMap": [],
                         "maxImpactedDocs": 10}
        write(repo, "doc-audit.json", json.dumps(cfg, ensure_ascii=False))
        if git:
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tests"], cwd=repo, check=True)
            subprocess.run(["git", "add", "-f", "docs/public.md", "docs/report-2026-09-04.md",
                            "src/change.py", "doc-audit.json"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
        return repo

    def resolve(self, repo, config, changed="docs/public.md\n", mode="incremental"):
        config_path = write(repo, "doc-audit.json", json.dumps(config, ensure_ascii=False))
        return run_script("resolve-impact", ["--config", config_path,
                                               "--expect-config-sha", tagged_sha(config_path),
                                               "--repo-root", repo, "--changed", "-", "--mode", mode],
                          input_text=changed)

    def start_manifest(self, repo, config):
        config_path = write(repo, "doc-audit.json", json.dumps(config, ensure_ascii=False))
        runid = "20260904T000000Z-12345678"
        run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", runid)
        os.makedirs(run_dir)
        impact_path = write(repo, ".claude/state/docaudit-run/%s/impact.json" % runid,
                            json.dumps({"impacted": []}))
        with open(impact_path, "rb") as handle:
            impact_raw = handle.read()
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                              capture_output=True, text=True).stdout.strip()
        dispatch_path = write(repo, ".claude/state/docaudit-run/%s/dispatch.json" % runid,
                              json.dumps({"impactSha": "sha256:" + hashlib.sha256(impact_raw).hexdigest(),
                                          "dispatch": [], "cached": [], "changedSet": [], "baselineSha": head,
                                          "changeSetSha": "sha256:" + "0" * 64,
                                          "contractVersion": "0.20.0"}))
        evidence = {"runid": runid, "runDir": run_dir, "config": tagged_sha(config_path),
                    "dispatch": tagged_sha(dispatch_path)}
        proc = run_script("start-run", ["--run-dir", run_dir, "--runid", runid, "--repo-root", repo,
                                         "--impact-json", impact_path, "--dispatch-json", dispatch_path,
                                         "--run-class", "standard", "--mode", "incremental", "--config", config_path,
                                         "--expect-config-sha", tagged_sha(config_path), "--evidence", json.dumps(evidence)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(read_text(os.path.join(run_dir, "manifest.json")))

    def test_provenance_closed_set_contains_self(self):
        self.assertIn("self", module("start-run").VALID_PROVENANCE)
        self.assertIn("self", module("decide-verdict").VALID_PROVENANCE)

    def test_corpus_settings_are_fail_closed(self):
        paths = module("docaudit_paths")
        with self.assertRaisesRegex(ValueError, "string array"):
            paths.corpus_settings({"excludeDocGlobs": "docs/private/**"})
        with self.assertRaisesRegex(ValueError, "boolean"):
            paths.corpus_settings({"respectGitignore": "yes"})

    def test_exclude_glob_and_self(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs"))
            for name in ("public.md", "private.md"):
                with open(os.path.join(repo, "docs", name), "w", encoding="utf-8") as handle:
                    handle.write("text\n")
            cfg = {"docGlobs": ["docs/**/*.md"], "excludeDocGlobs": ["docs/private.md"],
                   "respectGitignore": False, "impactMap": [], "maxImpactedDocs": 10}
            config = os.path.join(repo, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump(cfg, handle)
            with open(config, "rb") as handle:
                raw = handle.read()
            sha = "sha256:" + hashlib.sha256(raw).hexdigest()
            proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "resolve-impact.py"),
                                   "--config", config, "--expect-config-sha", sha,
                                   "--repo-root", repo, "--changed", "-"], input="docs/public.md\ndocs/private.md\n",
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["impacted"], [{"path": "docs/public.md", "provenance": "self"}])
            self.assertEqual(out["corpusFilter"]["excludedByGlobs"], 1)

    def test_list_docs_is_json_array(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs"))
            with open(os.path.join(repo, "docs", "a.md"), "w", encoding="utf-8") as handle:
                handle.write("a\n")
            config = os.path.join(repo, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                json.dump({"docGlobs": ["docs/**/*.md"], "respectGitignore": False}, handle)
            proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "generic-layers.py"),
                                   "--config", config, "--repo-root", repo, "--list-docs"],
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout), ["docs/a.md"])

    def test_c5_three_corpus_arms_cover_shared_helper_resolver_generic_and_fix_scope(self):
        """C5: the positive arm precedes both exclusion mechanisms for core consumers."""
        for arm, extra in (("none", {}), ("glob", {"excludeDocGlobs": ["docs/private.md"]}),
                           ("git", {"respectGitignore": True})):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                config = {"docGlobs": ["docs/**/*.md"], "impactMap": [],
                          "maxImpactedDocs": 10, **extra}
                if arm == "none":
                    config["respectGitignore"] = False
                paths = module("docaudit_paths")
                docs = paths.list_doc_files(repo, config["docGlobs"],
                                            exclude_globs=config.get("excludeDocGlobs", []),
                                            respect_gitignore=config.get("respectGitignore", True))
                resolved = self.resolve(repo, config, "docs/private.md\n")
                self.assertEqual(resolved.returncode, 0, resolved.stderr)
                generic = run_script("generic-layers", ["--config", os.path.join(repo, "doc-audit.json"),
                                                          "--repo-root", repo, "--list-docs"])
                self.assertEqual(generic.returncode, 0, generic.stderr)
                listed = json.loads(generic.stdout)
                present = arm == "none"
                self.assertEqual("docs/private.md" in docs, present)
                self.assertEqual("docs/private.md" in listed, present)
                self.assertEqual(any(row["path"] == "docs/private.md"
                                     for row in json.loads(resolved.stdout)["impacted"]), present)
                config_path = os.path.join(repo, "doc-audit.json")
                fixed = run_script("fix-scope", ["--repo-root", repo, "--config", config_path,
                                                   "--expect-config-sha", tagged_sha(config_path), "--paths", "-"],
                                   input_text="docs/private.md\n")
                self.assertEqual(fixed.returncode, 0, fixed.stderr)
                result = json.loads(fixed.stdout)
                self.assertEqual("docs/private.md" in result["allowed"], present)

    def test_c5_symlink_and_list_docs_closed_set(self):
        repo = self.make_repo(git=False, config={
            "docGlobs": ["docs/**/*.md", "nested/**/*.md"], "respectGitignore": False,
            "reportPath": "docs/report-<YYYY-MM-DD>.md"})
        write(repo, "docs/normal.md", "# normal\n")
        write(repo, "nested/.git/hidden.md", "hidden\n")
        write(repo, "nested/other.md", "must be pruned with nested checkout\n")
        write(repo, ".private/notes.md", "private\n")
        os.symlink("../.private/notes.md", os.path.join(repo, "docs", "public-alias.md"))
        os.symlink("../.private", os.path.join(repo, "docs", "linked-dir"))
        fifo = os.path.join(repo, "docs", "pipe.md")
        os.mkfifo(fifo)
        config_path = os.path.join(repo, "doc-audit.json")
        generic = run_script("generic-layers", ["--config", config_path, "--repo-root", repo,
                                                  "--list-docs"])
        self.assertEqual(generic.returncode, 0, generic.stderr)
        listed = set(json.loads(generic.stdout))
        helper = set(module("docaudit_paths").list_doc_files(
            repo, ["docs/**/*.md", "nested/**/*.md"], exclude_globs=[], respect_gitignore=False))
        with open(config_path, encoding="utf-8") as handle:
            report_rx = re.compile(module("resolve-impact").report_pattern(json.load(handle)))
        self.assertEqual(listed, {path for path in helper if not report_rx.fullmatch(path)})
        self.assertNotIn("docs/public-alias.md", helper)
        self.assertNotIn("docs/pipe.md", helper)
        self.assertNotIn("nested/other.md", helper)
        self.assertNotIn("nested/other.md", listed)
        semantic = run_script("generic-layers", ["--config", config_path, "--repo-root", repo,
                                                   "--layer", "semantic"])
        self.assertEqual(semantic.returncode, 0, semantic.stderr)
        self.assertNotIn("docs/public-alias.md", semantic.stdout)
        for args in (("--paths", "-"), ("--layer", "semantic"), ("--format", "text"), ("--exit-code",)):
            proc = run_script("generic-layers", ["--config", config_path, "--repo-root", repo,
                                                   "--list-docs", *args], input_text="docs/normal.md\n")
            self.assertEqual(proc.returncode, 2)

    def test_c6_invalid_corpus_settings_fail_closed_for_direct_consumers(self):
        bad_configs = (("excludeDocGlobs", "x", "must be a string array"),
                       ("excludeDocGlobs", [1], "must be a string array"),
                       ("respectGitignore", "yes", "must be a boolean"))
        for key, value, message in bad_configs:
            with self.subTest(key=key, value=value):
                repo = self.make_repo(config={"docGlobs": ["docs/**/*.md"], key: value})
                config_path = os.path.join(repo, "doc-audit.json")
                common = ["--config", config_path, "--expect-config-sha", tagged_sha(config_path)]
                resolve = run_script("resolve-impact", [*common, "--repo-root", repo, "--changed", "-"],
                                     input_text="docs/public.md\n")
                generic = run_script("generic-layers", ["--config", config_path, "--repo-root", repo])
                fixed = run_script("fix-scope", ["--repo-root", repo, *common, "--paths", "-"],
                                   input_text="docs/public.md\n")
                runid = "20260904T000000Z-12345678"
                run_dir = os.path.join(repo, ".claude", "state", "docaudit-run", runid)
                os.makedirs(run_dir)
                impact_path = write(repo, ".claude/state/docaudit-run/%s/impact.json" % runid,
                                    json.dumps({"impacted": []}))
                with open(impact_path, "rb") as handle:
                    impact_raw = handle.read()
                dispatch_path = write(repo, ".claude/state/docaudit-run/%s/dispatch.json" % runid,
                                      json.dumps({"impactSha": "sha256:" + hashlib.sha256(impact_raw).hexdigest(),
                                                  "dispatch": [], "cached": [], "changedSet": [],
                                                  "baselineSha": subprocess.run(
                                                      ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                                                      capture_output=True, text=True).stdout.strip(),
                                                  "changeSetSha": "sha256:" + "0" * 64,
                                                  "contractVersion": "0.20.0"}))
                evidence = {"runid": runid, "runDir": run_dir, "config": tagged_sha(config_path),
                            "dispatch": tagged_sha(dispatch_path)}
                started = run_script("start-run", ["--run-dir", run_dir, "--runid", runid,
                                                     "--repo-root", repo, "--impact-json", impact_path,
                                                     "--dispatch-json", dispatch_path, "--run-class", "standard",
                                                     "--mode", "incremental", *common,
                                                     "--evidence", json.dumps(evidence)])
                payload = {"repoRoot": repo, "manifest": {"docGlobs": ["docs/**/*.md"], key: value},
                           "returns": [{"verdict": "FAIL", "rationale": '"needle phrase"'}]}
                sibling = run_script("sibling-scan", ["--stdin"], input_text=json.dumps(payload))
                checked = run_script("import-audit-scope", ["--repo-root", repo, "--config",
                                                              "doc-audit.json", "--check", "--json"])
                for proc in (resolve, started, generic, fixed, sibling):
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertIn(message, proc.stderr)
                self.assertNotIn('"allowed"', fixed.stdout)
                self.assertEqual(checked.returncode, 1)
                self.assertTrue(any(message in error for error in json.loads(checked.stdout)["errors"]))

    def test_c6_sibling_scan_validates_empty_phrase_payload(self):
        repo = self.make_repo()
        base = {"repoRoot": repo,
                "manifest": {"docGlobs": ["docs/**/*.md"], "excludeDocGlobs": [],
                             "respectGitignore": True, "changedSet": []},
                "returns": []}
        control = run_script("sibling-scan", ["--stdin"], input_text=json.dumps(base))
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertEqual(json.loads(control.stdout)["phrases"], [])
        invalid = dict(base, manifest=dict(base["manifest"], excludeDocGlobs="x"))
        rejected = run_script("sibling-scan", ["--stdin"], input_text=json.dumps(invalid))
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("must be a string array", rejected.stderr)

    def test_c7_non_git_warning_once_and_list_stdout_stays_json(self):
        repo = self.make_repo(git=False)
        config = {"docGlobs": ["docs/**/*.md"], "impactMap": [], "maxImpactedDocs": 10}
        for mode in ("incremental", "full"):
            proc = self.resolve(repo, config, "docs/public.md\n", mode)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["warnings"].count("respectGitignore: gitignore not applied (not a git work tree)"), 1)
            self.assertFalse(out["corpusFilter"]["gitignoreApplied"])
            self.assertEqual((out["corpusFilter"]["excludedByGlobs"], out["corpusFilter"]["excludedByGitignore"]), (0, 0))
            self.assertEqual(out["counts"]["docCorpus"], 3)
        config_path = os.path.join(repo, "doc-audit.json")
        listed = run_script("generic-layers", ["--config", config_path, "--repo-root", repo, "--list-docs"])
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIsInstance(json.loads(listed.stdout), list)
        self.assertIn("gitignore not applied", listed.stderr)
        normal = run_script("generic-layers", ["--config", config_path, "--repo-root", repo])
        self.assertEqual(normal.returncode, 0, normal.stderr)
        self.assertEqual(json.loads(normal.stdout)["warnings"].count(
            "respectGitignore: gitignore not applied (not a git work tree)"), 1)

    def test_c8_known_coupling_cap_boundary_and_full_mode(self):
        repo = self.make_repo(git=False)
        config = {"docGlobs": ["docs/**/*.md"], "impactMap": [
            {"changed": "docs/public.md", "impacts": ["docs/public.md", "docs/private.md"]}], "maxImpactedDocs": 2,
            "respectGitignore": False}
        ok = self.resolve(repo, config)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        rows = json.loads(ok.stdout)["impacted"]
        self.assertIn({"path": "docs/public.md", "provenance": "self"}, rows)
        self.assertEqual(json.loads(ok.stdout)["counts"]["mapped"], 1)
        self.assertEqual(json.loads(ok.stdout)["counts"]["self"], 1)
        config["maxImpactedDocs"] = 1
        rejected = self.resolve(repo, config)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("known-coupling set (2 docs: mapped=2, self=1)", rejected.stderr)
        full = self.resolve(repo, config, "docs/public.md\n", "full")
        self.assertEqual(full.returncode, 0, full.stderr)
        output = json.loads(full.stdout)
        self.assertFalse(output["truncated"])
        self.assertEqual(output["counts"]["impacted"], output["counts"]["docCorpus"])

    def test_c15_newline_name_sealed_list_and_stoplist(self):
        repo = self.make_repo(git=False, config={"docGlobs": ["docs/**/*.md"], "respectGitignore": False})
        write(repo, "docs/a\nline.md", "# newline\n")
        config_path = os.path.join(repo, "doc-audit.json")
        live = run_script("generic-layers", ["--config", config_path, "--repo-root", repo, "--list-docs"])
        sealed = run_script("generic-layers", ["--config", config_path, "--repo-root", repo,
                                                "--expect-config-sha", tagged_sha(config_path), "--list-docs"])
        self.assertEqual(live.returncode, 0, live.stderr)
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        self.assertEqual(json.loads(live.stdout), json.loads(sealed.stdout))
        self.assertIn("docs/a\nline.md", json.loads(live.stdout))
        self.assertEqual(module("sibling-scan").quote_phrases("provenance `self`"), [])

    def test_a1_unencodable_paths_warn_and_are_excluded_in_both_walkers(self):
        repo = self.make_repo()
        unsafe = "docs/unsafe\ud800.md"
        paths = module("docaudit_paths")
        warnings, stats = [], {}
        self.assertEqual(paths._gitignored_paths(repo, [unsafe], warnings, stats), {unsafe})
        self.assertEqual(len(warnings), 1)
        generic = module("generic-layers")
        warnings = []
        ignored, applied = generic._gitignored(repo, [unsafe], warnings)
        self.assertTrue(applied)
        self.assertEqual(ignored, {unsafe})
        self.assertEqual(len(warnings), 1)

    def test_c6_check_ignore_128_is_fail_closed_in_both_walkers(self):
        result = type("Result", (), {})
        rev = result(); rev.returncode = 0; rev.stdout = b""; rev.stderr = b""
        broken = result(); broken.returncode = 128; broken.stdout = b""; broken.stderr = b"broken git"
        for name, call in (
            ("helper", lambda paths: paths._gitignored_paths("/repo", ["docs/a.md"], [], {})),
            ("generic", lambda paths: paths._gitignored("/repo", ["docs/a.md"], [])),
        ):
            with self.subTest(name=name):
                paths = module("docaudit_paths") if name == "helper" else module("generic-layers")
                with mock.patch.object(paths.subprocess, "run", side_effect=[rev, broken]):
                    with self.assertRaisesRegex(ValueError, "git check-ignore failed \\(exit 128\\)"):
                        call(paths)

    def test_mutation_l_saturation_counts_self_heuristic_document(self):
        with tempfile.TemporaryDirectory() as repo:
            for name, body in (("alpha.md", "alpha\n"), ("beta.md", "alpha\n"),
                               ("gamma.md", "none\n"), ("delta.md", "none\n")):
                write(repo, "docs/" + name, body)
            config = {"docGlobs": ["docs/*.md"], "respectGitignore": False,
                      "impactMap": [], "maxImpactedDocs": 10,
                      "heuristics": {"minIdentifierLength": 5, "saturationWarnRatio": 0.5}}
            proc = self.resolve(repo, config, "docs/alpha.md\n")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["counts"]["heuristicSaturation"], 0.5)
            self.assertEqual({row["path"] for row in out["impacted"]}, {"docs/alpha.md", "docs/beta.md"})

    def test_c4_mapped_target_exclusion_has_warning(self):
        for arm, config_extra in (("none", {"respectGitignore": False}),
                                  ("glob", {"excludeDocGlobs": ["docs/private.md"], "respectGitignore": False}),
                                  ("git", {"respectGitignore": True})):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                config = {"docGlobs": ["docs/**/*.md"], "maxImpactedDocs": 10,
                          "impactMap": [{"changed": "src/change.py", "impacts": ["docs/private.md"]}],
                          **config_extra}
                proc = self.resolve(repo, config, "src/change.py\n")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                out = json.loads(proc.stdout)
                present = arm == "none"
                self.assertEqual(any(row["path"] == "docs/private.md" for row in out["impacted"]), present)
                if not present:
                    self.assertIn("mapped impact path dropped as excluded: docs/private.md", out["warnings"])

    def test_c5_start_run_empty_corpus_and_raw_manifest_values(self):
        for arm, config in (
            ("none", {"docGlobs": ["docs/private.md"], "impactMap": [], "respectGitignore": False}),
            ("glob", {"docGlobs": ["docs/private.md"], "impactMap": [],
                      "excludeDocGlobs": ["docs/private.md"], "respectGitignore": False}),
            ("git", {"docGlobs": ["docs/private.md"], "impactMap": [], "respectGitignore": True}),
        ):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                manifest = self.start_manifest(repo, config)
                self.assertEqual(manifest["emptyCorpus"], arm != "none")
                self.assertEqual(manifest["excludeDocGlobs"], config.get("excludeDocGlobs", []))
                self.assertEqual(manifest["respectGitignore"], config.get("respectGitignore", True))
        manifest = self.start_manifest(self.make_repo(), {"docGlobs": ["docs/public.md"], "impactMap": [],
                                                          "excludeDocGlobs": ["b", "a", "a"], "respectGitignore": True})
        self.assertEqual(manifest["excludeDocGlobs"], ["b", "a", "a"])

    def test_c5_import_scope_and_indexfiles_three_arms(self):
        importer = module("import-audit-scope")
        for arm, config_extra in (("none", {"respectGitignore": False}),
                                  ("glob", {"excludeDocGlobs": ["docs/private.md"], "respectGitignore": False}),
                                  ("git", {"respectGitignore": True})):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                config = {"docGlobs": ["docs/**/*.md"], "impactMap": [],
                          "indexFiles": ["docs/private.md"], **config_extra}
                errors = []
                translated, _ = importer.validate_rules(
                    [("src/*.py", ["docs/private.md"], "src/**.py")], repo, config,
                    config["docGlobs"], errors)
                present = arm == "none"
                self.assertEqual(bool(translated), present)
                self.assertEqual(bool(errors), not present)
                config_path = write(repo, "doc-audit.json", json.dumps(config))
                generic = run_script("generic-layers", ["--config", config_path, "--repo-root", repo,
                                                         "--layer", "semantic"])
                self.assertEqual(generic.returncode, 0, generic.stderr)
                findings = json.loads(generic.stdout)["findings"]
                excluded = [item for item in findings if item["path"] == "docs/private.md"
                            and item["message"] == "indexFiles entry is excluded and was excluded"]
                self.assertEqual(bool(excluded), not present)

    def test_c5_sibling_scan_excludes_phrase_only_document(self):
        for arm, manifest_extra in (("none", {"respectGitignore": False}),
                                    ("glob", {"excludeDocGlobs": ["docs/private.md"], "respectGitignore": False}),
                                    ("git", {"respectGitignore": True})):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                write(repo, "docs/public.md", "public only\n")
                write(repo, "docs/private.md", "secret phrase\n")
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                payload = {"repoRoot": repo, "manifest": {"docGlobs": ["docs/**/*.md"], **manifest_extra},
                           "returns": [{"verdict": "FAIL", "rationale": '"secret phrase"'}]}
                proc = run_script("sibling-scan", ["--stdin"], input_text=json.dumps(payload))
                self.assertEqual(proc.returncode, 0, proc.stderr)
                paths = {item["path"] for item in json.loads(proc.stdout)["matches"]}
                self.assertEqual("docs/private.md" in paths, arm == "none")

    def test_c5_decide_sibling_payload_carries_corpus_settings(self):
        decide = module("decide-verdict")
        for exclude, respect in (([], False), (["docs/private.md"], False), ([], True)):
            with self.subTest(exclude=exclude, respect=respect):
                manifest = {"mode": "incremental", "head": "h", "baselineSha": "b", "changedSet": [],
                            "docGlobs": ["docs/**/*.md"], "excludeDocGlobs": exclude,
                            "respectGitignore": respect}
                with mock.patch.object(decide, "run_sibling_scan", return_value={}) as scan:
                    decide.run_sibling_step(manifest, [], None, {}, "/repo")
                payload = scan.call_args.args[0]
                self.assertEqual(payload["manifest"]["excludeDocGlobs"], exclude)
                self.assertEqual(payload["manifest"]["respectGitignore"], respect)

    def test_c5_impact_supplement_drops_excluded_graphify_candidate(self):
        for arm, config_extra in (("none", {"respectGitignore": False}),
                                  ("glob", {"excludeDocGlobs": ["docs/private.md"], "respectGitignore": False}),
                                  ("git", {"respectGitignore": True})):
            with self.subTest(arm=arm):
                repo = self.make_repo()
                if arm == "git":
                    write(repo, ".gitignore", "docs/private.md\n")
                config = {"docGlobs": ["docs/**/*.md"], "impactMap": [], **config_extra}
                config_path = write(repo, "doc-audit.json", json.dumps(config))
                impact_path = write(repo, "impact.json", json.dumps({"impacted": [], "mapGapCandidates": [],
                                                                        "warnings": [], "counts": {}}))
                tool = os.path.join(repo, "graphify")
                make_exec(tool, "#!/bin/sh\ncase \"$1\" in\naffected) echo '- x() [calls] docs/private.md:L1' ;;\nquery) : ;;\nesac\n")
                proc = run_script("impact-supplement", ["--impact-json", impact_path, "--changed", "-",
                                                          "--repo-root", repo, "--config", config_path,
                                                          "--expect-config-sha", tagged_sha(config_path),
                                                          "--graphify-bin", tool], input_text="src/change.py\n")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                out = json.loads(read_text(impact_path))
                present = arm == "none"
                self.assertEqual(any(item["path"] == "docs/private.md" for item in out["impacted"]), present)
                if not present:
                    self.assertIn("graphify candidate dropped as excluded: docs/private.md", out["warnings"])

    def test_c9_manifest_contract_rejects_old_and_accepts_raw_values(self):
        reader = module("read-manifest")
        with tempfile.TemporaryDirectory() as run_dir:
            current = {"runid": "r", "sealed": True,
                       "excludeDocGlobs": ["b", "a", "a"], "respectGitignore": True}
            raw = (json.dumps(current) + "\n").encode()
            with open(os.path.join(run_dir, "manifest.json"), "wb") as handle:
                handle.write(raw)
            evidence = {"manifest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            self.assertEqual(reader.read_manifest(run_dir, evidence)["excludeDocGlobs"], ["b", "a", "a"])
            old = {"runid": "r", "sealed": True}
            raw = (json.dumps(old) + "\n").encode()
            with open(os.path.join(run_dir, "manifest.json"), "wb") as handle:
                handle.write(raw)
            with self.assertRaisesRegex(ValueError, "predates the v0.20 corpus contract"):
                reader.read_manifest(run_dir, {"manifest": "sha256:" + hashlib.sha256(raw).hexdigest()})

    def test_c9_gate_refuses_old_manifest_and_accepts_control(self):
        def prepared():
            fixture = RunFixture(self)
            self.assertEqual(fixture.open().returncode, 0)
            self.assertEqual(fixture.plan_start_seal().returncode, 0)
            self.assertEqual(fixture.complete().returncode, 0)
            return fixture
        control = prepared()
        control_result = control.gate()
        self.assertNotEqual(json.loads(control_result.stdout)["verdict"], "REFUSED")
        old = prepared()
        manifest_path = os.path.join(old.run_dir, "manifest.json")
        manifest = json.loads(read_text(manifest_path))
        manifest.pop("excludeDocGlobs")
        manifest.pop("respectGitignore")
        raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        with open(manifest_path, "wb") as handle:
            handle.write(raw)
        old.evidence["manifest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
        refused = old.gate()
        self.assertEqual(refused.returncode, 3, refused.stdout + refused.stderr)
        result = json.loads(refused.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertEqual(result["reason"], "manifest predates the v0.20 corpus contract; rerun the audit")

    def test_c11_documented_phase5_and_mdq_contracts(self):
        skill = read_text(os.path.join(ROOT, "skills", "audit", "SKILL.md"))
        rank = "`mapped`/`full`/`self` ≥ `regression` ≥ `heuristic` ≥ `graphify` ≥ `semantic`"
        self.assertGreaterEqual(skill.count(rank), 2)
        self.assertIn("corpus: <docCorpus> docs in scope — excluded <excludedByGlobs> by excludeDocGlobs, <excludedByGitignore> by Git exclude rules", skill)
        self.assertIn("Git exclude rules NOT applied (not a git work tree)", skill)
        self.assertIn("(respectGitignore: false)", skill)
        self.assertIn("indexing.roots unset — whole repo indexed", skill)
        self.assertIn("open-run.py --release --runid", skill)
        self.assertIn("read-manifest.py", skill)
        for path in ("docs/ADOPTION.md", "docs/ADOPTION.ja.md",
                     "skills/audit/scripts/impact-supplement.py", "skills/audit/scripts/resolve-impact.py"):
            self.assertIn(rank, read_text(os.path.join(ROOT, path)))
        old = ("`mapped` ≥ `regression` ≥ `heuristic`", "`mapped` ≥ `heuristic` ≥ `graphify`",
               "`mapped` >= `regression`")
        corpus = "\n".join(read_text(os.path.join(ROOT, path))
                           for path in ("skills/audit/SKILL.md", "docs/ADOPTION.md",
                                        "docs/ADOPTION.ja.md", "skills/audit/scripts/impact-supplement.py"))
        self.assertFalse(any(value in corpus for value in old))
        mdq = read_text(os.path.join(SCRIPTS, "mdq-index.sh"))
        self.assertIn('"rootsDefaulted"', mdq)
        probe = read_text(os.path.join(SCRIPTS, "probe-record.py"))
        self.assertIn('"rootsDefaulted": indexing.get("rootsDefaulted")', probe)

    def test_c11_mdq_roots_default_and_explicit_execution(self):
        with tempfile.TemporaryDirectory() as repo:
            write(repo, "docs/a.md", "# a\n")
            bindir = os.path.join(repo, "bin")
            os.makedirs(bindir)
            stub = os.path.join(bindir, "mdq")
            make_exec(stub, "#!/bin/sh\nmkdir -p .mdq\nexit 0\n")
            for indexing, expected_roots, defaulted in (({"bin": stub}, ["."], True),
                                                        ({"bin": stub, "roots": ["docs"]}, ["docs"], False)):
                with self.subTest(indexing=indexing):
                    config_path = write(repo, "config-%s.json" % defaulted, json.dumps({"indexing": indexing}))
                    proc = subprocess.run(["bash", os.path.join(SCRIPTS, "mdq-index.sh"), "--config", config_path,
                                           "--expect-config-sha", tagged_sha(config_path), "--repo-root", repo],
                                          capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    indexed = json.loads(proc.stdout)
                    self.assertEqual(indexed["roots"], expected_roots)
                    self.assertEqual(indexed["rootsDefaulted"], defaulted)

    def test_c14_self_prompts_use_current_source(self):
        dispatch = module("codex-dispatch")
        prompt = dispatch.prompt_for({"runid": "r", "mode": "incremental", "head": "abc",
                                      "baselineSha": "def", "changedSet": ["docs/a.md"]},
                                     "/repo", "docs/a.md", "self")
        self.assertIn("This document itself was added or edited after the anchor (provenance self).", prompt)
        self.assertIn("verify its claims against the current content at the sealed HEAD", prompt)
        self.assertIn("Do not PASS merely because the listed changed paths do not contradict it.", prompt)
        self.assertIn("contradicted by the current source", prompt)
        template = read_text(os.path.join(ROOT, "skills", "audit", "references", "workflow-template.js"))
        self.assertIn("d.provenance === 'self'", template)
        self.assertIn("current source", template)
        self.assertNotIn("still ACCURATELY describes the changed source", template)

    def test_c17_excluded_scope_has_specific_recovery_instruction(self):
        repo = self.make_repo(git=False)
        importer = module("import-audit-scope")
        errors = []
        config = {"docGlobs": ["docs/**/*.md"], "excludeDocGlobs": ["docs/private.md"],
                  "respectGitignore": False}
        translated, skipped = importer.validate_rules(
            [("src/*.py", ["docs/private.md"], "src/**.py")], repo, config,
            config["docGlobs"], errors)
        self.assertEqual((translated, skipped), ([], []))
        self.assertEqual(len(errors), 1)
        self.assertIn("excluded from corpus", errors[0])
        self.assertIn("last target, remove the whole rule", errors[0])

    def test_c17_check_write_and_singleton_recovery_execution(self):
        repo = self.make_repo()
        config_rel = ".claude/doc-audit.json"
        scope_rel = ".claude/audit-scope.json"
        config = {"docGlobs": ["docs/**/*.md"], "excludeDocGlobs": ["docs/private.md"],
                  "respectGitignore": False, "impactMap": []}
        config_path = write(repo, config_rel, json.dumps(config))
        scope_path = write(repo, scope_rel, json.dumps({"src/*.py": ["docs/private.md"]}))
        bad = run_script("import-audit-scope", ["--repo-root", repo, "--config", config_rel,
                                                 "--scope", scope_rel, "--check", "--json"])
        self.assertEqual(bad.returncode, 1)
        self.assertIn("excluded from corpus", json.loads(bad.stdout)["errors"][0])
        scope_path = write(repo, scope_rel, "{}")
        fixed = run_script("import-audit-scope", ["--repo-root", repo, "--config", config_rel,
                                                   "--scope", scope_rel, "--write", "--expect-config-sha",
                                                   tagged_sha(config_path), "--expect-scope-sha", tagged_sha(scope_path)])
        self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
        clean = run_script("import-audit-scope", ["--repo-root", repo, "--config", config_rel,
                                                   "--scope", scope_rel, "--check", "--json"])
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
        out = json.loads(clean.stdout)
        self.assertEqual((out["state"], out["diff"]["missing"], out["diff"]["extra"]), ("in-sync", [], []))


if __name__ == "__main__":
    unittest.main()
