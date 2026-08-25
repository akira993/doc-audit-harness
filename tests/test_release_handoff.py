"""Branch and archive-boundary tests for the v0.12.0 release handoff."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(
    ROOT, "tasks", "route", "2026-08-25-issues-28-37-release",
    "release-handoff.sh")
APPROVED = "a" * 40
OLD_SHA = "b" * 40
WRONG = "c" * 40


FAKE_TOOL = r'''
import io
import json
import os
import shutil
import sys
import tarfile

tool = os.path.basename(sys.argv[0])
args = sys.argv[1:]
state_path = os.environ["FAKE_STATE"]
log_path = os.environ["FAKE_LOG"]

with open(state_path, encoding="utf-8") as handle:
    state = json.load(handle)
with open(log_path, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"tool": tool, "args": args}) + "\n")

def save():
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, sort_keys=True)

def finish(code=0, output=None):
    save()
    if output is not None:
        print(output)
    raise SystemExit(code)

if tool == "git":
    command = args[0] if args else ""
    if command == "fetch":
        finish(1 if state.get("fetch_fail") else 0)
    if command == "rev-parse":
        if args[1:] == ["--show-toplevel"]:
            finish(output=state["repo"])
        if args[1:] == ["HEAD"]:
            finish(output=state["head"])
        if args[1:] == ["refs/remotes/origin/main^{commit}"]:
            finish(output=state["origin"])
        if args[1:] == ["01344ea^{commit}"]:
            finish(output=state["old_sha"])
        if len(args) == 4 and args[1:3] == ["-q", "--verify"]:
            ref = args[3]
            prefix = "refs/tags/"
            suffix = "^{commit}"
            if ref.startswith(prefix) and ref.endswith(suffix):
                tag = ref[len(prefix):-len(suffix)]
                value = state["local_tags"].get(tag)
                finish(0 if value else 1, value)
        finish(2)
    if command == "branch" and args[1:] == ["--show-current"]:
        finish(output=state.get("branch", ""))
    if command == "status":
        finish(output=" M tracked.txt" if state.get("tracked_dirty") else "")
    if command == "checkout":
        if args[1] == "--detach":
            state["branch"] = ""
            state["head"] = args[2]
        elif args[1] == "main":
            state["branch"] = "main"
            state["head"] = state["approved"]
        else:
            finish(2)
        finish()
    if command == "tag" and len(args) == 3:
        state["local_tags"][args[1]] = args[2]
        finish()
    if command == "push" and len(args) == 3:
        tag = args[2]
        state["remote_tags"][tag] = state["local_tags"][tag]
        finish()
    if command == "ls-remote":
        tag = args[-1].removeprefix("refs/tags/")
        value = state["remote_tags"].get(tag)
        finish(output=f"{value}\trefs/tags/{tag}" if value else "")
    if command == "archive":
        tag = args[-1]
        state.setdefault("archive_refs", []).append(tag)
        save()
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            for name, content in state["archive_entries"].items():
                raw = content.encode("utf-8")
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                info.mode = 0o755 if name.endswith(".py") else 0o644
                archive.addfile(info, io.BytesIO(raw))
        raise SystemExit(0)
    finish(2)

if tool == "gh":
    if args[:2] == ["release", "view"]:
        tag = args[2]
        release = state["releases"].get(tag)
        if release is None:
            finish(1)
        field = args[args.index("--jq") + 1].lstrip(".")
        mapping = {"tagName": tag, "isDraft": release["draft"],
                   "isPrerelease": release["prerelease"], "body": release["body"]}
        value = mapping[field]
        if isinstance(value, bool):
            value = str(value).lower()
        finish(output=value)
    if args[:2] in (["release", "create"], ["release", "edit"]):
        action, tag = args[1], args[2]
        if action == "edit" and tag in state.get("release_edit_fail_tags", []):
            finish(1)
        notes = args[args.index("--notes-file") + 1]
        with open(notes, encoding="utf-8") as handle:
            body = handle.read()
        state["releases"][tag] = {"draft": False, "prerelease": False, "body": body}
        finish()
    if args[:2] == ["issue", "view"]:
        finish(output=state["issues"].get(args[2], "OPEN"))
    if args[:2] == ["issue", "close"]:
        issue = args[2]
        state["issues"][issue] = "CLOSED"
        state.setdefault("issue_comments", {})[issue] = args[args.index("--comment") + 1]
        finish()
    finish(2)

if tool == "python3":
    if args[:2] == ["-m", "unittest"]:
        state["suite_runs"] = state.get("suite_runs", 0) + 1
        finish(1 if state.get("suite_fail") else 0)
    if args and args[0].endswith("skills/audit/scripts/generic-layers.py") and args[1:] == ["--help"]:
        state["smoke_runs"] = state.get("smoke_runs", 0) + 1
        finish(0 if os.path.isfile(args[0]) else 2)
    finish(2)

if tool == "rsync":
    dry_run = "--dry-run" in args
    required = ["--delete", "--delete-excluded", "--filter=P /AGENTS.md",
                "--filter=H /AGENTS.md", "--filter=H /tasks/"]
    if any(item not in args for item in required):
        finish(8)
    source = args[-2].rstrip("/")
    destination = args[-1].rstrip("/")
    state.setdefault("rsync_sources", []).append(source)
    state.setdefault("rsync_dry_runs", 0)
    if dry_run:
        state["rsync_dry_runs"] += 1
        finish(output="MISMATCH" if state.get("dry_run_mismatch") else "")
    if state.get("rsync_failures_remaining", 0):
        state["rsync_failures_remaining"] -= 1
        finish(1)
    protected = {".git", ".venv", ".brv", ".DS_Store", "AGENTS.md",
                 ".claude", ".mdq", ".serena", ".envrc", "__pycache__"}
    os.makedirs(destination, exist_ok=True)
    for name in os.listdir(destination):
        if name in protected or name.endswith(".pyc"):
            continue
        path = os.path.join(destination, name)
        shutil.rmtree(path) if os.path.isdir(path) and not os.path.islink(path) else os.unlink(path)
    for name in os.listdir(source):
        if name in protected or name.endswith(".pyc"):
            continue
        src = os.path.join(source, name)
        dst = os.path.join(destination, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    state["synced_source_entries"] = sorted(os.listdir(source))
    finish()

finish(2)
'''


class TestReleaseHandoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        self.bin = os.path.join(self.tmp.name, "bin")
        self.dest = os.path.join(self.tmp.name, "skills", "docaudit")
        self.state_path = os.path.join(self.tmp.name, "state.json")
        self.log_path = os.path.join(self.tmp.name, "calls.jsonl")
        os.makedirs(self.repo)
        os.makedirs(self.bin)
        self.state = {
            "repo": self.repo,
            "approved": APPROVED,
            "old_sha": OLD_SHA,
            "branch": "main",
            "head": APPROVED,
            "origin": APPROVED,
            "local_tags": {},
            "remote_tags": {},
            "releases": {},
            "issues": {"28": "OPEN", "37": "OPEN"},
            "archive_entries": {
                ".claude-plugin/plugin.json": '{"version":"0.12.0"}\n',
                "skills/audit/scripts/generic-layers.py": "#!/usr/bin/env python3\n",
                "docs/ADOPTION.md": "tracked docs\n",
                "tasks/private.txt": "must not ship\n",
                "tests/private.txt": "must not ship\n",
                "docs/superpowers/private.txt": "must not ship\n",
                ".gitignore": "must not ship\n",
                "AGENTS.md": "archive copy must not overwrite local\n",
                "tracked.txt": "tracked archive content\n",
            },
        }
        self.save()
        shebang = f"#!{sys.executable}\n"
        for name in ("git", "gh", "rsync", "python3"):
            path = os.path.join(self.bin, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(shebang + FAKE_TOOL)
            os.chmod(path, 0o755)

    def save(self):
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, sort_keys=True)

    def load(self):
        with open(self.state_path, encoding="utf-8") as handle:
            self.state = json.load(handle)
        return self.state

    def valid_old_release(self):
        return {"draft": False, "prerelease": False,
                "body": "Retrospective release\nPublished retrospectively on 2026-08-25\n"
                        f"{OLD_SHA}\nKnown issue #37\nfollow-up v0.12.0\n"}

    def valid_new_release(self):
        return {"draft": False, "prerelease": False,
                "body": f"{APPROVED}\nFix #37 and ship #28 via phase3Backend\n"
                        "/docaudit:audit --break-lock\n"}

    def completed_publication(self):
        self.state["local_tags"] = {
            "docaudit--v0.11.0": OLD_SHA, "docaudit--v0.12.0": APPROVED}
        self.state["remote_tags"] = dict(self.state["local_tags"])
        self.state["releases"] = {
            "docaudit--v0.11.0": self.valid_old_release(),
            "docaudit--v0.12.0": self.valid_new_release(),
        }
        self.save()

    def run_handoff(self, *args, answer="y\n"):
        env = os.environ.copy()
        env.update({
            "PATH": self.bin + os.pathsep + "/usr/bin:/bin",
            "FAKE_STATE": self.state_path,
            "FAKE_LOG": self.log_path,
            "DOCAUDIT_SKILLS_DIR": self.dest,
        })
        return subprocess.run(
            ["/bin/bash", HANDOFF, *args], cwd=self.repo, env=env,
            input=answer, capture_output=True, text=True)

    def calls(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_wrong_sha_existing_tag_stops(self):
        for tag in ("docaudit--v0.11.0", "docaudit--v0.12.0"):
            with self.subTest(tag=tag):
                self.state["local_tags"] = {tag: WRONG}
                self.state["remote_tags"] = {tag: WRONG}
                self.state["releases"] = {}
                self.save()
                proc = self.run_handoff(APPROVED, "42")
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("local tag", proc.stderr)
                state = self.load()
                self.assertEqual(state.get("suite_runs", 0), 0)
                self.assertEqual(state["releases"], {})

    def test_correct_tag_missing_release_reruns_suite_and_resumes(self):
        self.state["local_tags"] = {
            "docaudit--v0.11.0": OLD_SHA, "docaudit--v0.12.0": APPROVED}
        self.state["remote_tags"] = dict(self.state["local_tags"])
        self.state["releases"] = {"docaudit--v0.11.0": self.valid_old_release()}
        self.save()
        proc = self.run_handoff(APPROVED, "42")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self.load()
        self.assertEqual(state["suite_runs"], 1)
        self.assertIn("docaudit--v0.12.0", state["releases"])
        suite_calls = [call for call in self.calls()
                       if call["tool"] == "python3" and call["args"][:2] == ["-m", "unittest"]]
        self.assertEqual(suite_calls[0]["args"],
                         ["-m", "unittest", "discover", "-s", "tests", "-t", "."])

    def test_releases_done_resumes_open_issues_and_sync(self):
        self.completed_publication()
        proc = self.run_handoff(APPROVED, "77")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self.load()
        self.assertEqual(state["issues"], {"28": "CLOSED", "37": "CLOSED"})
        self.assertIn("PR #77", state["issue_comments"]["28"])
        self.assertEqual(state["rsync_dry_runs"], 1)

    def test_missing_or_invalid_sha_argument_stops_before_tools(self):
        for args in ((), ("bad", "42"), ("a" * 39, "42")):
            with self.subTest(args=args):
                if os.path.exists(self.log_path):
                    os.unlink(self.log_path)
                proc = self.run_handoff(*args)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(self.calls(), [])

    def test_fetch_failure_stops(self):
        self.state["fetch_fail"] = True
        self.save()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("fetch", proc.stderr)
        self.assertEqual(self.calls()[0]["args"], ["fetch", "origin"])

    def test_local_remote_tag_mismatch_stops(self):
        self.state["local_tags"]["docaudit--v0.11.0"] = OLD_SHA
        self.state["remote_tags"]["docaudit--v0.11.0"] = WRONG
        self.save()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("remote tag", proc.stderr)

    def test_symlink_destination_stops_before_rsync(self):
        self.completed_publication()
        target = os.path.join(self.tmp.name, "actual-destination")
        os.makedirs(target)
        os.makedirs(os.path.dirname(self.dest), exist_ok=True)
        os.symlink(target, self.dest)
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("symlink", proc.stderr)
        self.assertFalse(any(call["tool"] == "rsync" for call in self.calls()))

    def test_rsync_failure_is_restart_safe(self):
        self.state["rsync_failures_remaining"] = 1
        self.save()
        first = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(first.returncode, 0)
        state = self.load()
        self.assertEqual(state["issues"], {"28": "CLOSED", "37": "CLOSED"})
        second = self.run_handoff(APPROVED, "42")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        state = self.load()
        self.assertEqual(state["suite_runs"], 2)
        creates = [call for call in self.calls()
                   if call["tool"] == "gh" and call["args"][:2] == ["release", "create"]]
        self.assertEqual(len(creates), 2)

    def test_first_run_publishes_both_stages_and_syncs_only_tag_archive(self):
        with open(os.path.join(self.repo, "untracked.txt"), "w", encoding="utf-8") as handle:
            handle.write("live worktree only")
        os.makedirs(os.path.join(self.dest, ".git"), exist_ok=True)
        with open(os.path.join(self.dest, ".git", "local"), "w", encoding="utf-8") as handle:
            handle.write("keep")
        with open(os.path.join(self.dest, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("local instructions")
        os.makedirs(os.path.join(self.dest, "tasks"), exist_ok=True)
        with open(os.path.join(self.dest, "tasks", "old"), "w", encoding="utf-8") as handle:
            handle.write("delete")
        with open(os.path.join(self.dest, "old.txt"), "w", encoding="utf-8") as handle:
            handle.write("delete")

        proc = self.run_handoff(APPROVED, "42")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self.load()
        self.assertEqual(state["remote_tags"], {
            "docaudit--v0.11.0": OLD_SHA, "docaudit--v0.12.0": APPROVED})
        self.assertEqual(set(state["releases"]), {
            "docaudit--v0.11.0", "docaudit--v0.12.0"})
        self.assertEqual(state["archive_refs"], ["docaudit--v0.12.0"])
        self.assertTrue(all(source != self.repo for source in state["rsync_sources"]))
        self.assertNotIn("tasks", state["synced_source_entries"])
        self.assertNotIn("tests", state["synced_source_entries"])
        self.assertNotIn(".gitignore", state["synced_source_entries"])
        with open(os.path.join(self.dest, "AGENTS.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "local instructions")
        self.assertTrue(os.path.exists(os.path.join(self.dest, ".git", "local")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "tasks")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "old.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.dest, "tracked.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.dest, "untracked.txt")))
        rsync_calls = [call["args"] for call in self.calls() if call["tool"] == "rsync"]
        self.assertEqual(len(rsync_calls), 2)
        first_boundary = [arg for arg in rsync_calls[0] if arg.startswith("--filter=")]
        second_boundary = [arg for arg in rsync_calls[1] if arg.startswith("--filter=")]
        self.assertEqual(first_boundary, second_boundary)
        self.assertEqual(rsync_calls[0][-2:], rsync_calls[1][-2:])

    def test_invalid_existing_release_must_be_repaired_or_stops_for_each_tag(self):
        for bad_tag in ("docaudit--v0.11.0", "docaudit--v0.12.0"):
            with self.subTest(tag=bad_tag):
                self.state["branch"] = "main"
                self.state["head"] = APPROVED
                self.state["local_tags"] = {
                    "docaudit--v0.11.0": OLD_SHA, "docaudit--v0.12.0": APPROVED}
                self.state["remote_tags"] = dict(self.state["local_tags"])
                self.state["releases"] = {
                    "docaudit--v0.11.0": self.valid_old_release(),
                    "docaudit--v0.12.0": self.valid_new_release(),
                }
                self.state["releases"][bad_tag] = {
                    "draft": True, "prerelease": False, "body": "missing required notes"}
                self.state["release_edit_fail_tags"] = [bad_tag]
                self.save()
                proc = self.run_handoff(APPROVED, "42")
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("invalid release", proc.stderr)
                self.assertTrue(any(call["tool"] == "gh"
                                    and call["args"][:3] == ["release", "edit", bad_tag]
                                    for call in self.calls()))


if __name__ == "__main__":
    unittest.main()
