import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


class TestV016DocumentContracts(unittest.TestCase):
    def test_ct_7_required_tokens_are_present_in_each_named_document(self):
        required_by_file = {
            "docs/ADOPTION.md": (
                "phase4FlipsUnchangedContent",
                "--expect-config-sha",
                "sealed-config-mismatch",
                "configAcceptanceRequired",
                "Upgrade the entire plugin tree together",
                "older, future, missing, invalid, or modified stamps fall back",
                "repository-writer trust",
                "data-only carry-forward",
            ),
            "docs/ADOPTION.ja.md": (
                "phase4FlipsUnchangedContent",
                "--expect-config-sha",
                "sealed-config-mismatch",
                "configAcceptanceRequired",
                "plugin tree 全体を同期",
                "旧版・未来版・欠落・不正・modified は plugin engine へ fallback",
                "repo 書込み相当の信頼",
                "repo 内 `file` と `severity` だけをデータとして自動で引き継ぐ",
            ),
            "README.md": (
                "phase4FlipsUnchangedContent",
                "sealed-config-mismatch",
                "validated `file` plus `severity` data",
                "repository-writer level",
            ),
            "skills/audit/references/config-schema.md": (
                "phase4FlipsUnchangedContent",
                "--expect-config-sha",
                "sealed-config-mismatch",
                "configAcceptanceRequired",
                "worktreeDigest, contractVersion, configSha, and carryForwardSha",
                "includes only `file` plus `severity`",
            ),
            "skills/audit/SKILL.md": (
                "phase4FlipsUnchangedContent",
                "--expect-config-sha",
                "sealed-config-mismatch",
                "same worktreeDigest, contractVersion, configSha, and carryForwardSha",
                "Carry-forward is data-only (`file` plus `severity`)",
                "every older, future, missing, invalid, or modified stamp falls back",
                "repository-writer level",
            ),
        }
        self.assertEqual(len(required_by_file), 5)
        for path, tokens in required_by_file.items():
            text = read(path)
            with self.subTest(path=path):
                for token in tokens:
                    self.assertIn(token, text, f"{path}: {token}")

    def test_v017_code_review_contract_is_documented_per_file(self):
        required_by_file = {
            "README.md": ("autonomously runs configured", "Claude Code 2.1.246"),
            "docs/ADOPTION.md": (
                "code-review autonomous execution and opt-out", "permissions.ask",
                "code-review is LLM-sampled", "excluded from `phase4Runs`"),
            "docs/ADOPTION.ja.md": (
                "code-review の自律実行と opt-out", "permissions.ask",
                "LLM サンプリング", "`phase4Runs` と flip 計測には入れない"),
            "skills/audit/references/config-schema.md": (
                "## code-review command contract", "/code-review low|medium|high",
                "required:true", "excluded from `phase4Runs`"),
            "skills/audit/SKILL.md": (
                "code-review-plan.py", "skill=code-review", "blocked-by-settings",
                "{{GATE_CODE_REVIEW_STATUS}}"),
        }
        for path, tokens in required_by_file.items():
            text = read(path)
            with self.subTest(path=path):
                for token in tokens:
                    self.assertIn(token, text)

    def test_old_code_review_meaning_is_absent(self):
        forbidden = (
            "not started by the audit", "audit does not start it",
            "offer `/code-review`", "offers `/code-review`", "not-model-invocable",
            "監査自身がまだ起動しない", "監査自身はまだ起動しない",
            "`/code-review` はユーザーに提案",
        )
        for path in ("README.md", "docs/ADOPTION.md", "docs/ADOPTION.ja.md",
                     "skills/audit/SKILL.md"):
            text = read(path)
            with self.subTest(path=path):
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
