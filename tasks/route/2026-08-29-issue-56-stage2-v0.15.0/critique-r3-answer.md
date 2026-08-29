メタ認知: rev.3 の詳細さを「十分な実装保証」と誤認するバイアス、前回指摘の言い換えを新規指摘として水増しするバイアスを警戒した。以下は新たに実測できた欠陥だけである。

裁定2には異議なし。完走済み所見を遡及的に無効化せず、版跨ぎ禁止を #59 の単一機構に集約する判断は妥当である。実際、#59 は manifest への版記録と両方向混在テストを要求している（[59-design-note.md:27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/59-design-note.md:27)）。

## 新規指摘

### 1. SHA 不一致が通常の `not-active` として処理され、Codex review を回避できる

重大度: High

根拠:

- PLAN は不一致時を `action:"not-active"/reason:"config-changed"` とする（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:60)）。
- `not-active` は所見なしで正常継続する状態である（[SKILL.md:578](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:578)）。
- その状態は Phase-4 evidence に保存される（[SKILL.md:620](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:620)）。
- 最終判定はその時点で設定が復元されていれば SHA 一致として通る（[decide-verdict.py:699](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:699)）。`required:false` では `completed` でなくても拒否されない（[decide-verdict.py:797](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:797)）。

したがって、planner 実行時だけ設定を変更し、直後に復元すれば、明示 opt-in 済みの review を省略して判定できる。Phase-5 も probe 側の理由を表示するため `not active (ok)` になり得る（[SKILL.md:754](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:754)）。

推奨修正: `config-changed` は非0終了の終端エラーとし、Phase-4 evidence を書かず run を解放して停止させる。

### 2. webExtract の resume 正規化には、封印済み設定を判定する実装手段がない

重大度: High

根拠:

- PLAN は SKILL の一文だけで「封印済み config にキーが無ければ正規化」とする（[PLAN.md:73](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:73)）。
- resume が保持する `EVIDENCE` には設定内容ではなく SHA しかない（[SKILL.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:41)、[open-run.py:221](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:221)）。
- manifest にも `webExtract` のキー有無は保存されない（[start-run.py:262](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:262)）。
- resume 後の Workflow は復元された `AX_AVAILABLE` を直接使用する（[SKILL.md:481](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:481)）。
- SHA 照合を伴う hard gate は Codex planner にしか計画されていない（[PLAN.md:57](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:57)）。

live config に一時的にキーを追加すれば、旧 probe の `available:true` から ax を起動し、最終判定前に復元できる。

推奨修正: AX を rebind する前にも同一 bytes の SHA 照合とキー判定を行う決定論的スクリプトを置き、不一致は停止させる。

### 3. Codex planner の SHA 確認後に生 config を再読する競合窓が残る

重大度: High

根拠:

- PLAN が照合するのは planner 時点の bytes とキー判定だけである（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:60)）。
- planner 成功後、`codexReview.model` を config から再取得する（[SKILL.md:583](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:583)）。
- `timeoutMs` も同様に再取得する（[SKILL.md:605](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:605)）。
- manifest はこれらを封印していない（[start-run.py:262](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:262)）。

planner 後だけ timeout を短縮するなどして review を失敗させ、gate 前に設定を復元できる。

推奨修正: planner が照合済み bytes から model・timeout を検証済み出力として返し、Phase-4 は以後 config を再読しない。

### 4. `--evidence` の必須配線を保証するテストがない

重大度: Medium

根拠:

- PLAN の追加試験は planner 単体の一致・不一致のみである（[PLAN.md:123](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:123)）。
- 現行 planner 試験の全呼出しは `--evidence` を渡さない（[test_codex_review_plan.py:21](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:21)、[test_codex_review_plan.py:42](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codex_review_plan.py:42)）。
- SKILL 配線試験も availability 引数しか確認しない（[test_v013_contracts.py:70](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:70)）。

`--evidence` を任意引数にした誤実装や、SKILL の呼出しだけ更新し忘れた実装が通り得る。

推奨修正: evidence 省略を失敗として固定し、Phase-4 の実呼出し文字列に `--evidence "$EVIDENCE"` があることを契約テストで直接 assert する。

### 5. probe→planner 一体テストが `required:true` の意味を判別できない

重大度: Medium

根拠:

- PLAN は4設定を列挙するが、mode・baseline・期待 action を定めていない（[PLAN.md:126](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:126)）。
- `required:true` と `{}` の差が現れるのは full mode である（[codex-review-plan.py:35](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:35)）。incremental＋有効 baseline では双方 `run/diff` になる（[codex-review-plan.py:41](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:41)）。

推奨修正: 一体テストを full mode・baseline false に固定し、4設定それぞれの action/state/reason/promptVariant を完全一致で検査する。

### 6. 生 bytes の SHA 契約をテストしていない

重大度: Medium

根拠:

- PLAN は明確に config「bytes」の SHA を要求する（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:60)）。
- しかし試験仕様は単に「書き換えた config」としか定めない（[PLAN.md:128](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:128)）。

