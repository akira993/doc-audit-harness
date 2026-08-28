import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "cocoindex-probe.sh")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def stub(log_path, exit_code=0):
    """A fake ccc that logs every subcommand it's called with to log_path (one
    line per invocation, space-joined args) and exits exit_code."""
    return (
        '#!/usr/bin/env bash\n'
        'echo "$@" >> "%s"\n'
        'exit %d\n' % (log_path, exit_code)
    )


def run_script(repo, config, extra_env=None):
    cfg = os.path.join(repo, ".claude", "doc-audit.json")
    write(cfg, json.dumps(config))
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(["bash", SCRIPT, "--config", cfg, "--repo-root", repo],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def run_raw(repo, args, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(["bash", SCRIPT, *args], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    assert len(p.stdout.splitlines()) == 1, p.stdout
    return json.loads(p.stdout), p


class TestCocoindexProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"semanticSearch": {"bin": "ccc-does-not-exist-zzz"}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"semanticSearch": {"enabled": False}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")

    def test_control_character_bins_are_rejected_or_normalized_when_disabled(self):
        for code in (*range(32), 127):
            with self.subTest(code=code):
                value = "tool" + chr(code)
                out = run_script(self.repo, {"semanticSearch": {"bin": value}})
                self.assertEqual(out["reason"], "invalid-config")
                self.assertEqual(out["semanticSearchBin"], "ccc")
                out = run_script(self.repo, {"semanticSearch": {"enabled": False, "bin": value}})
                self.assertEqual(out["reason"], "disabled-by-config")
                self.assertEqual(out["semanticSearchBin"], "ccc")

    def test_not_initialized_never_calls_init(self):
        # The single most safety-critical test in this whole plan: an absent
        # .cocoindex_code/ MUST short-circuit to not-initialized WITHOUT ever
        # invoking the stub with "init" (ccc init has a confirmed .gitignore
        # write side effect the report-only audit phase must never trigger).
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log))
        # No .cocoindex_code/ fixture created.
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "not-initialized")
        # Assert on the stub's call log, not just the JSON output.
        self.assertFalse(os.path.exists(log), "ccc must never be invoked when not-initialized")

    def test_stub_installed_reports_ok(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log))
        write(os.path.join(self.repo, ".cocoindex_code", "settings.yml"), "{}\n")
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "ok")
        with open(log, encoding="utf-8") as f:
            calls = [ln.strip() for ln in f if ln.strip()]
        # ccc index takes NO path argument (real-machine confirmed: `ccc index .`
        # errors "unexpected extra argument(s)") — unlike codegraph/graphify.
        self.assertEqual(calls, ["index"])

    def test_stub_index_failure_reports_index_failed(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log, exit_code=1))
        write(os.path.join(self.repo, ".cocoindex_code", "settings.yml"), "{}\n")
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "index-failed")

    def _marker(self):
        write(os.path.join(self.repo, ".cocoindex_code", "settings.yml"), "{}\n")

    def _default_stub(self):
        bindir = self.tmpdir()
        log = os.path.join(bindir, "calls.log")
        make_exec(os.path.join(bindir, "ccc"), stub(log))
        return log, {"PATH": bindir + os.pathsep + os.environ["PATH"]}

    def _sentinel_env(self, value):
        bindir = self.tmpdir()
        names = []
        for name in ("ccc", value, value.strip()):
            if not name or "\0" in name or name in names:
                continue
            try:
                name.encode("utf-8")
            except UnicodeEncodeError:
                continue
            names.append(name)
        markers = []
        for index, name in enumerate(names):
            marker = os.path.join(bindir, "marker-%d" % index)
            make_exec(os.path.join(bindir, name),
                      '#!/bin/sh\nprintf called >> "%s"\n' % marker)
            markers.append(marker)
        return {"PATH": bindir + os.pathsep + os.environ["PATH"]}, markers

    def _assert_unavailable(self, out, reason, log):
        self.assertEqual(set(out), {"semanticSearchAvailable", "semanticSearchBin", "reason"})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["semanticSearchBin"], "ccc")
        self.assertEqual(out["reason"], reason)
        self.assertFalse(os.path.exists(log), "ccc must not be invoked")
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".gitignore")))

    def test_absent_key_is_not_configured(self):
        """DoD (8): an absent key never probes the default binary."""
        self._marker()
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {}, env), "not-configured", log)

    def test_empty_object_key_is_enabled(self):
        """DoD (8): an existing empty object enables the default binary."""
        self._marker()
        log, env = self._default_stub()
        out = run_script(self.repo, {"semanticSearch": {}}, env)
        self.assertTrue(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertTrue(os.path.exists(log))

    def test_non_boolean_enabled_is_invalid_config(self):
        """DoD (8): enabled accepts JSON booleans only."""
        for value in ("false", 1):
            with self.subTest(value=value):
                self._marker()
                log, env = self._default_stub()
                configured_log = os.path.join(tempfile.mkdtemp(), "configured.log")
                binpath = os.path.join(tempfile.mkdtemp(), "cccstub")
                make_exec(binpath, stub(configured_log))
                self._assert_unavailable(run_script(self.repo, {"semanticSearch": {"enabled": value, "bin": binpath}}, env), "invalid-config", log)
                self.assertFalse(os.path.exists(configured_log), "configured ccc must not be invoked")

    def test_non_object_key_is_invalid_config(self):
        """DoD (8): each seam key must hold an object."""
        for value in (True, "x", [], None):
            with self.subTest(value=value):
                self._marker()
                log, env = self._default_stub()
                self._assert_unavailable(run_script(self.repo, {"semanticSearch": value}, env), "invalid-config", log)

    def test_invalid_json_config_is_invalid_config(self):
        """DoD (8): malformed JSON is rejected by the standalone probe."""
        self._marker()
        log, env = self._default_stub()
        cfg = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(cfg, "{")
        out, _ = run_raw(self.repo, ["--config", cfg, "--repo-root", self.repo], env)
        self._assert_unavailable(out, "invalid-config", log)

    def test_missing_config_file_is_invalid_config(self):
        """DoD (8): a missing config file is invalid-config."""
        self._marker()
        log, env = self._default_stub()
        out, _ = run_raw(self.repo, ["--config", os.path.join(self.repo, "missing.json"), "--repo-root", self.repo], env)
        self._assert_unavailable(out, "invalid-config", log)

    def test_non_object_top_level_is_invalid_config(self):
        """DoD (8): the config top level must be an object."""
        self._marker()
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, [], env), "invalid-config", log)

    def test_non_string_bin_is_invalid_config(self):
        """DoD (8): bin must be a non-empty string."""
        for value in ([], 1, None, ""):
            with self.subTest(value=value):
                self._marker()
                log, env = self._default_stub()
                self._assert_unavailable(run_script(self.repo, {"semanticSearch": {"bin": value}}, env), "invalid-config", log)

    def test_omitted_config_flag_is_invalid_config(self):
        """DoD (8): omitting --config cannot enable the seam."""
        self._marker()
        log, env = self._default_stub()
        out, _ = run_raw(self.repo, ["--repo-root", self.repo], env)
        self._assert_unavailable(out, "invalid-config", log)

    def test_disabled_with_invalid_bin_is_disabled_by_config(self):
        """DoD (8): enabled:false has precedence over an invalid bin."""
        self._marker()
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {"semanticSearch": {"enabled": False, "bin": []}}, env), "disabled-by-config", log)

    def test_non_finite_or_non_number_min_score_is_invalid_config(self):
        """DoD (8): minScore must be a finite non-boolean JSON number."""
        for value in ("0.4", True, None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                self._marker()
                log, env = self._default_stub()
                configured_log = os.path.join(tempfile.mkdtemp(), "configured.log")
                binpath = os.path.join(tempfile.mkdtemp(), "cccstub")
                make_exec(binpath, stub(configured_log))
                self._assert_unavailable(run_script(self.repo, {"semanticSearch": {"bin": binpath, "minScore": value}}, env), "invalid-config", log)
                self.assertFalse(os.path.exists(configured_log), "configured ccc must not be invoked")

    def test_disabled_with_invalid_min_score_is_disabled_by_config(self):
        """DoD (8): enabled:false has precedence over an invalid minScore."""
        self._marker()
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {"semanticSearch": {"enabled": False, "minScore": "x"}}, env), "disabled-by-config", log)

    def test_legacy_dir_without_settings_is_not_initialized(self):
        """DoD (12): a legacy directory without settings.yml is not initialized."""
        os.makedirs(os.path.join(self.repo, ".cocoindex_code"), exist_ok=True)
        log, env = self._default_stub()
        out = run_script(self.repo, {"semanticSearch": {}}, env)
        self._assert_unavailable(out, "not-initialized", log)

    def _index_mutator(self, content, exit_code=0):
        bindir = tempfile.mkdtemp()
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, '#!/usr/bin/env bash\nprintf "%s" >> .gitignore\nexit %d\n' % (content, exit_code))
        return binpath

    def test_index_that_modifies_gitignore_is_reported(self):
        """DoD (13): an index write is reported and never reverted."""
        self._marker()
        write(os.path.join(self.repo, ".gitignore"), "before\n")
        binpath = self._index_mutator("added\\n")
        out = run_script(self.repo, {"semanticSearch": {"bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "gitignore-modified")
        with open(os.path.join(self.repo, ".gitignore"), "rb") as handle:
            self.assertEqual(handle.read(), b"before\nadded\n")

    def test_index_that_creates_gitignore_is_reported(self):
        """DoD (13): a newly created .gitignore is reported and retained."""
        self._marker()
        binpath = self._index_mutator("created\\n")
        out = run_script(self.repo, {"semanticSearch": {"bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "gitignore-modified")
        with open(os.path.join(self.repo, ".gitignore"), "rb") as handle:
            self.assertEqual(handle.read(), b"created\n")

    def test_gitignore_change_wins_over_index_failure(self):
        """DoD (13): a .gitignore change takes precedence over index failure."""
        self._marker()
        binpath = self._index_mutator("added\\n", exit_code=1)
        out = run_script(self.repo, {"semanticSearch": {"bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "gitignore-modified")
        with open(os.path.join(self.repo, ".gitignore"), "rb") as handle:
            self.assertEqual(handle.read(), b"added\n")

    def test_gitignore_fingerprint_does_not_depend_on_shasum(self):
        """Final review P2: hashlib still detects changes when shasum is unavailable."""
        self._marker()
        write(os.path.join(self.repo, ".gitignore"), "before\n")
        binpath = self._index_mutator("added\\n")
        bindir = tempfile.mkdtemp()
        make_exec(os.path.join(bindir, "shasum"), "#!/usr/bin/env bash\nexit 127\n")
        out = run_script(
            self.repo,
            {"semanticSearch": {"bin": binpath}},
            {"PATH": bindir + os.pathsep + os.environ["PATH"]},
        )
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "gitignore-modified")
        with open(os.path.join(self.repo, ".gitignore"), "rb") as handle:
            self.assertEqual(handle.read(), b"before\nadded\n")

    def test_gitignore_fingerprint_failure_skips_index(self):
        """Final review P2: fingerprint failure degrades before invoking ccc index."""
        self._marker()
        os.makedirs(os.path.join(self.repo, ".gitignore"))
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log))
        cfg = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(cfg, json.dumps({"semanticSearch": {"bin": binpath}}))
        out, proc = run_raw(self.repo, ["--config", cfg, "--repo-root", self.repo])
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "index-failed")
        self.assertFalse(os.path.exists(log), "ccc must not run when fingerprinting fails")
        self.assertEqual(len(proc.stderr.splitlines()), 1)

    def test_bin_boundary_table(self):
        controls = set(range(32)) | {127}
        self.assertEqual(controls, set(range(32)) | {127})
        values = (["to" + chr(c) + "ol" for c in controls] +
                  [" ccc", "ccc ", " ccc ", "\u00a0ccc", "   ", "\ud800"])
        for value in values:
            for enabled in (True, False):
                with self.subTest(value=repr(value), enabled=enabled):
                    self._marker()
                    env, markers = self._sentinel_env(value)
                    out = run_script(self.repo, {"semanticSearch": {
                        "enabled": enabled, "bin": value}}, env)
                    self._assert_unavailable(
                        out,
                        "invalid-config" if enabled else "disabled-by-config",
                        markers[0],
                    )
                    self.assertEqual(
                        [os.path.exists(marker) for marker in markers],
                        [False] * len(markers),
                    )
        self._marker()
        env, markers = self._sentinel_env("custom-ccc")
        out = run_script(self.repo, {"semanticSearch": {
            "enabled": False, "bin": "custom-ccc"}}, env)
        self.assertEqual(out, {"semanticSearchAvailable": False,
                               "semanticSearchBin": "custom-ccc",
                               "reason": "disabled-by-config"})
        self.assertEqual([os.path.exists(marker) for marker in markers],
                         [False] * len(markers))

    def test_bin_positive_paths(self):
        ids = {"space_path", "non_ascii_path", "quote_backslash", "dash_name"}
        self.assertEqual(ids, {"space_path", "non_ascii_path",
                               "quote_backslash", "dash_name"})
        self._marker()
        for case_id, name in (("space_path", "dir with space/ccc"),
                              ("non_ascii_path", "éccc"),
                              ("quote_backslash", 'q"\\ccc'),
                              ("dash_name", "-x")):
            bindir = self.tmpdir()
            path = os.path.join(bindir, name)
            log = os.path.join(bindir, "calls.log")
            make_exec(path, stub(log))
            configured = "-x" if case_id == "dash_name" else path
            env = {"PATH": bindir + os.pathsep + os.environ["PATH"]}
            if case_id == "non_ascii_path":
                env["PYTHONIOENCODING"] = "ascii"
            out = run_script(self.repo, {"semanticSearch": {"bin": configured}}, env)
            self.assertEqual(out["semanticSearchBin"], configured)
            with open(log, encoding="utf-8") as handle:
                calls = [line.rstrip("\n") for line in handle]
            self.assertEqual(calls, ["index"])

    def test_output_key_sets_per_branch(self):
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        failed = os.path.join(bindir, "failed")
        mutator = os.path.join(bindir, "mutator")
        make_exec(ok, stub(os.path.join(bindir, "ok.log")))
        make_exec(failed, stub(os.path.join(bindir, "failed.log"), exit_code=1))
        make_exec(mutator, '#!/usr/bin/env bash\n'
                  'printf changed >> .gitignore\n'
                  'exit 0\n')

        configured_repo = self.tmpdir()
        write(os.path.join(configured_repo, ".cocoindex_code", "settings.yml"), "{}\n")
        uninitialized_repo = self.tmpdir()
        mutating_repo = self.tmpdir()
        write(os.path.join(mutating_repo, ".cocoindex_code", "settings.yml"), "{}\n")
        outputs = [
            run_script(configured_repo, {}),
            run_script(configured_repo, {"semanticSearch": {
                "bin": "missing-ccc-cr2"}}),
            run_script(configured_repo, {"semanticSearch": {"enabled": False}}),
            run_script(configured_repo, {"semanticSearch": None}),
            run_script(configured_repo, {"semanticSearch": {"bin": ok}}),
            run_script(configured_repo, {"semanticSearch": {"bin": failed}}),
            run_script(uninitialized_repo, {"semanticSearch": {"bin": ok}}),
            run_script(mutating_repo, {"semanticSearch": {"bin": mutator}}),
        ]
        expected_reasons = {"ok", "not-installed", "disabled-by-config",
                            "not-initialized", "index-failed", "not-configured",
                            "invalid-config", "gitignore-modified"}
        self.assertEqual({out["reason"] for out in outputs}, expected_reasons)
        for out in outputs:
            self.assertEqual(set(out),
                             {"semanticSearchAvailable", "semanticSearchBin",
                              "reason"})


if __name__ == "__main__":
    unittest.main()
