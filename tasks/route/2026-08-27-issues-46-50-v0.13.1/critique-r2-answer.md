メタ認知: 「14件対応済み」という自己申告を受け入れすぎる確証バイアスと、テスト追加を無条件に安全とみなす傾向を警戒した。結論として、rev.2 はまだ実装開始不可である。

1. **R2-1 — high：seal exit 2 で「監査停止・verdict なし」は現手順では保証されない**

   - 根拠: PLAN は [PLAN.md:21](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:21) で停止を断定しているが、[SKILL.md:360](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:360) は exit 5 のみ停止を明記する。`seal-run.py` は digest 拒否時に manifest を更新せず exit 2（[seal-run.py:63](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:63)）。その後の `read-manifest.py` は hash だけを検証し、`sealed:true` を確認しない（[read-manifest.py:15](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/read-manifest.py:15)）。未 seal manifest を渡す実測でも読み取りに成功した。したがって verifier/gate へ進み、最終的に REFUSED になる経路が残る。
   - 推奨: SKILL.md に「`seal-run.py` が非0なら、exit 5以外でも run を解放して即停止し、`read-manifest.py` を呼ばない」という明示分岐をDoD化する。

2. **R2-2 — high：契約テスト (c) は正しい付録でも必ず失敗する**

   - 根拠: [PLAN.md:150](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:150) は42ファイルのbasename集合と「付録フェンス内の全basename集合」の完全一致を要求する。しかし付録には plugin、SKILL、agents、docs、tests 等も正当に存在する（[ADOPTION.md:601](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:601)）。さらにbasename比較では別ディレクトリの同名ファイルを誤って許可する。現物の `__pycache__` は対象外である一方、`docaudit_cache.py`、`docaudit_paths.py` 等の通常ファイルは掲載対象である。
   - 推奨: 両側を通常ファイルに限定し、付録側を `skills/audit/scripts/` と `skills/audit/references/` の行だけに絞って、リポジトリ相対パスで完全一致させる。

3. **R2-3 — medium：契約テスト (f) は既定値でない設定を通す**

   - 根拠: [PLAN.md:153](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:153) はキーの存在しか検査しないため、`phase3Backend:"codex"`、`regressionRecheck.enabled:true`、`codexReview.required:true`、`models.light:{}` でも通る。これらは挙動を変える。正しい既定値は `workflow`、`false`、`false`、および light の `enabled:true/maxChanged:10/maxImpacted:15/maxDiffLines:200/maxDiffBytes:65536`。
   - 推奨: (f) で4設定の値を既定値と完全一致させ、config-schema表のトップレベルキーは曖昧な `models: { light: ... }` ではなく `models` として抽出可能にする。

4. **R2-4 — medium：5 Issue化によりhandoff再開テストの算術が破綻する**

   - 根拠: 現テストは3件を事前closeし、残り3件をcloseする六件構成（[test_release_handoff.py:439](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:439)）。rev.2 はIssue番号と一部件数だけを定数由来にし、「それ以外のロジックは変えない」とする（[PLAN.md:166](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:166)）。全5件では「3件close済み・残り3件」は成立しない。
   - 推奨: `preclosed` 集合を明示し、期待するclose集合と件数を `ISSUES - preclosed` から導出する変更まで許可する。

5. **R2-5 — medium：契約テスト (a) の抽出規則が判別不能**

   - 根拠: [PLAN.md:147](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:147) の「バッククォート内のpath」には、同じ記述中の `*`、`?`、`[`、`tree-digest.py`、`seal-run.py` も該当し得る。一方、先頭が`.`や`/`の値だけに絞ると `graphify-out` を落とす。件数 `≥6` だけでは同じ値の重複で欠落を隠せる。
   - 推奨: 各文書から期待する6プレフィックスを抽出して集合完全一致させ、その6値だけを `normalize()` に渡す。

