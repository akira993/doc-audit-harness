import os
import re
import subprocess
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as handle:
        return handle.read()


def normalize(text):
    return " ".join(text.split())


def markdown_units(text):
    """Split Markdown at the smallest contract unit: row, list item, or paragraph."""
    units = []
    pending = []
    pending_kind = None

    def flush():
        nonlocal pending, pending_kind
        if pending:
            units.append("\n".join(pending))
        pending = []
        pending_kind = None

    table_row = re.compile(r"^\s*\|")
    list_start = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
    for line in text.splitlines():
        if not line.strip():
            flush()
        elif table_row.match(line):
            flush()
            units.append(line)
        elif list_start.match(line):
            flush()
            pending = [line]
            pending_kind = "list"
        elif pending_kind == "list":
            pending.append(line)
        else:
            pending.append(line)
            pending_kind = "paragraph"
    flush()
    return units


SEAM_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:webExtract|ax|codexReview|codex)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
OLD_WORDING_RES = (
    re.compile(r"\bconditional" + r"-force\b", re.IGNORECASE),
    re.compile(r"\bauto" + r"-used\b", re.IGNORECASE),
    re.compile("自動" + "使用"),
    re.compile(
        r"\ban absent key (?:still )?(?:remains enabled by default|defaults to enabled)\b",
        re.IGNORECASE,
    ),
    re.compile("キーが無い場合は" + "従来どおり有効"),
)
HISTORY_HEADINGS = (
    "**v0.14.0 behavior changes:**",
    "**v0.14.0 の挙動変更:**",
)


def residue_hits(path, text):
    hits = []
    for number, unit in enumerate(markdown_units(text), 1):
        if (path == "tests/test_v014_contracts.py"
                and "def test_v014_behavior_changes_paragraph" in unit):
            continue
        stripped = unit.lstrip()
        if stripped.startswith(HISTORY_HEADINGS):
            continue
        compact = normalize(unit)
        if SEAM_RE.search(compact) and any(pattern.search(compact)
                                           for pattern in OLD_WORDING_RES):
            hits.append((path, number, compact))
    return hits


