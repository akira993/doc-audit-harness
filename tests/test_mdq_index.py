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
        self.repo = tempfile.mkdtemp()
        write(os.path.join(self.repo, "docs", "a.md"), "# A\n")

    def test_not_installed_degrades(self):
        out = run_script(self.repo, {"indexing": {"bin": "mdq-does-not-exist-zzz"}})
        self.assertFalse(out["mdqAvailable"])
        self.assertEqual(out["reason"], "not-installed")

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
        bindir = tempfile.mkdtemp()
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
        bindir = tempfile.mkdtemp()
        stub = os.path.join(bindir, "mdqfail")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(7))
        out = run_script(self.repo, {"indexing": {"bin": stub}}, {"ARGLOG": arglog})
        self.assertFalse(out["mdqAvailable"])
        self.assertEqual(out["reason"], "index-failed")
        self.assertEqual(out["rc"], 7)

    def test_default_root_is_whole_repo(self):
        bindir = tempfile.mkdtemp()
        stub = os.path.join(bindir, "mdqargs")
        arglog = os.path.join(bindir, "args.txt")
        make_exec(stub, arg_logging_stub(0))
        run_script(self.repo, {"indexing": {"bin": stub}}, {"ARGLOG": arglog})
        with open(arglog) as f:
            args = f.read()
        self.assertIn("index", args)
        self.assertIn("--root .\n", args)

    def test_roots_override_is_honored(self):
        bindir = tempfile.mkdtemp()
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


if __name__ == "__main__":
    unittest.main()
