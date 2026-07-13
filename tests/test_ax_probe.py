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
        self.repo = tempfile.mkdtemp()

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
        bindir = tempfile.mkdtemp()
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


if __name__ == "__main__":
    unittest.main()
