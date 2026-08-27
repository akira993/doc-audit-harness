包括承認（boss）: 本セッションの S1 作業について、以下を**事前に一括で承認**する。以後、個別の確認を求めずに完了まで進めよ。

- 読み取り（`git status`／`git branch`／`git log`／`rg`／`sed`／`cat` 等）と、`python3 -m unittest …`・`python3 skills/audit/scripts/scaffold.py --dry-run` 等のテスト・検査実行。
- `git checkout -b feat/v0.13.0-issues-39-44`（main から）、および依頼書 §5 の許可パス内のファイル作成・編集・削除、`git add`（許可パス内のみ）と `git commit`。
- 上記以外（許可パス外の変更、`git push`、`rm -rf`、パッケージ導入）は引き続き禁止 — 必要になった場合は修正せず報告のみ。

停止せずに `stage1-prompt.md` の §0〜§7 を順に実行し、§7 の形式で報告せよ。途中でユーザー確認が必要と判断した場合も、まず可能な作業をすべて終えてから最後にまとめて報告すること。
