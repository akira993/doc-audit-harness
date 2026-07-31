import json, os, stat, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "impact-supplement.py")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def make_exec(path, body):
    write(path, body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def base_impact(impacted, max_docs_used_candidates_before_cap=0):
    return {
        "impacted": impacted,
        "mapGapCandidates": [e["path"] for e in impacted if e["provenance"] == "heuristic"],
        "ssotRecheck": [],
        "warnings": [],
        "truncated": False,
        "counts": {
            "changed": 1,
            "impacted": len(impacted),
            "mapped": sum(1 for e in impacted if e["provenance"] in ("mapped", "both")),
            "heuristicOnly": sum(1 for e in impacted if e["provenance"] == "heuristic"),
            "candidatesBeforeCap": len(impacted),
        },
    }


def write_impact_json(path, impacted):
    write(path, json.dumps(base_impact(impacted), ensure_ascii=False, indent=2) + "\n")


def run_script(args_list, stdin_text=""):
    p = subprocess.run(["python3", SCRIPT] + args_list, input=stdin_text,
                        capture_output=True, text=True)
    return p


GRAPHIFY_MIXED_STUB = '''#!/usr/bin/env bash
case "$1" in
  affected)
    case "$2" in
      src/foo.py)
        printf -- '- bar() [calls] docs/a.md:L10\\n'
        printf -- '- baz() [imports] src/other.py:L2\\n'
        ;;
      *)
        echo "No affected nodes found."
        ;;
    esac
    exit 0
    ;;
  query)
    printf 'NODE bar() [src=docs/b.md loc=L1 community=z]\\n'
    printf 'NODE qux() [src=src/skip.py loc=L2 community=z]\\n'
    exit 0
    ;;
esac
exit 0
'''

GRAPHIFY_UNIQUENESS_STUB = '''#!/usr/bin/env bash
case "$1" in
  affected)
    echo "No unique node match for $2"
    exit 0
    ;;
  query)
    echo "No unique node match for $2"
    exit 0
    ;;
esac
exit 0
'''


def graphify_candidates_stub(candidates):
    """candidates: list of doc paths to emit, one via `affected`, rest via `query`."""
    lines = []
    lines.append('#!/usr/bin/env bash')
    lines.append('case "$1" in')
    lines.append('  affected)')
    if candidates:
        lines.append(f"    printf -- '- x() [calls] {candidates[0]}:L1\\n'")
    lines.append('    exit 0')
    lines.append('    ;;')
    lines.append('  query)')
    for c in candidates[1:]:
        lines.append(f"    printf 'NODE x() [src={c} loc=L1 community=z]\\n'")
    lines.append('    exit 0')
    lines.append('    ;;')
    lines.append('esac')
    lines.append('exit 0')
    return "\n".join(lines) + "\n"


def cocoindex_search_stub(results):
    """results: list of (file_path, score) tuples, wrapped in the real-machine
    confirmed `ccc search --json` shape (cocoindex-code 0.2.39):
    {"type":"search","success":true,"results":[...],"total_returned":N,
    "offset":0,"message":null} — NOT a bare array."""
    items = [{"file_path": fp, "language": "markdown", "content": "x",
              "start_line": 1, "end_line": 1, "score": score} for fp, score in results]
    payload = {"type": "search", "success": True, "results": items,
               "total_returned": len(items), "offset": 0, "message": None}
    body = json.dumps(payload)
    return "#!/usr/bin/env bash\ncat <<'JSONEOF'\n%s\nJSONEOF\nexit 0\n" % body


class TestImpactSupplement(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.impact_path = os.path.join(self.repo, "impact.json")
        self.bindir = tempfile.mkdtemp()

    def stub(self, name, body):
        path = os.path.join(self.bindir, name)
        make_exec(path, body)
        return path

    def test_passthrough_when_neither_source_passed(self):
        impacted = [{"path": "docs/x.md", "provenance": "mapped"}]
        write_impact_json(self.impact_path, impacted)
        with open(self.impact_path, encoding="utf-8") as f:
            before = f.read()
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "some change", "--repo-root", self.repo,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after)

    def test_graphify_only_merge_doc_filtered(self):
        impacted = [{"path": "docs/mapped.md", "provenance": "mapped"}]
        write_impact_json(self.impact_path, impacted)
        gbin = self.stub("graphify", GRAPHIFY_MIXED_STUB)
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--graphify-bin", gbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        paths = {e["path"]: e["provenance"] for e in data["impacted"]}
        self.assertEqual(paths.get("docs/mapped.md"), "mapped")
        self.assertEqual(paths.get("docs/a.md"), "graphify")
        self.assertEqual(paths.get("docs/b.md"), "graphify")
        # Code-file candidates must be filtered out.
        self.assertNotIn("src/other.py", paths)
        self.assertNotIn("src/skip.py", paths)
        self.assertEqual(data["counts"]["graphifyOnly"], 2)

    def test_cocoindex_only_merge_score_boundary(self):
        impacted = []
        write_impact_json(self.impact_path, impacted)
        results = [
            ("docs/exactly.md", 0.4),
            ("docs/below.md", 0.39999),
            ("docs/above.md", 0.40001),
        ]
        cbin = self.stub("ccc", cocoindex_search_stub(results))
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--cocoindex-bin", cbin, "--min-score", "0.4",
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        paths = {e["path"] for e in data["impacted"]}
        self.assertIn("docs/exactly.md", paths)   # == min_score admitted
        self.assertIn("docs/above.md", paths)     # > min_score admitted
        self.assertNotIn("docs/below.md", paths)  # < min_score dropped
        self.assertEqual(data["counts"]["semanticOnly"], 2)

    def test_cocoindex_bare_array_defensive_fallback(self):
        # Defensive: if a different ccc version ever reverts to emitting a bare
        # JSON array instead of the confirmed {"results": [...]} wrapper, the
        # parser must still work.
        impacted = []
        write_impact_json(self.impact_path, impacted)
        payload = json.dumps([{"file_path": "docs/bare.md", "language": "markdown",
                                "content": "x", "start_line": 1, "end_line": 1, "score": 0.9}])
        cbin = self.stub("ccc", "#!/usr/bin/env bash\ncat <<'JSONEOF'\n%s\nJSONEOF\nexit 0\n" % payload)
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--cocoindex-bin", cbin, "--min-score", "0.4",
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        paths = {e["path"] for e in data["impacted"]}
        self.assertIn("docs/bare.md", paths)

    def test_cap_priority_full_no_residual_slots(self):
        # mapped+heuristic already fill maxImpactedDocs=2: zero graphify/semantic
        # candidates admitted, existing entries untouched.
        impacted = [
            {"path": "docs/m1.md", "provenance": "mapped"},
            {"path": "docs/h1.md", "provenance": "heuristic"},
        ]
        write_impact_json(self.impact_path, impacted)
        gbin = self.stub("graphify", graphify_candidates_stub(["docs/g1.md"]))
        cbin = self.stub("ccc", cocoindex_search_stub([("docs/s1.md", 0.9)]))
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "2", "--graphify-bin", gbin, "--cocoindex-bin", cbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        paths = {e["path"] for e in data["impacted"]}
        self.assertEqual(paths, {"docs/m1.md", "docs/h1.md"})
        self.assertEqual(data["counts"]["graphifyOnly"], 0)
        self.assertEqual(data["counts"]["semanticOnly"], 0)
        self.assertTrue(data["truncated"])
        self.assertTrue(data["warnings"])

    def test_cap_priority_residual_slots_graphify_before_semantic(self):
        # max=4, 1 mapped entry already present -> residual=3.
        # graphify offers 2 new candidates (both fit) -> residual for semantic = 1.
        # semantic offers 2 new candidates -> only 1 fits, 1 is truncated.
        impacted = [{"path": "docs/m1.md", "provenance": "mapped"}]
        write_impact_json(self.impact_path, impacted)
        gbin = self.stub("graphify", graphify_candidates_stub(["docs/g1.md", "docs/g2.md"]))
        cbin = self.stub("ccc", cocoindex_search_stub(
            [("docs/s1.md", 0.9), ("docs/s2.md", 0.8)]))
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "4", "--graphify-bin", gbin, "--cocoindex-bin", cbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        paths = {e["path"] for e in data["impacted"]}
        self.assertIn("docs/g1.md", paths)
        self.assertIn("docs/g2.md", paths)
        self.assertEqual(data["counts"]["graphifyOnly"], 2)
        self.assertEqual(data["counts"]["semanticOnly"], 1)
        self.assertEqual(len(data["impacted"]), 4)
        self.assertTrue(data["truncated"])

    def test_graphify_uniqueness_error_fallback(self):
        impacted = [{"path": "docs/m1.md", "provenance": "mapped"}]
        write_impact_json(self.impact_path, impacted)
        gbin = self.stub("graphify", GRAPHIFY_UNIQUENESS_STUB)
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--graphify-bin", gbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["impacted"]), 1)
        self.assertEqual(data["counts"]["graphifyOnly"], 0)

    def test_cocoindex_low_score_wipeout_fallback(self):
        impacted = [{"path": "docs/m1.md", "provenance": "mapped"}]
        write_impact_json(self.impact_path, impacted)
        cbin = self.stub("ccc", cocoindex_search_stub(
            [("docs/noise1.md", 0.25), ("docs/noise2.md", 0.26)]))
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--cocoindex-bin", cbin, "--min-score", "0.4",
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["impacted"]), 1)
        self.assertEqual(data["counts"]["semanticOnly"], 0)

    def test_malformed_impact_json_is_noop(self):
        write(self.impact_path, "{not valid json")
        gbin = self.stub("graphify", graphify_candidates_stub(["docs/g1.md"]))
        p = run_script([
            "--impact-json", self.impact_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--graphify-bin", gbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.impact_path, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(after, "{not valid json")

    def test_missing_impact_json_is_noop(self):
        missing_path = os.path.join(self.repo, "does-not-exist.json")
        gbin = self.stub("graphify", graphify_candidates_stub(["docs/g1.md"]))
        p = run_script([
            "--impact-json", missing_path, "--changed", "-",
            "--change-summary", "change summary text", "--repo-root", self.repo,
            "--max-impacted-docs", "10", "--graphify-bin", gbin,
        ], stdin_text="src/foo.py\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(os.path.exists(missing_path))


if __name__ == "__main__":
    unittest.main()
