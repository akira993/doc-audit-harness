メタ認知: 対応件数の多さから「収束済み」と判断するバイアスと、既指摘を言い換えて再掲するバイアスを除外した。以下は rev.4 で新たに生じた、または初めて確認できた欠陥だけである。

結論として、裁定2には異議あり。裁定9は「歴史テストを不変にして新規側へ複製する」方針には異議なしだが、複製範囲には異議がある。

## 新規指摘

### 1. Codex の rebind を表示専用にすると、resume 後の Phase-4 が実行不能

重大度: High

根拠:

- PLAN は Codex の rebind 値を表示専用にする（[PLAN.md:84](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:84)）。
- checkpoint が持ち越すのは `RUNID` と `EVIDENCE` だけで、availability/reason/bin は含まれない（[SKILL.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:41)、[SKILL.md:50](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:50)）。
- planner には `CODEX_REVIEW_AVAILABLE` と `CODEX_REVIEW_REASON` が必要（[SKILL.md:577](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:577)）、実起動には `CODEX_REVIEW_BIN` が必要（[SKILL.md:600](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:600)）。
- rev.4 の planner 出力追加は model/timeout だけである（[PLAN.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:67)）。

checkpoint (g) 以前から resume すると、これら3値が未束縛になる。

推奨修正: resume 時に Codex probe を封印SHA照合付きで再実行し、available/reason/bin を再束縛してから planner を呼ぶ単一経路にする。

### 2. 裁定2の「ax は verdict に一切影響しない」という前提は誤り

重大度: High

根拠:

- PLAN は verdict 非影響を理由に、ax の封印照合を不要とする（[PLAN.md:86](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:86)）。
- `AX_AVAILABLE` は Phase-3 Workflow に渡される（[SKILL.md:481](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:481)）。
- true の場合、外部URLを ax で照合する指示が verifier prompt に追加される（[workflow-template.js:122](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:122)、[workflow-template.js:153](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:153)）。
- verifier の FAIL は最終 verdict を `NEEDS_FIX` にする（[workflow-template.js:156](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:156)、[decide-verdict.py:894](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:894)）。

「fetch失敗だけではFAILにしない」は、成功した照合結果が矛盾の証拠にならないという意味ではない。また、攻撃者が ax を直接実行できることと、その結果を監査の信頼済み判断経路へ入れられることは同値ではない。

推奨修正: fresh/resume とも ax probe のtool起動前に `EVIDENCE.config` と生bytesのSHA一致を必須化し、不一致は停止させる。

### 3. Codex の封印確認が Phase-0 より遅く、一時変更された `bin` を実行できる

重大度: High

根拠:

- Codex probe は live config から `bin` を取得する（[codex-probe.sh:24](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:24)）。
- その bin を `--version` と `exec --help` で実行する（[codex-probe.sh:79](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:79)）。
- 同じ値が Phase-4 の実行ファイルとして使われる（[SKILL.md:175](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:175)、[SKILL.md:600](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:600)）。
- rev.4 のSHA照合は後段 planner にしかなく、検証済み出力にも bin がない（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:61)）。

Phase-0 の間だけ `codexReview.bin` を別実行ファイルへ変更して復元すれば、planner のSHA検査は通るが、別binは既に実行されている。

推奨修正: 通常auditの Codex probe 自体に `EVIDENCE` を渡し、SHA一致した設定から得たbinだけをtool起動・Phase-4へ使用する。

### 4. SHA不一致時の手動 release が既存の config 変更承認機構を迂回する

重大度: High

根拠:

- PLAN は planner 不一致時に gate を呼ばず、runをreleaseして停止する（[PLAN.md:63](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:63)）。
- 現行gateは不一致時に `reason:"config-changed"` と `expectedConfigSha` を保存する（[decide-verdict.py:699](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:699)、[decide-verdict.py:1005](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1005)）。
- 次回 `open-run` が明示承認を要求するのは、この保存記録がある場合だけである（[open-run.py:163](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:163)）。

