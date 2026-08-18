"""Adversarial tests for the sealed v0.10 verdict gate."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from tests.wp12_helpers import RunFixture, git, write


class GateBase(unittest.TestCase):
    def prepared(self, verdicts=None, returns=None, phase4=None):
        fx = RunFixture(self)
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(verdicts, returns, phase4).returncode, 0)
        return fx

    def assert_refused(self, fx):
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "REFUSED")
        self.assertFalse(os.path.exists(fx.anchor))
        return proc


class TestHappy(GateBase):
    def test_all_pass_writes_anchor(self):
        fx = self.prepared()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")

    def test_warn_never_blocks(self):
        fx = self.prepared({"docs/a.md": "WARN", "docs/b.md": "PASS"})
        self.assertEqual(json.loads(fx.gate().stdout)["verdict"], "CONSISTENT")

    def test_phase4_fail_blocks(self):
        fx = self.prepared(phase4=[{"severity": "HIGH", "message": "broken"}])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "NEEDS_FIX")

    def test_phase4_finding_without_severity_is_refused(self):
        fx = self.prepared(phase4=[{"title": "critical issue"}])
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["verdict"], "REFUSED")
        self.assertIn("severity", result["reason"])


class TestAttacks(GateBase):
    def test_hand_fed_verdict_argument_does_not_exist(self):
        fx = self.prepared()
        proc = fx.call("decide-verdict.py", "--run-dir", fx.run_dir, "--repo-root", fx.repo,
                       "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
                       "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence),
                       "--verdict", "CONSISTENT")
        self.assertEqual(proc.returncode, 2)

    def test_assigned_path_mismatch_refuses(self):
        returns = [{"attempt": 1, "assignedPath": "docs/a.md", "returnedPath": "docs/b.md",
                    "verdict": "PASS", "rationale": "x", "suggestion": None},
                   {"attempt": 1, "assignedPath": "docs/b.md", "returnedPath": "docs/b.md",
                    "verdict": "PASS", "rationale": "x", "suggestion": None}]
        self.assert_refused(self.prepared(returns=returns))

    def test_return_verdict_mismatch_refuses(self):
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "WARN" if path == "docs/a.md" else "PASS",
                    "rationale": "x", "suggestion": None}
                   for path in ("docs/a.md", "docs/b.md")]
        self.assert_refused(self.prepared(returns=returns))

    def test_manifest_modification_refuses(self):
        fx = self.prepared()
        path = os.path.join(fx.run_dir, "manifest.json")
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
        value["runClass"] = "light"
        write(path, json.dumps(value) + "\n")
        self.assert_refused(fx)

    def test_returns_modification_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.run_dir, "returns.json"), "not json\n")
        proc = self.assert_refused(fx)
        with open(fx.last_run, encoding="utf-8") as handle:
            last_run = json.load(handle)
        self.assertEqual(last_run["runid"], fx.runid)
        self.assertEqual(last_run["verdict"], "REFUSED")
        self.assertEqual(last_run["reason"], json.loads(proc.stdout)["reason"])

    def test_missing_phase4_refuses(self):
        fx = RunFixture(self)
        fx.open(); fx.plan_start_seal()
        for path in fx.docs:
            fx.write_verdict(path)
        returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                    "verdict": "PASS", "rationale": "x", "suggestion": None}
                   for path in fx.docs]
        fx.write_evidence("returns", returns)
        fx.evidence["phase4"] = "none"
        self.assert_refused(fx)

    def test_seal_after_worktree_change_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.repo, "src", "app.py"), "print('changed')\n")
        self.assert_refused(fx)

    def test_clean_head_switch_refuses(self):
        fx = self.prepared()
        write(os.path.join(fx.repo, "new.txt"), "new\n")
        git(fx.repo, "add", "-A")
        git(fx.repo, "commit", "-m", "new head")
        self.assert_refused(fx)

    def test_evidence_key_missing_refuses(self):
        fx = self.prepared()
        fx.evidence.pop("returns")
        self.assert_refused(fx)
        with open(fx.last_run, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["verdict"], "REFUSED")

    def test_none_sentinel_with_existing_file_refuses(self):
        fx = self.prepared()
        fx.evidence["phase4"] = "none"
        self.assert_refused(fx)

    def test_config_change_refuses_and_poison_blocks_next_open(self):
        fx = self.prepared()
        config = dict(fx.config)
        config["maxImpactedDocs"] = 50
        write(fx.config_path, json.dumps(config) + "\n")
        proc = self.assert_refused(fx)
        self.assertIn("config", json.loads(proc.stdout)["reason"])
        next_run = fx.open(runid="20260818T120001Z-abcdef13")
        self.assertEqual(next_run.returncode, 6)
        accepted = fx.open(runid="20260818T120001Z-abcdef13", accept=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_history_change_is_tainted_and_refused(self):
        fx = self.prepared()
        self.assertEqual(fx.gate().returncode, 0)
        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete().returncode, 0)
        with open(fx.history, "a", encoding="utf-8") as handle:
            handle.write(" ")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_anchor_change_is_removed_and_refused(self):
        fx = self.prepared()
        self.assertEqual(fx.gate().returncode, 0)
        fx.open(runid="20260818T120001Z-abcdef13")
        fx.plan_start_seal(); fx.complete()
        write(fx.anchor, json.dumps({"sha": "forged"}) + "\n")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertFalse(os.path.exists(fx.anchor))

    def test_lock_and_history_tamper_still_quarantines_history(self):
        fx = self.prepared()
        lock = os.path.join(fx.run_base, "lock")
        write(lock, json.dumps({"runid": "tampered", "startedAt": "now"}) + "\n")
        write(fx.history, "{broken")
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_lock_unlink_recreate_is_refused(self):
        fx = self.prepared()
        lock = os.path.join(fx.run_base, "lock")
        with open(lock, "rb") as handle:
            raw = handle.read()
        replacement = lock + ".replacement"
        write(replacement, raw)
        os.replace(replacement, lock)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("lock", json.loads(proc.stdout)["reason"])
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.last_run))

    def test_old_gate_after_break_does_not_touch_later_run(self):
        fx = self.prepared()
        broken = fx.call("open-run.py", "--run-base", fx.run_base,
                         "--repo-root", fx.repo, "--break-lock")
        self.assertEqual(broken.returncode, 0, broken.stderr)
        later = "20260818T120001Z-deadbeef"
        opened = fx.call("open-run.py", "--run-base", fx.run_base,
                         "--repo-root", fx.repo, "--runid", later)
        self.assertEqual(opened.returncode, 0, opened.stderr)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        lock = os.path.join(fx.run_base, "lock")
        with open(lock, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["runid"], later)
        self.assertFalse(os.path.exists(fx.history))
        self.assertFalse(os.path.exists(fx.anchor))
        self.assertFalse(os.path.exists(fx.last_run))

    def test_manifest_replacement_after_snapshot_does_not_change_decision(self):
        fx = self.prepared()
        wrapper_dir = tempfile.TemporaryDirectory()
        self.addCleanup(wrapper_dir.cleanup)
        wrapper = os.path.join(wrapper_dir.name, "git")
        write(wrapper, """#!/bin/sh
