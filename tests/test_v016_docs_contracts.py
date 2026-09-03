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

    def test_v018_code_review_migration_is_documented_per_file(self):
        required_by_file = {
            "docs/ADOPTION.md": (
                "reviewCommands.code is no longer supported (removed in docaudit v0.18.0)",
                "keep reviewCommands.security", "Phase 4 security review,",
                "`reviewCommands.security` + `reportPath` set",
                "Report warnings use those codes",
                "leaving either key in an object no longer REFUSES a run",
                "Project-specific legacy command strings are no longer executed",
                "a non-object `reviewCommands` (`null`, string, array, or number) remains REFUSED"),
            "docs/ADOPTION.ja.md": (
                "reviewCommands.code は docaudit v0.18.0 で廃止され、無視されました。",
                "reviewCommands.security はそのまま残します。",
                "Phase 4 の security review、",
                "`reviewCommands.security` + `reportPath` を設定",
                "レポート内の warning はこの code を使う",
                "どちらかのキーが残っていても run は REFUSED にならず",
                "project 固有の legacy command 文字列も実行されなくなる",
                "非オブジェクトの `reviewCommands`（`null`・文字列・配列・数値）は従来どおり REFUSED"),
            "skills/audit/references/config-schema.md": (
                "## reviewCommands", "reviewCommandsCodeRemoved"),
            "skills/audit/SKILL.md": (
                "REVIEW_COMMANDS_JSON", "reviewCommands.security",
                "gate stdout keeps the fixed code only"),
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