class TestV015Contracts(unittest.TestCase):
    def test_config_schema_rows_are_key_gated(self):
        schema = read("skills/audit/references/config-schema.md")
        rows = {
            seam: next(line for line in schema.splitlines()
                       if line.startswith("| `" + seam + "` |"))
            for seam in ("webExtract", "codexReview")
        }
        for seam, row in rows.items():
            with self.subTest(seam=seam):
                self.assertIn("key-gated", row)
                self.assertIn("absent key", row.lower())
                self.assertIn("`not-configured`", row)
                self.assertRegex(row, r"never runs|is not run")
                self.assertNotIn("absent key remains enabled by default", row.lower())
        self.assertIn("`required:true`", rows["codexReview"])
        self.assertIn("REFUSED", rows["codexReview"])

    def test_init_omit_rules_are_key_gated(self):
        init = read("skills/init/SKILL.md")
        exact = ("OMIT the key; absent key ⇒ the audit reports `not-configured` "
                 "and never runs the tool.")
        for seam, following in (("webExtract", "codexReview"),
                                ("codexReview", "symbolGraph")):
            block = init.split("- `" + seam + "`", 1)[1].split(
                "- `" + following + "`", 1)[0]
            self.assertIn(exact, normalize(block), seam)

    def test_audit_enums_and_status_contracts_include_not_configured(self):
        skill = read("skills/audit/SKILL.md")
        phase0 = skill.split("## Phase 0 —", 1)[1].split("## Phase 0.5", 1)[0]
        expected = {
            "ax": {"ok", "not-installed", "disabled-by-config",
                   "not-configured", "invalid-config"},
            "codex": {"ok", "not-installed", "disabled-by-config",
                      "probe-exec-failed", "not-configured", "invalid-config"},
        }
        for seam, start, end in (
                ("ax", "Then probe **ax**", "Then probe **codex**"),
                ("codex", "Then probe **codex**", "Then probe **codegraph**")):
            block = phase0.split(start, 1)[1].split(end, 1)[0]
            match = re.search(r"\(`reason` ∈\s*([^)]*)\)", block)
            self.assertIsNotNone(match, seam)
            self.assertEqual(set(re.findall(r"`([a-z-]+)`", match.group(1))),
                             expected[seam])

        phase5 = skill.split("## Phase 5", 1)[1]
        ax_block = phase5.split("**ax status line**", 1)[1].split(
            "**codex-review status line**", 1)[0]
        ax_line = ("- `AX_REASON=not-configured` → `💡 ax: not configured — add "
                   "doc-audit.json webExtract to enable external URL checks [non-blocking]`")
        self.assertEqual(ax_block.count(ax_line), 1)
        codex_block = phase5.split("**codex-review status line**", 1)[1].split(
            "**code-review status line**", 1)[0]
        four_way = next(line for line in codex_block.splitlines()
                        if "`not-active` is" in line)
        self.assertIn("<rebind.codex-review.reason>", four_way)
        self.assertIn("`not-configured`", four_way)

    def test_resume_reprobes_and_records_both_key_gated_seams(self):
        skill = read("skills/audit/SKILL.md")
        resume = skill.split("**Cross-turn checkpoint rule.**", 1)[1].split(
            "## Phase 0 —", 1)[0]
        compact = normalize(resume)
        for script in ("ax-probe.sh", "codex-probe.sh"):
            with self.subTest(script=script):
                self.assertIn(script, compact)
                self.assertLess(compact.index(script), compact.index("before either consumer"))
        for instruction in (
                "bind each seam's operational availability/reason/bin from that same probe stdout",
                "re-record that same stdout through `probe-record.py`",
                "overwrites those two seam records while preserving every other seam"):
            self.assertIn(instruction, compact)
        self.assertIn("state unknown", resume)
        self.assertIn("probe-error", resume)
        self.assertNotIn(
            "Phase 4 may restore any missing operational availability, reason, or binary variables from `rebind`",
            resume,
        )

    def test_v015_behavior_change_paragraphs_are_exact(self):
        expected = {
            "docs/ADOPTION.md": (
                "**v0.15.0 behavior changes:**",
                (
                    "webExtract and codexReview are now key-gated like symbolGraph/docGraph/semanticSearch: an absent key reports not-configured and never runs the tool — ax and codex no longer run implicitly on configs without those keys (previously an absent key defaulted to enabled); a directly invoked probe with an unreadable or absent config now reports invalid-config instead of falling back to enabled, and the codex probe collects no caller CODEX_HOME/auth.json information for a keyless config (neutral values are recorded)",
                    "for a new run, or a run resumed before its codex review has run, a keyless config therefore loses the Phase-4 codex review and its verdict-affecting critical/high findings — an audit that was NEEDS FIX only because of implicit codex findings can become CONSISTENT after upgrading; add \"codexReview\": {} to keep the old best-effort behavior, or additionally \"required\": true for a separate, stronger fail-closed guarantee (a non-completed review becomes REFUSED — this is NOT the old implicit behavior)",
                    "on resume, the operational webExtract and codexReview state is re-derived by re-running their key-gated probes against the current config (probe records are overwritten accordingly); a run whose codex review already completed keeps those findings — cross-version in-flight resume is discouraged: start a fresh run (a mechanical prohibition is tracked in #59)",
                    "indexing and contextMode keep their enabled-by-default behavior (intentional: they reduce token consumption); enabled:false and invalid-config semantics are unchanged for all four seams, and bin validation is unchanged for the three bin-bearing seams (indexing/webExtract/codexReview; contextMode has no bin)",
                ),
            ),
            "docs/ADOPTION.ja.md": (
                "**v0.15.0 の挙動変更:**",
                (
                    "webExtract と codexReview は symbolGraph/docGraph/semanticSearch と同じ key-gated になった: キーが無い場合は not-configured と報告し、tool を一切起動しない — キー無し config で ax / codex が暗黙に実行されることはなくなった（従来はキー不在＝既定有効）。probe を単体で直接呼んだ場合も、読めない・存在しない config は既定有効へフォールバックせず invalid-config になる。また codex probe はキー無し config では呼び出し元の CODEX_HOME / auth.json 情報を収集しない（中立値を記録する）",
                    "したがって、新規 run および codex review 実行前に resume した run では、キー無し config は Phase-4 codex review と、その verdict に影響する critical/high 所見を失う — 暗黙の codex 所見だけが理由で NEEDS FIX だった audit は、更新後 CONSISTENT になり得る。旧来の best-effort 挙動を維持するには \"codexReview\": {} を追加する。さらに \"required\": true を付けると別種のより強い fail-closed 保証になる（未完走の review が REFUSED になる — これは旧来の暗黙挙動ではない）",
                    "resume 時、webExtract と codexReview の運用状態は key-gated な probe を現在の config に対して再実行して導出し直す（probe 記録も対応して上書きされる）。codex review が既に完走した run はその所見を保持する — 版をまたぐ resume は非推奨であり、新しい run を開始すること（機械的な禁止機構は #59 で追跡）",
                    "indexing と contextMode は従来どおり既定有効（トークン消費を減らす装置としての意図的設計）。enabled:false と invalid-config の意味論は 4 seam すべてで不変、bin 検査は bin を持つ 3 seam（indexing/webExtract/codexReview）で不変（contextMode に bin は無い）",
                ),
            ),
        }
        for path, (heading, sentences) in expected.items():
            units = [normalize(unit) for unit in markdown_units(read(path))]
            start = next(index for index, unit in enumerate(units)
                         if unit.startswith(heading))
            self.assertEqual(units[start:start + 4],
                             [heading + " " + sentences[0], *sentences[1:]], path)

    def test_minimum_unit_scanner_preserves_enabled_by_default_seams(self):
        old = "conditional" + "-force"
        fixture = (
            "| contextMode | " + old + " |\n"
            "| webExtract | " + old + " |\n\n"
            "- contextMode stays " + old + "\n"
            "  across this continuation\n"
            "- codexReview was " + old + "\n\n"
            "indexing stays " + old + ".\n\n"
            "ax was " + old + ".\n"
        )
        hits = residue_hits("fixture.md", fixture)
        self.assertEqual(len(hits), 3)
        self.assertTrue(any("webExtract" in hit[2] for hit in hits))
        self.assertTrue(any("codexReview" in hit[2] for hit in hits))
        self.assertTrue(any("ax was" in hit[2] for hit in hits))

        preserved_paths = {
            "skills/audit/references/config-schema.md",
            "skills/init/SKILL.md",
            "docs/ADOPTION.md",
            "docs/ADOPTION.ja.md",
            "README.md",
        }
        witnessed = set()
        for path in preserved_paths:
            for unit in markdown_units(read(path)):
                compact = normalize(unit)
                if (re.search(r"indexing|contextMode|context-mode|mdq", compact,
                              re.IGNORECASE)
                        and any(pattern.search(compact)
                                for pattern in OLD_WORDING_RES)):
                    witnessed.add(path)
                    self.assertEqual(residue_hits(path, unit), [], (path, compact))
        self.assertEqual(witnessed, preserved_paths)

    def test_no_nonhistorical_key_gate_residue_in_tracked_files(self):
        proc = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
        paths = [path for path in proc.stdout.splitlines()
                 if path and not path.startswith("tasks/")]
        scanned = set()
        unit_count = 0
        hits = []
        for path in paths:
            absolute = os.path.join(ROOT, path)
            if not os.path.isfile(absolute):
                continue
            text = read(path)
            scanned.add(path)
            unit_count += len(markdown_units(text))
            hits.extend(residue_hits(path, text))
        representatives = {
            "docs/ADOPTION.md", "skills/init/SKILL.md", "README.md",
            "tests/test_v014_contracts.py",
        }
        self.assertGreater(unit_count, 0)
        self.assertTrue(representatives.issubset(scanned))
        print("v0.15 residue scan: "
              f"files={len(scanned)} units={unit_count} hits={len(hits)}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
