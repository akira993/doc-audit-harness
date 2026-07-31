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


class TestCodegraphProbe(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"symbolGraph": {"bin": "codegraph-does-not-exist-zzz"}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"symbolGraph": {"enabled": False}})
        self.assertFalse(out["symbolGraphAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")

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
        self.assertEqual(out["rc"], 1)


if __name__ == "__main__":
    unittest.main()
