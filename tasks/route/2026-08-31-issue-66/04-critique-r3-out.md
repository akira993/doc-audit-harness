メタ認知: 「単純化＝安全」という設計上の魅力と、前回対応済みという確認バイアスを警戒した。今回は既存実装が実際に保証している意味を基準に裁定した。

裁定: 対応 #1 の代替案は **R2-1（Phase 4 全体の過剰起動）だけを満たし、R1-3（黙殺防止）は満たさない**。また、`codexReview.required` と完全対称という前提は実装事実と逆である。v3 は差し戻すべきである。

1. **Major — `required:true` の precedent が事実と逆で、強制契約が形骸化する**

   根拠: S3 は「`codexReview.required` も空 diff では Phase 4 を起動せず、REFUSED にしない」とする。[PLAN.md:121](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:121>)。しかし現行 `start-run.py` は `codexReview.required:true` 自体を `phase4Required=true` の条件にしており、空 diff でも Phase 4 を起動する。[start-run.py:247](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:247>)。gate も `phase4:"none"` と `codexReview.required:true` の組合せ、および `completed` 以外を明示的に REFUSED にする。[decide-verdict.py:1027](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027>)、[decide-verdict.py:1041](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1041>)。この挙動はテストでも固定されている。[test_start_run.py:406](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_start_run.py:406>)。したがって §9.8 の「P6・`required:true`・`phase4Required=false` → 正常」は codexReview と非対称であり、PLAN §1 の「強制は gate が導出」「設定層の黙ったスキップを不可能にする」と矛盾する。

   推奨修正: `required` を維持するなら、Phase 4 全体とは別の封印済み code-review eligibility を設け、空 diff でも code-review 層だけを実行必須にする。

2. **Major — optional の P6 も Phase 4 不要時には状態未束縛となり、実際には黙殺される**

   根拠: 新 planner は Phase 4 step 3 に配置されるが、現行 global gate は `phase4Required=false` なら Phase 4 内を一切実行しない。[PLAN.md:90](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:90>)、[SKILL.md:552](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:552>)。したがって空 diff の P6 では planner が呼ばれず、`CODE_REVIEW_STATE` も束縛されない。S5 には `phase4-not-required` 状態がなく、`ran`・`blocked-by-settings`・`not-run`・`legacy` しかない。[PLAN.md:159](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:159>)。既存の「Phase 4 不要」表示は codexReview 専用の probe record から生成され、code-review では利用できない。[SKILL.md:667](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:667>)、[SKILL.md:795](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:795>)。よって S3 の「報告書が理由を示す」は現計画から実装できない。

   推奨修正: planner を global Phase 4 分岐の前に移し、P6＋`phase4Required=false` を `phase4-not-required` として明示的に束縛・表示する。

3. **Major — `manifest.phase4Required` の型異常が双方向契約を迂回できる**

   根拠: §9.8 は true/false の二値だけを前提とし、厳密な boolean 型検証を規定していない。[PLAN.md:293](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:293>)。現行 gate は `manifest.get("phase4Required")` の truthiness を使うため、キー欠落・`null`・`0`・空文字列を false と同一視して `"none"` sentinel を受理する。[decide-verdict.py:1027](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027>)。封印前に manifest が改変された場合、Phase 4 を省略して CONSISTENT に到達し得る。

   推奨修正: 双方向判定より前に `phase4Required` が厳密な JSON boolean であることを gate で検査し、欠落・null・数値・文字列を REFUSED にする。

4. **Major — 双方向検査と taint／quarantine の非干渉をテストできない**

   根拠: 正常 producer については、`phase4Required=false`＋Phase 4 evidence が存在する正当経路は見つからない。preflight は必要なら同時に Phase 4 も true となり、通常 producer は true の場合だけ Phase 4 evidence を書く。[start-run.py:240](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:240>)、[SKILL.md:657](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:657>)。一方、taint は通常 gate より前の独立経路であり、履歴隔離も Phase 4 とは独立している。[decide-verdict.py:666](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:666>)、[decide-verdict.py:834](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:834>)。S7 は通常 gate の逆方向ケースしか要求しないため、双方向検査を共通前処理へ誤配置して early-taint を壊しても識別できない。[PLAN.md:182](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:182>)。

   推奨修正: config/history early-taint と、空 impact＋corrupt history＋`phase4:"none"` の隔離成功ケースを無回帰テストに追加する。

5. **Major — 新規 library と 0.17.0 版上げに対する既存テストの棚卸しが不足している**

   根拠: `docaudit_review.py` を追加すると、内部ファイル数を 44 に固定し、英日 ADOPTION のファイル一覧との完全一致を要求する既存テストが必ず失敗する。[test_v0131_docs_contracts.py:53](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0131_docs_contracts.py:53>)。さらに現行版を `0.16.0` に固定した箇所が `test_scaffold.py`、版面一致テスト、harness stamp 契約に残っている。[test_scaffold.py:192](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_scaffold.py:192>)、[test_scaffold.py:337](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_scaffold.py:337>)、[test_v013_contracts.py:187](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:187>)、[test_v016_contracts.py:829](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:829>)。S7 はこれらを列挙していない。[PLAN.md:174](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:174>)。

   推奨修正: S7 に `test_v0131_docs_contracts.py`・`test_v013_contracts.py`・`test_scaffold.py`・該当 v0.16 stamp 検査、および英日 ADOPTION のファイル一覧更新を明記する。

6. **Minor — `REVIEW_COMMANDS_JSON` の用途が S2 と registry で再び矛盾している**

   根拠: S2-1 は getter を security 専用とし、legacy は planner の `command` に一本化している。[PLAN.md:92](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:92>)。しかし §9.2 は依然として「security 実行値・legacy 実行値の供給源」としている。[PLAN.md:284](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:284>)。このままでは CT が誤った二重供給を固定し得る。

   推奨修正: §9.2 の消費先を security 実行値だけに訂正する。

7. **Minor — §9.8 の「全数表」に到達可能な P1/P3＋false 行がない**

   根拠: 空 diff かつ `reviewCommands` 未設定、または code 未設定では、P1/P3＋`phase4Required=false`＋`phase4:"none"` が通常到達する。しかし表は P1/P3 の true 行しか持たない。[PLAN.md:298](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:298>)。S7 が表を正本として生成されると、この正常経路が未検査になる。

   推奨修正: P1/P3＋false＋`"none"`＋codeReview キーなしを正常行として §9.8 に追加する。

| 区分 | 指摘 |
|---|---|
| PLAN 自体の欠陥 | #1、#2、#3、#6、#7 |
| worker 指示で吸収できる細部 | #4、#5 |

補足裁定として、`false ⇔ "none"` 自体は既存の正常 evidence・preflight・taint・quarantine 経路と両立する。また `docaudit_review.py` は複製版 `scripts/check-docs.py` の依存ではないため、check-docs-engine のハッシュ対象追加は不要である。ファイルへの修正は行っていない。