if [ ! -e "$DOCAUDIT_SWAP_MARKER" ]; then
  printf '{replaced after snapshot' > "$DOCAUDIT_SWAP_MANIFEST"
  : > "$DOCAUDIT_SWAP_MARKER"
fi
exec "$DOCAUDIT_REAL_GIT" "$@"
""")
        os.chmod(wrapper, 0o755)
        env = os.environ.copy()
        env.update({
            "PATH": wrapper_dir.name + os.pathsep + env.get("PATH", ""),
            "DOCAUDIT_REAL_GIT": shutil.which("git"),
            "DOCAUDIT_SWAP_MARKER": os.path.join(wrapper_dir.name, "swapped"),
            "DOCAUDIT_SWAP_MANIFEST": os.path.join(fx.run_dir, "manifest.json"),
        })
        proc = subprocess.run(
            ["python3", os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      "skills", "audit", "scripts", "decide-verdict.py"),
             "--run-dir", fx.run_dir, "--repo-root", fx.repo,
             "--config", fx.config_path, "--anchor-path", fx.anchor_rel,
             "--runid", fx.runid, "--expect-json", json.dumps(fx.evidence)],
            capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{replaced after snapshot")


class TestCache(GateBase):
    def two_passes(self, fx):
        for number in range(2):
            runid = f"20260818T12000{number}Z-abcdef1{number}"
            self.assertEqual(fx.open(runid=runid).returncode, 0)
            self.assertEqual(fx.plan_start_seal().returncode, 0)
            self.assertEqual(fx.complete().returncode, 0)
            self.assertEqual(fx.gate().returncode, 0)

    def test_all_cached_third_run_is_consistent(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        self.assertEqual(fx.open(runid="20260818T120002Z-abcdef12").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["cached"]), set(fx.docs))
        self.assertEqual(manifest["dispatch"], [])
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "CONSISTENT")

    def test_full_always_dispatches_after_qualified_history(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal(mode="full").returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["dispatch"]), set(fx.docs))
        self.assertEqual(manifest["cached"], [])

    def test_contract_version_change_is_cache_miss(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal(contract="0.10.1").returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(set(manifest["dispatch"]), set(fx.docs))

    def test_mixed_cache_and_dispatch_is_consistent(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        with open(fx.history, encoding="utf-8") as handle:
            history = json.load(handle)
        removed = False
        kept = []
        for entry in history["entries"]:
            if entry["path"] == "docs/b.md" and not removed:
                removed = True
                continue
            kept.append(entry)
        history["entries"] = kept
        write(fx.history, json.dumps(history, sort_keys=True, indent=2) + "\n")
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        with open(os.path.join(fx.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["cached"], ["docs/a.md"])
        self.assertEqual(manifest["dispatch"], ["docs/b.md"])
        fx.complete({"docs/b.md": "PASS"})
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_corrupt_history_is_quarantined_after_cold_dispatch(self):
        fx = RunFixture(self)
        write(fx.history, "{broken")
        fx.open(); self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.evidence["historyStatus"], "corrupt")
        fx.complete()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(fx.history + ".tainted-" + fx.runid))

    def test_cached_content_key_tamper_is_refused_even_with_matching_evidence_sha(self):
        fx = RunFixture(self)
        self.two_passes(fx)
        fx.open(runid="20260818T120002Z-abcdef12")
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(verdicts={}, returns_override=[]).returncode, 0)
        records = {}
        verdict_dir = os.path.join(fx.run_dir, "verdicts")
        for name in os.listdir(verdict_dir):
            path = os.path.join(verdict_dir, name)
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
            records[record["path"]] = (path, record)
        first = sorted(records)[0]
        records[first][1]["contentSha"] = "sha256:" + "0" * 64
        for path, record in records.values():
            raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
            write(path, raw)
        material = bytearray()
        for doc in sorted(records):
            with open(records[doc][0], "rb") as handle:
                material.extend(handle.read())
        fx.evidence["cached"] = "sha256:" + hashlib.sha256(material).hexdigest()
        proc = fx.gate()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "REFUSED")
        self.assertTrue(os.path.exists(fx.anchor))


if __name__ == "__main__":
    unittest.main()
