"""Release contracts for the v0.19.0 codex-claim adjudication layer."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class TestV019Contracts(unittest.TestCase):
    def test_adoption_guides_fix_the_four_adjudication_behavior_sentences_verbatim(self):
        expected = {
            "docs/ADOPTION.md": (
                "**v0.19.0 behavior changes:** codex-review `critical` and `high` findings are "
                "blocking only when a cited per-claim adjudication has effective state "
                "`confirmed`. If adjudication does not run or its record or evidence is missing, "
                "damaged, or invalid, the claim becomes non-blocking `unverified` and the gate "
                "emits a warning; this remains true with `codexReview.required:true`, whose "
                "fail-closed effect still applies to the codex review itself but no longer to "
                "adjudication availability. Adjudication is not monotonic across runs because "
                "carry-forward retains only file and severity: a claim may be `refuted` in one "
                "run and independently become `confirmed`, and therefore NEEDS FIX, in the next. "
                "Repository text is treated as quoted data and confirmed/refuted results require "
                "`file:line` evidence, but prompt injection remains a residual risk that can still "
                "bias an adjudicator toward `refuted`."
            ),
            "docs/ADOPTION.ja.md": (
                "**v0.19.0 の挙動変更:** codex-review の `critical` / `high` 所見は、所見ごとの裁定が "
                "`file:line` 根拠付きで `confirmed` の実効状態になった場合に限り blocking となる。"
                "裁定が動かない、または記録や根拠が欠落・破損・不正な場合、その主張は非 blocking の "
                "`unverified` となり gate が警告する。この扱いは `codexReview.required:true` でも同じで、"
                "`required` は codex review 自体には従来どおり fail-closed だが、裁定の利用可否には適用されない。"
                "carry-forward は file と severity しか保持しないため裁定結果は run 間で単調ではなく、"
                "ある run の `refuted` が次の run で独立に `confirmed` となり NEEDS FIX へ戻ることがある。"
                "repository 内の文章は指示ではなく引用データとして扱い、confirmed/refuted には "
                "`file:line` 根拠を必須とするが、裁定を `refuted` 側へ誘導し得る prompt injection は"
                "残余リスクとして残る。"
            ),
        }
        for path, heading in (
                ("docs/ADOPTION.md", "**v0.19.0 behavior changes:**"),
                ("docs/ADOPTION.ja.md", "**v0.19.0 の挙動変更:**")):
            matches = [part for part in re.split(r"\n\s*\n", read(path))
                       if heading in part]
            self.assertEqual(len(matches), 1, f"{path}: behavior paragraphs={len(matches)}")
            actual = " ".join(matches[0].split())
            self.assertEqual(actual, expected[path], path)

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

    def test_adoption_codex_summary_and_flip_counter_match_v019_behavior(self):
        contracts = {
            "docs/ADOPTION.md": (
                "findings are blocking only when their per-claim adjudication has effective state "
                "`confirmed`;\n`medium`/`low` remain non-blocking.",
                "when the set of paths reported as `critical`/`high` changes",
                "findings remain blocking",
                "when blocking-file status changes",
            ),
            "docs/ADOPTION.ja.md": (
                "所見ごとの裁定が実効状態 `confirmed` の場合に限り\nブロッキングとなり、"
                "`medium`/`low` は非ブロッキングのままである。",
                "`critical`/`high` として報告されたパスの集合が変わると",
                "所見はブロッキング",
                "ブロッキング対象ファイルが変わると",
            ),
        }
        for path, (blocking, flips, old_blocking, old_flips) in contracts.items():
            text = read(path)
            self.assertEqual(text.count(blocking), 1, path)
            self.assertEqual(text.count(flips), 1, path)
            self.assertNotIn(old_blocking, text)
            self.assertNotIn(old_flips, text)

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
