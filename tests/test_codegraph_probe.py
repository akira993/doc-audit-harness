import hashlib, json, os, stat, subprocess, tempfile, unittest

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
    """A fake codegraph that logs its complete invocation as one JSON line."""
    diagnostic = "FAKE-DIAG-%d" % exit_code
    return """#!/usr/bin/env python3
import json, os, sys
stdin_eof = sys.stdin.read() == ""
with open(%r, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({
        "argv": sys.argv[1:],
        "cwd": os.path.realpath(os.getcwd()),
        "CODEGRAPH_DIR": os.environ.get("CODEGRAPH_DIR"),
        "stdin_eof": stdin_eof,
    }, ensure_ascii=True, separators=(",", ":")) + "\\n")
if %d:
    print(%r, file=sys.stderr)
raise SystemExit(%d)
""" % (log_path, exit_code, diagnostic, exit_code)


def read_calls(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def assert_call(testcase, log_path, repo, argv, dirname=".codegraph"):
    testcase.assertEqual(read_calls(log_path), [{
        "argv": argv,
        "cwd": os.path.realpath(repo),
        "CODEGRAPH_DIR": dirname,
        "stdin_eof": True,
    }])


def run_script(repo, config, extra_env=None):
    cfg = os.path.join(repo, ".claude", "doc-audit.json")
    write(cfg, json.dumps(config))
    with open(cfg, "rb") as handle:
        expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    env = dict(os.environ)
    env.pop("CODEGRAPH_DIR", None)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(["bash", SCRIPT, "--config", cfg, "--expect-config-sha", expected, "--repo-root", repo],
                       capture_output=True, text=True, env=env,
                       input="STDIN-SENTINEL\n", timeout=30)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def run_process(repo, config, extra_env=None):
    cfg = os.path.join(repo, ".claude", "doc-audit.json")
    write(cfg, json.dumps(config))
    with open(cfg, "rb") as handle:
        expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    env = dict(os.environ)
    env.pop("CODEGRAPH_DIR", None)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(["bash", SCRIPT, "--config", cfg, "--expect-config-sha", expected, "--repo-root", repo],
                       capture_output=True, text=True, env=env,
                       input="STDIN-SENTINEL\n", timeout=30)
    assert p.returncode == 0, p.stderr
    assert len(p.stdout.splitlines()) == 1, p.stdout
    return p, json.loads(p.stdout)


def raw_process(repo, args, extra_env=None):
    env = dict(os.environ)
    env.pop("CODEGRAPH_DIR", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(["bash", SCRIPT, *args], capture_output=True, text=True,
                          env=env, input="STDIN-SENTINEL\n", timeout=30)


def run_raw(repo, args, extra_env=None):
    args = list(args)
    if "--config" in args and "--expect-config-sha" not in args:
        cfg = args[args.index("--config") + 1]
        with open(cfg, "rb") as handle:
            expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        args.extend(["--expect-config-sha", expected])
    p = raw_process(repo, args, extra_env)
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

    def fake(self, exit_code=0):
        bindir = self.tmpdir()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log, exit_code=exit_code))
        return binpath, log

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"symbolGraph": {"bin": "codegraph-does-not-exist-zzz"}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_json_emit_is_ascii_one_line(self):
        bin_name = "to\u2028ol-none"
        cfg = os.path.join(self.repo, ".claude", "json-emit.json")
        write(cfg, json.dumps({"symbolGraph": {"bin": bin_name}}))
        with open(cfg, "rb") as handle:
            expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        proc = subprocess.run(["bash", SCRIPT, "--config", cfg, "--expect-config-sha", expected, "--repo-root", self.repo],
                              capture_output=True, input=b"STDIN-SENTINEL\n",
                              timeout=30, env={k: v for k, v in os.environ.items()
                                               if k != "CODEGRAPH_DIR"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.isascii())
        self.assertEqual(len(proc.stdout.decode().splitlines()), 1)
        out = json.loads(proc.stdout)
        self.assertEqual(out["symbolGraphBin"], bin_name)
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
        assert_call(self, log, self.repo, ["init", "."])

    def test_stub_installed_existing_calls_sync(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log))
        # A regular codegraph.db is the initialization proof used for `sync .`.
        os.makedirs(os.path.join(self.repo, ".codegraph"), exist_ok=True)
        write(os.path.join(self.repo, ".codegraph", "codegraph.db"), "index")
        out = run_script(self.repo, {"symbolGraph": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["sync", "."])

    def test_stub_command_failure_reports_index_failed(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "codegraphstub")
        make_exec(binpath, stub(log, exit_code=1))
        out = run_script(self.repo, {"symbolGraph": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "index-failed")
        assert_call(self, log, self.repo, ["init", "."])

    def _default_stub(self):
        bindir = self.tmpdir()
        log = os.path.join(bindir, "calls.log")
        make_exec(os.path.join(bindir, "codegraph"), stub(log))
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

    def test_invalid_json_config_stops(self):
        """A malformed sealed config is a hard input error."""
        log, env = self._default_stub()
        cfg = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(cfg, "{")
        with open(cfg, "rb") as handle:
            expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        proc = raw_process(self.repo, ["--config", cfg, "--expect-config-sha", expected, "--repo-root", self.repo], env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("sealed-config:", proc.stderr)
        self.assertFalse(os.path.exists(log))

    def test_missing_config_file_stops(self):
        """An unreadable sealed config is a hard input error."""
        log, env = self._default_stub()
        proc = raw_process(self.repo, ["--config", os.path.join(self.repo, "missing.json"),
                                       "--expect-config-sha", "sha256:" + "0" * 64,
                                       "--repo-root", self.repo], env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("sealed-config:", proc.stderr)
        self.assertFalse(os.path.exists(log))

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

    def test_omitted_config_flag_stops(self):
        """The config flag is mandatory for a shell consumer."""
        log, env = self._default_stub()
        proc = raw_process(self.repo, ["--repo-root", self.repo], env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--config required", proc.stderr)
        self.assertFalse(os.path.exists(log))

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
            assert_call(self, log, self.repo, ["init", "."])

    def test_n1_ds_store_only_calls_init(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph", ".DS_Store"), "metadata")
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["init", "."])

    def test_n2_gitignore_only_calls_init(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph", ".gitignore"), "*")
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["init", "."])

    def test_n3_empty_directory_calls_init(self):
        binpath, log = self.fake()
        os.makedirs(os.path.join(self.repo, ".codegraph"))
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["init", "."])

    def test_n4_zero_byte_database_calls_sync(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph", "codegraph.db"), "")
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["sync", "."])

    def test_n5_database_directory_is_not_touched(self):
        binpath, log = self.fake()
        os.makedirs(os.path.join(self.repo, ".codegraph", "codegraph.db"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("not a regular file", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n5b_database_fifo_is_not_touched(self):
        binpath, log = self.fake()
        os.makedirs(os.path.join(self.repo, ".codegraph"))
        os.mkfifo(os.path.join(self.repo, ".codegraph", "codegraph.db"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("not a regular file", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n6_dangling_database_symlink_is_not_touched(self):
        binpath, log = self.fake()
        os.makedirs(os.path.join(self.repo, ".codegraph"))
        os.symlink("missing.db", os.path.join(self.repo, ".codegraph", "codegraph.db"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("symlink", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n7_database_symlink_to_file_is_not_touched(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, "real.db"), "index")
        os.makedirs(os.path.join(self.repo, ".codegraph"))
        os.symlink(os.path.join(self.repo, "real.db"),
                   os.path.join(self.repo, ".codegraph", "codegraph.db"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("symlink", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n8_index_directory_symlink_is_not_touched(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, "real-index", "codegraph.db"), "index")
        os.symlink(os.path.join(self.repo, "real-index"),
                   os.path.join(self.repo, ".codegraph"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("symlink", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n8b_dangling_index_directory_symlink_is_not_touched(self):
        binpath, log = self.fake()
        os.symlink("missing-index", os.path.join(self.repo, ".codegraph"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("symlink", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n9_index_directory_file_is_not_touched(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph"), "not a directory")
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("not a directory", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n9b_index_directory_fifo_is_not_touched(self):
        binpath, log = self.fake()
        os.mkfifo(os.path.join(self.repo, ".codegraph"))
        proc, out = run_process(self.repo, {"symbolGraph": {"bin": binpath}})
        self.assertEqual(out["reason"], "index-failed")
        self.assertIn("not a directory", proc.stderr)
        self.assertEqual(read_calls(log), [])

    def test_n10_custom_directory_database_calls_sync(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph-win", "codegraph.db"), "index")
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}},
                         {"CODEGRAPH_DIR": ".codegraph-win"})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["sync", "."], ".codegraph-win")
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".codegraph")))

    def test_n11_custom_directory_ignores_default_database(self):
        binpath, log = self.fake()
        write(os.path.join(self.repo, ".codegraph", "codegraph.db"), "index")
        out = run_script(self.repo, {"symbolGraph": {"bin": binpath}},
                         {"CODEGRAPH_DIR": ".codegraph-win"})
        self.assertEqual(out["reason"], "ok")
        assert_call(self, log, self.repo, ["init", "."], ".codegraph-win")

    def test_n12_codegraph_dir_resolution_table(self):
        invalid = ["../x", "foo..bar", "a/b", "a\\b", ".", "/abs", "", "   ", "\u00a0"]
        valid = [
            (" .codegraph-win ", ".codegraph-win"),
            ("\u00a0.codegraph-win\u00a0", ".codegraph-win"),
            ("\ufeff.codegraph-win", ".codegraph-win"),
            (".codegraph", ".codegraph"),
            (".CodeGraph-Win", ".CodeGraph-Win"),
            ("索引", "索引"),
            ("foo bar", "foo bar"),
            ("foo\nbar", "foo\nbar"),
        ]
        trim = ["\t", "\n", "\v", "\f", "\r", " ", "\u00a0", "\u1680"]
        trim += [chr(code) for code in range(0x2000, 0x200b)]
        trim += ["\u2028", "\u2029", "\u202f", "\u205f", "\u3000", "\ufeff"]
        keep = ["\x1c", "\x1d", "\x1e", "\x1f", "\x85"]
        cases = [(value, ".codegraph") for value in invalid] + valid
        cases += [(char + ".codegraph-win", ".codegraph-win") for char in trim]
        cases += [(".codegraph-win" + char, ".codegraph-win") for char in trim]
        cases += [(char + ".codegraph-win", char + ".codegraph-win") for char in keep]
        cases += [(".codegraph-win" + char, ".codegraph-win" + char) for char in keep]
        for index, (raw, expected) in enumerate(cases):
            with self.subTest(index=index, raw=repr(raw), expected=repr(expected)):
                repo = self.tmpdir()
                binpath, log = self.fake()
                write(os.path.join(repo, expected, "codegraph.db"), "index")
                out = run_script(repo, {"symbolGraph": {"bin": binpath}},
                                 {"CODEGRAPH_DIR": raw})
                self.assertEqual(out["reason"], "ok")
                assert_call(self, log, repo, ["sync", "."], expected)
                if expected != ".codegraph":
                    self.assertFalse(os.path.exists(os.path.join(repo, ".codegraph")))

    def test_n13_init_and_sync_failures_report_command_and_diagnostic(self):
        for command in ("init", "sync"):
            with self.subTest(command=command):
                repo = self.tmpdir()
                binpath, log = self.fake(exit_code=7)
                if command == "sync":
                    write(os.path.join(repo, ".codegraph", "codegraph.db"), "index")
                proc, out = run_process(repo, {"symbolGraph": {"bin": binpath}})
                self.assertEqual(out["reason"], "index-failed")
                self.assertIn("codegraph %s . failed (rc=7)" % command, proc.stderr)
                self.assertIn("FAKE-DIAG-7", proc.stderr)
                assert_call(self, log, repo, [command, "."])

    def test_n14_directory_diagnostics_are_ascii_single_line(self):
        for dirname in ("foo\nbar", "foo\u2028bar", "foo\u2029bar", "索引"):
            with self.subTest(dirname=repr(dirname)):
                repo = self.tmpdir()
                binpath, log = self.fake()
                write(os.path.join(repo, dirname), "not a directory")
                proc, out = run_process(repo, {"symbolGraph": {"bin": binpath}},
                                        {"CODEGRAPH_DIR": dirname})
                self.assertEqual(out["reason"], "index-failed")
                self.assertEqual(len(proc.stderr.splitlines()), 1)
                self.assertTrue(proc.stderr.isascii())
                self.assertIn(ascii(dirname), proc.stderr)
                self.assertEqual(read_calls(log), [])

    def test_n15_invalid_utf8_environment_is_replaced(self):
        repo = self.tmpdir()
        binpath, log = self.fake()
        dirname = "\ufffd.codegraph-win"
        write(os.path.join(repo, dirname, "codegraph.db"), "index")
        cfg = os.path.join(repo, ".claude", "doc-audit.json")
        write(cfg, json.dumps({"symbolGraph": {"bin": binpath}}))
        with open(cfg, "rb") as handle:
            expected = "sha256:" + hashlib.sha256(handle.read()).hexdigest()
        env = dict(os.environb)
        env.pop(b"CODEGRAPH_DIR", None)
        env[b"CODEGRAPH_DIR"] = b"\xff.codegraph-win"
        proc = subprocess.run(["bash", SCRIPT, "--config", cfg, "--expect-config-sha", expected, "--repo-root", repo],
                              capture_output=True, text=True, env=env,
                              input="STDIN-SENTINEL\n", timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        self.assertEqual(json.loads(proc.stdout)["reason"], "ok")
        assert_call(self, log, repo, ["sync", "."], dirname)

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
        assert_call(self, os.path.join(bindir, "ok.log"), self.repo, ["init", "."])
        assert_call(self, os.path.join(bindir, "failed.log"), self.repo, ["init", "."])

        unsafe = []
        for case in ("db-directory", "db-dangling-link", "db-file-link",
                     "dir-link", "dir-file", "custom-dir-file"):
            repo = self.tmpdir()
            binpath, log = self.fake()
            dirname = ".custom-index" if case == "custom-dir-file" else ".codegraph"
            directory = os.path.join(repo, dirname)
            database = os.path.join(directory, "codegraph.db")
            env = {"CODEGRAPH_DIR": dirname} if case == "custom-dir-file" else None
            if case == "db-directory":
                os.makedirs(database)
            elif case == "db-dangling-link":
                os.makedirs(directory)
                os.symlink("missing.db", database)
            elif case == "db-file-link":
                write(os.path.join(repo, "real.db"), "index")
                os.makedirs(directory)
                os.symlink(os.path.join(repo, "real.db"), database)
            elif case == "dir-link":
                write(os.path.join(repo, "real-index", "codegraph.db"), "index")
                os.symlink(os.path.join(repo, "real-index"), directory)
            else:
                write(directory, "not a directory")
            proc, out = run_process(repo, {"symbolGraph": {"bin": binpath}}, env)
            self.assertTrue(proc.stdout.isascii())
            self.assertEqual(read_calls(log), [])
            unsafe.append(out)
        outputs.extend(unsafe)
        expected_reasons = {"ok", "not-installed", "disabled-by-config",
                            "index-failed", "not-configured", "invalid-config"}
        self.assertEqual({out["reason"] for out in outputs}, expected_reasons)
        for out in outputs:
            self.assertEqual(set(out),
                             {"symbolGraphAvailable", "symbolGraphBin", "reason"})


if __name__ == "__main__":
    unittest.main()