6. **R2-6 — medium：契約テスト (g) は余計な未対応版を許す**

   - 根拠: [PLAN.md:155](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:155) は旧版集合の「包含」しか要求しないため、`0.9.0` や `0.10.0` を追加しても通る。また `--harness --refresh` は各ADOPTIONに複数回あり、対象段落の特定条件がない。
   - 推奨: §4a内で stamped templates とrefreshコマンドを併記する段落がちょうど1件と確認し、更新元版を包含ではなく完全一致で検査する。

7. **R2-7 — medium：契約テスト (h) はen/jaの同一欠落を検出しない**

   - 根拠: [PLAN.md:157](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:157) は言語間の一致だけなので、両方から同じ見出し・表行・付録pathを削除しても通る。現物は見出し15、§5キー23、付録path 45で、計画実施後は15、25、51となる。
   - 推奨: en/ja一致に加えて、各側の期待件数または必須集合も固定する。

8. **R2-8 — medium：契約テスト (i) は書式変更に脆く、空集合PASSも可能**

   - 根拠: [PLAN.md:158](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:158) はPythonソースを正規表現で読むが、ブロッキング集合は定数、非ブロッキング集合は別形式の行内setであり、改行や並べ替えで壊れる。文書側の「severity節」も§7または§8としか決まっていないため、一意に抽出できない。両抽出が空なら集合一致だけは成立し得る。
   - 推奨: Python側は構文木でset literalを読み、文書側には一意な表またはマーカーを設け、件数5・3を別途assertする。

9. **R2-9 — medium：`git ls-files` はS2 commit収録の証明にならない**

   - 根拠: [PLAN.md:170](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:170) の検査は、commit後にindexへ `git add -f` しただけでも非空になる。HEADにscriptがなくても誤ってPASSできる。
   - 推奨: `git cat-file -e HEAD:<path>` または `git ls-tree HEAD -- <path>` でHEAD収録を確認し、HEADからのdetached checkoutでも試験を実行する。

10. **R2-10 — medium：auto-mode fallbackの2コマンドではhandoffが失敗する**

   - 根拠: [PLAN.md:29](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:29) は `merge → handoff` の2コマンドを案内するが、正式手順はmainへの切替・取得を挟む（[PLAN.md:247](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:247)）。handoff本体もmain・HEAD・origin/main一致を必須にする（[release-handoff.sh:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh:41)）。
   - 推奨: fallbackにも「merge → mainへ切替 → pull → handoff」の完全な手順を記載する。

11. **R2-11 — low：旧版文字列検査は成功状態で終了コード1になる**

   - 根拠: [PLAN.md:207](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:207) の `grep -c` は一致0件なら表示は`0`だが終了状態は1であり、自動実行では正しい修正を失敗扱いし得る。
   - 推奨: `! grep -q '0\.13\.0' <script>` に置き換える。

問題なしと確認した観点:

- 正しい値を入れた4つのexampleキーは現実装で拒否されず、既定挙動も変えない。問題は(f)がその値を保証していない点のみ。
- (h)の見出しレベル列一致自体は過剰仕様ではない。ja側だけの`###`増減は構造パリティ違反として落とすべきである。
- docs-only範囲にruntime変更案は混入していない。#50-5と#48-6は既存挙動の明文化で足りる。ただしR2-1のSKILL手順補強は必須。
- handoff script、8本の契約テスト、短いPROMPTS節はいずれも削減対象ではない。検査仕様を直す方が費用対効果は高い。
- 基準試験は実測で `Ran 487 tests in 141.478s — OK`。

**判定: 未収束。** R2-1〜R2-10はPLAN自体を直してから実装すべき欠陥。R2-11だけはworker指示で吸収可能な細部である。

追跡対象ファイルは変更していない。ただし背景レビュー担当が作成した未追跡の `.claude/worktrees/agent-*` が残っている。削除禁止ルールに従い、無断では除去していない。