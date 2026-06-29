"""Adversarial tests for the deterministic verdict gate (decide-verdict.py).

Each test encodes one attack an orchestrator LLM could attempt to advance the
anchor on a false CONSISTENT. The invariant under test:

    the anchor is written  <=>  every integrity check passes AND verdict==CONSISTENT

Anything else (hand-fed verdict, skipped/partial Phase 3, hidden FAIL, replayed
evidence, missing required Phase 4, malformed evidence) must REFUSE and leave the
anchor untouched.
"""
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "skills", "audit", "scripts", "decide-verdict.py")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        with open(os.path.join(self.repo, "f"), "w") as fh:
            fh.write("x")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.anchor = ".claude/state/last-doc-audit.json"
        self.run_dir = tempfile.mkdtemp()
        self.runid = "run-test-0001"

    # --- run-dir builders ---------------------------------------------------
    def write_manifest(self, impacted, phase4Expected=False, head=None, runid=None,
                       mode="incremental", drop=None):
        m = {
            "runid": runid or self.runid,
            "head": head or self.head,
            "mode": mode,
            "impacted": impacted,
            "phase4Expected": phase4Expected,
        }
        if drop:
            m.pop(drop)
        with open(os.path.join(self.run_dir, "manifest.json"), "w") as fh:
            json.dump(m, fh)

    def write_verdicts(self, records):
        with open(os.path.join(self.run_dir, "verdicts.jsonl"), "w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")

    def write_verdicts_raw(self, text):
        with open(os.path.join(self.run_dir, "verdicts.jsonl"), "w") as fh:
            fh.write(text)

    def write_phase4(self, findings):
        with open(os.path.join(self.run_dir, "phase4.json"), "w") as fh:
            json.dump({"findings": findings}, fh)

    def rec(self, path, verdict, runid=None):
        return {"runid": runid or self.runid, "path": path, "verdict": verdict, "rationale": "r"}

    # --- invoke -------------------------------------------------------------
    def run_gate(self, extra=None, date="2026-06-04"):
        cmd = ["python3", GATE, "--run-dir", self.run_dir, "--repo-root", self.repo,
               "--anchor-path", self.anchor, "--date", date]
        if extra:
            cmd += extra
        return subprocess.run(cmd, capture_output=True, text=True)

    def anchor_file(self):
        return os.path.join(self.repo, self.anchor)

    def assertNoAnchor(self):
        self.assertFalse(os.path.exists(self.anchor_file()), "anchor must NOT exist")

    def out(self, proc):
        return json.loads(proc.stdout)


# === happy paths (the gate must still pass real CONSISTENT runs) =============
class TestHappy(Base):
    def test_all_pass_writes_anchor(self):
        self.write_manifest(["a.md", "b.md"])
        self.write_verdicts([self.rec("a.md", "PASS"), self.rec("b.md", "PASS")])
        self.write_phase4([])  # Phase 4 ran clean (gate opened because impacted>0)
        p = self.run_gate()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        o = self.out(p)
        self.assertEqual(o["verdict"], "CONSISTENT")
        self.assertTrue(o["anchorWritten"])
        data = json.load(open(self.anchor_file()))
        self.assertEqual(data["sha"], self.head)
        self.assertEqual(data["verdict"], "CONSISTENT")
        self.assertEqual(data["runid"], self.runid)
        self.assertTrue(data["evidenceDigest"].startswith("sha256:"))
        self.assertEqual(data["phase3Count"], 2)

    def test_warn_never_blocks(self):
        self.write_manifest(["a.md", "b.md"])
        self.write_verdicts([self.rec("a.md", "WARN"), self.rec("b.md", "PASS")])
        self.write_phase4([])
        p = self.run_gate()
        self.assertEqual(self.out(p)["verdict"], "CONSISTENT")
        self.assertTrue(os.path.exists(self.anchor_file()))

    def test_empty_impacted_consistent(self):
        # legitimate "nothing impacted" run: no docs, Phase 4 not required
        self.write_manifest([], phase4Expected=False)
        p = self.run_gate()
        self.assertEqual(self.out(p)["verdict"], "CONSISTENT")
        self.assertTrue(os.path.exists(self.anchor_file()))

    def test_phase4_clean_consistent(self):
        self.write_manifest(["a.md"], phase4Expected=True)
        self.write_verdicts([self.rec("a.md", "PASS")])
        self.write_phase4([{"severity": "MEDIUM"}, {"severity": "low"}])
        p = self.run_gate()
        self.assertEqual(self.out(p)["verdict"], "CONSISTENT")
        self.assertTrue(os.path.exists(self.anchor_file()))


