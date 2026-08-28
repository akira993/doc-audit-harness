import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "probe-record.py")
HEALTH = os.path.join(ROOT, "skills", "audit", "scripts", "mdq-health.py")
RUNID = "20260828T123456Z-deadbeef"

CASES = {
    "upsert", "overwrite", "atomic_invalid", "fixed_seams", "bad_indexing",
    "bad_mdq_health", "bad_mdq_degrade", "bad_context", "bad_ax", "bad_codex",
    "bad_codex_state", "bad_symbol", "bad_doc", "bad_semantic", "conflict",
    "extra_keys", "health_probe_error", "health_ok", "stdin_non_object", "read_absent",
    "read_corrupt", "complete_rebind", "mdq_health_missing_available", "mdq_health_missing_inactive",
    "partial_missing", "display_boundary", "middle_symlink", "run_symlink", "file_symlink",
    "run_dir_mismatch", "invalid_runid", "symlink_repo_root", "codex_state_only",
}


def probes():
    return {
        "indexing": {"mdqAvailable": True, "reason": "indexed", "bin": "mdq", "dbDir": ".mdq"},
        "mdqHealth": {"files": 3, "chunks": 7, "searchSmoke": True, "healthy": True, "status": "ok"},
        "mdqDegrade": {"degrade": "n/a"},
        "contextMode": {"contextModeAvailable": True, "contextModeHealthy": True, "status": "ok"},
        "webExtract": {"axAvailable": True, "axBin": "ax", "axVersion": "1", "reason": "ok"},
        "codexReview": {"codexReviewAvailable": True, "codexReviewBin": "codex", "codexReviewVersion": "1",
                        "probeCommands": ["codex --version"], "reason": "ok", "callerCodexHome": "/tmp/home",
                        "callerCodexHomeSource": "env", "callerAuthFile": "present"},
        "codexReviewState": {"state": "completed"},
        "symbolGraph": {"symbolGraphAvailable": True, "symbolGraphBin": "codegraph", "reason": "ok"},
        "docGraph": {"docGraphAvailable": True, "docGraphBin": "graphify", "reason": "ok", "gitignoreOk": True},
        "semanticSearch": {"semanticSearchAvailable": True, "semanticSearchBin": "ccc", "reason": "ok"},
    }


