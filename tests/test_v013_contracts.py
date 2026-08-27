import json
import os
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, ".claude-plugin", "plugin.json")
SHAS = os.path.join(ROOT, "skills", "audit", "references", "engine-shas.json")
SCAFFOLD = os.path.join(ROOT, "skills", "audit", "scripts", "scaffold.py")


class TestV013Contracts(unittest.TestCase):
    def test_a_init_argument_hint(self):
        self.skipTest("added in S2..S5")

    def test_b_audit_history_argument(self):
        self.skipTest("added in S2..S5")

    def test_c_audit_scope_check_order(self):
        self.skipTest("added in S2..S5")

    def test_d_audit_scope_write_contract(self):
        self.skipTest("added in S2..S5")

    def test_e_codex_review_evidence_order(self):
        self.skipTest("added in S2..S5")

    def test_f_sealed_manifest_rebinding(self):
        self.skipTest("added in S2..S5")

    def test_g_regression_provenance_consumers(self):
        self.skipTest("added in S2..S5")

    def test_h_config_schema_keys(self):
        self.skipTest("added in S2..S5")

    def test_i_release_version_matches_all_five_surfaces(self):
        with open(PLUGIN, encoding="utf-8") as handle:
            plugin_version = json.load(handle)["version"]
        with open(SHAS, encoding="utf-8") as handle:
            shipped = json.load(handle)
        latest_sha_version = max(shipped, key=self._semver_key)

        adoption_version = self._adoption_list_version("docs/ADOPTION.md")
        adoption_ja_version = self._adoption_list_version("docs/ADOPTION.ja.md")
        with tempfile.TemporaryDirectory() as repo:
            proc = subprocess.run(
                [sys.executable, SCAFFOLD, "--repo-root", repo, "--harness", "--dry-run"],
                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        stamp_version = json.loads(proc.stdout)["stampVersion"]

        self.assertEqual(
            {plugin_version, latest_sha_version, adoption_version,
             adoption_ja_version, stamp_version},
            {"0.13.0"})

    def test_j_only_allowlisted_0_12_0_references_remain(self):
        self.skipTest("enabled in S5 after release-handoff tests move to 0.13.0")
        old_version = "0." "12.0"
        old = re.escape(old_version)
        allowed = {
            "docs/ADOPTION.md": [
                rf"Separately, v{old} can opt Phase 3 into .*",
                rf"\*\*v{old} behavior changes:\*\*.*",
                rf"Existing unmodified stamped 0\.10\.1, 0\.11\.0, or {old} templates can be updated directly to 0\.13\.0 with",
            ],
            "docs/ADOPTION.ja.md": [
                rf"これとは別に、v{old} では Phase 3 を .*",
                rf"\*\*v{old} の挙動変更:\*\*.*",
                rf"変更されていない stamp 付きの 0\.10\.1、0\.11\.0、または {old} テンプレートは、",
            ],
            "skills/audit/references/engine-shas.json": [
                rf'\s*"{old}": \{{',
            ],
            "tests/test_scaffold.py": [
                rf'.*"tests", "data", "engine-{old}\.py".*',
                rf'\s*shipped = json\.loads\(read\(SHAS\)\)\["{old}"\]\["check-docs-engine"\]',
                rf'\s*module\._python_with_stamp\(old, "check-docs-engine", "{old}", shipped\)\)',
            ],
        }
        proc = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
        paths = proc.stdout.decode("utf-8").split("\0")
        shipped_paths = [path for path in paths if path and (
            path.startswith(("skills/", "agents/", "docs/", ".claude-plugin/", "tests/"))
            or path == "README.md")]
        unexpected = []
        for path in shipped_paths:
            with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    if old_version not in line:
                        continue
                    patterns = allowed.get(path, [])
                    if not any(re.fullmatch(pattern, line.rstrip("\r\n"))
                               for pattern in patterns):
                        unexpected.append(f"{path}:{line_number}: {line.rstrip()}")
        self.assertEqual(unexpected, [])

    @staticmethod
    def _semver_key(version):
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match:
            raise AssertionError(f"non-semver engine-shas key: {version}")
        return tuple(int(part) for part in match.groups())

    @staticmethod
    def _adoption_list_version(relative_path):
        with open(os.path.join(ROOT, relative_path), encoding="utf-8") as handle:
            matches = re.findall(
                r"^claude plugin list\s+# .* Version (\d+\.\d+\.\d+)\s+Scope:",
                handle.read(), re.MULTILINE)
        if len(matches) != 1:
            raise AssertionError(f"expected one claude plugin list version in {relative_path}")
        return matches[0]


if __name__ == "__main__":
    unittest.main()