planner が先にreleaseすると taint 記録が残らず、変更後configを `--accept-config` なしで次runに採用できる。

推奨修正: SHA不一致時は既存gateを直ちに呼び、`config-changed` のREFUSED記録とlock解放を既存経路に一元化する。

### 5. planner 異常終了後の停止・release・evidence非書込みが未検証

重大度: High

根拠:

- PLAN は異常終了時に Phase-4 evidence を書かずreleaseすると要求する（[PLAN.md:63](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:63)）。
- planner 試験は非0終了までしか固定しない（[PLAN.md:151](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:151)）。
- SKILL配線試験も `--evidence` とconfig再読不在だけである（[PLAN.md:169](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:169)）。
- 現行の終端経路はrelease必須（[SKILL.md:70](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:70)）で、Phase-4 evidence書込みは後段に存在する（[SKILL.md:620](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:620)）。

releaseを実装し忘れてlockが残る実装でも完了条件を通る。

推奨修正: SHA不一致で config-taint記録・releaseが各1回、Codex起動とPhase-4 evidence書込みが各0回になる一体テストを追加する。

### 6. 旧 rebind 契約テストが正しい rev.4 実装を拒否する

重大度: High

根拠:

- rev.4 は axを再probeし、Codex rebindも表示専用に変える（[PLAN.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:80)）。
- 現行テストは「Phase 4 may restore ... availability, reason, or binary variables from rebind」という旧文言を完全一致で要求する（[test_v014_contracts.py:222](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:222)、[test_v014_contracts.py:227](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:227)）。
- PLANの既存契約更新一覧はこの断言を対象に含めていない（[PLAN.md:171](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:171)）。

推奨修正: この現行断言を v0.15 契約へ移し、fresh/resumeそれぞれの運用値の取得元を直接固定する。

### 7. planner の既存16行判定表を削除しても完了条件を満たせる

重大度: High

根拠:

- PLAN はキー存在時の v0.14 意味論を不変とする（[PLAN.md:10](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:10)）。
- 現行テストは availability×mode×required×baseline の16組を網羅する（[test_codex_review_plan.py:30](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:30)）。
- rev.4 の完了条件は planner を「≥12ケース」とし、full-mode 4構成を中心に数える（[PLAN.md:147](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:147)、[PLAN.md:202](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:202)）。

incrementalのbaseline true/falseやavailabilityとの組合せを削っても合格できる。また既存成功呼出しは新しい必須evidenceを渡していない（[test_codex_review_plan.py:41](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:41)）。

推奨修正: 既存16行表を削除禁止とし、全行へ正しいEVIDENCEと新出力フィールドを加えた上で、rev.4追加ケースを上乗せする。

### 8. 裁定9の安全停止テストは複製対象が不足している

重大度: High

歴史テストを変更せず、新規ファイルへ複製する方針には異議なし。ただし5条件だけでは不足する。

根拠:

- PLANが複製するのは不正SHA・branch・dirty・HEAD・同期先だけ（[PLAN.md:191](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:191)）。
- 既存契約にはさらに fetch失敗（[test_release_handoff.py:306](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:306)）、origin/main不一致（[test_release_handoff.py:334](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:334)）、テストスイート失敗（[test_release_handoff.py:355](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:355)）、誤った既存tag（[test_release_handoff.py:363](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:363)）、不正な既存Release（[test_release_handoff.py:371](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:371)）がある。

v0.15 scriptは独立コピーなので、これらを落としてもv0.14テストは検出しない。

推奨修正: 共通化は不要だが、既存の公開前・再実行境界ケース集合を全件v0.15テストへ複製する。

### 9. `model` 出力だけでは既存retry契約を保存できない

重大度: Medium

根拠:

- PLANが出力に追加するのは `model` と `timeoutMs` だけ（[PLAN.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:67)）。
- 現行はconfig明示modelと既定modelを区別する（[SKILL.md:583](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:583)）。
- 明示modelはretryせず、light既定の Luna だけ Terraへ1回retryする（[SKILL.md:606](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:606)）。

明示 `"model":"gpt-5.6-luna"` とlight既定Lunaを最終model文字列だけでは区別できない。加えて、model/timeoutの空・型違い・非正数に対する意味論も未定義で、試験はhappy path 2件だけである（[PLAN.md:154](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:154)）。

推奨修正: planner出力schemaに `modelSource:"config"|"default"` と値検証規則を追加し、明示Luna・既定Luna・不正値を同じ判定表で固定する。

### 10. v0.14 resume の旧Codex recordが Phase-5表示とcaller情報を汚染する

重大度: Medium

根拠:

- Phase-4が保存するCodex情報は stateだけである（[SKILL.md:620](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:620)）。
- rebindは旧recordのreason・available・caller情報をそのまま復元する（[probe-record.py:279](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279)）。
- Phase-5はそのreasonを表示し、available=trueならcaller suffixを付ける（[SKILL.md:754](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:754)、[SKILL.md:760](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:760)）。
- plannerによるkeyless正規化は保存済みprobe recordを更新しない（[PLAN.md:84](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:84)）。

v0.14の `reason:ok/available:true` recordを持つkeyless runは、v0.15で `not active (ok)` と旧CODEX_HOMEを表示し、ADOPTIONの「not-configuredへ正規化」と一致しない（[PLAN.md:106](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:106)）。

推奨修正: plannerがkeylessと判断した時点でcanonicalなneutral Codex seamをrecordへ上書きし、Phase-5表示を一体テストする。

### 11. `not-configured` recordに未知フィールドで秘密情報を保存できる

重大度: Medium

根拠:

- PLANはcanonicalな8フィールド形を要求する（[PLAN.md:48](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:48)）。
- `probe-record.py` は必須フィールドを検査するだけでキー集合を制限しない（[probe-record.py:45](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:45)）。
- 入力objectはそのまま保存される（[probe-record.py:327](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:327)、[probe-record.py:334](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:334)）。
- mutation表は既存7フィールドの値変更しか試さない（[PLAN.md:139](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:139)）。

正規8フィールドに `leakedHome:"/secret"` を追加したrecordを受理する誤実装でも通る。

推奨修正: `reason=="not-configured"` ではキー集合を正規8フィールドと完全一致させ、未知フィールド追加も拒否する。

### 12. plannerの責務変更が文書更新範囲から漏れている

重大度: Medium

根拠:

- rev.4では planner がSHA、model、timeoutまで担当する（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:61)）。
- 現行ADOPTIONは「availability、mode、baseline、requiredからactionを決める」とだけ説明する（[ADOPTION.md:133](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:133)、[ADOPTION.ja.md:118](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:118)）。
- config-schemaのPhase-4説明も同じ旧責務のままである（[config-schema.md:250](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:250)）。
- PLANの文書変更はschema表行とwalkthroughに限定され、これらの段落を含まない（[PLAN.md:94](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:94)）。

推奨修正: en/ja ADOPTIONとconfig-schemaのplanner説明を、SHA照合・検証済み実行値・終端失敗まで含む単一の現行契約へ更新する。

### 13. #59非close試験がRelease notesの誤記を検出しない

重大度: Medium

根拠:

- PLANはAPIのclose集合と#59のOPEN状態だけを厳密化する（[PLAN.md:187](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:187)）。
- 雛形のRelease本文検査は必須断片の `assertIn` だけである（[test_release_handoff.py:384](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:384)、[test_release_handoff.py:391](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:391)）。

本文に誤って `Closes #59` を追加しても、API上は#59をOPENのままにして試験を通せる。

推奨修正: Release本文中のclose directive集合も厳密に `{"56"}` とし、#59継続文を固定する。

ファイル変更は行っていない。