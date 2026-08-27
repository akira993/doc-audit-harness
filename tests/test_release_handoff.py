"""Branch, publication, and archive-boundary tests for the v0.13.1 handoff."""

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(
    ROOT,
    "tasks",
    "route",
    "2026-08-27-issues-46-50-v0.13.1",
    "release-handoff.sh",
)
APPROVED = "a" * 40
WRONG = "c" * 40
TAG = "docaudit--v0.13.1"
TITLE = "docaudit v0.13.1 — documentation consistency (#46–#50)"
ISSUES = {str(number) for number in range(46, 51)}
PRECLOSED = {"46", "47"}
REQUIRED_BODY = (
    APPROVED,
    "#46",
    "#47",
    "#48",
    "#49",
    "#50",
    "digestExclude",
    "docs-only",
)


FAKE_TOOL = r'''
import io
import json
import os
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


def tag_from_commit_ref(ref):
    prefix = "refs/tags/"
    suffix = "^{commit}"
    if not ref.startswith(prefix) or not ref.endswith(suffix):
        return None
    return ref[len(prefix):-len(suffix)]


def run_git():
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
        if len(args) == 4 and args[1:3] == ["-q", "--verify"]:
            tag = tag_from_commit_ref(args[3])
            value = state["local_tags"].get(tag)
            finish(0 if value else 1, value)
        finish(2)
    if command == "branch" and args[1:] == ["--show-current"]:
        finish(output=state["branch"])
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
    if command == "tag":
        state["local_tags"][args[1]] = args[2]
        finish()
    if command == "push":
        source, destination = args[2].split(":", 1)
        tag = source.removeprefix("refs/tags/")
        if destination != f"refs/tags/{tag}":
            finish(2)
        state["remote_tags"][tag] = state["local_tags"][tag]
        finish()
    if command == "ls-remote":
        tag = args[-1].removeprefix("refs/tags/")
        value = state["remote_tags"].get(tag)
        output = f"{value}\trefs/tags/{tag}" if value else ""
        finish(output=output)
    if command == "archive":
        state.setdefault("archive_refs", []).append(args[-1])
        save()
        payload = b"#!/usr/bin/env python3\n"
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            info = tarfile.TarInfo("skills/audit/scripts/generic-layers.py")
            info.size = len(payload)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(payload))
        raise SystemExit(0)
    finish(2)


def run_gh():
    if args[:2] == ["release", "view"]:
        release = state["releases"].get(args[2])
        if release is None:
            finish(1)
        field = args[args.index("--jq") + 1].lstrip(".")
        values = {
            "tagName": args[2],
            "name": release["title"],
            "isDraft": str(release.get("draft", False)).lower(),
            "isPrerelease": str(release.get("prerelease", False)).lower(),
            "body": release["body"],
        }
        finish(output=values[field])
    if args[:2] == ["release", "create"]:
        notes_path = args[args.index("--notes-file") + 1]
        with open(notes_path, encoding="utf-8") as handle:
            body = handle.read()
        state["releases"][args[2]] = {
            "title": args[args.index("--title") + 1],
            "body": body,
            "draft": False,
            "prerelease": False,
        }
        finish()
    if args[:2] == ["issue", "view"]:
        finish(output=state["issues"][args[2]])
    if args[:2] == ["issue", "close"]:
        issue = args[2]
        state["issues"][issue] = "CLOSED"
        state.setdefault("closed", []).append(issue)
        finish()
    finish(2)


def run_python():
    if args[:2] == ["-m", "unittest"]:
        state["suite_runs"] = state.get("suite_runs", 0) + 1
        finish(1 if state.get("suite_fail") else 0)
    if args and args[0].endswith("generic-layers.py"):
        state["smoke_runs"] = state.get("smoke_runs", 0) + 1
        finish()
    finish(2)


def run_rsync():
    if "--dry-run" in args:
        state["rsync_dry_runs"] = state.get("rsync_dry_runs", 0) + 1
    else:
        state["rsync_runs"] = state.get("rsync_runs", 0) + 1
    finish()


if tool == "git":
    run_git()
if tool == "gh":
    run_gh()
if tool == "python3":
    run_python()
if tool == "rsync":
    run_rsync()
finish(2)
'''


