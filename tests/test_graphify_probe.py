import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "graphify-probe.sh")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def update_stub(exit_code=0, create_output_dir=False):
    """A fake graphify that answers `update .` with a given exit code. When
    create_output_dir is set, it also `mkdir -p graphify-out` in the cwd it's
    invoked from, mirroring the real `graphify update .`'s confirmed behavior of
    creating graphify-out/ — `git check-ignore -q graphify-out` only matches a
    trailing-slash gitignore pattern against a path that actually exists as a
    directory on disk, so the probe's real-world ordering (update, THEN check)
    is load-bearing here too."""
    body = '#!/usr/bin/env bash\n'
    if create_output_dir:
        body += 'mkdir -p graphify-out\n'
    body += 'exit %d\n' % exit_code
    return body


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


def init_git_repo(repo):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)


class TestGraphifyProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"docGraph": {"bin": "graphify-does-not-exist-zzz"}})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "not-installed")
        self.assertFalse(out["gitignoreOk"])

    def test_json_emit_is_ascii_one_line(self):
        bin_name = "to\u2028ol-none"
        cfg = os.path.join(self.repo, ".claude", "json-emit.json")
        write(cfg, json.dumps({"docGraph": {"bin": bin_name}}))
        proc = subprocess.run(["bash", SCRIPT, "--config", cfg, "--repo-root", self.repo],
                              capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.isascii())
        self.assertEqual(len(proc.stdout.decode().splitlines()), 1)
        out = json.loads(proc.stdout)
        self.assertEqual(out["docGraphBin"], bin_name)
        self.assertEqual(out["reason"], "not-installed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"docGraph": {"enabled": False}})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")
        self.assertFalse(out["gitignoreOk"])

    def test_control_character_bins_are_rejected_or_normalized_when_disabled(self):
        for code in (*range(32), 127):
            with self.subTest(code=code):
                value = "tool" + chr(code)
                out = run_script(self.repo, {"docGraph": {"bin": value}})
                self.assertEqual(out["reason"], "invalid-config")
                self.assertEqual(out["docGraphBin"], "graphify")
                out = run_script(self.repo, {"docGraph": {"enabled": False, "bin": value}})
                self.assertEqual(out["reason"], "disabled-by-config")
                self.assertEqual(out["docGraphBin"], "graphify")
        self.assertFalse(out["gitignoreOk"])

    def test_gitignore_ok_true_via_git_check_ignore(self):
        init_git_repo(self.repo)
        write(os.path.join(self.repo, ".gitignore"), "graphify-out/\n")
        bindir = tempfile.mkdtemp()
        binpath = os.path.join(bindir, "graphifystub")
        make_exec(binpath, update_stub(0, create_output_dir=True))
        out = run_script(self.repo, {"docGraph": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertTrue(out["gitignoreOk"])

    def test_gitignore_missing_reports_false(self):
        init_git_repo(self.repo)
        # No .gitignore entry for graphify-out — git check-ignore exits 1.
        bindir = tempfile.mkdtemp()
        binpath = os.path.join(bindir, "graphifystub")
        make_exec(binpath, update_stub(0))
        out = run_script(self.repo, {"docGraph": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertFalse(out["gitignoreOk"])

    def test_update_failure_reports_update_failed(self):
        bindir = tempfile.mkdtemp()
        binpath = os.path.join(bindir, "graphifystub")
        make_exec(binpath, update_stub(1))
        out = run_script(self.repo, {"docGraph": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "update-failed")
        self.assertFalse(out["gitignoreOk"])

    def _default_stub(self):
        bindir = self.tmpdir()
        log = os.path.join(bindir, "calls.log")
        make_exec(os.path.join(bindir, "graphify"), '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % log)
        return log, {"PATH": bindir + os.pathsep + os.environ["PATH"]}

    def _sentinel_env(self, value):
        bindir = self.tmpdir()
        names = []
        for name in ("graphify", value, value.strip()):
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
        self.assertEqual(set(out), {"docGraphAvailable", "docGraphBin", "reason", "gitignoreOk"})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["docGraphBin"], "graphify")
        self.assertEqual(out["reason"], reason)
        self.assertFalse(out["gitignoreOk"])
        self.assertFalse(os.path.exists(log), "graphify must not be invoked")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "graphify-out")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".gitignore")))

    def test_absent_key_is_not_configured(self):
        """DoD (8): an absent key never probes the default binary."""
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {}, env), "not-configured", log)

    def test_empty_object_key_is_enabled(self):
        """DoD (8): an existing empty object enables the default binary."""
        log, env = self._default_stub()
        out = run_script(self.repo, {"docGraph": {}}, env)
        self.assertTrue(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertTrue(os.path.exists(log))

    def test_non_boolean_enabled_is_invalid_config(self):
        """DoD (8): enabled accepts JSON booleans only."""
        for value in ("false", 1):
            with self.subTest(value=value):
                log, env = self._default_stub()
                configured_log = os.path.join(tempfile.mkdtemp(), "configured.log")
                binpath = os.path.join(tempfile.mkdtemp(), "graphifystub")
                make_exec(binpath, '#!/usr/bin/env bash\necho "$@" >> "%s"\n' % configured_log)
                self._assert_unavailable(run_script(self.repo, {"docGraph": {"enabled": value, "bin": binpath}}, env), "invalid-config", log)
                self.assertFalse(os.path.exists(configured_log), "configured graphify must not be invoked")

    def test_non_object_key_is_invalid_config(self):
        """DoD (8): each seam key must hold an object."""
        for value in (True, "x", [], None):
            with self.subTest(value=value):
                log, env = self._default_stub()
                self._assert_unavailable(run_script(self.repo, {"docGraph": value}, env), "invalid-config", log)

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
                self._assert_unavailable(run_script(self.repo, {"docGraph": {"bin": value}}, env), "invalid-config", log)

    def test_omitted_config_flag_is_invalid_config(self):
        """DoD (8): omitting --config cannot enable the seam."""
        log, env = self._default_stub()
        self._assert_unavailable(run_raw(self.repo, ["--repo-root", self.repo], env), "invalid-config", log)

    def test_disabled_with_invalid_bin_is_disabled_by_config(self):
        """DoD (8): enabled:false has precedence over an invalid bin."""
        log, env = self._default_stub()
        self._assert_unavailable(run_script(self.repo, {"docGraph": {"enabled": False, "bin": []}}, env), "disabled-by-config", log)

    def test_bin_boundary_table(self):
        controls = set(range(32)) | {127}
        self.assertEqual(controls, set(range(32)) | {127})
        values = (["to" + chr(c) + "ol" for c in controls] +
                  [" graphify", "graphify ", " graphify ",
                   "\u00a0graphify", "   ", "\ud800"])
        for value in values:
            for enabled in (True, False):
                with self.subTest(value=repr(value), enabled=enabled):
                    env, markers = self._sentinel_env(value)
                    out = run_script(self.repo, {"docGraph": {
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
        env, markers = self._sentinel_env("custom-graphify")
        out = run_script(self.repo, {"docGraph": {
            "enabled": False, "bin": "custom-graphify"}}, env)
        self.assertEqual(out, {"docGraphAvailable": False,
                               "docGraphBin": "custom-graphify",
                               "reason": "disabled-by-config",
                               "gitignoreOk": False})
        self.assertEqual([os.path.exists(marker) for marker in markers],
                         [False] * len(markers))

    def test_bin_positive_paths(self):
        ids = {"space_path", "non_ascii_path", "quote_backslash", "dash_name"}
        self.assertEqual(ids, {"space_path", "non_ascii_path",
                               "quote_backslash", "dash_name"})
        for case_id, name in (("space_path", "dir with space/graphify"),
                              ("non_ascii_path", "égraphify"),
                              ("quote_backslash", 'q"\\graphify'),
                              ("dash_name", "-x")):
            bindir = self.tmpdir()
            path = os.path.join(bindir, name)
            log = os.path.join(bindir, "calls.log")
            make_exec(path, '#!/usr/bin/env bash\n'
                      'echo "$@" >> "%s"\n'
                      'exit 0\n' % log)
            configured = "-x" if case_id == "dash_name" else path
            env = {"PATH": bindir + os.pathsep + os.environ["PATH"]}
            if case_id == "non_ascii_path":
                env["PYTHONIOENCODING"] = "ascii"
            out = run_script(self.repo, {"docGraph": {"bin": configured}}, env)
            self.assertEqual(out["docGraphBin"], configured)
            with open(log, encoding="utf-8") as handle:
                calls = [line.rstrip("\n") for line in handle]
            self.assertEqual(calls, ["update ."])

    def test_output_key_sets_per_branch(self):
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        failed = os.path.join(bindir, "failed")
        make_exec(ok, update_stub(0))
        make_exec(failed, update_stub(1))
        outputs = [
            run_script(self.repo, {}),
            run_script(self.repo, {"docGraph": {"bin": "missing-graphify-cr2"}}),
            run_script(self.repo, {"docGraph": {"enabled": False}}),
            run_script(self.repo, {"docGraph": None}),
            run_script(self.repo, {"docGraph": {"bin": ok}}),
            run_script(self.repo, {"docGraph": {"bin": failed}}),
        ]
        expected_reasons = {"ok", "not-installed", "disabled-by-config",
                            "update-failed", "not-configured", "invalid-config"}
        self.assertEqual({out["reason"] for out in outputs}, expected_reasons)
        for out in outputs:
            self.assertEqual(set(out),
                             {"docGraphAvailable", "docGraphBin", "reason",
                              "gitignoreOk"})


if __name__ == "__main__":
    unittest.main()
