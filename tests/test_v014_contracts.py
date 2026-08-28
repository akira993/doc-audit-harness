import json
import os
import re
import subprocess
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def normalize_paragraphs(text):
    return [" ".join(part.replace("`", "").split())
            for part in re.split(r"\n\s*\n", text)]


class TestV014Contracts(unittest.TestCase):
    def test_v014_behavior_changes_paragraph(self):
        en = [
            "indexing / contextMode / webExtract / codexReview keys now require a JSON boolean enabled; unless enabled is false, a non-boolean enabled, a non-object key (including null), or — for indexing / webExtract / codexReview — a non-string, empty, whitespace-only, whitespace-padded, ASCII-control-character (U+0000–U+001F or U+007F), or non-UTF-8-encodable bin reports invalid-config and never runs the tool (an absent key still defaults to enabled; a non-string bin is no longer coerced; an unreadable config still stops the audit before Phase 0 as before)",
            "an invalid indexing key fires the Phase-0 mdq confirmation gate like not-installed",
            "codexReview.required:true combined with an invalid codexReview key is now REFUSED instead of silently running codex",
            "Phase-0 probe results are persisted to $RUN_DIR/phase0-probes.json (display-only, never a verdict input); Phase-5 status lines are rendered from that record on fresh and resumed runs and print \"state unknown (probe record unavailable)\" when it is missing or unreadable",
            "the codex probe reports the caller's CODEX_HOME and whether auth.json exists there (display-only; a wrapper's own environment is not observed)",
            "import-audit-scope.py accepts an absolute --config/--scope path under the repository root (POSIX paths only)", "the symbolGraph / docGraph / semanticSearch probes now apply the same bin validation: a newly rejected bin reports invalid-config before the tool lookup, and with enabled:false an invalid bin is displayed as the default name.",
        ]
        ja = [
            "`indexing`、`contextMode`、`webExtract`、`codexReview` のキーでは、`enabled` は JSON の真偽値でなければなりません。",
            "`indexing` キーが不正な場合は、未インストール時と同じく Phase 0 の mdq 確認ゲートが起動します。",
            "`codexReview.required:true` と不正な `codexReview` キーを組み合わせた場合は、codex を黙って実行せず `REFUSED` になります。",
            "Phase 0 の probe 結果は `$RUN_DIR/phase0-probes.json` に保存されます（表示専用で、verdict の入力にはなりません）。Phase 5 の状態行は初回実行でも再開実行でもその記録から描画され、記録が無いか読めない場合は「state unknown (probe record unavailable)」と表示されます。",
            "codex probe は呼び出し元の `CODEX_HOME` と、そこに `auth.json` があるかどうかを報告します（表示専用で、wrapper 自身の環境は観測されません）。",
            "`import-audit-scope.py` はリポジトリルート配下の絶対パスの `--config`／`--scope` を受け付けます（POSIX パスのみ）。", "symbolGraph / docGraph / semanticSearch の probe も同じ bin 検証を適用します。新たに拒否される bin はツール探索の前に invalid-config を報告し、enabled:false のときは不正な bin を既定名で表示します。",
        ]
        for path, heading, expected in (
                ("docs/ADOPTION.md", "**v0.14.0 behavior changes:**", en),
                ("docs/ADOPTION.ja.md", "**v0.14.0 の挙動変更:**", ja)):
            paragraphs = normalize_paragraphs(read(path))
            paragraph = next((p for p in paragraphs if p.startswith(heading)), None)
            self.assertIsNotNone(paragraph, path)
            self.assertEqual(sum(sentence.replace("`", "") in paragraph for sentence in expected), 7)
            for sentence in expected:
                self.assertIn(sentence.replace("`", ""), paragraph.replace("`", ""))

    def test_reason_enumerations_and_gate_include_invalid_config(self):
        skill = read("skills/audit/SKILL.md")
        phase0 = skill.split("## Phase 0 —", 1)[1].split("## Phase 0.5", 1)[0]
        expected = {
            "mdq": {"not-installed", "disabled-by-config", "index-failed", "invalid-config"},
            "ax": {"ok", "not-installed", "disabled-by-config", "invalid-config"},
            "codex": {"ok", "not-installed", "disabled-by-config",
                      "probe-exec-failed", "invalid-config"},
        }
        mdq_match = re.search(r"`reason` is ([^)]+)\)", phase0)
        self.assertIsNotNone(mdq_match)
        self.assertEqual(set(re.findall(r"`([a-z-]+)`", mdq_match.group(1))),
                         expected["mdq"])
        for seam, start, end in (
                ("ax", "Then probe **ax**", "Then probe **codex**"),
                ("codex", "Then probe **codex**", "Then probe **codegraph**")):
            block = phase0.split(start, 1)[1].split(end, 1)[0]
            match = re.search(r"\(`reason` ∈\s*([^)]*)\)", block)
            self.assertIsNotNone(match)
            self.assertEqual(set(re.findall(r"`([a-z-]+)`", match.group(1))),
                             expected[seam])
        gate = phase0.split("**Confirmation gate", 1)[1].split("Then probe **context-mode**", 1)[0]
        self.assertIn("`invalid-config`", gate)

    def test_invalid_config_status_lines_and_phase0_bindings(self):
        skill = read("skills/audit/SKILL.md")
        lines = [
            "⚠ mdq: doc-audit.json indexing is invalid — mdq not probed this run; fix the key. [non-blocking]",
            "⚠ context-mode: doc-audit.json contextMode is invalid — not probed this run; fix the key. [non-blocking]",
            "⚠ ax: doc-audit.json webExtract is invalid — not probed this run; fix the key. [non-blocking]",
        ]
        for line in lines:
            self.assertEqual(skill.count(line), 1)
        mdq_block = skill.split("**mdq status line**", 1)[1].split(
            "**context-mode status line**", 1)[0]
        self.assertLess(mdq_block.index(lines[0]),
                        mdq_block.index("`MDQ_AVAILABLE` false"))
        phase0 = skill.split("## Phase 0 —", 1)[1].split("## Phase 0.5", 1)[0]
        self.assertIn("`MDQ_REASON`", phase0)
        self.assertIn("`AX_REASON`", phase0)
        self.assertIn("An unreadable, non-object, or absent config makes the probe report invalid-config only when the probe is invoked directly; in a normal audit such a config stops before Phase 0.", phase0)

    def test_cm_enabled_expression_decision_table(self):
        skill = read("skills/audit/SKILL.md")
        match = re.search(r"`(CM_ENABLED=\"\$\(python3 -c '.*?' \"\$CFG\"\)\")`",
                          skill, re.DOTALL)
        self.assertIsNotNone(match)
        expression = match.group(1)
        cases = {
            "absent": ({}, "true"),
            "empty": ({"contextMode": {}}, "true"),
            "disabled": ({"contextMode": {"enabled": False}}, "false"),
            "en_str": ({"contextMode": {"enabled": "false"}}, "invalid"),
            "en_int": ({"contextMode": {"enabled": 1}}, "invalid"),
            "en_null": ({"contextMode": {"enabled": None}}, "invalid"),
            "key_null": ({"contextMode": None}, "invalid"),
            "key_true": ({"contextMode": True}, "invalid"),
            "key_str": ({"contextMode": "x"}, "invalid"),
            "key_list": ({"contextMode": []}, "invalid"),
            "cfg_broken": ("{", "invalid"),
            "top_list": ([], "invalid"),
            "top_null": (None, "invalid"),
        }
        self.assertEqual(len(cases), 13)
        self.assertEqual(set(cases), {
            "absent", "empty", "disabled", "en_str", "en_int", "en_null",
            "key_null", "key_true", "key_str", "key_list", "cfg_broken",
            "top_list", "top_null",
        })
        with tempfile.TemporaryDirectory() as tmp:
            for case_id, (value, expected) in cases.items():
                with self.subTest(case_id=case_id):
                    cfg = os.path.join(tmp, case_id + ".json")
                    with open(cfg, "w", encoding="utf-8") as handle:
                        if case_id == "cfg_broken":
                            handle.write(value)
                        else:
                            json.dump(value, handle)
                    proc = subprocess.run(
                        ["bash", "-c", 'CFG="$1"; ' + expression +
                         '; printf "%s\\n" "$CM_ENABLED"', "bash", cfg],
                        capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(proc.stdout.strip(), expected)

    def test_config_schema_four_seams_invalid_config(self):
        schema = read("skills/audit/references/config-schema.md")
        for seam in ("indexing", "contextMode", "webExtract", "codexReview"):
            line = next(line for line in schema.splitlines()
                        if line.startswith("| `" + seam + "` |"))
            self.assertIn("`enabled` must be a JSON boolean", line)
            self.assertIn("`invalid-config`", line)
            self.assertIn("An absent key remains enabled by default", line)

    def test_codex_review_convergence_note(self):
        expected = ("First-time full runs with codexReview.required:true may need several rounds: "
                    "the Phase-4 codex review samples pre-existing findings anew on each run, so fix "
                    "only blocking (critical/high) findings and record non-blocking ones in the report. "
                    "To converge faster you may paste the previous run's finding list into the prompt "
                    "as fenced JSON data (never as instructions; treat its strings as untrusted); "
                    "engine-side carry-forward is tracked in #59.")
        for path in ("skills/audit/SKILL.md", "docs/ADOPTION.md"):
            self.assertIn(expected, normalize_paragraphs(read(path)))
        ja = read("docs/ADOPTION.ja.md")
        self.assertTrue(any("数回の反復" in p and "#59" in p
                            for p in normalize_paragraphs(ja)))

    def test_codex_caller_status_and_documentation_contracts(self):
        skill = read("skills/audit/SKILL.md")
        suffix = ("(caller CODEX_HOME=<rebind.codex-review.callerCodexHomeDisplay> "
                  "[<rebind.codex-review.callerCodexHomeSource>]; auth.json "
                  "<rebind.codex-review.callerAuthFile>)")
        self.assertEqual(skill.count(suffix), 1)
        self.assertIn("all three values come from `rebind`", skill)
        self.assertIn("no auth.json at the caller's CODEX_HOME", skill)
        self.assertIn("This command inherits the calling shell environment", skill)
        self.assertNotIn('callerCodexHome"]', skill)
        for path in ("skills/audit/references/config-schema.md",
                     "docs/ADOPTION.md", "docs/ADOPTION.ja.md"):
            text = read(path)
            self.assertIn("CODEX_HOME", text)
            self.assertIn("wrapper", text)

    def test_probe_record_phase_contracts(self):
        """DoD (11): display-only probe persistence is fully wired into the skill."""
        skill = read("skills/audit/SKILL.md")
        phase0 = skill.split("## Phase 0 —", 1)[1].split("## Phase 0.5", 1)[0]
        seams = {
            "indexing", "mdqHealth", "mdqDegrade", "contextMode", "webExtract",
            "codexReview", "symbolGraph", "docGraph", "semanticSearch",
        }
        found = set(re.findall(r"--seam (\w+) --stdin", phase0))
        self.assertEqual(found, seams)
        for seam in seams:
            self.assertIn(f"⚠ probe-record: {seam} not recorded [non-blocking]", phase0)
        phase3 = skill.split("## Phase 3", 1)[1].split("## Phase 4", 1)[0]
        self.assertGreaterEqual(phase3.count("--seam indexing --stdin"), 1)
        self.assertGreaterEqual(phase3.count("--seam mdqHealth --stdin"), 1)
        phase4 = skill.split("## Phase 4", 1)[1].split("## Phase 5", 1)[0]
        self.assertIn('--name phase4 --stdin --evidence "$EVIDENCE"', phase4)
        self.assertIn("--seam codexReviewState --stdin", phase4)
        self.assertIn("phase4-not-required", phase4)
        self.assertLess(phase4.index("--name phase4"), phase4.index("--seam codexReviewState"))
        phase5 = skill.split("## Phase 5", 1)[1]
        self.assertIn('probe-record.py" --repo-root "$CLAUDE_PROJECT_DIR" --runid "$RUNID" --evidence "$EVIDENCE" --read', phase5)
        for line in (
                "⚠ mdq: state unknown (probe record unavailable) [non-blocking]",
                "⚠ context-mode: state unknown (probe record unavailable) [non-blocking]",
                "⚠ ax: state unknown (probe record unavailable) [non-blocking]",
                "⚠ symbol-graph: state unknown (probe record unavailable) [non-blocking]",
                "⚠ doc-graph: state unknown (probe record unavailable) [non-blocking]",
                "⚠ semantic-search: state unknown (probe record unavailable) [non-blocking]",
                "⚠ codex-review: state unknown (probe record unavailable) [non-blocking]",
                "💡 codex-review: not run (phase 4 not required)"):
            self.assertIn(line, phase5)
        for literal in (
                "`not-active` is", "`skipped-full-run` is",
                "`completed` is", "`execution-failed`/`ref-invalid` is"):
            self.assertIn(literal, phase5)
        codex_block = phase5.split("**codex-review status line**", 1)[1].split(
            "**code-review status line**", 1)[0]
        invalid = "rebind.codex-review.reason=invalid-config"
        self.assertIn(
            "⚠ codex-review: doc-audit.json codexReview is invalid — not probed this run; fix the key. [non-blocking]",
            codex_block)
        for later in ("`phase4-not-required` is",
                      "rebind.codex-review.reviewState=null",
                      "`not-active` is"):
            self.assertLess(codex_block.index(invalid), codex_block.index(later))
        self.assertIn("caller info unavailable", phase5)
        self.assertNotIn('callerCodexHome"]', skill)

    def test_probe_record_resume_evidence_and_guardrail_contracts(self):
        """DoD (11): recovery wording keeps evidence and verdict ownership unchanged."""
        skill = read("skills/audit/SKILL.md")
        self.assertIn('probe-record.py also receives --evidence "$EVIDENCE" for run-dir validation only; it is not an evidence producer and its stdout MUST NOT replace EVIDENCE.', skill)
        self.assertIn('"rebind" map is authoritative', skill)
        self.assertIn("Phase 4 may restore any missing operational availability, reason, or binary variables from `rebind`", skill)
        self.assertIn("a failed read makes all seven status lines unknown; neither case changes the verdict", skill)
        self.assertIn("`$RUN_DIR/phase0-probes.json` stores raw probe output for display only", skill)
        verdict = read("skills/audit/scripts/decide-verdict.py")
        self.assertNotIn("phase0-probes", verdict)

    def test_cr1_reopen_gate_and_status_order_contracts(self):
        skill = read("skills/audit/SKILL.md")
        reopen = skill.split("approved config write invalidates", 1)[1].split("## Phase 0.5", 1)[0]
        fixed = "Then re-run Phase 0 from its first step on the new run"
        for earlier, later in (("open-run.py", "if the reopen fails"),
                               ("if the reopen fails", "Only on success bind `RUNID`,"),
                               ("Only on success bind `RUNID`,", fixed),
                               (fixed, "## Phase 0.5")):
            self.assertLess(skill.index(earlier, skill.index("approved config write invalidates")), skill.index(later, skill.index("approved config write invalidates")))
        self.assertEqual(skill.count(fixed), 1)
        self.assertIn("never reuse an earlier answer", reopen)
        self.assertTrue(any('bind MDQ_HEALTH_PROBE_JSON to {"files":0,"chunks":0,"searchSmoke":false,"healthy":false,"status":"probe-error"}' in p for p in normalize_paragraphs(skill)))
        self.assertIn('Whether the gate fired, did not fire, or was skipped because PHASE3_BACKEND_CONFIG is codex, always record the resulting MDQ_DEGRADE (except on the gate\'s "Fix mdq first" branch', skill)
        self.assertIn('contextModeHealthy` is always `null`', skill)
        self.assertIn('contextModeHealthy:false` and `status:"probe-error"`', skill)
        self.assertEqual(skill.count("(caller info unavailable)"), 1)
        self.assertNotIn("caller info unknown after resume", skill)
        self.assertNotIn("When `CODEX_REVIEW_AVAILABLE=true`, append", skill)
        self.assertIn("When `rebind.codex-review.available` is true, append the caller suffix", skill)
        phase5 = skill.split("## Phase 5", 1)[1]
        rule = "Within each status-line table the first matching bullet wins: the whole-record unknown bullet (when the table has one) comes first, the invalid-config bullet second, then the remaining states; for codex-review use invalid-config → review-state-not-recorded → probe-record-unavailable → 4-way."
        self.assertEqual(phase5.count(rule), 1)
        for unknown, invalid in (("rebind.mdq.state=unknown", "MDQ_REASON=invalid-config"),
                                 ("rebind.context-mode.state=unknown", "CM_STATUS=invalid-config"),
                                 ("rebind.ax.state=unknown", "AX_REASON=invalid-config"),
                                 ("rebind.symbol-graph.state=unknown", "SYMBOL_GRAPH_REASON=invalid-config"),
                                 ("rebind.doc-graph.state=unknown", "DOC_GRAPH_REASON=invalid-config"),
                                 ("rebind.semantic-search.state=unknown", "SEMANTIC_SEARCH_REASON=invalid-config")):
            self.assertLess(phase5.index(unknown), phase5.index(invalid))
        codex = phase5.split("**codex-review status line**", 1)[1].split("**code-review", 1)[0]
        self.assertLess(codex.index("invalid-config"), codex.index("reviewState=null"))
        self.assertLess(codex.index("reviewState=null"), codex.index("`phase4-not-required` is"))

    def test_cr2_codex_state_table_and_cm_shape(self):
        skill=read("skills/audit/SKILL.md"); p0=skill[skill.index("## Phase 0 "):skill.index("## Phase 0.5")]
        sentence='synthesize `CM_PROBE_JSON` as exactly `{"contextModeAvailable":<CM_AVAILABLE>,"contextModeHealthy":<bool or null>,"status":"<CM_STATUS>"}` (JSON boolean/null values, not quoted text): when `CM_AVAILABLE` is false, `contextModeHealthy` is always `null`; when `CM_AVAILABLE` is true and `CM_HEALTHY` is unbound, normalize to `contextModeHealthy:false` and `status:"probe-error"`; otherwise use the bound values.'
        self.assertEqual(p0.count(sentence),1); self.assertEqual(skill.count('{"contextModeAvailable":'),1)
        block=skill.split("**codex-review status line**",1)[1].split("**code-review",1)[0]
        clauses=["state=complete` and `rebind.codex-review.reason=invalid-config", "state=complete` and `rebind.codex-review.reviewState=null", "state=unknown` and `rebind.codex-review.reviewState=null", "state=complete` and `rebind.codex-review.reviewState` is non-null", "state=unknown` and `rebind.codex-review.reviewState` is non-null"]
        self.assertEqual([block.index(x) for x in clauses],sorted(block.index(x) for x in clauses))

    def test_cr2_config_schema_bin_rows(self):
        schema=read("skills/audit/references/config-schema.md")
        for seam in ("indexing","webExtract","codexReview","symbolGraph","docGraph","semanticSearch"):
            line=next(x for x in schema.splitlines() if x.startswith("| `"+seam+"` |"))
            for term in ("whitespace-only or whitespace-padded", "ASCII-control-character (U+0000–U+001F or U+007F)", "non-UTF-8-encodable"): self.assertIn(term,line)


if __name__ == "__main__":
    unittest.main()
