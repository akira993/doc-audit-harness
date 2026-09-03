"""Contracts and end-to-end checks for v0.19 codex claim adjudication."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.wp12_helpers import RunFixture, write
from tests.issue70_baseline_helpers import collect_current


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "audit" / "scripts"
WORKFLOW = ROOT / "skills" / "audit" / "references" / "claim-adjudication-workflow.js"
AGENT = ROOT / "agents" / "doc-claim-adjudicator.md"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claim_record


def load_script(name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DECIDE = load_script("decide-verdict.py", "decide_claim_tests")


def phase(findings, state="completed"):
    return {
        "findings": findings,
        "codexReview": {
            "state": state,
            "promptVariant": "diff" if state in {"completed", "execution-failed"} else None,
            "carryForwardSha": "none",
        },
    }


def finding(title="Claim A", severity="HIGH", file="docs/a.md", source="codex-review"):
    return {"source": source, "severity": severity, "title": title, "file": file}


class ClaimWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        self.run_dir = os.path.join(self.repo, ".claude", "state", "docaudit-run", "run-1")
        os.makedirs(self.run_dir)
        write(os.path.join(self.repo, "docs", "a.md"), "# A\nline two\n")
        write(os.path.join(self.repo, "docs", "b.md"), "# B\n")

    def target(self, value=None):
        return claim_record.extract_claim_targets(phase([value or finding()]))[0][0]

    def put_record(self, target, state, *, runid="run-1", evidence=True,
                   reason_marker=False, directory=None):
        record = {"runid": runid, "findingId": target["findingId"],
                  "state": state, "rationale": "checked"}
        if state in {"confirmed", "refuted"} and evidence:
            record.update({"evidenceFile": "docs/a.md", "evidenceLine": 1})
        if state == "not-adjudicable" or reason_marker:
            record["reason"] = "path-unresolved"
        claims = directory or os.path.join(self.run_dir, "claims")
        os.makedirs(claims, exist_ok=True)
        write(os.path.join(claims, target["findingId"] + ".json"),
              claim_record.encode_claim_record(record))
        return record

    def adjudicate(self, phase_value, state="completed", run_dir=None):
        warnings = []
        items, count = DECIDE.adjudicate_codex_claims(
            self.repo, run_dir or self.run_dir, "run-1", phase_value, state, warnings)
        return items, count, warnings


class TestP1ThroughP7(ClaimWorkspace):
    def test_p1_state_finding_consistency_both_branches(self):
        with self.assertRaises(DECIDE.Refused):
            self.adjudicate(phase([finding()], "execution-failed"), "execution-failed")
        items, count, _warnings = self.adjudicate(phase([finding()]), "completed")
        self.assertEqual(count, 1)
        self.assertEqual(items[0]["effectiveState"], "unverified")

    def test_p2_missing_or_invalid_record_and_valid_record(self):
        value = phase([finding()])
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "unverified")
        self.assertIn("codexClaimsUnadjudicated", warnings)
        target = self.target()
        self.put_record(target, "refuted")
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "refuted")
        self.assertNotIn("codexClaimsUnadjudicated", warnings)

    def test_p3_not_adjudicable_is_rederived_both_branches(self):
        value = phase([finding()])
        target = self.target()
        self.put_record(target, "not-adjudicable")
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "unverified")
        self.assertIn("claimNotAdjudicableRejected", warnings)

        unresolved = finding(file="docs/missing.md")
        unresolved_phase = phase([unresolved])
        unresolved_target = self.target(unresolved)
        shutil.rmtree(os.path.join(self.run_dir, "claims"))
        self.put_record(unresolved_target, "not-adjudicable")
        items, _count, warnings = self.adjudicate(unresolved_phase)
        self.assertEqual(items[0]["effectiveState"], "not-adjudicable")
        self.assertNotIn("claimNotAdjudicableRejected", warnings)

    def test_p4_evidence_resolution_both_branches(self):
        value = phase([finding()])
        target = self.target()
        record = self.put_record(target, "confirmed", evidence=False)
        record.update({"evidenceFile": "docs/a.md", "evidenceLine": 99})
        write(os.path.join(self.run_dir, "claims", target["findingId"] + ".json"),
              json.dumps(record))
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "unverified")
        self.assertIn("claimEvidenceUnresolved", warnings)
        self.put_record(target, "confirmed")
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "confirmed")
        self.assertNotIn("claimEvidenceUnresolved", warnings)

    def test_p5_only_confirmed_blocks_both_branches(self):
        self.assertTrue(DECIDE.codex_claims_block([{"effectiveState": "confirmed"}]))
        for state in ("refuted", "unverified", "not-adjudicable"):
            self.assertFalse(DECIDE.codex_claims_block([{"effectiveState": state}]))

    def test_p6_medium_low_are_not_targets_but_high_is(self):
        items, count, _warnings = self.adjudicate(
            phase([finding(severity="MEDIUM"), finding("low", severity="LOW")]))
        self.assertEqual((items, count), ([], 0))
        items, count, _warnings = self.adjudicate(phase([finding(severity=" high ")]))
        self.assertEqual(count, 1)
        self.assertEqual(items[0]["severity"], "HIGH")

    def test_p7_unexpected_record_warns_and_clean_directory_does_not(self):
        target = self.target()
        self.put_record(target, "refuted")
        value = phase([finding()])
        _items, _count, warnings = self.adjudicate(value)
        self.assertNotIn("claimRecordUnexpected", warnings)
        write(os.path.join(self.run_dir, "claims", "stale.json"), "{}")
        _items, _count, warnings = self.adjudicate(value)
        self.assertIn("claimRecordUnexpected", warnings)

    def test_target_extraction_normalizes_identically_and_deduplicates(self):
        value = phase([finding(severity=" high "), finding(severity="HIGH")])
        targets, missing = claim_record.extract_claim_targets(value)
        self.assertEqual((len(targets), missing), (1, 0))
        items, count, _warnings = self.adjudicate(value)
        self.assertEqual(count, 1)
        self.assertEqual(items[0]["findingId"], targets[0]["findingId"])
        source = (ROOT / "skills/audit/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("severity.strip().upper()", source)

    def test_zero_targets_never_touch_any_new_run_path(self):
        accesses = []
        originals = {
            "open": DECIDE.os.open, "read": DECIDE.os.read, "stat": DECIDE.os.stat,
            "listdir": DECIDE.os.listdir, "isdir": DECIDE.os.path.isdir,
        }

        def wrap(name):
            def tracked(first, *args, **kwargs):
                if name not in {"read"}:
                    try:
                        if "claims" in os.fspath(first):
                            accesses.append((name, os.fspath(first)))
                    except TypeError:
                        pass
                return originals[name](first, *args, **kwargs)
            return tracked

        with mock.patch.object(DECIDE.os, "open", wrap("open")), \
             mock.patch.object(DECIDE.os, "read", wrap("read")), \
             mock.patch.object(DECIDE.os, "stat", wrap("stat")), \
             mock.patch.object(DECIDE.os, "listdir", wrap("listdir")), \
             mock.patch.object(DECIDE.os.path, "isdir", wrap("isdir")):
            items, count, warnings = self.adjudicate(
                phase([finding(severity="LOW"), finding(source="security-review")]))
        self.assertEqual((items, count, warnings, accesses), ([], 0, [], []))


class TestGateOutcomes(unittest.TestCase):
    def prepare(self, states, record_indexes=None):
        findings = [finding(f"Claim {index}", file="docs/a.md" if index % 2 == 0 else "docs/b.md")
                    for index in range(len(states))]
        fx = RunFixture(self, config_extra={"codexReview": {}})
        self.assertEqual(fx.open().returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        self.assertEqual(fx.complete(phase4=phase(findings)).returncode, 0)
        indexes = range(len(states)) if record_indexes is None else record_indexes
        for index in indexes:
            target = claim_record.extract_claim_targets(phase([findings[index]]))[0][0]
            args = ["--run-dir", fx.run_dir,
                    "--out", os.path.join(fx.run_dir, "claims", target["findingId"] + ".json"),
                    "--runid", fx.runid, "--repo-root", fx.repo,
                    "--finding-id", target["findingId"],
                    "--state", states[index]]
            if states[index] in {"confirmed", "refuted"}:
                args.extend(["--evidence-file", findings[index]["file"], "--evidence-line", "1"])
            proc = fx.call("write-claim.py", *args, input_text="checked")
            self.assertEqual(proc.returncode, 0, proc.stderr)
        return fx

    def assert_derived(self, states, record_indexes=None):
        fx = self.prepare(states, record_indexes)
        proc = fx.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        present = list(range(len(states))) if record_indexes is None else list(record_indexes)
        effective = [states[index] if index in present else "unverified"
                     for index in range(len(states))]
        expected = "NEEDS_FIX" if "confirmed" in effective else "CONSISTENT"
        self.assertEqual(result["verdict"], expected)
        return result

    def test_c3_i_empty_claims_is_consistent_with_warning(self):
        result = self.assert_derived(["refuted"], record_indexes=[])
        self.assertIn("codexClaimsUnadjudicated", result["warnings"])

    def test_c3_ii_all_confirmed_is_needs_fix(self):
        self.assert_derived(["confirmed", "confirmed"])

    def test_c3_iii_all_refuted_is_consistent(self):
        self.assert_derived(["refuted", "refuted"])

    def test_c3_iv_mixed_confirmed_refuted_is_needs_fix(self):
        self.assert_derived(["confirmed", "refuted"])

    def test_c3_v_partial_without_confirmed_is_consistent(self):
        result = self.assert_derived(["refuted", "refuted"], record_indexes=[0])
        self.assertEqual(result["counts"]["codexClaims"]["unverified"], 1)

    def test_two_run_refuted_then_confirmed_becomes_needs_fix(self):
        fx = self.prepare(["refuted"])
        first = json.loads(fx.gate().stdout)
        self.assertEqual(first["verdict"], "CONSISTENT")
        self.assertEqual(fx.open(runid="20260818T120001Z-abcdef13").returncode, 0)
        self.assertEqual(fx.plan_start_seal().returncode, 0)
        current_finding = finding("Claim 0")
        self.assertEqual(fx.complete(phase4=phase([current_finding])).returncode, 0)
        target = claim_record.extract_claim_targets(phase([current_finding]))[0][0]
        proc = fx.call(
            "write-claim.py", "--run-dir", fx.run_dir,
            "--out", os.path.join(fx.run_dir, "claims", target["findingId"] + ".json"),
            "--runid", fx.runid, "--repo-root", fx.repo,
            "--finding-id", target["findingId"],
            "--state", "confirmed", "--evidence-file", "docs/a.md",
            "--evidence-line", "1", input_text="now confirmed")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        second = json.loads(fx.gate().stdout)
        self.assertEqual(second["verdict"], "NEEDS_FIX")


class TestPlannerWriterAndContract(ClaimWorkspace):
    def run_planner(self, phase_value):
        phase_path = os.path.join(self.run_dir, "phase4.json")
        write(phase_path, json.dumps(phase_value))
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "plan-claims.py"),
             "--run-dir", self.run_dir, "--runid", "run-1",
             "--repo-root", self.repo, "--phase4-json", phase_path],
            capture_output=True, text=True)

    def test_fresh_partial_h_resume_i_resume_and_stale_record(self):
        findings = [finding("Claim A"), finding("Claim B", file="docs/b.md")]
        value = phase(findings)
        fresh = self.run_planner(value)
        self.assertEqual(len(json.loads(fresh.stdout)), 2)

        first = claim_record.extract_claim_targets(phase([findings[0]]))[0][0]
        self.put_record(first, "refuted")
        partial = json.loads(self.run_planner(value).stdout)
        self.assertEqual([item["title"] for item in partial], ["Claim B"])

        second = claim_record.extract_claim_targets(phase([findings[1]]))[0][0]
        self.put_record(second, "unverified")
        complete_before = Path(self.run_dir, "claims", first["findingId"] + ".json").read_bytes()
        self.assertEqual(json.loads(self.run_planner(value).stdout), [])
        self.assertEqual(Path(self.run_dir, "claims", first["findingId"] + ".json").read_bytes(),
                         complete_before)

        write(os.path.join(self.run_dir, "claims", "f" * 64 + ".json"), "{}")
        self.assertEqual(json.loads(self.run_planner(value).stdout), [])

        old_run = os.path.join(self.repo, ".claude", "state", "docaudit-run", "run-h")
        os.makedirs(old_run)
        old_phase = os.path.join(old_run, "phase4.json")
        write(old_phase, json.dumps(value))
        resumed = subprocess.run(
            [sys.executable, str(SCRIPTS / "plan-claims.py"), "--run-dir", old_run,
             "--runid", "run-h", "--repo-root", self.repo, "--phase4-json", old_phase],
            capture_output=True, text=True)
        self.assertEqual(len(json.loads(resumed.stdout)), 2)

    def test_record_limit_exact_and_plus_one_agree_for_planner_writer_gate(self):
        value = phase([finding()])
        target = self.target()
        base = {"runid": "run-1", "findingId": target["findingId"],
                "state": "unverified", "rationale": ""}
        base_size = len((json.dumps(base, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
        exact = dict(base, rationale="x" * (claim_record.MAX_CLAIM_RECORD_BYTES - base_size))
        exact_raw = claim_record.encode_claim_record(exact)
        self.assertEqual(len(exact_raw), claim_record.MAX_CLAIM_RECORD_BYTES)
        claims = os.path.join(self.run_dir, "claims")
        os.makedirs(claims)
        path = os.path.join(claims, target["findingId"] + ".json")
        write(path, exact_raw)
        self.assertEqual(json.loads(self.run_planner(value).stdout), [])
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "unverified")
        self.assertEqual(warnings, [])

        write(path, exact_raw + b" ")
        self.assertEqual(len(json.loads(self.run_planner(value).stdout)), 1)
        items, _count, warnings = self.adjudicate(value)
        self.assertEqual(items[0]["effectiveState"], "unverified")
        self.assertIn("codexClaimsUnadjudicated", warnings)

        writer_args = [sys.executable, str(SCRIPTS / "write-claim.py"),
                       "--run-dir", self.run_dir, "--out", path, "--runid", "run-1",
                       "--repo-root", self.repo, "--finding-id", target["findingId"],
                       "--state", "unverified"]
        ok = subprocess.run(writer_args, input=exact["rationale"], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        too_big = subprocess.run(writer_args, input=exact["rationale"] + "x",
                                 capture_output=True, text=True)
        self.assertNotEqual(too_big.returncode, 0)
        for script_name in ("plan-claims.py", "write-claim.py", "decide-verdict.py"):
            self.assertNotIn("MAX_CLAIM_RECORD_BYTES =",
                             (SCRIPTS / script_name).read_text(encoding="utf-8"))

    def test_state_reason_contract_and_three_state_agent_schema(self):
        target = self.target()
        for state in claim_record.CLAIM_STATES:
            record = {"runid": "run-1", "findingId": target["findingId"],
                      "state": state, "rationale": "checked"}
            finding_file = "docs/missing.md" if state == "not-adjudicable" else "docs/a.md"
            if state == "not-adjudicable":
                record["reason"] = "path-unresolved"
            if state in {"confirmed", "refuted"}:
                record.update({"evidenceFile": "docs/a.md", "evidenceLine": 1})
            claim_record.validate_claim_record(
                record, runid="run-1", finding_id=target["findingId"],
                repo_root=self.repo, finding_file=finding_file)
        invalid = {"runid": "run-1", "findingId": target["findingId"],
                   "state": "confirmed", "reason": "path-unresolved",
                   "rationale": "x", "evidenceFile": "docs/a.md", "evidenceLine": 1}
        with self.assertRaises(claim_record.ClaimRecordError):
            claim_record.validate_claim_record(
                invalid, runid="run-1", finding_id=target["findingId"],
                repo_root=self.repo, finding_file="docs/a.md")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("enum: ['confirmed', 'refuted', 'unverified']", workflow)
        self.assertNotIn("enum: ['confirmed', 'refuted', 'unverified', 'not-adjudicable']", workflow)
        agent_text = AGENT.read_text(encoding="utf-8")
        for state in claim_record.AGENT_CLAIM_STATES:
            self.assertIn(state, agent_text)
        writer = (SCRIPTS / "write-claim.py").read_text(encoding="utf-8")
        self.assertIn("AGENT_CLAIM_STATES", writer)
        self.assertNotIn('"not-adjudicable"', writer)
        planner = (SCRIPTS / "plan-claims.py").read_text(encoding="utf-8")
        self.assertIn("load_valid_claim_record", planner)
        self.assertIn("not-adjudicable", planner)

    def test_output_order_uses_phase4_not_directory_creation_order(self):
        findings = [finding("first"), finding("second", file="docs/b.md")]
        value = phase(findings)
        expected = None
        for reverse in (False, True):
            run_dir = os.path.join(self.repo, "run-" + str(reverse))
            claims_dir = os.path.join(run_dir, "claims")
            os.makedirs(claims_dir)
            targets = claim_record.extract_claim_targets(value)[0]
            for target in reversed(targets) if reverse else targets:
                record = {"runid": "run-1", "findingId": target["findingId"],
                          "state": "refuted", "rationale": "checked",
                          "evidenceFile": target["file"], "evidenceLine": 1}
                write(os.path.join(claims_dir, target["findingId"] + ".json"),
                      claim_record.encode_claim_record(record))
            items, _count, _warnings = self.adjudicate(value, run_dir=run_dir)
            titles = [item["title"] for item in items]
            if expected is None:
                expected = titles
            self.assertEqual(titles, expected)
        self.assertEqual(expected, ["first", "second"])

    def test_claim_payload_budget_omits_tail_below_four_mib(self):
        items = [{"findingId": f"{index:064x}", "title": "claim", "file": "docs/a.md",
                  "severity": "HIGH", "effectiveState": "unverified", "reason": None,
                  "evidenceFile": None, "evidenceLine": None,
                  "rationale": "x" * claim_record.MAX_CLAIM_RECORD_BYTES}
                 for index in range(1000)]
        template = "\n".join([
            "{{GATE_REPORT_DATE}}", "{{GATE_REPORT_DATE}}", "{{GATE_VERDICT}}",
            "{{GATE_COUNTS}}", "{{GATE_HISTORY_STATUS}}", "{{GATE_WARNINGS}}",
            "{{GATE_SIBLING_SCAN}}", "{{GATE_ANCHOR_WRITTEN}}",
            "{{GATE_CODEX_CLAIMS}}",
        ])
        payload = {}
        raw = DECIDE.render_report(
            template, "CONSISTENT", "2026-08-18", counts={}, history_status="ok",
            warnings=[], sibling={}, claim_items=items, claim_target_count=len(items),
            claim_payload_result=payload)
        self.assertLessEqual(len(raw), DECIDE.MAX_REPORT_BYTES)
        self.assertGreater(payload["omittedCount"], 0)
        self.assertEqual(payload["omittedCount"] + len(payload["items"]), 1000)


class TestInteractionMatrix(ClaimWorkspace):
    def test_source_severity_state_table(self):
        states = ("confirmed", "refuted", "unverified", "not-adjudicable", "missing")
        for source in ("codex-review", "security-review", "docAuditCommands"):
            for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                for state in states:
                    with self.subTest(source=source, severity=severity, state=state):
                        run_dir = os.path.join(self.repo, "matrix", source, severity, state)
                        os.makedirs(run_dir)
                        item = finding(source=source, severity=severity)
                        value = phase([item])
                        claim_items = []
                        if source == "codex-review" and severity in {"CRITICAL", "HIGH"}:
                            target = claim_record.extract_claim_targets(value)[0][0]
                            if state != "missing":
                                record = {"runid": "run-1", "findingId": target["findingId"],
                                          "state": state, "rationale": "checked"}
                                if state in {"confirmed", "refuted"}:
                                    record.update({"evidenceFile": "docs/a.md", "evidenceLine": 1})
                                if state == "not-adjudicable":
                                    record["reason"] = "path-unresolved"
                                claims_dir = os.path.join(run_dir, "claims")
                                os.makedirs(claims_dir)
                                write(os.path.join(claims_dir, target["findingId"] + ".json"),
                                      claim_record.encode_claim_record(record))
                            warnings = []
                            claim_items, _count = DECIDE.adjudicate_codex_claims(
                                self.repo, run_dir, "run-1", value, "completed", warnings)
                        blocked = DECIDE.findings_fail(value) or DECIDE.codex_claims_block(claim_items)
                        expected = (severity in {"CRITICAL", "HIGH"}
                                    and (source != "codex-review" or state == "confirmed"))
                        self.assertEqual(blocked, expected)

    def test_four_confirmed_positive_controls_cover_defect_classes(self):
        controls = [
            finding("This statement contradicts docs/b.md."),
            finding("The referenced docs/b.md §9 does not exist.", file="docs/b.md"),
            finding("The procedure omits a required prerequisite."),
            finding("The named option is absent from the documented command."),
        ]
        value = phase(controls)
        for target in claim_record.extract_claim_targets(value)[0]:
            record = {"runid": "run-1", "findingId": target["findingId"],
                      "state": "confirmed", "rationale": "confirmed control",
                      "evidenceFile": target["file"], "evidenceLine": 1}
            claims = os.path.join(self.run_dir, "claims")
            os.makedirs(claims, exist_ok=True)
            write(os.path.join(claims, target["findingId"] + ".json"),
                  claim_record.encode_claim_record(record))
        items, count, warnings = self.adjudicate(value)
        self.assertEqual((count, len(items), warnings), (4, 4, []))
        self.assertTrue(all(item["effectiveState"] == "confirmed" for item in items))


class TestClaimWorkflow(unittest.TestCase):
    def setUp(self):
        found = shutil.which("node")
        if not found:
            self.fail("Node.js is required for claim workflow tests")
        self.node = found
        self.source = WORKFLOW.read_text(encoding="utf-8")

    def execute(self, args_value, stringify):
        source = self.source.replace("export ", "", 1)
        program = r"""
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const source = process.env.SOURCE
const parsed = JSON.parse(process.env.ARGS)
const delivered = process.env.STRINGIFY === 'yes' ? JSON.stringify(parsed) : parsed
const execute = new AsyncFunction('args', 'phase', 'parallel', 'agent', source)
;(async () => {
  const result = await execute(delivered, () => {}, async tasks => Promise.all(tasks.map(t => t())),
    async (_prompt, opts) => ({findingId: parsed.claims[0]?.findingId, state: 'unverified', rationale: 'x'}))
  process.stdout.write(JSON.stringify(result))
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1 })
"""
        env = dict(os.environ, SOURCE=source, ARGS=json.dumps(args_value),
                   STRINGIFY="yes" if stringify else "no")
        return subprocess.run([self.node, "-e", program], capture_output=True, text=True, env=env)

    def valid_args(self):
        return {"repoRoot": "/repo", "runId": "run-1", "runDir": "/repo/run-1",
                "scriptsDir": "/plugin/scripts",
                "claims": [{"findingId": "a" * 64, "file": "docs/a.md",
                            "severity": "HIGH", "title": "claim"}]}

    def test_args_string_and_object_both_execute(self):
        for stringify in (True, False):
            proc = self.execute(self.valid_args(), stringify)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)[0]["state"], "unverified")

    def test_missing_runid_rundir_scriptsdir_each_throws(self):
        for key in ("runId", "runDir", "scriptsDir"):
            args = self.valid_args()
            del args[key]
            proc = self.execute(args, True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("runId/runDir/scriptsDir missing", proc.stderr)


class TestPublicFixtureDiscipline(unittest.TestCase):
    def test_new_data_fixture_paths_are_generic(self):
        data = ROOT / "tests" / "data" / "issue70_baseline.json"
        if not data.exists():
            self.fail("issue70_baseline.json is required")
        value = json.loads(data.read_text(encoding="utf-8"))
        paths = []
        for run in value.get("runs", []):
            paths.extend(item.get("file") for item in run.get("findings", [])
                         if isinstance(item, dict) and isinstance(item.get("file"), str))
        self.assertTrue(paths)
        self.assertTrue(all(path in {"docs/a.md", "docs/b.md"} for path in paths))

    def test_static_baseline_matches_three_non_codex_and_one_zero_target_fixture(self):
        data = ROOT / "tests" / "data" / "issue70_baseline.json"
        expected = json.loads(data.read_text(encoding="utf-8"))["snapshots"]
        self.assertEqual(collect_current(self), expected)


if __name__ == "__main__":
    unittest.main()
