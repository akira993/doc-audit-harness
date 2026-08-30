メタ認知: rev.4の追加ゲート数ではなく、同じゲートを通過する誤実装を具体的に構成できるかだけで判定した。socket等の追加状態検査は費用対効果が低いため指摘しない。

## 計画自体の欠陥

1／HIGH（前回 #1 対応不十分）／trim同値性を支えるN12が仕様の一部しか検査しない  
根拠: [PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:41) はU+1680、U+2000〜U+200A、U+2028等もtrim対象とするが、N12が実際に試すtrim文字はASCII空白・NBSP・BOMだけである（[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:78)）。例えばU+1680を剥がし忘れる実装は全検査を通る。その場合probeは`U+1680foo`を調べてexportするが、codegraphは[directory.js:85](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/directory.js:85)で`foo`へ再trimし、別ディレクトリを操作する。exportは「保険」にならない。  
推奨: 明記したtrim対象コードポイントすべてと、非対象U+001C〜U+001Fを表駆動N12で検査する。

2／HIGH（前回 #2 対応不十分）／Phase 3の同一環境・同一作業位置という前提がsealed契約にない  
根拠: Workflowへ渡るのはavailabilityだけである（[SKILL.md:213](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:213)、[SKILL.md:484](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:484)）。後段の案内は`cd`も`--path`もない`codegraph impact/node`である（[workflow-template.js:131](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:131)）。codegraphは`--path`未指定なら実行時cwdから索引を探索する（[codegraph.js:1317](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/bin/codegraph.js:1317)、[codegraph.js:1863](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/bin/codegraph.js:1863)）。別agentのenv/cwdが同じという前提を検査するゲートもないため、custom dirをprobeが`ok`としてもPhase 3が既定dirや別rootを見る経路が残る。#63へ持ち越すと、本版の「CODEGRAPH_DIR尊重」はPhase 0だけになる。  
推奨: 本版で解決済みdirとrepo rootをWorkflowへ渡し、後段コマンドをその値で明示実行する。

3／HIGH（前回 #3 対応不十分）／`stdin_eof`は`</dev/null`の有無を区別できない  
根拠: fakeは`sys.stdin.read()==""`を記録するだけで、probeへ非空stdinを渡す規則がない（[PLAN.md:59](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:59)）。現行helperはstdinを指定せず親から継承する（[test_codegraph_probe.py:34](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:34)）。CIで親stdinが既にEOFなら、実装から`</dev/null`を削除しても`stdin_eof=true`となり全テストを通る。対話端末ではfakeが読み待ちして停止し得る。  
推奨: probeへ既知の非空sentinelをstdinから与え、timeoutも設定し、正実装だけがsentinelを遮断するfixtureにする。

4／HIGH（前回 #7 対応不十分）／G10が任意段階の成果物まで必須化し、正しい短期完了をFAILにする  
根拠: [PLAN.md:128](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:128) はforce-add配列の全件追跡を要求するが、[PLAN.md:156](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:156) には任意の`sol-r5`、opus 2回、impl 5回、各out、`codex-review-out.md`まで含まれる。§4は追加実装roundを「不足時」としており、早期に成功した正しい実装ではこれらは存在しない。現時点の実測でもsol-r5/opus/impl/codex-review成果物は不存在である。また§5.6は依然としてglob表記で、具体配列と一致しない（[PLAN.md:109](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:109)）。  
推奨: 必須成果物と任意生成物を分離し、後者は「存在する場合だけ、許可名かつ追跡済み」を検査する。

5／HIGH（前回 #8 対応不十分）／G3＋G12は空でない無意味なテストを通す  
根拠: G3はmethod名と件数だけ、G12は`pass`・docstring・`...`だけを拒否する（[PLAN.md:121](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:121)、[PLAN.md:130](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:130)）。新しい#66テストを`self.assertTrue(True)`にすれば、handoffが#66を確認しなくてもG1/G3/G12をすべて通る。またPRECLOSEDを空にする計画に対し、既存methodは`assertTrue(PRECLOSED)`を要求する（[test_release_handoff.py:428](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:428)）が、その再設計も未指定である。  
推奨: ASTの一般的な「空テスト」判定をやめ、変更対象methodごとに#65 close集合、#59/#63/#66 OPEN条件、preclosed再開動作の必須assertを固定する。

6／HIGH（前回 #14 対応不十分）／G11は許可範囲外の挿入と同一行内の変更を見逃す  
根拠: [PLAN.md:129](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:129) は旧側のhunk範囲だけを見る。許可行3の直後へ新しいfrontmatter行を挿入すると、差分は`@@ -3,0 +4 @@`となり、旧側位置3だけを見れば許可内として通る。また§7はSKILL.md:3の括弧内だけを許可するが、G11は行3全体の変更を許すため、skillの起動条件を同時に改変しても通る。単一行hunkでは`,1`が省略される形式も未定義である。  
推奨: hunk行番号ではなく、許可された旧断片から期待する新断片への具体的な置換内容を比較する。

7／HIGH（前回 #6 対応不十分）／G13は禁止ignored範囲全体とファイル種別・属性を保護しない  
根拠: G13のmanifest対象は`docs/superpowers`と他routeの通常ファイルだけである（[PLAN.md:131](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:131)）。しかし[.gitignore:5](/Users/akiratakahashi/Projects/doc-audit-harness/.gitignore:5) 以降には`.serena/`、`.brv/`、`data/`、`.mdq/`、`.envrc`、`AGENTS.md`等もあり、§7ではすべて許可外である。これらの変更はG8にもG13にも出ない。また`find -type f`＋内容shaではsymlink追加やchmodだけの変更も検出しない。  
推奨: 明示許可した作業物以外のignored全体を、相対パス・種別・mode・symlink先・通常ファイル内容の正規化済みmanifestで比較する。

## worker指示で吸収できる細部

8／MEDIUM／G8のroute接頭辞が追跡済み許可外ファイルまで通し得る  
根拠: [PLAN.md:126](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:126) は許可集合を具体配列＋ディレクトリ接頭辞と定義する。§7では接頭辞を追跡外ファイル用とするが、単純なパス集合として実装すると、`git add -f route/secret.md`も接頭辞で許可される。G10が余分な追跡を拒否するのはlog/revだけなので、この`secret.md`は完了判定を通る。  
推奨: route接頭辞許可を削除し、G8の追跡対象は具体配列だけに限定する。

9／MEDIUM／A2のG2違反fixtureは必ずFAILするとは限らない  
根拠: [PLAN.md:137](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:137) は新規methodを1本コメントアウトするが、仕様は17本「以上」である。実装が18本追加して38件なら、1本消しても37件でG2はPASSし、既存20名称も残る。  
推奨: 下限数ではなく、e1c0b19由来の既存methodを1本一時改名するfixtureに置き換える。

10／MEDIUM／A2のG8 fixtureは今回修正したrename解析を試していない  
根拠: G8の違反fixtureは通常の禁止ファイルへの空行追加だけである（[PLAN.md:137](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:137)）。workerがrev.3の`--name-only`実装を残してもこのfixtureはFAILするため、rename旧名を取得できない誤実装を見分けられない。  
推奨: G8のfixtureを「禁止パスを許可パスへコミット済みrename」にし、旧パス検出を直接確認する。

計画自体を直すべき HIGH の一覧: **1、2、3、4、5、6、7**  
このまま実装に進めてよいか: **進めるべきではない。特にPhase 3の索引整合、G10、G11、G13はworker判断では一意に安全実装できない。**