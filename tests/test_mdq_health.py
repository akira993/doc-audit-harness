import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "mdq-health.py")

# A fake mdq whose stats/list/search output is controlled by env vars.
# Set ARGLOG to a file path to capture each invocation's argv.
# `search` additionally supports PER-CALL output: point STUB_COUNTER at a scratch
# file and set STUB_SEARCH_<n> / STUB_SEARCH_ERR_<n> to override the n-th call
# (1-based). Unset/empty falls back to STUB_SEARCH / STUB_SEARCH_ERR. This is what
# separates "aggregate every search call" from "read only the last one".
STUB = """#!/usr/bin/env bash
if [ -n "${ARGLOG:-}" ]; then echo "$@" >> "$ARGLOG"; fi
case "$1" in
  stats)  [ -n "${STUB_STATS:-}" ] && echo "$STUB_STATS"; exit "${STUB_STATS_RC:-0}";;
  list)   [ -n "${STUB_LIST:-}" ] && echo "$STUB_LIST"; exit 0;;
  search)
    n=1
    if [ -n "${STUB_COUNTER:-}" ]; then
      n=$(( $(cat "$STUB_COUNTER" 2>/dev/null || echo 0) + 1 ))
      echo "$n" > "$STUB_COUNTER"
    fi
    ovar="STUB_SEARCH_$n"; evar="STUB_SEARCH_ERR_$n"
    out="${!ovar:-${STUB_SEARCH:-}}"
    err="${!evar:-${STUB_SEARCH_ERR:-}}"
    [ -n "$err" ] && echo "$err" >&2
    [ -n "$out" ] && echo "$out"
    exit 0;;
  *) exit 0;;
esac
"""

# Real mdq emits this on stderr when the index is behind the working tree
# (freshness.py emit_warning). Verbatim from an observed run of mdq c559e767.
STALE_LINE = ('{"warning": "stale", "changed": 1, '
              '"hint": "run `python -m mdq index` to refresh the index"}')
# Real mdq also writes NON-JSON notices to the same stream (search.py fusion guard).
FUSION_LINE = "[mdq:search] fusion disabled (embedding provider unavailable: boom)"
HEALTHY_STATS = '{"files":3,"chunks":10}'
HEALTHY_LIST = '{"path":"README.md","heading_path":"docaudit Modes"}'
HEALTHY_HIT = '{"chunk_id":"x","path":"README.md"}'


def make_stub():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "mdqstub")
    with open(p, "w") as f:
        f.write(STUB)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


def run_health(env_extra, db="ignored.sqlite"):
    env = dict(os.environ)
    env.update(env_extra)
    cmd = ["python3", SCRIPT, "--bin", make_stub()]
    if db is not None:
        cmd += ["--db", db]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class TestMdqHealth(unittest.TestCase):
    def test_healthy(self):
        out = run_health({
            "STUB_STATS": '{"files":3,"chunks":10}',
            "STUB_LIST": '{"path":"README.md","heading_path":"docaudit Modes"}',
            "STUB_SEARCH": '{"chunk_id":"x","path":"README.md"}',
        })
        self.assertTrue(out["healthy"])
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["chunks"], 10)
        self.assertTrue(out["searchSmoke"])

    def test_empty_index(self):
        out = run_health({"STUB_STATS": '{"files":0,"chunks":0}'})
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "empty-index")
        self.assertEqual(out["chunks"], 0)

    def test_search_broken(self):
        out = run_health({
            "STUB_STATS": '{"files":3,"chunks":10}',
            "STUB_LIST": '{"path":"README.md","heading_path":"docaudit Modes"}',
            "STUB_SEARCH": "",
        })
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "search-broken")
        self.assertFalse(out["searchSmoke"])

    def test_probe_error_nonzero_stats(self):
        out = run_health({"STUB_STATS": '{"files":3,"chunks":10}', "STUB_STATS_RC": "1"})
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "probe-error")

    def test_probe_error_garbage_stats(self):
        out = run_health({"STUB_STATS": "not-json"})
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "probe-error")

    def test_probe_error_bad_type_stats(self):
        # JSON-valid but non-numeric field must degrade to probe-error, never crash.
        out = run_health({"STUB_STATS": '{"files":"bad","chunks":10}'})
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "probe-error")

    def test_files_present_chunks_zero_is_empty(self):
        out = run_health({"STUB_STATS": '{"files":2,"chunks":0}'})
        self.assertFalse(out["healthy"])
        self.assertEqual(out["status"], "empty-index")

    def test_db_omitted_lets_mdq_self_resolve(self):
        # Regression pin: with --db omitted the probe must not inject any --db of its
        # own (the retired hardcoded .mdq/index.sqlite default) — mdq resolves its
        # default DB itself, so probe/indexer/verifiers all see the same file.
        arglog = os.path.join(tempfile.mkdtemp(), "args.txt")
        out = run_health({
            "ARGLOG": arglog,
            "STUB_STATS": '{"files":3,"chunks":10}',
            "STUB_LIST": '{"path":"README.md","heading_path":"docaudit Modes"}',
            "STUB_SEARCH": '{"chunk_id":"x","path":"README.md"}',
        }, db=None)
        self.assertTrue(out["healthy"])
        self.assertEqual(out["status"], "ok")
        with open(arglog) as f:
            args = f.read()
        self.assertNotIn("--db", args)
        self.assertNotIn("index.sqlite", args)

    def test_db_explicit_override_is_passed_through(self):
        arglog = os.path.join(tempfile.mkdtemp(), "args.txt")
        out = run_health({
            "ARGLOG": arglog,
            "STUB_STATS": '{"files":3,"chunks":10}',
            "STUB_LIST": '{"path":"README.md","heading_path":"docaudit Modes"}',
            "STUB_SEARCH": '{"chunk_id":"x","path":"README.md"}',
        }, db="custom/override.sqlite")
        self.assertTrue(out["healthy"])
        with open(arglog) as f:
            args = f.read()
        self.assertIn("--db custom/override.sqlite", args)

    def test_non_ascii_headings_smoke(self):
        # A healthy index whose headings + filenames are entirely non-ASCII (CJK) must
        # still yield smoke terms and report ok — not a false search-broken WARN.
        out = run_health({
            "STUB_STATS": '{"files":3,"chunks":10}',
            "STUB_LIST": '{"path":"ドキュメント/導入.md","heading_path":"ドキュメント監査ハーネス > 要件"}',
            "STUB_SEARCH": '{"chunk_id":"x","path":"ドキュメント/導入.md"}',
        })
        self.assertTrue(out["healthy"])
        self.assertEqual(out["status"], "ok")


