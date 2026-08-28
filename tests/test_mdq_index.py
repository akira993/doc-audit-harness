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

    def tmpdir(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name
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
            "bin_int", "bin_empty", "bin_nul", "compound",
        }
        self.assertEqual(len(case_ids), 20)
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


if __name__ == "__main__":
    unittest.main()