# === real FAIL must block ====================================================
class TestRealFail(Base):
    def test_phase3_fail_blocks(self):
        self.write_manifest(["a.md", "b.md"])
        self.write_verdicts([self.rec("a.md", "FAIL"), self.rec("b.md", "PASS")])
        self.write_phase4([])
        p = self.run_gate()
        self.assertEqual(p.returncode, 0)
        self.assertEqual(self.out(p)["verdict"], "NEEDS_FIX")
        self.assertNoAnchor()

    def test_phase4_fail_blocks(self):
        self.write_manifest(["a.md"], phase4Expected=True)
        self.write_verdicts([self.rec("a.md", "PASS")])
        self.write_phase4([{"severity": "HIGH", "title": "x"}])
        p = self.run_gate()
        self.assertEqual(self.out(p)["verdict"], "NEEDS_FIX")
        self.assertNoAnchor()


# === attacks: must REFUSE and never write the anchor =========================
class TestAttacks(Base):
    def test_hand_fed_verdict_arg_does_not_exist(self):
        # the old --verdict CONSISTENT hand-off is gone -> usage error, no anchor
        self.write_manifest(["a.md"])
        self.write_verdicts([self.rec("a.md", "FAIL")])
        p = self.run_gate(extra=["--verdict", "CONSISTENT"])
        self.assertEqual(p.returncode, 2)
        self.assertNoAnchor()

    def test_skip_phase3_entirely(self):
        self.write_manifest(["a.md", "b.md"])  # no verdicts.jsonl at all
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertEqual(self.out(p)["verdict"], "REFUSED")
        self.assertNoAnchor()

    def test_partial_phase3(self):
        self.write_manifest(["a.md", "b.md"])
        self.write_verdicts([self.rec("a.md", "PASS")])  # b.md missing
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_hide_fail_by_omission_and_dup(self):
        # c.md was a FAIL; attacker drops it and duplicates b.md to keep count==3
        self.write_manifest(["a.md", "b.md", "c.md"])
        self.write_verdicts([self.rec("a.md", "PASS"), self.rec("b.md", "PASS"),
                             self.rec("b.md", "PASS")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_extra_foreign_path(self):
        self.write_manifest(["a.md"])
        self.write_verdicts([self.rec("a.md", "PASS"), self.rec("z.md", "PASS")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_foreign_runid_record(self):
        self.write_manifest(["a.md"])
        self.write_verdicts([self.rec("a.md", "PASS", runid="other-run")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_replayed_stale_evidence(self):
        # manifest from an older HEAD must not pass against the current tree
        self.write_manifest(["a.md"], head="0" * 40)
        self.write_verdicts([self.rec("a.md", "PASS")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_garbage_verdict_line(self):
        self.write_manifest(["a.md"])
        self.write_verdicts_raw(json.dumps(self.rec("a.md", "PASS")) + "\nNOT JSON\n")
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_unknown_verdict_value(self):
        self.write_manifest(["a.md"])
        self.write_verdicts([self.rec("a.md", "MAYBE")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_phase4_required_but_missing(self):
        self.write_manifest(["a.md"], phase4Expected=True)
        self.write_verdicts([self.rec("a.md", "PASS")])  # no phase4.json
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_phase4_unknown_severity(self):
        self.write_manifest(["a.md"], phase4Expected=True)
        self.write_verdicts([self.rec("a.md", "PASS")])
        self.write_phase4([{"severity": "spicy"}])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_no_manifest(self):
        p = self.run_gate()  # empty run-dir
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_manifest_missing_field(self):
        self.write_manifest(["a.md"], drop="head")
        self.write_verdicts([self.rec("a.md", "PASS")])
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()

    def test_impacted_nonempty_requires_phase4(self):
        # impacted>0 opens the Phase-4 gate even if the flag lies "false"
        self.write_manifest(["a.md"], phase4Expected=False)
        self.write_verdicts([self.rec("a.md", "PASS")])
        # no phase4.json -> required by local derivation (len(impacted)>0)
        p = self.run_gate()
        self.assertEqual(p.returncode, 3)
        self.assertNoAnchor()


if __name__ == "__main__":
    unittest.main()