class TestMdqHealthStale(unittest.TestCase):
    """v0.18.0: `stale` is OBSERVATION ONLY — it must never move healthy/status."""

    def test_stale_true_when_search_warns(self):
        out = run_health({
            "STUB_STATS": HEALTHY_STATS,
            "STUB_LIST": HEALTHY_LIST,
            "STUB_SEARCH": HEALTHY_HIT,
            "STUB_SEARCH_ERR": STALE_LINE,
        })
        self.assertTrue(out["stale"])
        # The whole point of D6/U2: a stale index still audits.
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["healthy"])

    def test_stale_false_when_fresh(self):
        out = run_health({
            "STUB_STATS": HEALTHY_STATS,
            "STUB_LIST": HEALTHY_LIST,
            "STUB_SEARCH": HEALTHY_HIT,
        })
        self.assertFalse(out["stale"])
        self.assertEqual(out["status"], "ok")

    def test_stale_false_on_non_json_and_non_dict_stderr(self):
        # A plain-text notice and a JSON line that decodes to a *string* must both be
        # skipped. A substring match would fire on the second; a bare `.get()` would
        # raise on it and (via main's blanket except) corrupt status to probe-error.
        out = run_health({
            "STUB_STATS": HEALTHY_STATS,
            "STUB_LIST": HEALTHY_LIST,
            "STUB_SEARCH": HEALTHY_HIT,
            "STUB_SEARCH_ERR": FUSION_LINE,
            "STUB_SEARCH_ERR_1": FUSION_LINE + '\n"stale"',
        })
        self.assertFalse(out["stale"])
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["healthy"])

    def test_stale_aggregated_across_search_calls(self):
        # Call 1 warns stale but returns no hit; call 2 is clean and hits, ending the
        # loop. Reading only the last call would report stale:false.
        counter = os.path.join(tempfile.mkdtemp(), "n.txt")
        out = run_health({
            "STUB_STATS": HEALTHY_STATS,
            "STUB_LIST": HEALTHY_LIST,
            "STUB_COUNTER": counter,
            "STUB_SEARCH": "",          # default: no hit
            "STUB_SEARCH_ERR_1": STALE_LINE,
            "STUB_SEARCH_2": HEALTHY_HIT,
        })
        with open(counter) as f:
            self.assertEqual(f.read().strip(), "2", "expected exactly two search calls")
        self.assertTrue(out["stale"])
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["healthy"])

    def test_stale_key_present_on_empty_index(self):
        # The key must exist on every path, including the ones that never search.
        out = run_health({"STUB_STATS": '{"files":0,"chunks":0}'})
        self.assertIn("stale", out)
        self.assertFalse(out["stale"])
        self.assertEqual(out["status"], "empty-index")

    def test_stale_reported_alongside_search_broken(self):
        out = run_health({
            "STUB_STATS": HEALTHY_STATS,
            "STUB_LIST": HEALTHY_LIST,
            "STUB_SEARCH": "",
            "STUB_SEARCH_ERR": STALE_LINE,
        })
        self.assertTrue(out["stale"])
        self.assertEqual(out["status"], "search-broken")
        self.assertFalse(out["healthy"])


if __name__ == "__main__":
    unittest.main()
