import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")
SCRIPT = os.path.join(SCRIPTS, "import-audit-scope.py")
OPEN_RUN = os.path.join(SCRIPTS, "open-run.py")
RESOLVE_IMPACT = os.path.join(SCRIPTS, "resolve-impact.py")
FIXTURE_DIR = os.path.join(ROOT, "tests", "data", "dir-framework-scope")
ABSENT = object()

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def load_importer():
    spec = importlib.util.spec_from_file_location("import_audit_scope", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IMPORTER = load_importer()


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    kwargs = {} if mode == "wb" else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as handle:
        handle.write(content)


def read(path):
    with open(path, "rb") as handle:
        return handle.read()


class ImportAuditScopeTests(unittest.TestCase):
    def make_repo(self, scope='{"src/*.py":["docs/a.md"]}', config=ABSENT,
                  files=(), track=True):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = temp.name
        write(os.path.join(root, "docs", "a.md"), "# a\n")
        write(os.path.join(root, "docs", "b.md"), "# b\n")
        write(os.path.join(root, "src", "x.py"), "")
        if scope is not ABSENT:
            write(os.path.join(root, ".claude", "audit-scope.json"), scope)
        if config is not ABSENT:
            if not isinstance(config, str):
                config = json.dumps(config, ensure_ascii=False)
            write(os.path.join(root, ".claude", "doc-audit.json"), config)
        for path, content in files:
            write(os.path.join(root, path), content)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        if track:
            subprocess.run(["git", "add", "-f", "."], cwd=root, check=True)
        return root

    def invoke(self, root, *args, input_text=None, env=None):
        command = [sys.executable, SCRIPT, "--repo-root", root, *args]
        return subprocess.run(command, input=input_text, text=True,
                              capture_output=True, env=env)

    def output(self, proc):
        self.assertTrue(proc.stdout, proc.stderr)
        return json.loads(proc.stdout)

    def config_path(self, root):
        return os.path.join(root, ".claude", "doc-audit.json")

    def scope_path(self, root, rel=".claude/audit-scope.json"):
        return os.path.join(root, *rel.split("/"))

    def expected(self, root, config_rel=".claude/doc-audit.json",
                 scope_rel=".claude/audit-scope.json"):
        config_path = os.path.join(root, *config_rel.split("/"))
        return [
            "--expect-config-sha",
            sha(read(config_path)) if os.path.isfile(config_path) else "none",
            "--expect-scope-sha", sha(read(self.scope_path(root, scope_rel))),
        ]

    def import_existing(self, root, scope_rel=".claude/audit-scope.json"):
        proc = self.invoke(root, "--scope", scope_rel, "--write",
                           *self.expected(root, scope_rel=scope_rel))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(read(self.config_path(root)))

    # PLAN §1.6 (i)
    def test_i_glob_translation_positive_and_negative_examples(self):
        positive = {
            "README.md": "README.md",
            "src/*.py": "src/**.py",
            "src/**.py": "src/**.py",
            "docs/**": "docs/**",
            "prefix-*.py": "prefix-**.py",
            "dir/*.json": "dir/**.json",
            ".claude/*.json": ".claude/**.json",
        }
        for original, expected in positive.items():
            with self.subTest(original=original):
                errors = []
                self.assertEqual(IMPORTER.convert(original, errors), expected)
                self.assertEqual(errors, [])

        negative = ("*/foo", "**/*", "a?b", "x[y]", "./x", "x/", "", "*", "**")
        for original in negative:
            with self.subTest(original=original):
                errors = []
                self.assertIsNone(IMPORTER.convert(original, errors))
                self.assertTrue(errors)

        self.assertFalse(fnmatch.fnmatchcase("foo", "*/foo"))
        self.assertTrue(IMPORTER.matches_glob("foo", "**/foo"))
        self.assertTrue(fnmatch.fnmatchcase("a/b", "a?b"))
        self.assertFalse(IMPORTER.matches_glob("a/b", "a?b"))

    def test_i_allowed_fnmatch_and_docaudit_dialects_match_on_composite_paths(self):
        paths = (
            "a.md", "d/a.md", "d/e/a.md", "d/a.mdx", ".a.md", "d/.a.md",
            "a-b.md", "prefix-a.py", "prefix-.py", "dir/a.json", "dir/a/b.json",
            ".claude/a.json", ".claude/nested/a.json", "src/x.py", "src/x.pyc",
        )
        patterns = (
            "a.md", "*.md", "d/*.md", "d/**.md", "prefix-*.py",
            "dir/*.json", ".claude/*.json", "src/**", "docs/**",
        )
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                errors = []
                converted = IMPORTER.convert(pattern, errors)
                self.assertEqual(errors, [])
                fnmatch_regex = re.compile(fnmatch.translate(pattern))
                by_fnmatch_regex = {path for path in paths if fnmatch_regex.fullmatch(path)}
                by_docaudit = {
                    path for path in paths if IMPORTER.matches_glob(path, converted)
                }
                self.assertEqual(by_fnmatch_regex, by_docaudit)

    # PLAN §1.6 (ii)
    def test_ii_absent_skips_git_even_with_crlf_filename(self):
        root = self.make_repo(scope=ABSENT, track=False,
                              files=(("odd\nname", ""), ("odd\rname", "")))
        fake_dir = tempfile.TemporaryDirectory()
        self.addCleanup(fake_dir.cleanup)
        marker = os.path.join(fake_dir.name, "git-called")
        fake_git = os.path.join(fake_dir.name, "git")
        write(fake_git, "#!/bin/sh\nprintf called >> \"$DOCAUDIT_GIT_MARKER\"\nexit 99\n")
        os.chmod(fake_git, 0o755)
        env = os.environ.copy()
        env["PATH"] = fake_dir.name + os.pathsep + env.get("PATH", "")
        env["DOCAUDIT_GIT_MARKER"] = marker
        proc = self.invoke(root, "--json", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.output(proc)["state"], "absent")
        self.assertEqual(self.output(proc)["scopePath"], ".claude/audit-scope.json")
        self.assertFalse(os.path.exists(marker))

    def test_ii_tracked_and_untracked_crlf_names_are_rejected_and_count_is_reported(self):
        root = self.make_repo()
        tracked = os.path.join(root, "tracked\nname")
        untracked = os.path.join(root, "untracked\rname")
        write(tracked, "")
        subprocess.run(["git", "add", "-f", "tracked\nname"], cwd=root, check=True)
        write(untracked, "")
        proc = self.invoke(root, "--json")
        out = self.output(proc)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertGreaterEqual(out["equivalenceChecked"], 1)
        unsupported = [error for error in out["errors"] if "unsupported filename" in error]
        self.assertEqual(len(unsupported), 2, out)

    def test_ii_zero_git_paths_is_an_error(self):
        root = self.make_repo(track=False)
        fake_dir = tempfile.TemporaryDirectory()
        self.addCleanup(fake_dir.cleanup)
        fake_git = os.path.join(fake_dir.name, "git")
        write(fake_git, "#!/bin/sh\nexit 0\n")
        os.chmod(fake_git, 0o755)
        env = os.environ.copy()
        env["PATH"] = fake_dir.name + os.pathsep + env.get("PATH", "")
        proc = self.invoke(root, "--json", env=env)
        out = self.output(proc)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(out["equivalenceChecked"], 0)
        self.assertTrue(any("zero paths" in error for error in out["errors"]))

    # PLAN §1.6 (iii)
    def test_iii_rejects_duplicate_empty_missing_nonstring_invalid_and_outside_values(self):
        cases = {
            "top-level non-object": "[]",
            "duplicate": '{"src/*.py":["docs/a.md"],"src/*.py":["docs/b.md"]}',
            "nested duplicate": '{"src/*.py":{"impact":"none","impact":"none"}}',
            "empty impacts": '{"src/*.py":[]}',
            "missing impact": '{"src/*.py":["docs/missing.md"]}',
            "non-string impact": '{"src/*.py":[7]}',
            "invalid scalar": '{"src/*.py":false}',
            "outside docGlobs": '{"src/*.py":["notes/a.txt"]}',
            "invalid object": '{"src/*.py":{"impact":"all"}}',
            "non-object top level": '["src/*.py"]',
        }
        for name, scope in cases.items():
            with self.subTest(name=name):
                extra = (("notes/a.txt", "text\n"),) if name == "outside docGlobs" else ()
                root = self.make_repo(scope=scope, files=extra)
                proc = self.invoke(root, "--json")
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertTrue(self.output(proc)["errors"])

    def test_iii_report_exclusion_respects_audit_reports_in_corpus(self):
        scope = '{"src/*.py":["docs/logs/audit_2026-08-27.md"]}'
        base = {
            "docGlobs": ["docs/**/*.md"],
            "reportPath": "docs/logs/audit_<YYYY-MM-DD>[_NN].md",
            "impactMap": [],
        }
        for enabled, expected in ((False, 1), (True, 2)):
            with self.subTest(auditReportsInCorpus=enabled):
                config = dict(base, auditReportsInCorpus=enabled)
                root = self.make_repo(
                    scope=scope, config=config,
                    files=(("docs/logs/audit_2026-08-27.md", "# report\n"),),
                )
                proc = self.invoke(root, "--json")
                self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
                out = self.output(proc)
                if enabled:
                    self.assertEqual(out["errors"], [])
                    self.assertEqual(out["state"], "not-imported")
                else:
                    self.assertTrue(any("document corpus" in error for error in out["errors"]))

    def test_iii_crlf_in_rule_and_impact_are_rejected(self):
        cases = (
            '{"src/line\\n*.py":["docs/a.md"]}',
            '{"src/*.py":["docs/a.md\\rwrong"]}',
        )
        for scope in cases:
            with self.subTest(scope=scope):
                root = self.make_repo(scope=scope)
                proc = self.invoke(root, "--json")
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertTrue(any("CR/LF" in error for error in self.output(proc)["errors"]))

    def test_iii_each_unsupported_rule_error_is_reported_once(self):
        root = self.make_repo(scope='{"*/foo":["docs/a.md"]}')
        proc = self.invoke(root, "--json")
        out = self.output(proc)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        matching = [error for error in out["errors"] if "*/foo" in error]
        self.assertEqual(len(matching), 1, out["errors"])

    # PLAN §1.6 (iv)
    def test_iv_impact_none_is_skipped_and_reported(self):
        root = self.make_repo(scope='{"bak/**":{"impact":"none"},"src/*.py":["docs/a.md"]}')
        proc = self.invoke(root, "--json")
        out = self.output(proc)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(out["skippedNoImpact"], ["bak/**"])
        self.assertEqual([item["from"] for item in out["translated"]], ["src/*.py"])

    # PLAN §1.6 (v)
    def test_v_fresh_run_base_mode_state_symlink_and_existing_lock(self):
        config = {"docGlobs": ["docs/**/*.md"], "impactMap": []}

        root = self.make_repo(config=config)
        proc = self.invoke(root, "--write", *self.expected(root))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        run_base = os.path.join(root, ".claude", "state", "docaudit-run")
        self.assertEqual(stat.S_IMODE(os.stat(run_base).st_mode), 0o700)
        self.assertFalse(os.path.exists(os.path.join(run_base, "lock")))

        root = self.make_repo(config=config)
        original = read(self.config_path(root))
        state_target = os.path.join(root, "state-target")
        os.mkdir(state_target)
        os.symlink(state_target, os.path.join(root, ".claude", "state"))
        proc = self.invoke(root, "--write", *self.expected(root))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(read(self.config_path(root)), original)

        root = self.make_repo(config=config)
        original = read(self.config_path(root))
        lock = os.path.join(root, ".claude", "state", "docaudit-run", "lock")
        write(lock, "other")
        proc = self.invoke(root, "--write", *self.expected(root))
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(read(self.config_path(root)), original)
        self.assertEqual(read(lock), b"other")

    def test_v_lock_inode_mismatch_does_not_remove_replacement_lock(self):
        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        lock = os.path.join(root, ".claude", "state", "docaudit-run", "lock")
        real_flock = IMPORTER.fcntl.flock

        def replace_before_inode_check(fd, operation):
            real_flock(fd, operation)
            os.unlink(lock)
            write(lock, "replacement")

        with mock.patch.object(IMPORTER.fcntl, "flock", side_effect=replace_before_inode_check):
            with self.assertRaises(IMPORTER.LockBusy):
                IMPORTER.acquire(root, None)
        self.assertEqual(read(lock), b"replacement")

    def test_v_hold_lock_blocks_break_lock_in_real_process(self):
        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        resume = os.path.join(root, "resume-import")
        env = os.environ.copy()
        env["DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT"] = "hold-lock:" + resume
        command = [sys.executable, SCRIPT, "--repo-root", root, "--write",
                   *self.expected(root)]
        proc = subprocess.Popen(command, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env)
        lock = os.path.join(root, ".claude", "state", "docaudit-run", "lock")
        deadline = time.monotonic() + 10
        while not os.path.exists(lock) and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        try:
            self.assertIsNone(proc.poll(), "importer exited before holding lock")
            broken = subprocess.run(
                [sys.executable, OPEN_RUN, "--run-base", os.path.dirname(lock),
                 "--repo-root", root, "--break-lock"],
                text=True, capture_output=True,
            )
            self.assertEqual(broken.returncode, 4, broken.stdout + broken.stderr)
            self.assertEqual(json.loads(broken.stdout)["reason"], "gate-running")
            write(resume, "continue")
            stdout, stderr = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, stdout + stderr)
            self.assertFalse(os.path.exists(lock))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

    def test_v_faults_before_and_after_replace_cleanup_and_atomic_state(self):
        config = {"docGlobs": ["docs/**/*.md"], "impactMap": []}
        for fault in ("before-replace", "after-replace"):
            with self.subTest(fault=fault):
                root = self.make_repo(config=config)
                config_path = self.config_path(root)
                original = read(config_path)
                env = os.environ.copy()
                env["DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT"] = fault
                proc = self.invoke(root, "--write", *self.expected(root), env=env)
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertTrue(proc.stderr.strip(), proc.stdout)
                lock = os.path.join(root, ".claude", "state", "docaudit-run", "lock")
                self.assertFalse(os.path.exists(lock))
                names = set(os.listdir(os.path.dirname(config_path)))
                self.assertEqual(names, {"audit-scope.json", "doc-audit.json", "state"})
                if fault == "before-replace":
                    self.assertEqual(read(config_path), original)
                else:
                    completed = json.loads(read(config_path))
                    self.assertEqual(completed["auditScope"]["path"], ".claude/audit-scope.json")
                    self.assertEqual(completed["impactMap"][-1]["source"], "audit-scope")

    def test_v_unlink_before_flock_stops_without_change(self):
        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        original = read(self.config_path(root))
        env = os.environ.copy()
        env["DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT"] = "unlink-before-flock"
        proc = self.invoke(root, "--write", *self.expected(root), env=env)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(read(self.config_path(root)), original)
        self.assertFalse(os.path.exists(os.path.join(
            root, ".claude", "state", "docaudit-run", "lock")))

    def test_v_expect_sha_mismatches_exit_four_without_change(self):
        wrong = "sha256:" + "0" * 64
        for kind in ("config", "scope"):
            with self.subTest(kind=kind):
                root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
                original = read(self.config_path(root))
                args = self.expected(root)
                args[1 if kind == "config" else 3] = wrong
                proc = self.invoke(root, "--write", *args)
                self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
                self.assertEqual(read(self.config_path(root)), original)
                self.assertFalse(os.path.exists(os.path.join(
                    root, ".claude", "state", "docaudit-run", "lock")))

    def test_v_replaces_only_source_entries_and_preserves_other_items(self):
        manual_note = {
            "changed": "manual.py", "impacts": ["docs/b.md"],
            "note": "auto: audit-scope hand-written and must survive",
        }
        other = {"changed": "other.py", "impacts": ["docs/a.md"], "source": "human"}
        old_auto = {
            "changed": "stale.py", "impacts": ["docs/a.md"],
            "source": "audit-scope", "note": "old",
        }
        root = self.make_repo(config={
            "docGlobs": ["docs/**/*.md"],
            "impactMap": [manual_note, old_auto, other],
        })
        final = self.import_existing(root)
        self.assertEqual(final["impactMap"][:2], [manual_note, other])
        self.assertEqual(len(final["impactMap"]), 3)
        self.assertEqual(final["impactMap"][2]["source"], "audit-scope")
        self.assertEqual(final["impactMap"][2]["changed"], "src/**.py")

    def test_v_base_config_rejects_existing_bad_sha_and_missing_base(self):
        draft = json.dumps({"docGlobs": ["docs/**/*.md"], "impactMap": []}) + "\n"
        draft_sha = sha(draft.encode())

        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        original = read(self.config_path(root))
        proc = self.invoke(
            root, "--write", "--base-config", "-",
            "--expect-base-config-sha", draft_sha,
            "--expect-scope-sha", sha(read(self.scope_path(root))), input_text=draft,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(read(self.config_path(root)), original)

        root = self.make_repo(config=ABSENT)
        proc = self.invoke(
            root, "--write", "--base-config", "-",
            "--expect-base-config-sha", "sha256:" + "0" * 64,
            "--expect-scope-sha", sha(read(self.scope_path(root))), input_text=draft,
        )
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(self.config_path(root)))

        root = self.make_repo(config=ABSENT)
        proc = self.invoke(
            root, "--write", "--expect-config-sha", "none",
            "--expect-scope-sha", sha(read(self.scope_path(root))),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(self.config_path(root)))
        self.assertIn("config absent: use --base-config -", proc.stderr + proc.stdout)

    def test_v_base_config_success_publishes_only_complete_config(self):
        draft = json.dumps({"docGlobs": ["docs/**/*.md"], "impactMap": []}) + "\n"
        root = self.make_repo(config=ABSENT)
        draft_file = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(lambda: os.path.exists(draft_file.name) and os.unlink(draft_file.name))
        draft_file.write(draft)
        draft_file.close()
        resume = os.path.join(root, "resume-base")
        env = os.environ.copy()
        env["DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT"] = "hold-lock:" + resume
        command = [
            sys.executable, SCRIPT, "--repo-root", root, "--write", "--base-config", "-",
            "--expect-base-config-sha", sha(draft.encode()),
            "--expect-scope-sha", sha(read(self.scope_path(root))),
        ]
        with open(draft_file.name, "r", encoding="utf-8") as stdin:
            proc = subprocess.Popen(command, stdin=stdin, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=env)
            lock = os.path.join(root, ".claude", "state", "docaudit-run", "lock")
            deadline = time.monotonic() + 10
            while not os.path.exists(lock) and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            try:
                self.assertIsNone(proc.poll(), "importer exited before hold-lock")
                self.assertFalse(os.path.exists(self.config_path(root)))
                write(resume, "continue")
                while proc.poll() is None:
                    if os.path.exists(self.config_path(root)):
                        observed = json.loads(read(self.config_path(root)))
                        self.assertIn("auditScope", observed)
                        self.assertTrue(any(
                            item.get("source") == "audit-scope"
                            for item in observed.get("impactMap", [])
                        ))
                    time.sleep(0.001)
                stdout, stderr = proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0, stdout + stderr)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()
        completed = json.loads(read(self.config_path(root)))
        self.assertEqual(completed["auditScope"]["rules"], 1)
        self.assertEqual(completed["impactMap"][0]["source"], "audit-scope")

    # PLAN §1.6 (vi)
    def test_vi_check_absent_not_imported_in_sync_and_four_drift_paths(self):
        absent = self.make_repo(scope=ABSENT, config=ABSENT)
        proc = self.invoke(absent, "--json")
        self.assertEqual((proc.returncode, self.output(proc)["state"]), (0, "absent"))

        not_imported = self.make_repo(config=ABSENT)
        proc = self.invoke(not_imported, "--json")
        self.assertEqual((proc.returncode, self.output(proc)["state"]), (2, "not-imported"))

        mutators = {
            "scope changed": lambda root, data: write(
                self.scope_path(root), '{"src/*.py":["docs/b.md"]}'
            ),
            "auto edited": lambda root, data: data["impactMap"][0].update(
                impacts=["docs/b.md"]
            ),
            "auto deleted": lambda root, data: data.update(impactMap=[]),
            "scope missing": lambda root, data: os.unlink(self.scope_path(root)),
        }
        for name, mutate in mutators.items():
            with self.subTest(name=name):
                root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
                data = self.import_existing(root)
                mutate(root, data)
                if name in ("auto edited", "auto deleted"):
                    write(self.config_path(root), json.dumps(data))
                proc = self.invoke(root, "--json")
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(self.output(proc)["state"], "drift")

        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        self.import_existing(root)
        proc = self.invoke(root, "--json")
        self.assertEqual((proc.returncode, self.output(proc)["state"]), (0, "in-sync"))

    def test_vi_multiset_detects_one_deleted_duplicate(self):
        scope = json.dumps({
            "src/*.py": ["docs/a.md"],
            "src/**.py": ["docs/a.md"],
        })
        root = self.make_repo(scope=scope,
                              config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        data = self.import_existing(root)
        self.assertEqual(len(data["impactMap"]), 2)
        del data["impactMap"][0]
        write(self.config_path(root), json.dumps(data))
        proc = self.invoke(root, "--json")
        out = self.output(proc)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(out["state"], "drift")
        self.assertEqual(len(out["diff"]["missing"]), 1)

    def test_vi_metadata_type_contract_rejects_invalid_forms(self):
        good = {
            "path": ".claude/audit-scope.json",
            "sha256": "0" * 64,
            "rules": 1,
            "importedAt": "2026-08-27T00:00:00+00:00",
        }
        cases = {
            "null": None,
            "non-object": [],
            "non-string path": dict(good, path=7),
            "absolute path": dict(good, path="/tmp/audit-scope.json"),
            "repo escape": dict(good, path="../audit-scope.json"),
            "bad sha": dict(good, sha256="sha256:" + "0" * 64),
            "bool rules": dict(good, rules=True),
            "non-string importedAt": dict(good, importedAt=7),
        }
        for name, meta in cases.items():
            with self.subTest(name=name):
                config = {"docGlobs": ["docs/**/*.md"], "impactMap": [], "auditScope": meta}
                root = self.make_repo(config=config)
                proc = self.invoke(root, "--json")
                out = self.output(proc)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(out["state"], "error")
                self.assertTrue(out["errors"])

    def test_vi_repeated_doc_glob_and_comma_is_one_literal_glob(self):
        scope = json.dumps({
            "src/a.py": ["docs/a.md"],
            "src/b.py": ["guide/b.md"],
        })
        root = self.make_repo(
            scope=scope, config=ABSENT,
            files=(("guide/b.md", "# b\n"), ("src/a.py", ""), ("src/b.py", "")),
        )
        proc = self.invoke(root, "--json", "--doc-glob", "docs/**/*.md",
                           "--doc-glob", "guide/**/*.md")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(len(self.output(proc)["translated"]), 2)

        root = self.make_repo(
            scope='{"src/*.py":["docs/a,b/x.md"]}', config=ABSENT,
            files=(("docs/a,b/x.md", "# comma\n"),),
        )
        proc = self.invoke(root, "--json", "--doc-glob", "docs/a,b/**/*.md")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        out = self.output(proc)
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["translated"][0]["impacts"], ["docs/a,b/x.md"])

    # PLAN §1.6 (vii)
    def test_vii_config_and_scope_containment_missing_and_symlink_contract(self):
        root = self.make_repo(scope=ABSENT, config=ABSENT)
        proc = self.invoke(root, "--config", ".claude/missing.json", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.output(proc)["state"], "absent")

        for option in ("--config", "--scope"):
            for unsafe in ("../outside.json",):
                with self.subTest(option=option, unsafe=unsafe):
                    proc = self.invoke(root, option, unsafe, "--json")
                    self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

        root = self.make_repo(scope=ABSENT, config=ABSENT)
        outside = os.path.join(root, "outside.json")
        write(outside, "{}")
        os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
        for option, rel in (("--config", ".claude/config-link.json"),
                            ("--scope", ".claude/scope-link.json")):
            with self.subTest(option=option):
                link = os.path.join(root, *rel.split("/"))
                os.symlink(outside, link)
                proc = self.invoke(root, option, rel, "--json")
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                os.unlink(link)

    def test_absolute_path_cases_v014(self):
        cases = {
            "real_real": True, "symlink_symlink": True, "symlink_real": True,
            "real_symlink": False, "outside": False, "sub_dotdot": False,
            "root_dotdot": False, "intermediate_symlink": False,
            "trailing_slash": False, "double_slash": False,
        }
        self.assertEqual(len(cases), 10)
        expected_ids = {f"{option}_{name}" for option in ("config", "scope") for name in cases}
        self.assertEqual(len(expected_ids), 20)
        seen = set()
        for option in ("config", "scope"):
            for name, accepted in cases.items():
                case_id = f"{option}_{name}"
                seen.add(case_id)
                with self.subTest(case_id=case_id):
                    root = self.make_repo(config={"docGlobs": ["docs/**/*.md"]})
                    real_root = os.path.realpath(root)
                    parent = os.path.dirname(root)
                    apparent = os.path.join(parent, "repo-link-" + os.path.basename(root))
                    os.symlink(root, apparent)
                    self.addCleanup(lambda p=apparent: os.path.lexists(p) and os.unlink(p))
                    filename = "doc-audit.json" if option == "config" else "audit-scope.json"
                    real_path = os.path.join(real_root, ".claude", filename)
                    apparent_path = os.path.join(apparent, ".claude", filename)
                    outside = os.path.join(parent, "outside-" + os.path.basename(root) + filename)
                    write(outside, "{}")
                    self.addCleanup(lambda p=outside: os.path.exists(p) and os.unlink(p))
                    alias = os.path.join(root, "alias")
                    os.symlink(os.path.join(root, ".claude"), alias)
                    if name == "real_real": repo_arg, value = root, real_path
                    elif name == "symlink_symlink": repo_arg, value = apparent, apparent_path
                    elif name == "symlink_real": repo_arg, value = apparent, real_path
                    elif name in ("real_symlink", "intermediate_symlink"):
                        repo_arg, value = root, os.path.join(alias, filename)
                    elif name == "outside": repo_arg, value = root, outside
                    elif name == "sub_dotdot": repo_arg, value = root, root + "/sub/../.claude/" + filename
                    elif name == "root_dotdot": repo_arg, value = root, root + "/../" + filename
                    elif name == "trailing_slash": repo_arg, value = root, real_path + "/"
                    else: repo_arg, value = root, root + "//.claude/" + filename
                    proc = self.invoke(repo_arg, "--" + option, value, "--json")
                    self.assertEqual(proc.returncode == 1, not accepted,
                                     proc.stdout + proc.stderr)
                    if not accepted:
                        self.assertTrue(self.output(proc)["errors"])
        self.assertEqual(seen, expected_ids)

    def test_vii_custom_scope_path_is_saved_in_metadata(self):
        root = self.make_repo(scope=ABSENT,
                              config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        custom = "config/scopes/project.json"
        write(self.scope_path(root, custom), '{"src/*.py":["docs/a.md"]}')
        subprocess.run(["git", "add", "-f", custom], cwd=root, check=True)
        final = self.import_existing(root, custom)
        self.assertEqual(final["auditScope"]["path"], custom)
        proc = self.invoke(root, "--scope", custom, "--json")
        self.assertEqual((proc.returncode, self.output(proc)["state"]), (0, "in-sync"))
        derived = self.invoke(root, "--json")
        self.assertEqual((derived.returncode, self.output(derived)["state"]), (0, "in-sync"))
        self.assertEqual(self.output(derived)["scopePath"], custom)

    # PLAN §1.6 (viii)
    def test_viii_generated_source_is_accepted_by_resolve_impact(self):
        root = self.make_repo(config={"docGlobs": ["docs/**/*.md"], "impactMap": []})
        self.import_existing(root)
        proc = subprocess.run(
            [sys.executable, RESOLVE_IMPACT, "--repo-root", root,
             "--config", self.config_path(root), "--expect-config-sha",
             sha(read(self.config_path(root))), "--changed", "-", "--mode", "incremental"],
            input="src/x.py\n", text=True, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        out = json.loads(proc.stdout)
        mapped = {item["path"]: item["provenance"] for item in out["impacted"]}
        self.assertIn(mapped.get("docs/a.md"), ("mapped", "both"))

    def test_dir_framework_fixture_scope_is_not_imported_with_24_rules_and_48_paths(self):
        """DoD (15): the fixed 951570b fixture stays not-imported and checks 48 paths."""
        scope_raw = read(os.path.join(FIXTURE_DIR, "audit-scope.json"))
        config_raw = read(os.path.join(FIXTURE_DIR, "doc-audit.json"))
        paths_raw = read(os.path.join(FIXTURE_DIR, "paths.txt"))
        self.assertEqual(hashlib.sha256(scope_raw).hexdigest(),
                         "d68186952fee273130685b329c1cd4727c34c55065866a054b51ab0629e0982d")
        self.assertEqual(hashlib.sha256(config_raw).hexdigest(),
                         "9723e2837c235c75fa28d32eb97f04d884d9a1d12ea001ea7e21bfd4bf44599c")
        self.assertEqual(hashlib.sha256(paths_raw).hexdigest(),
                         "b1a1356a14935bbd2aed214dbf7d732c25379213395f14ee4fd98d5689e7d91d")
        scope_fixture = json.loads(scope_raw)
        config_fixture = json.loads(config_raw)
        source_paths = paths_raw.decode("utf-8").splitlines()
        self.assertEqual(len(source_paths), 48)
        self.assertEqual(len(scope_fixture), 24)
        self.assertNotIn("auditScope", config_fixture)

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = temp.name
        for rel in source_paths:
            target = os.path.join(root, *rel.split("/"))
            write(target, b"")
        write(os.path.join(root, ".claude", "audit-scope.json"), scope_raw)
        write(os.path.join(root, ".claude", "doc-audit.json"), config_raw)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-f", "."], cwd=root, check=True)
        proc = self.invoke(root, "--check", "--json", "--doc-glob", "**/*.md")
        out = self.output(proc)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(out["state"], "not-imported")
        self.assertEqual(out["rules"], len(scope_fixture))
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["equivalenceChecked"], len(source_paths))


if __name__ == "__main__":
    unittest.main()
