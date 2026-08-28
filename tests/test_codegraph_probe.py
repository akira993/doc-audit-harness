import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "codegraph-probe.sh")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def stub(log_path, exit_code=0):
    """A fake codegraph that logs every subcommand it's called with to log_path
    (one line per invocation, space-joined args) and exits exit_code."""
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
    return json.loads(p.stdout)


class TestCodegraphProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"symbolGraph": {"bin": "codegraph-does-not-exist-zzz"}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"symbolGraph": {"enabled": False}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")

    def test_control_character_bins_are_rejected_or_normalized_when_disabled(self):
        for code in (*range(32), 127):
            with self.subTest(code=code):
                value = "tool" + chr(code)
                out = run_script(self.repo, {"symbolGraph": {"bin": value}})
                self.assertEqual(out["reason"], "invalid-config")
                self.assertEqual(out["symbolGraphBin"], "codegraph")
                out = run_script(self.repo, {"symbolGraph": {"enabled": False, "bin": value}})
                self.assertEqual(out["reason"], "disabled-by-config")
                self.assertEqual(out["symbolGraphBin"], "codegraph")

    def test_stub_installed_fresh_calls_init(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log))
        # No pre-existing .codegraph/ — probe must call `init .`.
        out = run_script(self.repo, {"symbolGraph": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertEqual(out["symbolGraphBin"], binpath)
        with open(log, encoding="utf-8") as f:
            calls = [ln.strip() for ln in f if ln.strip()]
        self.assertEqual(calls, ["init ."])

    def test_stub_installed_existing_calls_sync(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log))
        # Pre-create .codegraph/ fixture — probe must call `sync .`, not `init .`
        # (a bare `init` against an existing .codegraph/ is rejected, confirmed).
        os.makedirs(os.path.join(self.repo, ".codegraph"), exist_ok=True)
        out = run_script(self.repo, {"symbolGraph": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        with open(log, encoding="utf-8") as f:
            calls = [ln.strip() for ln in f if ln.strip()]
        self.assertEqual(calls, ["sync ."])

    def test_stub_command_failure_reports_index_failed(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log, exit_code=1))
        out = run_script(self.repo, {"symbolGraph": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "index-failed")

    def _default_stub(self):
        bindir = self.tmpdir()
        log = os.path.join(bindir, "calls.log")
        make_exec(os.path.join(bindir, "codegraph"), '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % log)
        return log, {"PATH": bindir + os.pathsep + os.environ["PATH"]}

    def _sentinel_env(self, value):
        bindir = self.tmpdir()
        names = []
        for name in ("codegraph", value, value.strip()):
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
        self.assertEqual(set(out), {"symbolGraphAvailable", "symbolGraphBin", "reason"})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["symbolGraphBin"], "codegraph")
        self.assertEqual(out["reason"], reason)
        self.assertFalse(os.path.exists(log), "codegraph must not be invoked")
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".codegraph")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".gitignore")))

    def test_absent_key_is_not_configured(self):
        """DoD (8): an absent key never probes the default binary."""
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {}, env), "not-configured", log)

    def test_empty_object_key_is_enabled(self):
        """DoD (8): an existing empty object enables the default binary."""
        log, env = self._default_stub()
        out = run_script(self.repo, {"symbolGraph": {}}, env)
        self.assertTrue(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertTrue(os.path.exists(log))

    def test_non_boolean_enabled_is_invalid_config(self):
        """DoD (8): enabled accepts JSON booleans only."""
        for value in ("false", 1):
            with self.subTest(value=value):
                log, env = self._default_stub()
                configured_log = os.path.join(tempfile.mkdtemp(), "configured.log")
                binpath = os.path.join(tempfile.mkdtemp(), "codegraphstub")
                make_exec(binpath, '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % configured_log)
                self._assert_unavailable(run_script(self.repo, {"symbolGraph": {"enabled": value, "bin": binpath}}, env), "invalid-config", log)
                self.assertFalse(os.path.exists(configured_log), "configured codegraph must not be invoked")

    def test_non_object_key_is_invalid_config(self):
        """DoD (8): each seam key must hold an object."""
        for value in (True, "x", [], None):
            with self.subTest(value=value):
                log, env = self._default_stub()
                self._assert_unavailable(run_script(self.repo, {"symbolGraph": value}, env), "invalid-config", log)

    def test_invalid_json_config_is_invalid_config(self):
        """DoD (8): malformed JSON is rejected by the standalone probe."""
        log, env = self._default_stub()
        cfg = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(cfg, "{")
        self._assert_unavailable(run_raw(self.repo, ["--config", cfg, "--repo-root", self.repo], env), "invalid-config", log)

    def test_missing_config_file_is_invalid_config(self):
        """DoD (8): a missing config file is invalid-config."""
        log, env = self._default_stub()
        self._assert_unavailable(run_raw(self.repo, ["--config", os.path.join(self.repo, "missing.json"), "--repo-root", self.repo], env), "invalid-config", log)

    def test_non_object_top_level_is_invalid_config(self):
        """DoD (8): the config top level must be an object."""
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, [], env), "invalid-config", log)

    def test_non_string_bin_is_invalid_config(self):
        """DoD (8): bin must be a non-empty string."""
        for value in ([], 1, None, ""):
            with self.subTest(value=value):
                log, env = self._default_stub()
                self._assert_unavailable(run_script(self.repo, {"symbolGraph": {"bin": value}}, env), "invalid-config", log)

    def test_omitted_config_flag_is_invalid_config(self):
        """DoD (8): omitting --config cannot enable the seam."""
        log, env = self._default_stub()
        self._assert_unavailable(run_raw(self.repo, ["--repo-root", self.repo], env), "invalid-config", log)

    def test_disabled_with_invalid_bin_is_disabled_by_config(self):
        """DoD (8): enabled:false has precedence over an invalid bin."""
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {"symbolGraph": {"enabled": False, "bin": []}}, env), "disabled-by-config", log)

    def test_bin_boundary_table(self):
        controls = set(range(32)) | {127}
        self.assertEqual(controls, set(range(32)) | {127})
        values = (["to" + chr(c) + "ol" for c in controls] +
                  [" codegraph", "codegraph ", " codegraph ",
                   "\u00a0codegraph", "   ", "\ud800"])
        for value in values:
            for enabled in (True, False):
                with self.subTest(value=repr(value), enabled=enabled):
                    env, markers = self._sentinel_env(value)
                    out = run_script(self.repo, {"symbolGraph": {
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
        env, markers = self._sentinel_env("custom-codegraph")
        out = run_script(self.repo, {"symbolGraph": {
            "enabled": False, "bin": "custom-codegraph"}}, env)
        self.assertEqual(out, {"symbolGraphAvailable": False,
                               "symbolGraphBin": "custom-codegraph",
                               "reason": "disabled-by-config"})
        self.assertEqual([os.path.exists(marker) for marker in markers],
                         [False] * len(markers))

    def test_bin_positive_paths(self):
        ids = {"space_path", "non_ascii_path", "quote_backslash", "dash_name"}
        self.assertEqual(ids, {"space_path", "non_ascii_path",
                               "quote_backslash", "dash_name"})
        for case_id, name in (("space_path", "dir with space/codegraph"),
                              ("non_ascii_path", "écodegraph"),
                              ("quote_backslash", 'q"\\codegraph'),
                              ("dash_name", "-x")):
            bindir = self.tmpdir()
            path = os.path.join(bindir, name)
            log = os.path.join(bindir, "calls.log")
            make_exec(path, stub(log))
            configured = "-x" if case_id == "dash_name" else path
            env = {"PATH": bindir + os.pathsep + os.environ["PATH"]}
            if case_id == "non_ascii_path":
                env["PYTHONIOENCODING"] = "ascii"
            out = run_script(self.repo, {"symbolGraph": {"bin": configured}}, env)
            self.assertEqual(out["symbolGraphBin"], configured)
            with open(log, encoding="utf-8") as handle:
                calls = [line.rstrip("\n") for line in handle]
            self.assertEqual(calls, ["init ."])

    def test_output_key_sets_per_branch(self):
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        failed = os.path.join(bindir, "failed")
        make_exec(ok, stub(os.path.join(bindir, "ok.log")))
        make_exec(failed, stub(os.path.join(bindir, "failed.log"), exit_code=1))
        outputs = [
            run_script(self.repo, {}),
            run_script(self.repo, {"symbolGraph": {"bin": "missing-codegraph-cr2"}}),
            run_script(self.repo, {"symbolGraph": {"enabled": False}}),
            run_script(self.repo, {"symbolGraph": None}),
            run_script(self.repo, {"symbolGraph": {"bin": ok}}),
            run_script(self.repo, {"symbolGraph": {"bin": failed}}),
        ]
        expected_reasons = {"ok", "not-installed", "disabled-by-config",
                            "index-failed", "not-configured", "invalid-config"}
        self.assertEqual({out["reason"] for out in outputs}, expected_reasons)
        for out in outputs:
            self.assertEqual(set(out),
                             {"symbolGraphAvailable", "symbolGraphBin", "reason"})


if __name__ == "__main__":
    unittest.main()
