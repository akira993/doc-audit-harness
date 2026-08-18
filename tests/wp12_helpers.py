import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "audit", "scripts")


def script(name):
    return os.path.join(SCRIPTS, name)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    kwargs = {} if mode == "wb" else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as handle:
        handle.write(content)


class RunFixture:
    def __init__(self, test, docs=("docs/a.md", "docs/b.md"), config_extra=None):
        self.tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.test")
        git(self.repo, "config", "user.name", "Test")
        self.config = {"docGlobs": ["docs/**/*.md", "*.md"], "diffGlobs": ["**"],
                       "maxImpactedDocs": 200,
                       "verdictCache": {"enabled": True, "minConsecutivePasses": 2}}
        if config_extra:
            self.config.update(config_extra)
        self.config_path = os.path.join(self.repo, ".claude", "doc-audit.json")
        write(self.config_path, json.dumps(self.config, indent=2) + "\n")
        self.docs = list(docs)
        for path in docs:
            write(os.path.join(self.repo, path), "# " + path + "\n")
        write(os.path.join(self.repo, "src", "app.py"), "print('x')\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "initial")
        self.head = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.runid = "20260818T120000Z-abcdef12"
        self.run_base = os.path.join(self.repo, ".claude", "state", "docaudit-run")
        self.anchor_rel = ".claude/state/last-doc-audit.json"
        self.anchor = os.path.join(self.repo, self.anchor_rel)
        self.history = os.path.join(self.repo, ".claude", "state", "docaudit-history.json")
        self.last_run = os.path.join(self.repo, ".claude", "state", "docaudit-last-run.json")
        self.evidence = None
        self.run_dir = None

    def call(self, name, *args, input_text=None):
        return subprocess.run([sys.executable, script(name), *map(str, args)], input=input_text,
                              capture_output=True, text=True)

    def open(self, runid=None, accept=False):
        self.runid = runid or self.runid
        args = ["--run-base", self.run_base, "--repo-root", self.repo,
                "--anchor-path", self.anchor_rel, "--runid", self.runid]
        if accept:
            args.append("--accept-config")
        proc = self.call("open-run.py", *args)
        if proc.returncode == 0:
            self.evidence = json.loads(proc.stdout)
            self.run_dir = self.evidence["runDir"]
        return proc

    def plan_start_seal(self, impacted=None, mode="incremental", contract="0.10.0"):
        impacted = self.docs if impacted is None else impacted
        impact = {"impacted": [{"path": path, "provenance": "full" if mode == "full" else "mapped"}
                               for path in impacted], "ssotRecheck": [], "warnings": []}
        impact_path = os.path.join(self.run_dir, "impact.json")
        write(impact_path, json.dumps(impact) + "\n")
        baseline = self.head
        proc = self.call("plan-dispatch.py", "--run-dir", self.run_dir, "--runid", self.runid,
                         "--repo-root", self.repo, "--config", self.config_path,
                         "--history", self.history, "--impact-json", impact_path,
                         "--baseline-sha", baseline, "--mode", mode,
                         "--contract-version", contract, "--evidence", json.dumps(self.evidence))
        if proc.returncode != 0:
            return proc
        self.evidence = json.loads(proc.stdout)
        proc = self.call("start-run.py", "--run-dir", self.run_dir, "--runid", self.runid,
                         "--repo-root", self.repo, "--impact-json", impact_path,
                         "--dispatch-json", os.path.join(self.run_dir, "dispatch.json"),
                         "--run-class", "standard", "--mode", mode, "--config", self.config_path,
                         "--evidence", json.dumps(self.evidence))
        if proc.returncode != 0:
            return proc
        self.evidence = json.loads(proc.stdout)
        proc = self.call("seal-run.py", "--run-dir", self.run_dir, "--repo-root", self.repo,
                         "--evidence", json.dumps(self.evidence))
        if proc.returncode == 0:
            self.evidence = json.loads(proc.stdout)
        return proc

    def write_verdict(self, path, verdict="PASS"):
        out = os.path.join(self.run_dir, "verdicts", path.replace("/", "__") + ".json")
        return self.call("write-verdict.py", "--run-dir", self.run_dir, "--out", out,
                         "--runid", self.runid, "--path", path, "--verdict", verdict,
                         input_text="checked\n")

    def write_evidence(self, name, value):
        proc = self.call("write-evidence.py", "--run-dir", self.run_dir, "--name", name,
                         "--stdin", "--evidence", json.dumps(self.evidence),
                         input_text=json.dumps(value))
        if proc.returncode == 0:
            self.evidence = json.loads(proc.stdout)
        return proc

    def complete(self, verdicts=None, returns_override=None, phase4=None):
        if verdicts is None:
            verdicts = {path: "PASS" for path in self.docs}
        for path, verdict in verdicts.items():
            proc = self.write_verdict(path, verdict)
            if proc.returncode:
                return proc
        returns = returns_override
        if returns is None:
            returns = [{"attempt": 1, "assignedPath": path, "returnedPath": path,
                        "verdict": verdict, "rationale": "checked", "suggestion": None}
                       for path, verdict in verdicts.items()]
        proc = self.write_evidence("returns", returns)
        if proc.returncode:
            return proc
        with open(os.path.join(self.run_dir, "manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest["phase4Required"]:
            proc = self.write_evidence("phase4", {"findings": phase4 or []})
            if proc.returncode:
                return proc
        return proc

    def gate(self):
        return self.call("decide-verdict.py", "--run-dir", self.run_dir,
                         "--repo-root", self.repo, "--config", self.config_path,
                         "--anchor-path", self.anchor_rel, "--runid", self.runid,
                         "--expect-json", json.dumps(self.evidence), "--date", "2026-08-18")
