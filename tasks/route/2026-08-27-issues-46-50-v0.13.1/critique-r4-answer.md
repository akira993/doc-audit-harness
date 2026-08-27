結論は「未収束」。rev.4で新たに4件のhighと1件のmediumを確認した。

1. **R4-1 — high：#47のREFUSED理由は依然として事実と異なる**

   - 根拠: [PLAN.md:21](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:21) は、gateが`manifest is not sealed`で拒否すると断定する。しかしseal前の`EVIDENCE`には`digest`がなく（[open-run.py:221](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:221)）、`digest`を追加する通常箇所はseal成功処理だけである（[seal-run.py:70](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:70)）。exit 2では追加されないため、gateへ到達してもmanifest検査より前の必須キー検査で`EVIDENCE required keys are missing`になる（[decide-verdict.py:316](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:316)、[decide-verdict.py:653](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:653)）。
   - さらにworkflow backendは未sealのままverifierを起動し得る一方（[SKILL.md:418](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:418)）、Codex backendは先に未sealを拒否する（[codex-dispatch.py:60](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:60)）。したがって単一の後続経路は存在しない。
   - 推奨: 文書契約は「glob拒否→seal-run exit 2→manifestは未seal」までに限定し、その後の非対称な挙動は別runtime Issueへ分離する。

2. **R4-2 — high：契約テスト (a) の文末抽出は正しい英語文を壊す**

   - 根拠: [PLAN.md:161](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:161) はマーカーから最初の`.`までを抽出する仕様だが、期待値の`.claude/state`、`.claude/worktrees`、`.mdq`、`.codegraph`自体が`.`で始まる。単純な最短一致では最初の値の冒頭で終了し、正しいconfig-schemaとADOPTION.mdがFAILする。集合化は同じ値の重複記載も隠す。
   - 推奨: マーカーと6値を1物理行に固定し、句読点ではなく行末／表セル末までからコードスパンを抽出して、集合一致に加え出現数も6件とassertする。

3. **R4-3 — high：契約テスト (i) は矛盾する重複行と誤ったcatch-allを通す**

   - 根拠: [PLAN.md:184](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:184) は行から写像を作るが、辞書化すると同一severityの重複行が上書きされる。例えば`PASS → blocking`の後に`PASS → non-blocking`を書けば最終写像は正しくなり、矛盾した表でもPASSする。またREFUSED行の第1列が`any other value`／`上記以外の値`であることを検査しないため、`ERROR → REFUSED`だけでも通る。
   - 推奨: データ行を正確に9行、8 severityを各1回、言語別catch-allを正確に1回と確認してから写像を比較する。

4. **R4-4 — high：detached試験の失敗が後始末成功で隠される**

   - 根拠: [PLAN.md:244](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:244) は試験と後始末を`;`で接続している。18試験が失敗しても、その後の`git worktree remove --force`が成功すれば複合コマンド全体は終了状態0になる。また強制終了時の後始末がなく、親一時ディレクトリも残る。
   - 推奨: trap付きのサブシェルで試験の終了状態を保存し、worktreeと親一時ディレクトリを後始末した後、元の失敗状態を返す。

5. **R4-5 — medium：契約テスト (a) は#47の結果説明を検査していない**

   - 根拠: DoD (1) はseal exit 2、未seal、gate結果まで要求する（[PLAN.md:102](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:102)）が、契約テスト(a)はプレフィックス集合と`normalize()`の成否しか検査しない（[PLAN.md:160](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:160)）。今回のように結果説明が誤っていてもgreenになる。
   - 推奨: (a)で3文書の対象文に`tree-digest.py`拒否、`seal-run.py`、`exit 2`、未sealの安定した契約語が存在することも検査し、到達が一定しないgate理由は検査対象から外す。

問題なしと確認した点:

- severity表の共通トークン`non-blocking`／`blocking`／`REFUSED`は既存文体と衝突しない。第2列の後続説明に別のコードスパンがあっても、先頭だけ読む仕様なら問題ない。
- (d)のaudit 3／init 5、(f)の固定example、(h)の付録51件に新しい矛盾はない。
- `PRECLOSED`の真部分集合検査、fallback手順、HEAD収録検査に新しい問題はない。
- `test_release_handoff.py`は実測18件で、detached側を18件へ縮小した判断は妥当。成果物の追加削減は不要。
- 追跡対象の差分は0。レビューによるファイル変更は行っていない。

**判定：未収束。R4-1〜R4-5はいずれもPLANを直してから実装すべき。**