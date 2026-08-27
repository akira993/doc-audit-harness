結論は「未収束」。rev.3には、実行範囲の重大な矛盾1件と、誤った文書でも通る契約検査が残っている。

1. **R3-1 — high：停止分岐追加はdocs-only／runtime挙動不変ではない**

   - 根拠: [PLAN.md:21](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:21) は全非0終了でrun解放・停止する分岐を追加する一方、[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:49) はruntime挙動を一切変えないとする。SKILL.mdは説明資料ではなく実行手順であり、現状の「exit 2後にreader/gateへ進み得る」動作（[SKILL.md:358](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:358)）を「必ず停止」に変える。run解放はlockを削除する状態変更でもある（[open-run.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:87)）。
   - 推奨: v0.13.1から停止分岐を外して現挙動を正確に文書化し、停止保証は別のruntime Issueへ分離する。

2. **R3-2 — high：契約テスト (i) はseverityとgate効果の逆対応を検出しない**

   - 根拠: [PLAN.md:179](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:179) は表内に3語・5語が存在することしか要求しない。`PASS`をblocking、`HIGH`をnon-blockingと誤記しても通る。実装の正は [decide-verdict.py:276](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:276) にある。
   - 推奨: 表を行単位で解析し、5語→non-blocking、3語→blocking、未知語→REFUSEDの対応を完全一致で検査する。

3. **R3-3 — medium：DoD (1b) は要求した停止分岐を判別できず、恒久テストにも接続されていない**

   - 根拠: 要求本文は解放・停止・reader非呼出・stderr報告の4条件（[PLAN.md:104](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:104)）だが、判定は`non-zero`と`stop`を同じ行に含むことしか見ない（[PLAN.md:106](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:106)）。既存exit 5専用診断を削除しても、releaseやstderrを実装しなくても通る。また8本の契約テスト(a)〜(i)のいずれにも(1b)は割り当てられていない。
   - 推奨: 分岐を残す場合は(a)へ統合し、exit 5専用処理の維持と、別の非0分岐にreleaseコマンド・停止・reader非呼出・stderr報告が揃うことを検査する。

4. **R3-4 — medium：契約テスト (a) は余分な不許可パスを見逃す**

   - 根拠: [PLAN.md:160](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:160) は抽出集合との積集合だけを比較し、`normalize()`へ渡すのも固定6値だけである。6値に加えて不許可の`.claude/foo`を許可例として記載しても通る。さらに「同段落」はMarkdown表全体になり、ADOPTIONでは`.claude/state`が別の`anchorPath`行にも存在する（[ADOPTION.md:301](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:301)）。
   - 推奨: accepted-prefixes句を一意に切り出し、そこから抽出した全例を6値と完全一致させ、全例を`normalize()`へ渡す。

5. **R3-5 — medium：契約テスト (d) はinit/audit間のフラグ取り違えを許す**

   - 根拠: [PLAN.md:169](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:169) は両SKILLの和集合8件とREADME全体を比較するだけである。`--full`をinit側、`--scaffold`をaudit側へ誤配置しても集合は一致する。現物はaudit 3件（[README.md:90](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:90)）、init 5件（[README.md:95](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:95)）に分かれる。
   - 推奨: `/docaudit:audit`と`/docaudit:init`を別々に抽出し、それぞれ対応するargument-hintと3件／5件で完全一致させる。

6. **R3-6 — medium：契約テスト (f) は一部過剰で、一部の同時編集回帰を見逃す**

   - 根拠: [PLAN.md:170](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:170) は`models`辞書全体を固定するため、runtime既定リストを明示した正しい`sensitiveTokens`設定を拒否する（[classify-run.py:11](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/classify-run.py:11)）。逆に、同じ`codexReview`を編集するのに`required:false`しか検査せず、既存の`enabled:true`・`bin:"codex"`を壊しても通る（[doc-audit.example.json:9](/Users/akiratakahashi/Projects/doc-audit-harness/docs/examples/doc-audit.example.json:9)）。
   - 推奨: lightの5必須値を固定し、任意の`sensitiveTokens`は既定リストのみ許可するとともに、`codexReview`の`enabled`・`bin`・`required`を全て固定する。

7. **R3-7 — medium：severity表の配置仕様が内部矛盾している**

   - 根拠: [PLAN.md:127](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:127) は§7へ固定するが、[PLAN.md:251](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:251) は§8もworker判断で許可する。現行の不完全なseverity説明は§8にある（[ADOPTION.md:446](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:446)、[ADOPTION.ja.md:419](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:419)）。新表を§7に追加して旧説明を残しても(i)は通る。
   - 推奨: 現行§8のseverity説明を完全表へ置換する仕様に一本化する。

8. **R3-8 — medium：契約テスト (h) は付録の非scripts/references行の同一欠落を依然検出しない**

   - 根拠: [PLAN.md:177](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:177) は付録件数を(c)が固定するとするが、(c)が固定するのはscripts/referencesの42件だけである。両言語からplugin、SKILL、agents、docsを同じように削除しても(c)(h)とも通る。現行付録はroot行を除き45 pathで、6件追加後は51となる（[ADOPTION.md:601](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:601)）。
   - 推奨: (h)で各文書の付録path総数51もassertする。

9. **R3-9 — medium：detached checkout検証が実行手順に接続されていない**

   - 根拠: DoDはcommit後のworktree試験を要求する（[PLAN.md:195](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:195)）が、「検証コマンド一式」には`cat-file`と`bash -n`しかない（[PLAN.md:219](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:219）。進行順もboss再実行→commitで終了している（[PLAN.md:282](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:282)）。
   - 推奨: §8と進行順に、S2 commit後の`git worktree add --detach`、試験、`git worktree remove`までの完全な手順を追加する。

10. **R3-10 — low：`PRECLOSED`が再開分岐を試している保証がない**

   - 根拠: [PLAN.md:190](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:190) は`PRECLOSED`を別定数にするが、非空かつ`ISSUES`の真部分集合である検査がない。次版で`ISSUES`だけ更新すると、事前closeが対象外になり「一部close済み」の分岐を試さないまま通り得る。
   - 推奨: `PRECLOSED`が非空で`PRECLOSED < ISSUES`であることを明示assertする。

11. **R3-11 — low：未seal時のREFUSED到達箇所が誤っている**

   - 根拠: [PLAN.md:22](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:22) は`run_tree_digest`でREFUSEDになるとするが、実際はそれより前の`manifest.sealed is not True`で拒否される（[decide-verdict.py:693](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:693)）。digest再計算は [decide-verdict.py:804](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:804)。
   - 推奨: 根拠を`decide-verdict.py:693-695`へ訂正する。

問題なしと確認した点:

- 固定値は実測でscripts 36＋references 6＝42、argument-hintはinit 5＋audit 3＝8、en/ja見出し各15、§5は23＋2＝25、severity集合は3／5で正しい。
- references 6本の内訳もPLANどおりである。
- (g)の空行区切りは現物のen 2行、ja 3行のrefresh段落と一致し、前後の段落から余計な版番号を拾わない。
- 既存のexit 5専用処理と`read-manifest.py`失敗時停止には、新しい矛盾はない。
- fallback手順と`! grep -q`への修正は成立している。
- 成果物の削除は不要。8契約テスト、handoff派生、PROMPTS節はいずれも維持すべきである。detached側の全487件実行だけは、通常checkoutでフルスイートと作業差分0を確認するなら、`tests.test_release_handoff`の18件へ縮小可能。

**判定：未収束。R3-1〜R3-9はPLAN自体を直してから実装すべき。R3-10、R3-11はworker指示でも吸収できる細部。**