class TestReleaseHandoff(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = os.path.realpath(self.temp.name)
        self.repo = os.path.join(base, "repo")
        self.bin_dir = os.path.join(base, "bin")
        self.skills_root = os.path.join(base, "skills")
        self.destination = os.path.join(self.skills_root, "docaudit")
        self.state_path = os.path.join(base, "state.json")
        self.log_path = os.path.join(base, "calls.jsonl")
        os.makedirs(self.repo)
        os.makedirs(self.bin_dir)
        self.state = {
            "repo": self.repo,
            "approved": APPROVED,
            "head": APPROVED,
            "origin": APPROVED,
            "branch": "main",
            "local_tags": {},
            "remote_tags": {},
            "releases": {},
            "issues": {issue: "OPEN" for issue in ISSUES},
            "closed": [],
        }
        self.save_state()
        self.install_fake_tools()

    def install_fake_tools(self):
        shebang = f"#!{sys.executable}\n"
        for name in ("git", "gh", "python3", "rsync"):
            path = os.path.join(self.bin_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(shebang + FAKE_TOOL)
            os.chmod(path, 0o755)

    def save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, sort_keys=True)

    def load_state(self):
        with open(self.state_path, encoding="utf-8") as handle:
            self.state = json.load(handle)
        return self.state

    def run_handoff(self, *args, answer="y\n", destination=None, skills_root=None):
        env = os.environ.copy()
        env.update({
            "PATH": self.bin_dir + os.pathsep + "/usr/bin:/bin",
            "FAKE_STATE": self.state_path,
            "FAKE_LOG": self.log_path,
            "DOCAUDIT_SKILLS_DIR": destination or self.destination,
            "DOCAUDIT_SKILLS_ROOT": skills_root or self.skills_root,
        })
        return subprocess.run(
            ["/bin/bash", HANDOFF, *args],
            cwd=self.repo,
            env=env,
            input=answer,
            capture_output=True,
            text=True,
        )

    def calls(self, tool=None, prefix=None):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as handle:
            calls = [json.loads(line) for line in handle if line.strip()]
        if tool is not None:
            calls = [call for call in calls if call["tool"] == tool]
        if prefix is not None:
            calls = [call for call in calls if call["args"][:len(prefix)] == prefix]
        return calls

    def assert_no_release_mutations(self):
        self.assertEqual(self.calls("git", ["tag"]), [])
        self.assertEqual(self.calls("git", ["push"]), [])
        self.assertEqual(self.calls("gh", ["release", "create"]), [])
        self.assertEqual(self.calls("gh", ["issue", "close"]), [])
        self.assertEqual(self.calls("rsync"), [])

    def valid_release(self):
        return {
            "title": TITLE,
            "body": "\n".join(REQUIRED_BODY),
            "draft": False,
            "prerelease": False,
        }

    def mark_tag_published(self):
        self.state["local_tags"][TAG] = APPROVED
        self.state["remote_tags"][TAG] = APPROVED

    def test_invalid_sha_stops_before_tools(self):
        for args in ((), ("bad", "42"), ("a" * 39, "42")):
            with self.subTest(args=args):
                proc = self.run_handoff(*args)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(self.calls(), [])

    def test_missing_pr_number_stops_before_tools(self):
        proc = self.run_handoff(APPROVED)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_nonnumeric_pr_number_stops_before_tools(self):
        proc = self.run_handoff(APPROVED, "PR-42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_fetch_failure_stops_before_publication(self):
        self.state["fetch_fail"] = True
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_non_main_branch_stops_before_publication(self):
        self.state["branch"] = "feature"
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_dirty_tree_stops_before_publication(self):
        self.state["tracked_dirty"] = True
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_head_mismatch_stops_before_publication(self):
        self.state["head"] = WRONG
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_origin_main_mismatch_stops_before_publication(self):
        self.state["origin"] = WRONG
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_symlink_destination_stops_before_publication(self):
        os.makedirs(self.skills_root)
        os.symlink(self.skills_root, self.destination)
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_outside_destination_stops_before_publication(self):
        outside = os.path.join(os.path.dirname(self.skills_root), "outside", "docaudit")
        os.makedirs(outside)
        proc = self.run_handoff(APPROVED, "42", destination=outside)
        self.assertNotEqual(proc.returncode, 0)
        self.assert_no_release_mutations()

    def test_unittest_failure_stops_before_tag(self):
        self.state["suite_fail"] = True
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.load_state()["suite_runs"], 1)
        self.assert_no_release_mutations()

    def test_wrong_existing_tag_stops_before_publication(self):
        self.state["local_tags"][TAG] = WRONG
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("local tag", proc.stderr)
        self.assert_no_release_mutations()

    def test_invalid_existing_release_stops_before_close(self):
        self.mark_tag_published()
        self.state["releases"][TAG] = {
            "title": "wrong title",
            "body": "missing required notes",
        }
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.calls("gh", ["release", "create"]), [])
        self.assertEqual(self.calls("gh", ["issue", "close"]), [])
        self.assertEqual(self.calls("rsync"), [])

    def test_success_and_second_run_are_idempotent(self):
        first = self.run_handoff(APPROVED, "77")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        state = self.load_state()
        self.assertEqual(state["local_tags"][TAG], APPROVED)
        self.assertEqual(state["remote_tags"][TAG], APPROVED)
        self.assertEqual(state["releases"][TAG]["title"], TITLE)
        for required in REQUIRED_BODY:
            self.assertIn(required, state["releases"][TAG]["body"])
        self.assertEqual(set(state["closed"]), ISSUES)

        second = self.run_handoff(APPROVED, "77")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        state = self.load_state()
        self.assertEqual(state["suite_runs"], 2)
        self.assertEqual(state["closed"], sorted(ISSUES))

    def test_unrelated_tag_is_not_pushed(self):
        self.state["local_tags"]["scratch-tag"] = APPROVED
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        pushes = [call["args"] for call in self.calls("git", ["push"])]
        self.assertEqual(pushes, [[
            "push",
            "origin",
            f"refs/tags/{TAG}:refs/tags/{TAG}",
        ]])

    def test_resume_from_existing_tag_creates_release_and_retests(self):
        self.mark_tag_published()
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self.load_state()
        self.assertEqual(state["suite_runs"], 1)
        self.assertEqual(self.calls("git", ["tag"]), [])
        self.assertEqual(len(self.calls("gh", ["release", "create"])), 1)
        self.assertEqual(len(self.calls("gh", ["issue", "close"])), len(ISSUES))
        self.assertEqual(state["rsync_runs"], 1)

    def test_resume_release_with_preclosed_issues_closes_only_remaining(self):
        self.assertTrue(PRECLOSED)
        self.assertTrue(PRECLOSED < ISSUES)
        self.mark_tag_published()
        self.state["releases"][TAG] = self.valid_release()
        for issue in PRECLOSED:
            self.state["issues"][issue] = "CLOSED"
        self.save_state()
        proc = self.run_handoff(APPROVED, "42")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.calls("gh", ["release", "create"]), [])
        closed_calls = self.calls("gh", ["issue", "close"])
        self.assertEqual({call["args"][2] for call in closed_calls}, ISSUES - PRECLOSED)
        self.assertEqual(len(closed_calls), len(ISSUES - PRECLOSED))

    def test_declined_sync_stops_after_publication_without_rsync(self):
        proc = self.run_handoff(APPROVED, "42", answer="n\n")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(len(self.calls("git", ["tag"])), 1)
        self.assertEqual(len(self.calls("gh", ["release", "create"])), 1)
        self.assertEqual(len(self.calls("gh", ["issue", "close"])), len(ISSUES))
        self.assertEqual(self.calls("rsync"), [])


if __name__ == "__main__":
    unittest.main()
