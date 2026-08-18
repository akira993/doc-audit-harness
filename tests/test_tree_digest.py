"""Tests for deterministic worktree digest calculation."""

import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "tree-digest.py")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    )


class TestTreeDigest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@t.t")
        git(self.repo, "config", "user.name", "t")
        self.write("tracked.txt", "tracked\n")
        self.write("staged.txt", "staged\n")
        self.write(".mdq/tracked.txt", "excluded\n")
        self.write(".codegraph/tracked.txt", "also excluded\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")

    def write(self, rel, content):
        path = os.path.join(self.repo, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def digest(self, *excludes):
        cmd = [sys.executable, SCRIPT, "--repo-root", self.repo]
        for value in excludes:
            cmd += ["--exclude", value]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        digest = json.loads(p.stdout)["digest"]
        self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
        return digest

    def test_excluded_new_and_changed_files_do_not_change_digest(self):
        before = self.digest(".mdq", ".codegraph")
        self.write(".mdq/tracked.txt", "changed\n")
        self.write(".mdq/new.txt", "new\n")
        self.write(".codegraph/tracked.txt", "changed\n")
        self.write(".codegraph/new.txt", "new\n")
        after = self.digest(".mdq", ".codegraph")
        self.assertEqual(after, before)

    def test_claude_worktrees_are_allowlisted_and_excluded(self):
        before = self.digest(".claude/worktrees")
        self.write(".claude/worktrees/agent/copy.py", "first\n")
        self.assertEqual(self.digest(".claude/worktrees"), before)
        self.write(".claude/worktrees/agent/copy.py", "second\n")
        self.assertEqual(self.digest(".claude/worktrees"), before)

    def test_tracked_unstaged_change_changes_digest(self):
        before = self.digest(".mdq")
        self.write("tracked.txt", "changed unstaged\n")
        self.assertNotEqual(self.digest(".mdq"), before)

    def test_tracked_staged_change_changes_digest(self):
        before = self.digest(".mdq")
        self.write("staged.txt", "changed staged\n")
        git(self.repo, "add", "staged.txt")
        self.assertNotEqual(self.digest(".mdq"), before)

    def test_untracked_content_change_changes_digest(self):
        self.write("new.txt", "one\n")
        before = self.digest(".mdq")
        self.write("new.txt", "two\n")
        self.assertNotEqual(self.digest(".mdq"), before)

    def test_without_excludes_changes_inside_excluded_directory_are_visible(self):
        before = self.digest()
        self.write(".mdq/tracked.txt", "changed without exclusion\n")
        self.write(".mdq/new.txt", "new without exclusion\n")
        self.assertNotEqual(self.digest(), before)

    def test_external_diff_driver_is_ignored(self):
        external = os.path.join(self.repo, "external-diff.sh")
        with open(external, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nprintf fixed\n")
        os.chmod(external, 0o755)
        git(self.repo, "config", "diff.external", external)
        self.write("tracked.txt", "first change\n")
        before = self.digest(".mdq")
        self.write("tracked.txt", "second change\n")
        self.assertNotEqual(self.digest(".mdq"), before)

    def test_untracked_symlink_target_change_changes_digest(self):
        target_a = os.path.join(self.repo, "target-a.txt")
        target_b = os.path.join(self.repo, "target-b.txt")
        self.write("target-a.txt", "a\n")
        self.write("target-b.txt", "b\n")
        link = os.path.join(self.repo, "link.txt")
        os.symlink("target-a.txt", link)
        before = self.digest(".mdq")
        os.unlink(link)
        os.symlink("target-b.txt", link)
        self.assertNotEqual(self.digest(".mdq"), before)

    def test_untracked_directory_symlink_contributes_to_digest(self):
        os.makedirs(os.path.join(self.repo, "real-dir"))
        os.symlink("real-dir", os.path.join(self.repo, "dir-link"))
        before = self.digest(".mdq")
        os.unlink(os.path.join(self.repo, "dir-link"))
        self.assertNotEqual(self.digest(".mdq"), before)


if __name__ == "__main__":
    unittest.main()
