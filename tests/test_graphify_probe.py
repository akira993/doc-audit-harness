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


def init_git_repo(repo):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)


class TestGraphifyProbe(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"docGraph": {"bin": "graphify-does-not-exist-zzz"}})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "not-installed")
        self.assertFalse(out["gitignoreOk"])

    def test_disabled_by_config(self):
        out = run_script(self.repo, {"docGraph": {"enabled": False}})
        self.assertFalse(out["docGraphAvailable"])
        self.assertEqual(out["reason"], "disabled-by-config")
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
        self.assertEqual(out["rc"], 1)
        self.assertFalse(out["gitignoreOk"])


if __name__ == "__main__":
    unittest.main()
