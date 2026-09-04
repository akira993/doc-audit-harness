"""Release contracts for the v0.19.0 codex-claim adjudication layer."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def plugin_version():
    return json.loads(read(".claude-plugin/plugin.json"))["version"]


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

    def test_v021_public_explanations_make_missing_adjudication_fail_closed(self):
        contracts = {
            "README.md": (
                "a missing title or any such claim without a valid adjudication record makes "
                "the run REFUSED",
                "valid `refuted`, `unverified`, and `not-adjudicable` records remain non-blocking",
            ),
            "skills/audit/SKILL.md": (
                "A missing title makes the gate REFUSED, as does any target without a valid "
                "claim record",
                "If claims still remain after the third attempt, proceed to Phase 5: the gate "
                "refuses",
                "Never synthesize a record",
            ),
            "skills/audit/references/config-schema.md": (
                "A missing finding title makes the gate\nREFUSED as `codexClaimTitleMissing`",
                "makes the gate REFUSED as `codexClaimsUnadjudicated`",
                "regardless of `codexReview.required`",
            ),
        }
        old_statements = (
            "missing or invalid adjudication is warning-only",
            "never turn an adjudication failure into REFUSED",
            "Adjudication failures never make a run REFUSED",
        )
        for path, statements in contracts.items():
            text = read(path)
            for statement in statements:
                self.assertEqual(text.count(statement), 1, f"{path}: {statement}")
            for statement in old_statements:
                self.assertNotIn(statement, text, f"{path}: {statement}")

    def test_v021_adoption_guides_document_refused_scope_and_carry_forward_limit(self):
        contracts = {
            "docs/ADOPTION.md": (
                "**v0.21.0 behavior changes:**",
                "without a valid claim record produces `codexClaimsUnadjudicated`",
                "Findings from a REFUSED run are not written to history and therefore are not "
                "carried forward",
                "the unchanged anchor causes the same change set to be reviewed again",
                "the only opt-out is to set `codexReview.enabled:false`",
                "Corrupt history still takes the existing quarantine path first",
            ),
            "docs/ADOPTION.ja.md": (
                "**v0.21.0 の挙動変更:**",
                "有効な claim record が無い対象があると `codexClaimsUnadjudicated`",
                "REFUSED run の所見は history に入らず carry-forward されない",
                "anchor が進まないため、次の run で同じ変更集合が再 review される",
                "唯一の回避策は `codexReview.enabled:false`",
                "history が壊れている場合は従来の隔離経路が先に走り",
            ),
        }
        for path, statements in contracts.items():
            text = read(path)
            for statement in statements:
                self.assertEqual(text.count(statement), 1, f"{path}: {statement}")

    def test_v021_skill_documents_version_handshake_and_template_validation(self):
        skill = read("skills/audit/SKILL.md")
        normal_open = next(
            line for line in skill.splitlines()
            if "open-run.py" in line and "[--accept-config]" in line
        )
        self.assertIn(f"--skill-version {plugin_version()}", normal_open)
        self.assertEqual(len(re.findall(r"--skill-version (\d+\.\d+\.\d+)", skill)), 1)
        for line in skill.splitlines():
            if "open-run.py" in line and ("--release" in line or "--break-lock" in line):
                self.assertNotIn("--skill-version", line)
        self.assertIn("unrecognized arguments: --skill-version", skill)
        self.assertIn("does not match plugin engine version", skill)
        self.assertIn("start a new session and rerun `/docaudit:audit`", skill)
        self.assertIn("runid, runDir, anchor, config, lockIno, engineVersion", skill)
        self.assertIn("Bind `CONTRACT_VERSION` from `EVIDENCE.engineVersion`", skill)
        self.assertNotIn("Bind `CONTRACT_VERSION` from the installed plugin's version", skill)
        for statement in (
            "do not put a placeholder name in the report body with its braces",
            "receipt remains `failed:true`",
            "after an initial-creation failure, or `--replace` after a replacement failure",
            "completely renders the final report bytes before writing history or the\nanchor",
            "produces REFUSED and does not advance the anchor",
        ):
            self.assertEqual(skill.count(statement), 1, statement)

    def test_v021_adoption_guides_document_index_and_harness_changes(self):
        contracts = {
            "docs/ADOPTION.md": (
                "`import-audit-scope.py --check --from-index` now checks one Git index snapshot",
                "accepting only stage-0 regular blobs",
                "`path-mismatch` and exits 4",
                "`--check-stamps` to compare each uniquely and canonically placed stamp",
                "reports them `up-to-date` without rewriting their stamps",
                "`engineVersion` only when at least one template is written",
            ),
            "docs/ADOPTION.ja.md": (
                "`import-audit-scope.py --check --from-index` は作業ツリーから独立した 1 回の Git index snapshot を検査",
                "stage 0 の通常 blob のみを採用",
                "`path-mismatch` として exit 4 を返す",
                "`--check-stamps` を使い",
                "stamp を書き換えず `up-to-date` と報告",
                "template を 1 本以上書いた場合のみ更新",
            ),
        }
        for path, statements in contracts.items():
            text = read(path)
            for statement in statements:
                self.assertEqual(text.count(statement), 1, f"{path}: {statement}")

    def test_v021_init_and_schema_document_refresh_decisions(self):
        init_skill = read("skills/init/SKILL.md")
        for statement in (
            "A newly created decision object is",
            "preserve the existing\n`harness.engineVersion` when `created` is empty",
            "update it to `<version>` only when `created`\nis non-empty",
            "Only when `upToDate` contains all three harness paths",
            "If `created` is\nempty but any file is `not-refreshable`, show its `skipReasons` detail",
        ):
            self.assertEqual(init_skill.count(statement), 1, statement)

        schema = read("skills/audit/references/config-schema.md")
        for statement in (
            "`missing`, `current`, `refreshable`, or `not-refreshable`",
            "`scaffold.py --harness --check-stamps` writes nothing",
            "a stamp-name mismatch",
            "`path-mismatch` (exit 4)",
            "its JSON includes `recordedScopePath`",
            "reads config and scope bytes by object ID",
        ):
            self.assertEqual(schema.count(statement), 1, statement)


if __name__ == "__main__":
    unittest.main()
