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
        self.repo = tempfile.mkdtemp()

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
        bindir = tempfile.mkdtemp()
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
        bindir = tempfile.mkdtemp()
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


if __name__ == "__main__":
    unittest.main()
