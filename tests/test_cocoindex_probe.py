import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "cocoindex-probe.sh")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def stub(log_path, exit_code=0):
    """A fake ccc that logs every subcommand it's called with to log_path (one
    line per invocation, space-joined args) and exits exit_code."""
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


class TestCocoindexProbe(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"semanticSearch": {"bin": "ccc-does-not-exist-zzz"}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "not-installed")

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"semanticSearch": {"enabled": False}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")

    def test_not_initialized_never_calls_init(self):
        # The single most safety-critical test in this whole plan: an absent
        # .cocoindex_code/ MUST short-circuit to not-initialized WITHOUT ever
        # invoking the stub with "init" (ccc init has a confirmed .gitignore
        # write side effect the report-only audit phase must never trigger).
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log))
        # No .cocoindex_code/ fixture created.
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "not-initialized")
        # Assert on the stub's call log, not just the JSON output.
        self.assertFalse(os.path.exists(log), "ccc must never be invoked when not-initialized")

    def test_stub_installed_reports_ok(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log))
        os.makedirs(os.path.join(self.repo, ".cocoindex_code"), exist_ok=True)
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertTrue(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "ok")
        with open(log, encoding="utf-8") as f:
            calls = [ln.strip() for ln in f if ln.strip()]
        # ccc index takes NO path argument (real-machine confirmed: `ccc index .`
        # errors "unexpected extra argument(s)") — unlike codegraph/graphify.
        self.assertEqual(calls, ["index"])

    def test_stub_index_failure_reports_index_failed(self):
        bindir = tempfile.mkdtemp()
        log = os.path.join(bindir, "calls.log")
        binpath = os.path.join(bindir, "cccstub")
        make_exec(binpath, stub(log, exit_code=1))
        os.makedirs(os.path.join(self.repo, ".cocoindex_code"), exist_ok=True)
        out = run_script(self.repo, {"semanticSearch": {"enabled": True, "bin": binpath}})
        self.assertFalse(out["semanticSearchAvailable"])
        self.assertEqual(out["reason"], "index-failed")
        self.assertEqual(out["rc"], 1)


if __name__ == "__main__":
    unittest.main()
