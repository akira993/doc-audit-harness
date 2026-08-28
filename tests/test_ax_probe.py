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
            "bin_int", "bin_empty", "bin_nul", "compound",
        }
        self.assertEqual(len(case_ids), 20)
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


if __name__ == "__main__":
    unittest.main()
