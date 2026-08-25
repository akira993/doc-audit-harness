"""Deterministic fake-codex tests for the Phase-3 dispatcher prototype."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISPATCH = os.path.join(ROOT, "skills", "audit", "scripts", "codex-dispatch.py")
CHECK = os.path.join(ROOT, "skills", "audit", "scripts", "check-verdicts.py")
SCHEMA = os.path.join(ROOT, "skills", "audit", "references",
                      "codex-phase3-verdict.schema.json")


FAKE_CODEX = r'''#!/bin/sh
set -u
out=""
repo=""
schema=""
sandbox=""
model=""
effort=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    exec|-) shift ;;
    -s) sandbox="$2"; shift 2 ;;
    --output-schema) schema="$2"; shift 2 ;;
    -o) out="$2"; shift 2 ;;
    -C) repo="$2"; shift 2 ;;
    -m) model="$2"; shift 2 ;;
    -c) effort="$2"; shift 2 ;;
    *) shift ;;
  esac
done
prompt=$(cat)
identity=$(printf '%s\n' "$prompt" | sed -n 's/^Expected identity JSON: //p')
runid=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["runid"])' "$identity")
doc=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["path"])' "$identity")
printf '%s\n' "$prompt" > "$FAKE_STATE/last-prompt.txt"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$doc" "$sandbox" "$repo" "$schema" "$model" "$effort" >> "$FAKE_LOG"

emit() {
  target="$1"
  emitted_runid="$2"
  emitted_doc="$3"
  verdict="${4:-PASS}"
  python3 - "$target" "$emitted_runid" "$emitted_doc" "$verdict" <<'PY'
import json, sys
target, runid, path, verdict = sys.argv[1:]
with open(target, "w", encoding="utf-8") as handle:
    json.dump({"runid": runid, "path": path, "verdict": verdict,
               "rationale": "checked " + path + ":1",
               "evidence": [path + ":1"]}, handle)
PY
}

counter() {
  python3 - "$FAKE_STATE/counter" "$FAKE_COUNTS" "$1" <<'PY'
import fcntl, os, sys
path, log, delta = sys.argv[1], sys.argv[2], int(sys.argv[3])
with open(path, "a+", encoding="utf-8") as handle:
    fcntl.flock(handle, fcntl.LOCK_EX)
    handle.seek(0)
    raw = handle.read().strip()
    value = (int(raw) if raw else 0) + delta
    handle.seek(0); handle.truncate(); handle.write(str(value)); handle.flush()
    if delta > 0:
        with open(log, "a", encoding="utf-8") as counts:
            counts.write(str(value) + "\n")
PY
}

case "$FAKE_MODE" in
  normal)
    emit "$out" "$runid" "$doc"
    ;;
  p4_once)
    case "$out" in
      */attempt-01-*) : ;;
      *) emit "$out" "$runid" "$doc" ;;
    esac
    ;;
  missing)
    :
    ;;
  nonzero_valid)
    emit "$out" "$runid" "$doc"
    exit 7
    ;;
  schema_bad)
    printf '{"runid":"%s"}\n' "$runid" > "$out"
    ;;
  runid_mismatch)
    emit "$out" "other-run" "$doc"
    ;;
  path_mismatch)
    emit "$out" "$runid" "docs/other.md"
    ;;
  symlink_output)
    external="$FAKE_STATE/external-$PPID.json"
    emit "$external" "$runid" "$doc"
    ln -s "$external" "$out"
    ;;
  oversized)
    python3 - "$out" <<'PY'
import sys
with open(sys.argv[1], "wb") as handle:
    handle.write(b"x" * (2 * 1024 * 1024 + 1))
PY
    ;;
  timeout_once)
    case "$out" in
      */attempt-01-*)
        (trap '' TERM; sleep 1; emit "$out" "$runid" "$doc") &
        trap '' TERM
        sleep 10
        ;;
      *) emit "$out" "$runid" "$doc" ;;
    esac
    ;;
  parallel)
    counter 1
    sleep 0.2
    emit "$out" "$runid" "$doc"
    counter -1
    ;;
  *) exit 9 ;;
esac
'''


class CodexDispatchFixture:
    def __init__(self, case, docs=None, cached=None, run_mode="incremental",
                 changed_set=None):
        self.case = case
        self.temp = tempfile.TemporaryDirectory()
        case.addCleanup(self.temp.cleanup)
        self.repo = os.path.join(self.temp.name, "repo")
        self.run_dir = os.path.join(self.temp.name, "run")
        self.bin_dir = os.path.join(self.temp.name, "bin")
        self.state = os.path.join(self.temp.name, "fake-state")
        for path in (self.repo, self.run_dir, self.bin_dir, self.state,
                     os.path.join(self.run_dir, "verdicts")):
            os.makedirs(path, exist_ok=True)
        self.docs = docs if docs is not None else ["docs/a.md", "docs/b.md"]
        self.cached = cached if cached is not None else []
        for path in self.docs + self.cached:
            target = os.path.join(self.repo, path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(f"# {path}\n")
        self.runid = "20260825T120000Z-c0decafe"
        manifest = {"sealed": True, "runid": self.runid,
                    "dispatch": self.docs, "cached": self.cached,
                    "impacted": self.docs + self.cached,
                    "baselineSha": "baseline", "head": "head", "mode": run_mode,
                    "changedSet": changed_set if changed_set is not None else []}
        self._write_json(os.path.join(self.run_dir, "manifest.json"), manifest)
        impact = {"impacted": [{"path": path, "provenance": "mapped"}
                               for path in self.docs + self.cached]}
        self._write_json(os.path.join(self.run_dir, "impact.json"), impact)
        self.fake = os.path.join(self.bin_dir, "codex")
        with open(self.fake, "w", encoding="utf-8") as handle:
            handle.write(FAKE_CODEX)
        os.chmod(self.fake, 0o755)
        self.log = os.path.join(self.state, "calls.log")
        self.counts = os.path.join(self.state, "counts.log")

    @staticmethod
    def _write_json(path, value):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle)

    def run(self, mode="normal", timeout="1", concurrency=None, codex_bin=None):
        env = os.environ.copy()
        env["PATH"] = self.bin_dir + os.pathsep + env.get("PATH", "")
        env.update({"FAKE_MODE": mode, "FAKE_LOG": self.log,
                    "FAKE_STATE": self.state, "FAKE_COUNTS": self.counts})
        command = [sys.executable, DISPATCH, "--run-dir", self.run_dir,
                   "--repo-root", self.repo, "--model", "gpt-5.6-luna",
                   "--effort", "medium", "--timeout-seconds", timeout]
        if concurrency is not None:
            command.extend(["--concurrency", str(concurrency)])
        if codex_bin is not None:
            command.extend(["--codex-bin", codex_bin])
        return subprocess.run(command, capture_output=True, text=True, env=env)

    def returns(self):
        with open(os.path.join(self.run_dir, "returns.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def verdicts(self):
        root = os.path.join(self.run_dir, "verdicts")
        records = []
        for name in sorted(os.listdir(root)):
            if name.endswith(".json"):
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    records.append(json.load(handle))
        return records

    def private_dirs(self):
        root = os.path.join(self.run_dir, "codex-out")
        return sorted(os.path.join(root, name) for name in os.listdir(root))

    def prompt(self):
        with open(os.path.join(self.state, "last-prompt.txt"), encoding="utf-8") as handle:
            return handle.read()


class TestCodexDispatch(unittest.TestCase):
    def test_prompt_scope_tracks_full_and_incremental_manifest_modes(self):
        full = CodexDispatchFixture(self, docs=["docs/a.md"], run_mode="full")
        proc = full.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        prompt = full.prompt()
        self.assertIn("This is a full-corpus audit. There is no diff scope.", prompt)
        self.assertIn("current source and configuration at the sealed HEAD", prompt)
        self.assertIn("contradicted by the current source", prompt)
        self.assertNotIn("Baseline commit:", prompt)
        self.assertNotIn("changes between the baseline and sealed HEAD", prompt)
        self.assertNotIn("contradicted by the changed source", prompt)

        incremental = CodexDispatchFixture(
            self, docs=["docs/a.md"], run_mode="incremental",
            changed_set=["src/changed.py", "docs/new-untracked.md"])
        proc = incremental.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        prompt = incremental.prompt()
        self.assertIn("Baseline commit: baseline", prompt)
        self.assertIn("changes between the baseline and sealed HEAD", prompt)
        self.assertIn("contradicted by the changed source", prompt)
        self.assertIn("Sealed changed paths: 2 total; showing 2:", prompt)
        self.assertIn('- "src/changed.py"', prompt)
        self.assertIn('- "docs/new-untracked.md"', prompt)
        self.assertIn("may include uncommitted\nand untracked changes", prompt)
        self.assertIn("do not rely only on commit history", prompt)
        self.assertNotIn("This is a full-corpus audit", prompt)
        self.assertNotIn("contradicted by the current source", prompt)

    def test_incremental_prompt_caps_changed_paths_with_total_count(self):
        changed = [f"src/changed-{number:03d}.py" for number in range(105)]
        fx = CodexDispatchFixture(
            self, docs=["docs/a.md"], run_mode="incremental",
            changed_set=changed)
        proc = fx.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        prompt = fx.prompt()
        self.assertIn("Sealed changed paths: 105 total; showing 100:", prompt)
        self.assertIn('- "src/changed-099.py"', prompt)
        self.assertNotIn("src/changed-100.py", prompt)

    def test_empty_dispatch_writes_empty_returns_without_starting_codex(self):
        fx = CodexDispatchFixture(self, docs=[])
        proc = fx.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {
            "returnsPath": os.path.realpath(os.path.join(fx.run_dir, "returns.json")),
            "attempts": 0, "ok": 0, "failed": 0})
        self.assertEqual(fx.returns(), [])
        self.assertEqual(fx.private_dirs(), [])
        self.assertFalse(os.path.exists(fx.log))

    def test_happy_path_publishes_atomic_verdicts_and_current_returns_contract(self):
        fx = CodexDispatchFixture(self, cached=["docs/cached.md"])
        proc = fx.run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary, {
            "returnsPath": os.path.realpath(os.path.join(fx.run_dir, "returns.json")),
            "attempts": 1, "ok": 2, "failed": 0})
        returns = fx.returns()
        self.assertEqual(len(returns), 2)
        for row in returns:
            self.assertEqual(row["attempt"], 1)
            self.assertEqual(row["returnedPath"], row["assignedPath"])
            self.assertEqual(row["verdict"], "PASS")
            self.assertIsInstance(row["rationale"], str)
            self.assertIsNone(row["suggestion"])
        self.assertEqual({item["path"] for item in fx.verdicts()}, set(fx.docs))
        self.assertFalse(any(name.startswith(".verdict.")
                             for name in os.listdir(os.path.join(fx.run_dir, "verdicts"))))

        checked = subprocess.run(
            [sys.executable, CHECK, "--run-dir", fx.run_dir,
             "--impact-json", os.path.join(fx.run_dir, "impact.json"), "--returns"],
            capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        check_result = json.loads(checked.stdout)
        self.assertEqual(check_result["returnMissing"], [])
        self.assertEqual(check_result["mismatch"], [])
        with open(fx.log, encoding="utf-8") as handle:
            calls = [line.rstrip("\n").split("\t") for line in handle]
        self.assertEqual({call[0] for call in calls}, set(fx.docs))
        self.assertNotIn("docs/cached.md", {call[0] for call in calls})
        for _doc, sandbox, repo, schema, model, effort in calls:
            self.assertEqual(sandbox, "read-only")
            self.assertEqual(repo, os.path.realpath(fx.repo))
            self.assertEqual(schema, SCHEMA)
            self.assertEqual(model, "gpt-5.6-luna")
            self.assertEqual(effort, "model_reasoning_effort=medium")

    def test_p4_exit_zero_without_output_is_null_then_retried(self):
        fx = CodexDispatchFixture(self, docs=["docs/a.md"])
        proc = fx.run(mode="p4_once", codex_bin=fx.fake)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["attempts"], 2)
        rows = fx.returns()
        self.assertEqual(rows[0], {
            "attempt": 1, "assignedPath": "docs/a.md", "returnedPath": None,
            "verdict": None, "rationale": None, "suggestion": None})
        self.assertEqual(rows[1]["attempt"], 2)
        self.assertEqual(rows[1]["returnedPath"], "docs/a.md")

    def test_nonzero_exit_rejects_an_otherwise_valid_file(self):
        fx = CodexDispatchFixture(self, docs=["docs/a.md"])
        proc = fx.run(mode="nonzero_valid")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {
            "returnsPath": os.path.realpath(os.path.join(fx.run_dir, "returns.json")),
            "attempts": 3, "ok": 0, "failed": 1})
        self.assertEqual(len(fx.returns()), 3)
        self.assertTrue(all(row["returnedPath"] is None for row in fx.returns()))
        self.assertEqual(fx.verdicts(), [])
        self.assertTrue(all(os.path.isfile(os.path.join(path, "out.json"))
                            for path in fx.private_dirs()))

    def test_schema_runid_and_path_mismatches_are_rejected(self):
        for mode in ("schema_bad", "runid_mismatch", "path_mismatch"):
            with self.subTest(mode=mode):
                fx = CodexDispatchFixture(self, docs=["docs/a.md"])
                proc = fx.run(mode=mode)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["failed"], 1)
                self.assertEqual(len(fx.returns()), 3)
                self.assertTrue(all(row["verdict"] is None for row in fx.returns()))
                self.assertEqual(fx.verdicts(), [])

    def test_symlink_and_oversized_outputs_are_rejected(self):
        for mode in ("symlink_output", "oversized"):
            with self.subTest(mode=mode):
                fx = CodexDispatchFixture(self, docs=["docs/a.md"])
                proc = fx.run(mode=mode)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["failed"], 1)
                self.assertTrue(all(row["verdict"] is None for row in fx.returns()))
                self.assertEqual(fx.verdicts(), [])

    def test_timeout_kills_process_group_and_late_writer_cannot_contaminate_retry(self):
        fx = CodexDispatchFixture(self, docs=["docs/a.md"])
        proc = fx.run(mode="timeout_once", timeout="0.5")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["attempts"], 2)
        rows = fx.returns()
        self.assertIsNone(rows[0]["returnedPath"])
        self.assertEqual(rows[1]["returnedPath"], "docs/a.md")
        first, second = fx.private_dirs()
        self.assertIn("attempt-01-", first)
        self.assertIn("attempt-02-", second)
        time.sleep(1.1)
        self.assertFalse(os.path.exists(os.path.join(first, "out.json")))
        self.assertTrue(os.path.isfile(os.path.join(second, "out.json")))
        self.assertEqual([item["path"] for item in fx.verdicts()], ["docs/a.md"])

    def test_concurrency_two_completes_four_docs_without_mixing(self):
        docs = [f"docs/{name}.md" for name in "abcd"]
        fx = CodexDispatchFixture(self, docs=docs)
        proc = fx.run(mode="parallel", concurrency=2)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["ok"], 4)
        with open(fx.counts, encoding="utf-8") as handle:
            counts = [int(line) for line in handle]
        self.assertEqual(max(counts), 2)
        self.assertEqual({row["assignedPath"] for row in fx.returns()}, set(docs))
        records = fx.verdicts()
        self.assertEqual({item["path"] for item in records}, set(docs))
        for record in records:
            self.assertIn(record["path"], record["rationale"])

    def test_three_attempt_limit_keeps_null_rows_for_gate_refusal(self):
        fx = CodexDispatchFixture(self, docs=["docs/a.md"])
        proc = fx.run(mode="missing")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["attempts"], 3)
        self.assertEqual(summary["failed"], 1)
        rows = fx.returns()
        self.assertEqual([row["attempt"] for row in rows], [1, 2, 3])
        self.assertTrue(all(row["assignedPath"] == "docs/a.md" for row in rows))
        self.assertTrue(all(row["returnedPath"] is None and row["verdict"] is None
                            and row["rationale"] is None and row["suggestion"] is None
                            for row in rows))

    def test_same_run_reexecution_never_reuses_private_directories(self):
        fx = CodexDispatchFixture(self, docs=["docs/a.md"])
        first = fx.run()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = set(fx.private_dirs())
        second = fx.run()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        after = set(fx.private_dirs())
        self.assertEqual(len(before), 1)
        self.assertEqual(len(after), 2)
        self.assertTrue(before < after)
        self.assertEqual(len(fx.returns()), 1)
        self.assertEqual(len(fx.verdicts()), 1)


if __name__ == "__main__":
    unittest.main()
