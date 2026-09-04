"""Deterministic complete-ledger fixtures for the Issue #70 static baseline."""

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

from tests.wp12_helpers import RunFixture, write

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "audit" / "scripts"))
import claim_record


ROOT = Path(__file__).resolve().parents[1]
DECIDE = ROOT / "skills" / "audit" / "scripts" / "decide-verdict.py"
REPORT = {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
KINDS = ("incremental", "incremental-preflight", "full", "codex-zero")


def frozen_environment(owner):
    hook = tempfile.TemporaryDirectory()
    owner.addCleanup(hook.cleanup)
    source = textwrap.dedent("""
        import datetime
        class _FixedDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                value = cls(2026, 8, 18, 12, 0, 0, tzinfo=datetime.timezone.utc)
                return value if tz is not None else value.replace(tzinfo=None)
        datetime.datetime = _FixedDateTime
    """)
    write(os.path.join(hook.name, "sitecustomize.py"), source)
    return dict(os.environ, PYTHONPATH=hook.name)


def prepare_fixture(owner, kind, env=None):
    if kind == "incremental-preflight":
        config = dict(REPORT, harness={"state": "integrated"})
    elif kind == "codex-zero":
        config = dict(REPORT, codexReview={"required": True})
    else:
        config = REPORT
    fx = RunFixture(owner, config_extra=config)
    assert fx.open().returncode == 0
    if kind == "incremental-preflight":
        assert fx.plan_start_seal(impacted=[]).returncode == 0
        preflight = {"state": "integrated", "findings": [], "userDecision": None,
                     "parsed": True}
        assert fx.write_evidence("preflight", preflight).returncode == 0
        assert fx.complete(verdicts={}, returns_override=[], phase4=[]).returncode == 0
    elif kind == "full":
        assert fx.plan_start_seal(mode="full").returncode == 0
        assert fx.complete().returncode == 0
    elif kind == "codex-zero":
        assert fx.plan_start_seal(mode="full").returncode == 0
        prior_finding = {"source": "codex-review", "severity": "HIGH",
                         "title": "Prior claim", "file": "docs/a.md"}
        prior = {"findings": [prior_finding], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none"}}
        assert fx.complete(phase4=prior).returncode == 0
        target = claim_record.extract_claim_targets(prior)[0][0]
        claim_args = [
            "--run-dir", fx.run_dir,
            "--out", os.path.join(fx.run_dir, "claims", target["findingId"] + ".json"),
            "--runid", fx.runid, "--repo-root", fx.repo,
            "--finding-id", target["findingId"],
            "--state", "refuted", "--evidence-file", "docs/a.md", "--evidence-line", "1",
        ]
        assert fx.call("write-claim.py", *claim_args, input_text="false positive").returncode == 0
        assert fx.write_template(
            body=fx.report_template() + "codexClaims: {{GATE_CODEX_CLAIMS}}\n").returncode == 0
        first = run_gate(fx, env or os.environ)
        assert first.returncode == 0
        first_report = json.loads(first.stdout).get("reportPath")
        if first_report:
            os.unlink(os.path.join(fx.repo, first_report))
        assert fx.open(runid="20260818T120001Z-abcdef13").returncode == 0
        assert fx.plan_start_seal(mode="full").returncode == 0
        completed = {"findings": [], "codexReview": {
            "state": "completed", "promptVariant": "full", "carryForwardSha": "none"}}
        assert fx.complete(phase4=completed).returncode == 0
    else:
        assert fx.plan_start_seal().returncode == 0
        assert fx.complete().returncode == 0
    assert fx.write_template().returncode == 0
    return fx


def run_gate(fx, env):
    return subprocess.run(
        [sys.executable, str(DECIDE), "--run-dir", fx.run_dir,
         "--repo-root", fx.repo, "--config", fx.config_path,
         "--anchor-path", fx.anchor_rel, "--runid", fx.runid,
         "--expect-json", json.dumps(fx.evidence), "--date", "2026-08-18"],
        capture_output=True, text=True, env=env,
    )


def snapshot(fx, proc):
    result = json.loads(proc.stdout)

    def read_text(path):
        return Path(path).read_text(encoding="utf-8") if os.path.exists(path) else None

    report = None
    if result.get("reportPath"):
        report = read_text(os.path.join(fx.repo, result["reportPath"]))
    artifacts = {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "history": read_text(fx.history),
        "lastRun": read_text(fx.last_run),
        "anchor": read_text(fx.anchor),
        "report": report,
    }
    return {
        "exitCode": proc.returncode,
        "verdict": result["verdict"],
        "artifactSha256": {
            name: (hashlib.sha256(value.encode("utf-8")).hexdigest()
                   if value is not None else None)
            for name, value in artifacts.items()
        },
    }


def collect_current(owner):
    env = frozen_environment(owner)
    return {kind: snapshot(fx, run_gate(fx, env))
            for kind in KINDS for fx in (prepare_fixture(owner, kind, env),)}
