結論は「未収束」。上限到達とは無関係に、PLAN自体へ残る欠陥があるため実装開始不可である。

1. **R5-1 — high：#47の文書契約がPLAN自身と実装に矛盾する**

   - 根拠: [PLAN.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:23) は、gate到達時に`REFUSED`を返す経路を認識している。一方、[PLAN.md:26](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:26) とDoD [PLAN.md:107](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:107) は「verdictは得られない」と断定する。gateはpre-lock拒否でも`{"verdict":"REFUSED"}`を出力し（[decide-verdict.py:1027](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027)）、SKILLもREFUSEDをverdictの一種として扱う（[SKILL.md:602](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:602)）。
   - さらにS1確定仕様には旧記述「Phase 3冒頭で停止」が残る（[PLAN.md:262](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:262)）。workflowではverifierを起動し得るため事実と異なる。
   - 推奨: 文書契約と§9を「seal-runはexit 2、runは未seal」に統一し、「verdictなし」「Phase 3冒頭で停止」を削除する。

2. **R5-2 — medium：Codex backendの経路説明が空dispatchを落としている**

   - 根拠: [PLAN.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:23) はCodex backendなら`codex-dispatch.py`が未sealを拒否すると断定する。しかしdispatchが空ならdispatcherは呼ばれず、空のreturnsを書いて先へ進む（[SKILL.md:394](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:394)）。dispatcherを呼ぶのは非空時のみ（[SKILL.md:399](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:399)）。
   - 推奨: 「Codex backendかつdispatch非空の場合」と限定する。

3. **R5-3 — medium：契約テスト (a) は「未seal」を検査しない**

   - 根拠: DoDはrunが未sealであることまで要求する（[PLAN.md:106](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:106)）が、(a)が結果説明について確認するのは`tree-digest.py`、`seal-run.py`、`exit 2`の3語だけ（[PLAN.md:165](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:165)）。「exit 2だがrunはseal済み」と誤記しても通る。
   - 推奨: (a)に各言語の「未seal」を表す固定句の検査を追加し、経路依存のverdict説明は検査対象から外す。

4. **R5-4 — high：detached検証の`SCRATCHPAD`が未定義で、削除対象がroot直下になり得る**

   - 根拠: [PLAN.md:254](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:254) は`$SCRATCHPAD`を使うが、リポジトリ内の他箇所にも現環境にも定義がない。実測は`SCRATCHPAD_UNSET`。通常のshellでは`WT=/wt-<sha>`となり、root直下を対象にする。`|| exit 1`もサブシェル外なので、対話shell自体を終了させ得る。
   - 推奨: 検証全体をサブシェルに入れ、その内部で安全な一時親ディレクトリを作成・実在確認してから`WT`を組み立てる。

5. **R5-5 — high：worktree後始末の失敗が成功扱いされる**

   - 根拠: [PLAN.md:256](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:256) は`git worktree remove; echo; test "$rc" -eq 0`の順である。試験が成功して`rc=0`なら、worktree削除が失敗しても最後の`test`が成功し、全体の終了状態は0になる。
   - 推奨: 試験と後始末の終了状態を別々に保存し、どちらか一方でも非0なら検証全体を非0にする。

6. **R5-6 — medium：割り込み時にlinked worktreeが残り、再実行不能になる**

   - 根拠: [PLAN.md:254](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:254)〜[256](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:256) に`EXIT`／`INT`／`TERM`の後始末がない。パスも短いHEAD SHAだけで固定されるため、割り込みでworktreeが残ると同じcommitでの再実行が失敗する。
   - 推奨: 一意なworktreeパスを使い、trapで登録解除と後始末を保証する。

問題なしと確認した点:

- (a)の句読点切断、6件重複、余分な許可例の穴は閉じている。
- (i)はデータ9行、8 severity各1回、言語別catch-all、効果写像まで判別可能。
- (d)(f)(h)、`PRECLOSED`、fallback、handoffの18件への縮小に新しい問題はない。
- 追跡対象の差分は0。レビューによるファイル変更は行っていない。

区分要約:

- **計画自体の欠陥（PLANを直してから実装）:** R5-1〜R5-6。
- **worker指示で吸収できる細部:** 実質的な正確性問題はなし。`git worktree remove --force`実行時の削除承認など、運用上の安全確認のみ。

**最終判定：未収束。実装開始不可。**