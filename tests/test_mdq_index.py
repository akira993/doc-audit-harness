import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "mdq-index.sh")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def read_marker(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def sentinel_env(bindir, value, default_name):
    names = []
    for name in (default_name, value, value.strip()):
        if not name or "\0" in name or name in names:
            continue
        try:
            name.encode("utf-8")
        except UnicodeEncodeError:
            continue
        names.append(name)
    markers = []
    env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"])
    for index, name in enumerate(names):
        marker = os.path.join(bindir, "marker-%d" % index)
        make_exec(os.path.join(bindir, name),
                  '#!/bin/sh\nprintf called >> "$MARKER_%d"\n' % index)
        env["MARKER_%d" % index] = marker
        markers.append(marker)
    return env, markers


def arg_logging_stub(rc=0):
    """A fake mdq that appends its argv to ARGLOG (env) and creates .mdq, then exits rc."""
    return ('#!/usr/bin/env bash\n'
            'echo "$@" >> "$ARGLOG"\n'
            'mkdir -p .mdq\n'
            'exit %d\n' % rc)


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


class TestMdqIndex(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name
        write(os.path.join(self.repo, "docs", "a.md"), "# A\n")

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_setup_creates_corpus(self):
        self.assertTrue(os.path.exists(os.path.join(self.repo, "docs", "a.md")))

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"indexing": {"bin": "mdq-does-not-exist-zzz"}})
        self.assertFalse(out["mdqAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_json_emit_is_ascii_one_line(self):
        def invoke(bin_name, env=None):
            cfg = os.path.join(self.repo, ".claude", "json-emit.json")
            write(cfg, json.dumps({"indexing": {"bin": bin_name}}))
            proc = subprocess.run(["bash", SCRIPT, "--config", cfg, "--repo-root", self.repo],
                                  capture_output=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.isascii())
            self.assertEqual(len(proc.stdout.decode().splitlines()), 1)
            out = json.loads(proc.stdout)
            self.assertEqual(out["bin"], bin_name)
            return out

        self.assertEqual(invoke("to\u2028ol-none")["reason"], "not-installed")
        bindir = self.tmpdir()
        name = "to\u2028ol-mdq"
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"],
                   ARGLOG=os.path.join(bindir, "args"))
        make_exec(os.path.join(bindir, name), arg_logging_stub(0))
        self.assertEqual(invoke(name, env)["reason"], "indexed")
        make_exec(os.path.join(bindir, name), arg_logging_stub(1))
        self.assertEqual(invoke(name, env)["reason"], "index-failed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"indexing": {"enabled": False}})
        self.assertFalse(out["mdqAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")

    def test_default_when_no_indexing_block(self):
        # enabled defaults true, bin defaults "mdq"; mdq may or may not be installed
        # in the test env — either way the script must emit valid JSON and exit 0.
        out = run_script(self.repo, {})
        self.assertIn(out["reason"], ("indexed", "not-installed", "index-failed"))
        if out["reason"] == "indexed":
            self.assertTrue(out["mdqAvailable"])
        else:
            self.assertFalse(out["mdqAvailable"])

    def test_stub_indexes_corpus(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "mdqstub")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(0))
        out = run_script(self.repo, {"indexing": {"bin": stub}}, {"ARGLOG": arglog})
        self.assertTrue(out["mdqAvailable"])
        self.assertEqual(out["reason"], "indexed")
        self.assertEqual(out["dbDir"], ".mdq")
        # Regression pin: the retired hardcoded default DB name must not resurface —
        # mdq resolves its own default DB, so the harness never names the file.
        self.assertNotIn("index.sqlite", json.dumps(out))
        self.assertTrue(os.path.isdir(os.path.join(self.repo, ".mdq")))

    def test_stub_failure_degrades(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "mdqfail")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(7))
        out = run_script(self.repo, {"indexing": {"bin": stub}}, {"ARGLOG": arglog})
        self.assertFalse(out["mdqAvailable"])
        self.assertEqual(out["reason"], "index-failed")
        self.assertEqual(out["rc"], 7)

    def test_default_root_is_whole_repo(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "mdqargs")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(0))
        run_script(self.repo, {"indexing": {"bin": stub}}, {"ARGLOG": arglog})
        with open(arglog) as f:
            args = f.read()
        self.assertIn("index", args)
        self.assertIn("--root .\n", args)

    def test_roots_override_is_honored(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "mdqargs2")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(0))
        run_script(self.repo, {"indexing": {"bin": stub, "roots": ["docs", "skills"]}},
                   {"ARGLOG": arglog})
        with open(arglog) as f:
            args = f.read()
        self.assertIn("--root docs", args)
        self.assertIn("--root skills", args)
        self.assertNotIn("--root .", args)

    def test_config_decision_table_v014(self):
        case_ids = {
            "absent", "empty", "disabled", "en_str", "en_int", "en_null",
            "key_null", "key_true", "key_str", "key_list", "cfg_omitted",
            "cfg_empty", "cfg_missing", "cfg_broken", "top_list", "top_null",
            "bin_int", "bin_empty", "bin_nul", "compound", "bin_ws_lead", "bin_ws_trail", "bin_ws_both", "bin_ws_nbsp", "bin_wsonly", "bin_surrogate",
        }
        self.assertEqual(len(case_ids), 26)
        bindir = self.tmpdir()
        marker = os.path.join(bindir, "sentinel")
        make_exec(os.path.join(bindir, "mdq"),
                  '#!/bin/sh\nprintf called >> "$SENTINEL"\nexit 0\n')
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"],
                   SENTINEL=marker)
        payloads = {
            "absent": {}, "empty": {"indexing": {}},
            "disabled": {"indexing": {"enabled": False}},
            "en_str": {"indexing": {"enabled": "false"}},
            "en_int": {"indexing": {"enabled": 1}},
            "en_null": {"indexing": {"enabled": None}},
            "key_null": {"indexing": None}, "key_true": {"indexing": True},
            "key_str": {"indexing": "x"}, "key_list": {"indexing": []},
            "top_list": [], "top_null": None,
            "bin_int": {"indexing": {"bin": 1}},
            "bin_empty": {"indexing": {"bin": ""}},
            "bin_nul": '{"indexing":{"bin":"bad\\u0000bin"}}',
            "bin_ws_lead":{"indexing":{"bin":" mdq"}}, "bin_ws_trail":{"indexing":{"bin":"mdq "}}, "bin_ws_both":{"indexing":{"bin":" mdq "}}, "bin_ws_nbsp":{"indexing":{"bin":"\u00a0mdq"}}, "bin_wsonly":{"indexing":{"bin":"   "}}, "bin_surrogate":'{"indexing":{"bin":"\\ud800"}}',
            "compound": {"indexing": {"enabled": False, "bin": []}},
        }
        invalid = case_ids - {"absent", "empty", "disabled", "cfg_omitted", "compound"}
        for case_id in sorted(case_ids):
            with self.subTest(case_id=case_id):
                cfg = os.path.join(self.repo, ".claude", case_id + ".json")
                args = ["bash", SCRIPT]
                if case_id != "cfg_omitted":
                    if case_id == "cfg_empty":
                        cfg = ""
                    elif case_id == "cfg_missing":
                        pass
                    elif case_id == "cfg_broken":
                        write(cfg, "{")
                    else:
                        value = payloads[case_id]
                        write(cfg, value if isinstance(value, str) else json.dumps(value))
                    args += ["--config", cfg]
                args += ["--repo-root", self.repo]
                before = read_marker(marker)
                proc = subprocess.run(args, capture_output=True, text=True, env=env)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(len(proc.stdout.splitlines()), 1)
                out = json.loads(proc.stdout)
                if case_id in invalid:
                    self.assertEqual(out, {"mdqAvailable": False,
                                           "reason": "invalid-config", "bin": "mdq"})
                    self.assertEqual(read_marker(marker), before)
                elif case_id in {"disabled", "compound"}:
                    self.assertEqual(out, {"mdqAvailable": False,
                                           "reason": "disabled-by-config"})
                else:
                    self.assertIn(out["reason"], {"indexed", "index-failed"})

    def test_output_key_sets_per_branch(self):
        expected = {
            "disabled-by-config": {"mdqAvailable", "reason"},
            "invalid-config": {"mdqAvailable", "reason", "bin"},
            "not-installed": {"mdqAvailable", "reason", "bin"},
            "indexed": {"mdqAvailable", "reason", "bin", "dbDir"},
            "index-failed": {"mdqAvailable", "reason", "rc", "bin"},
        }
        self.assertEqual(len(expected), 5)
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        bad = os.path.join(bindir, "bad")
        make_exec(ok, arg_logging_stub(0))
        make_exec(bad, arg_logging_stub(7))
        env = {"ARGLOG": os.path.join(bindir, "args")}
        outputs = [
            run_script(self.repo, {"indexing": {"enabled": False}}),
            run_script(self.repo, {"indexing": None}),
            run_script(self.repo, {"indexing": {"bin": "missing-mdq-v014"}}),
            run_script(self.repo, {"indexing": {"bin": ok}}, env),
            run_script(self.repo, {"indexing": {"bin": bad}}, env),
        ]
        self.assertEqual({out["reason"] for out in outputs}, set(expected))
        for out in outputs:
            self.assertEqual(set(out), expected[out["reason"]])

    def test_bin_boundary_table(self):
        controls = set(range(32)) | {127}
        self.assertEqual(controls, set(range(32)) | {127})
        values = (["to" + chr(c) + "ol" for c in controls] +
                  [" mdq", "mdq ", " mdq ", "\u00a0mdq", "   ", "\ud800"])
        for value in values:
            for enabled in (True, False):
                with self.subTest(value=repr(value), enabled=enabled):
                    bindir = self.tmpdir()
                    env, markers = sentinel_env(bindir, value, "mdq")
                    before = [read_marker(marker) for marker in markers]
                    out = run_script(self.repo, {"indexing": {"enabled": enabled,
                                                               "bin": value}}, env)
                    self.assertEqual(out["reason"], "invalid-config" if enabled else "disabled-by-config")
                    self.assertEqual([read_marker(marker) for marker in markers], before)
        bindir = self.tmpdir()
        env, markers = sentinel_env(bindir, "custom-mdq", "mdq")
        out = run_script(self.repo, {"indexing": {"enabled": False,
                                                   "bin": "custom-mdq"}}, env)
        self.assertEqual(out, {"mdqAvailable": False,
                               "reason": "disabled-by-config"})
        self.assertEqual([read_marker(marker) for marker in markers],
                         [None] * len(markers))

    def test_bin_positive_paths(self):
        ids = {"space_path", "non_ascii_path", "quote_backslash", "dash_name"}
        self.assertEqual(ids, {"space_path", "non_ascii_path", "quote_backslash", "dash_name"})
        for case_id, name in (("space_path", "dir with space/mdq"),
                              ("non_ascii_path", "émdq"),
                              ("quote_backslash", 'q"\\mdq'),
                              ("dash_name", "-x")):
            bindir = self.tmpdir()
            path = os.path.join(bindir, name)
            make_exec(path, arg_logging_stub(0))
            configured = "-x" if case_id == "dash_name" else path
            arglog = os.path.join(bindir, "args.txt")
            env = {"ARGLOG": arglog,
                   "PATH": bindir + os.pathsep + os.environ["PATH"]}
            if case_id == "non_ascii_path":
                env["PYTHONIOENCODING"] = "ascii"
            out = run_script(self.repo, {"indexing": {"bin": configured}}, env)
            self.assertEqual(out["bin"], configured)
            with open(arglog, encoding="utf-8") as handle:
                calls = [line.rstrip("\n") for line in handle]
            self.assertEqual(calls, ["index --root ."])


if __name__ == "__main__":
    unittest.main()
