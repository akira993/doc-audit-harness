"""Release contracts for the v0.19.0 codex-claim adjudication layer."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class TestV019Contracts(unittest.TestCase):
    def test_adoption_guides_state_the_same_six_adjudication_facts(self):
        markers = (
            "confirmed",
            "unverified",
            "codexReview.required:true",
            "file:line",
            "carry-forward",
            "prompt injection",
        )
        paragraphs = []
        for path, heading in (
                ("docs/ADOPTION.md", "**v0.19.0 behavior changes:**"),
                ("docs/ADOPTION.ja.md", "**v0.19.0 の挙動変更:**")):
            matches = [part for part in re.split(r"\n\s*\n", read(path))
                       if heading in part]
            self.assertEqual(len(matches), 1, f"{path}: behavior paragraphs={len(matches)}")
            paragraphs.append(matches[0])
        for marker in markers:
            for paragraph in paragraphs:
                self.assertIn(marker, paragraph, marker)

    def test_shipped_adjudication_files_are_documented_in_both_appendices(self):
        paths = (
            "agents/doc-claim-adjudicator.md",
            "skills/audit/references/claim-adjudication-workflow.js",
            "skills/audit/scripts/claim_record.py",
            "skills/audit/scripts/plan-claims.py",
            "skills/audit/scripts/write-claim.py",
        )
        for guide in ("docs/ADOPTION.md", "docs/ADOPTION.ja.md"):
            text = read(guide)
            for path in paths:
                self.assertEqual(text.count(path), 1, f"{guide}: {path}")

    def test_public_explanations_keep_adjudication_warning_only_on_failure(self):
        contracts = (
            ("README.md", "missing or invalid adjudication is warning-only and treated as non-blocking `unverified`"),
            ("skills/audit/SKILL.md", "Missing, invalid, or unavailable adjudication degrades to non-blocking `unverified` with a warning and never makes the verdict REFUSED"),
            ("skills/audit/references/config-schema.md", "Missing or invalid records become\nnon-blocking `unverified` with a warning. Adjudication failures never make a run REFUSED"),
        )
        for path, statement in contracts:
            text = read(path)
            self.assertEqual(text.count(statement), 1, path)


if __name__ == "__main__":
    unittest.main()
