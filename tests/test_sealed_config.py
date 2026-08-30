import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "sealed_config.py")


def tagged_sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class TestSealedConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "config.json")
        self.raw = json.dumps({
            "top": {"value": "hello", "count": 3, "nothing": None},
            "enabled": True,
        }, ensure_ascii=False).encode("utf-8")
        with open(self.path, "wb") as handle:
            handle.write(self.raw)
        self.sha = tagged_sha(self.raw)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, "--config", self.path,
             "--expect-sha", self.sha, *args],
            capture_output=True, text=True)

    def test_module_loads_matching_bytes_and_document(self):
        spec = importlib.util.spec_from_file_location("sealed_config_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw, doc = module.load_sealed_config(self.path, self.sha)
        self.assertEqual(raw, self.raw)
        self.assertEqual(doc["top"]["value"], "hello")

    def test_module_returns_signature_from_read_descriptor(self):
        spec = importlib.util.spec_from_file_location("sealed_config_signature_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw, doc, signature = module.load_sealed_config(
            self.path, self.sha, with_signature=True)
        info = os.lstat(self.path)
        self.assertEqual(raw, self.raw)
        self.assertEqual(doc["enabled"], True)
        self.assertEqual(signature, (info.st_ino, info.st_size, info.st_mtime_ns))

    def test_mismatch_exits_seven_with_fixed_token(self):
        wrong = "sha256:" + "0" * 64
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--config", self.path,
             "--expect-sha", wrong, "--print"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 7)
        self.assertEqual(
            proc.stderr.strip(),
            f"sealed-config-mismatch: expected {wrong} observed {self.sha}")

    def test_symlink_is_rejected(self):
        link = os.path.join(self.tmp.name, "link.json")
        os.symlink(self.path, link)
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--config", link,
             "--expect-sha", self.sha, "--print"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_print_returns_verified_json(self):
        proc = self.run_cli("--print")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), json.loads(self.raw))

    def test_get_dotted_default_and_null(self):
        self.assertEqual(self.run_cli("--get", "top.value").stdout.strip(), '"hello"')
        self.assertEqual(self.run_cli("--get", "missing").stdout.strip(), "null")
        defaulted = self.run_cli("--get", "missing", "--default", '{"x":1}')
        self.assertEqual(json.loads(defaulted.stdout), {"x": 1})
        self.assertEqual(self.run_cli("--get", "top.nothing").stdout.strip(), "null")

    def test_raw_string_and_null(self):
        value = self.run_cli("--get", "top.value", "--raw")
        self.assertEqual((value.returncode, value.stdout), (0, "hello\n"))
        null = self.run_cli("--get", "top.nothing", "--raw")
        self.assertEqual((null.returncode, null.stdout), (0, "\n"))

    def test_raw_non_string_exits_two(self):
        proc = self.run_cli("--get", "top.count", "--raw")
        self.assertEqual(proc.returncode, 2)

    def test_invalid_json_and_invalid_arguments_exit_two(self):
        bad_raw = b"{"
        with open(self.path, "wb") as handle:
            handle.write(bad_raw)
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--config", self.path,
             "--expect-sha", tagged_sha(bad_raw), "--print"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        malformed_sha = subprocess.run(
            [sys.executable, SCRIPT, "--config", self.path,
             "--expect-sha", "bad", "--print"],
            capture_output=True, text=True)
        self.assertEqual(malformed_sha.returncode, 2)

    def test_standalone_generic_copy_supports_optional_and_sealed_modes(self):
        repo = os.path.join(self.tmp.name, "repo")
        scripts = os.path.join(repo, "scripts")
        docs = os.path.join(repo, "docs")
        os.makedirs(scripts)
        os.makedirs(docs)
        copied = os.path.join(scripts, "check-docs.py")
        shutil.copyfile(
            os.path.join(ROOT, "skills", "audit", "scripts", "generic-layers.py"),
            copied)
        config_path = os.path.join(repo, "config.json")
        config_raw = json.dumps({"docGlobs": ["docs/**/*.md"]}).encode("utf-8")
        with open(config_path, "wb") as handle:
            handle.write(config_raw)
        with open(os.path.join(docs, "a.md"), "w", encoding="utf-8") as handle:
            handle.write("# A\n")
        command = [sys.executable, copied, "--config", config_path,
                   "--repo-root", repo, "--layer", "format"]
        unsealed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(unsealed.returncode, 0, unsealed.stderr)
        sealed = subprocess.run(
            command + ["--expect-config-sha", tagged_sha(config_raw)],
            capture_output=True, text=True)
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        wrong = "sha256:" + "0" * 64
        mismatch = subprocess.run(
            command + ["--expect-config-sha", wrong],
            capture_output=True, text=True)
        self.assertEqual(mismatch.returncode, 7)
        self.assertEqual(
            mismatch.stderr.strip(),
            f"sealed-config-mismatch: expected {wrong} observed {tagged_sha(config_raw)}")


if __name__ == "__main__":
    unittest.main()
