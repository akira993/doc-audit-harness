# S2 実装依頼 — docaudit v0.13.1 版バンプ・テスト・契約テスト・release-handoff

あなたは worker（実装者）である。boss（Fable）が確定した計画 `tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md`（rev.8）の
**S2（版バンプ 5 面・engine-shas・既存テスト更新・契約テスト 8 本・release-handoff.sh 派生＋test 再照準）だけ**を実装する。
S1（文書修正）は既に boss がコミット済み（HEAD に含まれる）。S1 対象文書の本文は S2 で **変更しない**（版行・refresh 行を除く）。

## 進め方

1. 最初に PLAN.md 全文（特に §0・§6 S2・§7・§8・§10・§11・§12）を読む。§10 のリテラル本文・正規表現は**導出せずそのまま書く**。
2. 版バンプ前に `git diff --name-only main..HEAD` に `skills/init/**` が無いことを確認してから、`engine-shas.json` に `"0.13.1"` を `0.13.0` の
   3 hash のコピーで追加する。`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run` で `stampVersion: 0.13.1` を確認。
3. 契約テスト `tests/test_v0131_docs_contracts.py` は PLAN §6 (23) の (a)(b)(c)(d)(f)(g)(h)(i) の 8 本。各 test は対象件数を assert メッセージに
   含め、抽出 0 件を明示的に fail させる。**S1 済みの現物に対して全 8 本が緑になる**ことを確認し、さらに各 test が「誤った文書で赤になる」ことを
   一時的な改変（作業ツリー内で改変→実行→`git checkout -- <file>` で復元）で 1 本ずつ確認して報告に記す（復元後 `git status --short` が
   S2 の変更だけであること）。
4. `release-handoff.sh` は `cp tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`
   の後に PLAN §6 (24)／§10 の差し替えを行う。`! grep -q '0\.13\.0' <新 script>` と `bash -n` を確認。
5. `tests/test_release_handoff.py` は PLAN §6 (25) の範囲のみ変更。一括置換禁止（`:304` の `"a" * 39` は SHA 長）。
6. 作業後、§8 の検証コマンド（S2 該当分。detached 検証は boss が行うので不要）を全て実行し、**各コマンドの実出力（数値・exit code）を報告に貼る**。
   フルスイートは `python3 -m unittest discover -s tests -t .` で **`Ran 495 tests … OK`（skip 0）** を確認する。
7. git commit はしない（boss が行う）。`git status --short` と `git diff --stat` を報告に含める。新規ファイル 2 本（契約テスト・handoff script）は
   untracked のままでよい。

## 報告書式（最後に `tasks/route/2026-08-27-issues-46-50-v0.13.1/stage2-report.md` へ書き出す）

- 冒頭 1 文で結果（完了／未完了とその理由）。
- DoD (20)〜(26) ごとに「変更ファイル:行」「確認コマンドと実出力」を 1 行ずつ。
- 契約テスト 8 本それぞれの「緑の根拠（件数）」と「赤にする改変→赤の出力→復元」の記録。
- §8 検証コマンドの実出力（全て）。
- 許可外ファイルの変更が必要と判断した箇所があれば、修正せず「報告のみ」の節に列挙。
- 未検証・未対応があれば明示（黙って省略しない）。

---

以下は PLAN.md から転記した **完了条件（S2）／変更範囲／検証コマンド一式／S2 確定仕様／意図的差分リスト／リリース手順**（原文）。