JSON を読み直して正規化してから hash する誤実装でも、値を変更した試験だけなら通る。

推奨修正: JSON の意味は同一だが空白・改行・キー順だけが異なる config を不一致ケースとして固定する。

### 7. `not-configured` の一括相関検証が1件の拒否試験で通ってしまう

重大度: Medium

根拠:

- 実装契約は available、bin、version、commands、caller 3値を同時に固定する（[PLAN.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:52)）。
- 完了条件は矛盾拒否を「≥1」にしかしていない（[PLAN.md:167](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:167)）。

例えば caller home だけ検査し、version・commands・auth を検査しない実装でも、その1 fixture 次第で通る。

推奨修正: 正常レコードから各連動フィールドを1つずつ変える mutation 表を作り、全フィールドの拒否を個別に固定する。

### 8. 歴史契約テストの隣接断言が残り、正しい v0.15 実装が失敗する

重大度: High

根拠:

- PLAN は `not-configured` の件数を3→5へ変える指定だけである（[PLAN.md:146](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:146)）。
- 同じ現行テストは、`not-configured` を含む全段落が3 seam の名前に一致することも要求している（[test_v0132_contracts.py:300](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:300)、[test_v0132_contracts.py:304](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:304)）。

webExtract/codexReview の正しい新段落は `symbolGraph|docGraph|semanticSearch` に一致せず、フルスイートが落ちる。

推奨修正: 件数だけでなく対象 seam 集合も5種へ更新し、この現行断言を `test_v015_contracts.py` に移す。

### 9. 新 release-handoff の安全停止条件が未検証

重大度: High

根拠:

- PLAN は v0.15 用スクリプトを独立に作る一方、既存 v0.14 テストを変更禁止とする（[PLAN.md:151](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:151)）。
- 新試験は成功・再実行・#59 非close を中心とした5件以上に留まる（[PLAN.md:155](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:155)、[PLAN.md:169](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:169)）。
- 既存試験には不正SHA、別branch、dirty tree、HEAD不一致、範囲外・symlink同期先などの公開停止条件がある（[test_release_handoff.py:289](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:289)、[test_release_handoff.py:313](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:313)、[test_release_handoff.py:341](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:341)）。

v0.15 のコピーで防御を落としても v0.14 テストは検出しない。

推奨修正: 公開前の安全停止契約を共通テスト化し、v0.14/v0.15 の両スクリプトへ同じケース群を適用する。

### 10. 残骸ゲートの件数一致は全ファイル走査を証明しない

重大度: Medium

根拠:

- PLAN の完全性条件は「走査ファイル数＝対象 tracked 数」だけである（[PLAN.md:136](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:136)、[PLAN.md:172](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:172)）。

1ファイルを飛ばして別ファイルを二重走査しても件数は一致する。同じ誤った絞り込み処理から「対象数」と「走査対象」を生成した場合も偽陽性になる。

推奨修正: `git ls-files` から独立に作った期待 path 集合と、実際に走査した一意な path 集合を完全一致で assert する。

### 11. seam 名「近接」判定は README の現物では偽陽性か偽陰性になる

重大度: Medium

根拠:

- PLAN は seam 名の近接で mdq/contextMode の正当な `auto-used` を除外する（[PLAN.md:136](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:136)）。
- README は context-mode、ax、codex を同じ1行・同じ段落に記載している（[README.md:25](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:25)）。

行・段落単位では正当な context-mode 文言を誤検出し、README 全体を除外すれば ax/codex の再混入を見逃す。

推奨修正: README の Optional 項目を1 seam 1行へ分離し、残骸ゲートも seam 単位の行を検査する。

### 12. `--config` の値欠落が probe の単体入力防御から漏れている

重大度: Low

根拠:

- 現行両 probe は `--config` の直後に無条件で `$2` を参照する（[ax-probe.sh:15](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:15)、[codex-probe.sh:16](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:16)）。
- `set -u` のため `--config` 単独では JSON を emit せず終了するが、ヘッダは「ALWAYS emit JSON + exit 0」を契約している（[ax-probe.sh:9](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:9)、[codex-probe.sh:10](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:10)）。
- PLAN の判定表は config 省略・不存在・壊れだけで、option 値欠落を含まない（[PLAN.md:111](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:111)）。

推奨修正: `--config` 値欠落を `invalid-config`・tool起動0回・ASCII JSON 1行・exit 0として両判定表へ追加する。

### 13. ADOPTION 固定文②と裁定2の例外が文面上は矛盾する

重大度: Medium

根拠:

- ②は無条件に「keyless config therefore loses the Phase-4 codex review and findings」と断言する（[PLAN.md:91](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:91)、[PLAN.md:96](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:96)）。
- ③は完走済みの版跨ぎ resume では所見を保持すると定める（[PLAN.md:92](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:92)、[PLAN.md:97](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:97)）。

裁定2自体は妥当だが、固定文②の無条件表現はその裁定を正しく伝えていない。

推奨修正: ②の対象を「新規 run、または codex review 実行前に resume した run」に限定する。

ファイル変更は行っていない。