class TestProbeRecord(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        self.run = os.path.join(self.root, ".claude", "state", "docaudit-run", RUNID)
        os.makedirs(self.run)
        self.evidence = json.dumps({"runDir": self.run})

    def command(self, *extra, input=None, root=None, evidence=None, runid=RUNID):
        return subprocess.run(
            [sys.executable, SCRIPT, "--repo-root", root or self.root, "--runid", runid,
             "--evidence", evidence or self.evidence, *extra], input=input,
            capture_output=True, text=True)

    def write(self, seam, value):
        proc = self.command("--seam", seam, "--stdin", input=json.dumps(value))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def read(self):
        proc = self.command("--read")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_case_ids_are_fixed_and_complete(self):
        self.assertEqual(len(CASES), 33)
        self.assertEqual(CASES, {
            "upsert", "overwrite", "atomic_invalid", "fixed_seams", "bad_indexing",
            "bad_mdq_health", "bad_mdq_degrade", "bad_context", "bad_ax", "bad_codex",
            "bad_codex_state", "bad_symbol", "bad_doc", "bad_semantic", "conflict",
            "extra_keys", "health_probe_error", "health_ok", "stdin_non_object", "read_absent",
            "read_corrupt", "complete_rebind", "mdq_health_missing_available", "mdq_health_missing_inactive",
            "partial_missing", "display_boundary", "middle_symlink", "run_symlink", "file_symlink",
            "run_dir_mismatch", "invalid_runid", "symlink_repo_root", "codex_state_only",
        })

    def test_upsert_overwrite_and_atomicity(self):
        first = self.write("indexing", probes()["indexing"])
        self.assertEqual(set(first["seams"]), {"indexing"})
        self.write("mdqDegrade", {"degrade": "user-approved"})
        self.write("indexing", {"mdqAvailable": False, "reason": "not-installed", "bin": "other"})
        path = os.path.join(self.run, "phase0-probes.json")
        with open(path, "rb") as handle:
            before = handle.read()
        bad = self.command("--seam", "indexing", "--stdin", input="{}")
        self.assertEqual(bad.returncode, 2)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)
        out = self.read()
        self.assertEqual(out["seams"]["indexing"]["bin"], "other")

    def test_schema_rejections_and_extra_keys(self):
        invalid = {
            "indexing": {"mdqAvailable": True, "reason": "not-installed", "bin": "mdq"},
            "mdqHealth": {"files": -1, "chunks": 0, "searchSmoke": False, "healthy": False, "status": "ok"},
            "mdqDegrade": {"degrade": "later"},
            "contextMode": {"contextModeAvailable": False, "contextModeHealthy": False, "status": "not-installed"},
            "webExtract": {"axAvailable": False, "axBin": "ax", "axVersion": None, "reason": "ok"},
            "codexReview": {"codexReviewAvailable": True, "codexReviewBin": "codex", "codexReviewVersion": None,
                            "probeCommands": [], "reason": "ok", "callerCodexHome": None,
                            "callerCodexHomeSource": "bad", "callerAuthFile": "unknown"},
            "codexReviewState": {"state": "other"},
            "symbolGraph": {"symbolGraphAvailable": True, "symbolGraphBin": "codegraph", "reason": "index-failed"},
            "docGraph": {"docGraphAvailable": True, "docGraphBin": "graphify", "reason": "ok", "gitignoreOk": "yes"},
            "semanticSearch": {"semanticSearchAvailable": False, "semanticSearchBin": "ccc", "reason": "ok"},
        }
        self.assertEqual(set(invalid), {
            "indexing", "mdqHealth", "mdqDegrade", "contextMode", "webExtract", "codexReview",
            "codexReviewState", "symbolGraph", "docGraph", "semanticSearch"})
        for seam, value in invalid.items():
            with self.subTest(case_id="bad_" + seam):
                proc = self.command("--seam", seam, "--stdin", input=json.dumps(value))
                self.assertEqual(proc.returncode, 2, proc.stderr)
        value = probes()["webExtract"].copy()
        value["extra"] = {"ignored": True}
        self.write("webExtract", value)
        self.assertTrue(self.read()["seams"]["webExtract"]["extra"]["ignored"])

    def test_mdq_health_actual_output_and_input_shape(self):
        error = subprocess.run([sys.executable, HEALTH, "--bin", "/nonexistent"], capture_output=True, text=True)
        self.assertEqual(error.returncode, 0, error.stderr)
        self.write("mdqHealth", json.loads(error.stdout))
        healthy = {"files": 3, "chunks": 10, "searchSmoke": True, "healthy": True, "status": "ok"}
        self.write("mdqHealth", healthy)
        self.assertEqual(self.read()["seams"]["mdqHealth"], healthy)
        proc = self.command("--seam", "mdqHealth", "--stdin", input="[]")
        self.assertEqual(proc.returncode, 2)

    def test_read_absent_corrupt_and_rebind_completeness(self):
        absent = self.read()
        self.assertTrue(all(value["state"] == "unknown" for value in absent["rebind"].values()))
        self.assertIsNone(absent["rebind"]["codex-review"]["bin"])
        path = os.path.join(self.run, "phase0-probes.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{")
        proc = self.command("--read")
        self.assertEqual(proc.returncode, 2)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"schemaVersion": 1, "seams": {}}, handle)
        for seam, value in probes().items():
            self.write(seam, value)
        out = self.read()["rebind"]
        self.assertTrue(all(value["state"] == "complete" for value in out.values()))
        self.assertEqual(out["mdq"], {"state": "complete", "available": True, "reason": "indexed", "bin": "mdq",
                                      "healthy": True, "chunks": 7, "status": "ok", "degrade": "n/a"})
        self.assertEqual(out["codex-review"], {
            "state": "complete", "available": True, "reason": "ok", "bin": "codex",
            "reviewState": "completed", "callerCodexHomeDisplay": "/tmp/home",
            "callerCodexHomeSource": "env", "callerAuthFile": "present",
        })

    def test_rebind_missing_health_partial_and_display(self):
        self.write("indexing", probes()["indexing"])
        self.write("mdqDegrade", probes()["mdqDegrade"])
        self.assertEqual(self.read()["rebind"]["mdq"]["state"], "unknown")
        self.write("indexing", {"mdqAvailable": False, "reason": "disabled-by-config"})
        self.assertEqual(self.read()["rebind"]["mdq"]["state"], "complete")
        self.write("symbolGraph", probes()["symbolGraph"])
        self.assertEqual(self.read()["rebind"]["doc-graph"]["state"], "unknown")
        codex = probes()["codexReview"].copy()
        codex["callerCodexHome"] = "x" * 199 + "\nrest"
        self.write("codexReview", codex)
        display = self.read()["rebind"]["codex-review"]["callerCodexHomeDisplay"]
        self.assertEqual(display, "x" * 199 + "\\n")
        self.assertNotIn("\n", display)

    def test_codex_review_state_without_probe_keeps_review_state(self):
        self.write("codexReviewState", {"state": "completed"})
        codex = self.read()["rebind"]["codex-review"]
        self.assertEqual(codex["state"], "unknown")
        self.assertEqual(codex["reviewState"], "completed")
        self.assertIsNone(codex["bin"])
        for key in ("callerCodexHomeDisplay", "callerCodexHomeSource", "callerAuthFile"):
            self.assertIsNone(codex[key])

    def test_symlinks_identity_and_symlink_repo_root(self):
        other = tempfile.mkdtemp()
        root2 = tempfile.mkdtemp()
        os.symlink(other, os.path.join(root2, ".claude"))
        proc = self.command("--read", root=root2,
                            evidence=json.dumps({"runDir": os.path.join(root2, ".claude", "state", "docaudit-run", RUNID)}))
        self.assertEqual(proc.returncode, 2)
        external = tempfile.mkdtemp()
        other_runid = "20260828T123457Z-deadbeef"
        os.symlink(external, os.path.join(self.root, ".claude", "state", "docaudit-run", other_runid))
        proc = self.command("--read", runid=other_runid,
                            evidence=json.dumps({"runDir": os.path.join(self.root, ".claude", "state", "docaudit-run", other_runid)}))
        self.assertEqual(proc.returncode, 2)
        path = os.path.join(self.run, "phase0-probes.json")
        os.symlink("/dev/null", path)
        proc = self.command("--read")
        self.assertEqual(proc.returncode, 2)
        os.unlink(path)
        mismatch = self.command("--read", evidence=json.dumps({"runDir": external}))
        self.assertEqual(mismatch.returncode, 2)
        invalid = self.command("--read", runid="bad")
        self.assertEqual(invalid.returncode, 2)
        link = self.root + "-link"
        os.symlink(self.root, link)
        accepted = self.command("--read", root=link)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)


if __name__ == "__main__":
    unittest.main()
