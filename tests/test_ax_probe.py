import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "ax-probe.sh")


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


def version_stub(version="0.1.10-stub"):
    """A fake ax that answers --version without touching the network."""
    return ('#!/usr/bin/env bash\n'
            'if [[ "$1" == "--version" ]]; then echo "%s"; exit 0; fi\n'
            'exit 0\n' % version)


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


class TestAxProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"webExtract": {"bin": "ax-does-not-exist-zzz"}})
        self.assertFalse(out["axAvailable"])
        self.assertEqual(out["reason"], "not-installed")
        self.assertIsNone(out["axVersion"])

    def test_json_emit_is_ascii_one_line(self):
        def invoke(bin_name, env=None):
            cfg = os.path.join(self.repo, ".claude", "json-emit.json")
            write(cfg, json.dumps({"webExtract": {"bin": bin_name}}))
            proc = subprocess.run(["bash", SCRIPT, "--config", cfg, "--repo-root", self.repo],
                                  capture_output=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(proc.stdout.isascii())
            self.assertEqual(len(proc.stdout.decode().splitlines()), 1)
            out = json.loads(proc.stdout)
            self.assertEqual(out["axBin"], bin_name)
            return out

        self.assertEqual(invoke("to\u2028ol-none")["reason"], "not-installed")
        bindir = self.tmpdir()
        name = "to\u2028ol-ax"
        make_exec(os.path.join(bindir, name),
                  '#!/bin/sh\nprintf "ax 1.0-\\342\\200\\250x\\n"\n')
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"])
        out = invoke(name, env)
        self.assertEqual(out["reason"], "ok")
        self.assertEqual(out["axVersion"], "ax 1.0-\u2028x")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"webExtract": {"enabled": False}})
        self.assertFalse(out["axAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")
        self.assertIsNone(out["axVersion"])

    def test_stub_installed_reports_ok_and_version(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "axstub")
        make_exec(stub, version_stub("0.1.10-stub"))
        out = run_script(self.repo, {"webExtract": {"enabled": True, "tool": "ax", "bin": stub}})
        self.assertTrue(out["axAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertEqual(out["axBin"], stub)
        self.assertEqual(out["axVersion"], "0.1.10-stub")

    def test_default_when_no_webextract_block(self):
        # enabled defaults true, bin defaults "ax"; ax may or may not be installed
        # in the test env — either way the script must emit valid JSON and exit 0.
        out = run_script(self.repo, {})
        self.assertIn(out["reason"], ("ok", "not-installed"))
        if out["reason"] == "ok":
            self.assertTrue(out["axAvailable"])
        else:
            self.assertFalse(out["axAvailable"])
            self.assertIsNone(out["axVersion"])

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
        make_exec(os.path.join(bindir, "ax"),
                  '#!/bin/sh\nprintf called >> "$SENTINEL"\necho sentinel-version\n')
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"],
                   SENTINEL=marker)
        payloads = {
            "absent": {}, "empty": {"webExtract": {}},
            "disabled": {"webExtract": {"enabled": False}},
            "en_str": {"webExtract": {"enabled": "false"}},
            "en_int": {"webExtract": {"enabled": 1}},
            "en_null": {"webExtract": {"enabled": None}},
            "key_null": {"webExtract": None}, "key_true": {"webExtract": True},
            "key_str": {"webExtract": "x"}, "key_list": {"webExtract": []},
            "top_list": [], "top_null": None,
            "bin_int": {"webExtract": {"bin": 1}},
            "bin_empty": {"webExtract": {"bin": ""}},
            "bin_nul": '{"webExtract":{"bin":"bad\\u0000bin"}}',
            "bin_ws_lead":{"webExtract":{"bin":" ax"}}, "bin_ws_trail":{"webExtract":{"bin":"ax "}}, "bin_ws_both":{"webExtract":{"bin":" ax "}}, "bin_ws_nbsp":{"webExtract":{"bin":"\u00a0ax"}}, "bin_wsonly":{"webExtract":{"bin":"   "}}, "bin_surrogate":'{"webExtract":{"bin":"\\ud800"}}',
            "compound": {"webExtract": {"enabled": False, "bin": []}},
        }
        invalid = case_ids - {"absent", "empty", "disabled", "cfg_omitted", "compound"}
        for case_id in sorted(case_ids):
            with self.subTest(case_id=case_id):
                cfg = os.path.join(self.repo, case_id + ".json")
                args = ["bash", SCRIPT]
                if case_id != "cfg_omitted":
                    if case_id == "cfg_empty": cfg = ""
                    elif case_id == "cfg_missing": pass
                    elif case_id == "cfg_broken": write(cfg, "{")
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
                    self.assertEqual(out, {"axAvailable": False, "axBin": "ax",
                                           "axVersion": None, "reason": "invalid-config"})
                    self.assertEqual(read_marker(marker), before)
                elif case_id in {"disabled", "compound"}:
                    self.assertEqual(out["reason"], "disabled-by-config")
                else:
                    self.assertEqual(out["reason"], "ok")

    def test_output_key_sets_per_branch(self):
        expected = {"axAvailable", "axBin", "axVersion", "reason"}
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        make_exec(ok, version_stub())
        outputs = [
            run_script(self.repo, {"webExtract": {"enabled": False}}),
            run_script(self.repo, {"webExtract": None}),
            run_script(self.repo, {"webExtract": {"bin": "missing-ax-v014"}}),
            run_script(self.repo, {"webExtract": {"bin": ok}}),
        ]
        self.assertEqual({out["reason"] for out in outputs},
                         {"disabled-by-config", "invalid-config",
                          "not-installed", "ok"})
        for out in outputs:
            self.assertEqual(set(out), expected)

    def test_bin_boundary_table(self):
        controls = set(range(32)) | {127}
        self.assertEqual(controls, set(range(32)) | {127})
        values = (["to" + chr(c) + "ol" for c in controls] +
                  [" ax", "ax ", " ax ", "\u00a0ax", "   ", "\ud800"])
        for value in values:
            for enabled in (True, False):
                with self.subTest(value=repr(value), enabled=enabled):
                    bindir = self.tmpdir()
                    env, markers = sentinel_env(bindir, value, "ax")
                    before = [read_marker(marker) for marker in markers]
                    out = run_script(self.repo, {"webExtract": {"enabled": enabled,
                                                                 "bin": value}}, env)
                    self.assertEqual(out["reason"], "invalid-config" if enabled else "disabled-by-config")
                    self.assertEqual([read_marker(marker) for marker in markers], before)
        bindir = self.tmpdir()
        env, markers = sentinel_env(bindir, "custom-ax", "ax")
        out = run_script(self.repo, {"webExtract": {"enabled": False,
                                                     "bin": "custom-ax"}}, env)
        self.assertEqual(out["axBin"], "ax")
        self.assertEqual(out["reason"], "disabled-by-config")
        self.assertEqual([read_marker(marker) for marker in markers],
                         [None] * len(markers))

    def test_bin_positive_paths(self):
        ids = {"space_path", "non_ascii_path", "quote_backslash", "dash_name"}
        self.assertEqual(ids, {"space_path", "non_ascii_path", "quote_backslash", "dash_name"})
        for case_id, name in (("space_path", "dir with space/ax"),
                              ("non_ascii_path", "éax"),
                              ("quote_backslash", 'q"\\ax'),
                              ("dash_name", "-x")):
            bindir = self.tmpdir()
            path = os.path.join(bindir, name)
            arglog = os.path.join(bindir, "args.txt")
            make_exec(path, '#!/usr/bin/env bash\n'
                      'echo "$@" >> "$ARGLOG"\n'
                      'echo 0.1.10-stub\n')
            configured = "-x" if case_id == "dash_name" else path
            env = {"ARGLOG": arglog,
                   "PATH": bindir + os.pathsep + os.environ["PATH"]}
            if case_id == "non_ascii_path":
                env["PYTHONIOENCODING"] = "ascii"
            out = run_script(self.repo, {"webExtract": {"bin": configured}}, env)
            self.assertTrue(out["axAvailable"])
            self.assertEqual(out["axBin"], configured)
            with open(arglog, encoding="utf-8") as handle:
                calls = [line.rstrip("\n") for line in handle]
            self.assertEqual(calls, ["--version"])


if __name__ == "__main__":
    unittest.main()
