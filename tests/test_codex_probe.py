import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "codex-probe.sh")


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


def version_stub(version="0.145.0-stub"):
    """A fake codex that answers both local-only probe commands."""
    return ('#!/usr/bin/env bash\n'
            'if [[ "$1" == "--version" ]]; then echo "%s"; exit 0; fi\n'
            'if [[ "$1" == "exec" && "$2" == "--help" ]]; then exit 0; fi\n'
            'exit 2\n' % version)


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


class TestCodexProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = self.temp.name

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"codexReview": {"bin": "codex-does-not-exist-zzz"}})
        self.assertFalse(out["codexReviewAvailable"])
        self.assertEqual(out["reason"], "not-installed")
        self.assertIsNone(out["codexReviewVersion"])
        self.assertEqual(out["probeCommands"], [])

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"codexReview": {"enabled": False}})
        self.assertFalse(out["codexReviewAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")
        self.assertIsNone(out["codexReviewVersion"])
        self.assertEqual(out["probeCommands"], [])

    def test_stub_installed_reports_ok_and_version(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "codexstub")
        make_exec(stub, version_stub("0.145.0-stub"))
        out = run_script(self.repo, {"codexReview": {"enabled": True, "bin": stub}})
        self.assertTrue(out["codexReviewAvailable"])
        self.assertEqual(out["reason"], "ok")
        self.assertEqual(out["codexReviewBin"], stub)
        self.assertEqual(out["codexReviewVersion"], "0.145.0-stub")
        self.assertEqual(out["probeCommands"],
                         [stub + " --version", stub + " exec --help"])

    def test_exec_help_failure_degrades(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "codexstub")
        make_exec(stub, '#!/usr/bin/env bash\n'
                        'if [[ "$1" == "--version" ]]; then echo "stub"; exit 0; fi\n'
                        'exit 9\n')
        out = run_script(self.repo, {"codexReview": {"bin": stub}})
        self.assertFalse(out["codexReviewAvailable"])
        self.assertEqual(out["reason"], "probe-exec-failed")
        self.assertEqual(out["probeCommands"],
                         [stub + " --version", stub + " exec --help"])

    def test_default_when_no_codexreview_block(self):
        # enabled defaults true, bin defaults "codex"; codex may or may not be installed
        # in the test env — either way the script must emit valid JSON and exit 0.
        out = run_script(self.repo, {})
        self.assertIn(out["reason"], ("ok", "not-installed", "probe-exec-failed"))
        if out["reason"] == "ok":
            self.assertTrue(out["codexReviewAvailable"])
        else:
            self.assertFalse(out["codexReviewAvailable"])
            self.assertIsNone(out["codexReviewVersion"])

    def test_config_decision_table_v014(self):
        case_ids = {
            "absent", "empty", "disabled", "en_str", "en_int", "en_null",
            "key_null", "key_true", "key_str", "key_list", "cfg_omitted",
            "cfg_empty", "cfg_missing", "cfg_broken", "top_list", "top_null",
            "bin_int", "bin_empty", "bin_nul", "compound",
        }
        self.assertEqual(len(case_ids), 20)
        bindir = self.tmpdir()
        marker = os.path.join(bindir, "sentinel")
        make_exec(os.path.join(bindir, "codex"),
                  '#!/bin/sh\nprintf called >> "$SENTINEL"\n'
                  'if [ "$1" = "--version" ]; then echo v; fi\nexit 0\n')
        env = {"PATH": bindir + os.pathsep + os.environ["PATH"], "SENTINEL": marker}
        payloads = {
            "absent": {}, "empty": {"codexReview": {}},
            "disabled": {"codexReview": {"enabled": False}},
            "en_str": {"codexReview": {"enabled": "false"}},
            "en_int": {"codexReview": {"enabled": 1}},
            "en_null": {"codexReview": {"enabled": None}},
            "key_null": {"codexReview": None}, "key_true": {"codexReview": True},
            "key_str": {"codexReview": "x"}, "key_list": {"codexReview": []},
            "top_list": [], "top_null": None,
            "bin_int": {"codexReview": {"bin": 1}},
            "bin_empty": {"codexReview": {"bin": ""}},
            "bin_nul": '{"codexReview":{"bin":"bad\\u0000bin"}}',
            "compound": {"codexReview": {"enabled": False, "bin": []}},
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
                    self.assertEqual(out["reason"], "invalid-config")
                    self.assertEqual(out["codexReviewBin"], "codex")
                    self.assertEqual(read_marker(marker), before)
                elif case_id in {"disabled", "compound"}:
                    self.assertEqual(out["reason"], "disabled-by-config")
                else:
                    self.assertEqual(out["reason"], "ok")

    def test_caller_codex_home_and_auth_file(self):
        case_ids = {
            "env_auth", "env_noauth", "default_auth", "default_noauth",
            "env_empty", "home_unset", "env_special_chars",
        }
        self.assertEqual(len(case_ids), 7)
        bindir = self.tmpdir()
        stub = os.path.join(bindir, "codexstub")
        make_exec(stub, version_stub())
        cfg = os.path.join(self.repo, "config.json")
        write(cfg, json.dumps({"codexReview": {"bin": stub}}))
        for case_id in sorted(case_ids):
            with self.subTest(case_id=case_id):
                base = self.tmpdir()
                caller = base + ('/special\n"\\home' if case_id == "env_special_chars" else "/caller")
                default = os.path.join(base, ".codex")
                env = {"PATH": os.environ["PATH"]}
                expected_home = None
                expected_source = "unknown"
                if case_id.startswith("env_") and case_id != "env_empty":
                    env["CODEX_HOME"] = caller
                    expected_home, expected_source = caller, "env"
                elif case_id != "home_unset":
                    env["HOME"] = base
                    if case_id == "env_empty":
                        env["CODEX_HOME"] = ""
                    expected_home, expected_source = default, "default"
                if case_id in {"env_auth", "default_auth"}:
                    os.makedirs(expected_home, exist_ok=True)
                    write(os.path.join(expected_home, "auth.json"), "{}")
                proc = subprocess.run(
                    ["bash", SCRIPT, "--config", cfg, "--repo-root", self.repo],
                    capture_output=True, text=True, env=env,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                out = json.loads(proc.stdout)
                self.assertTrue(out["codexReviewAvailable"])
                self.assertEqual(out["callerCodexHome"], expected_home)
                self.assertEqual(out["callerCodexHomeSource"], expected_source)
                expected_auth = ("unknown" if expected_home is None else
                                 "present" if case_id in {"env_auth", "default_auth"}
                                 else "absent")
                self.assertEqual(out["callerAuthFile"], expected_auth)

    def test_caller_keys_present_in_every_branch(self):
        caller_keys = {"callerCodexHome", "callerCodexHomeSource", "callerAuthFile"}
        bindir = self.tmpdir()
        ok = os.path.join(bindir, "ok")
        bad = os.path.join(bindir, "bad")
        make_exec(ok, version_stub())
        make_exec(bad, '#!/bin/sh\nif [ "$1" = "--version" ]; then echo v; exit 0; fi\nexit 9\n')
        configs = [
            ("invalid-config", {"codexReview": None}),
            ("disabled-by-config", {"codexReview": {"enabled": False}}),
            ("not-installed", {"codexReview": {"bin": "missing-codex-v014"}}),
            ("probe-exec-failed", {"codexReview": {"bin": bad}}),
            ("ok", {"codexReview": {"bin": ok}}),
        ]
        self.assertEqual(len(configs), 5)
        expected_base = {
            "codexReviewAvailable", "codexReviewBin", "codexReviewVersion",
            "probeCommands", "reason",
        }
        for reason, config in configs:
            with self.subTest(reason=reason):
                out = run_script(self.repo, config)
                self.assertEqual(out["reason"], reason)
                self.assertEqual(set(out), expected_base | caller_keys)

    def test_output_key_sets_per_branch(self):
        self.test_caller_keys_present_in_every_branch()

    def test_json_escaping_of_bin_and_home(self):
        bindir = self.tmpdir()
        stub = os.path.join(bindir, 'codex\n"\\stub')
        caller = os.path.join(bindir, 'home\n"\\caller')
        make_exec(stub, version_stub('v\n"\\special'))
        os.makedirs(caller)
        out = run_script(self.repo, {"codexReview": {"bin": stub}},
                         {"CODEX_HOME": caller})
        self.assertEqual(out["codexReviewBin"], stub)
        self.assertEqual(out["callerCodexHome"], caller)
        self.assertEqual(out["probeCommands"],
                         [stub + " --version", stub + " exec --help"])


if __name__ == "__main__":
    unittest.main()
