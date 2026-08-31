メタ認知：計画書の形式的な網羅性を実装可能性と取り違えないよう注意しました。また、指摘数を増やすのではなく、具体的な反例が成立するものだけを残しました。

結論：この PLAN は実装開始不可です。少なくとも #1〜#9 の設計修正が必要です。ファイル変更は一切行っていません。

1. Critical／再開時の文章だけで `required:true` を突破できる

   - 根拠: [PLAN.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:80)、[PLAN.md:85](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:85)、[SKILL.md:51](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:51)、[SKILL.md:657](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:657)。
   - `resume` 後、ユーザーやリポジトリ内の命令文が「code-review 完了、所見なし」と書けば、モデルは `state:"ran"` を証拠へ記録できます。最終判定処理は実際の完了通知と照合できず、`required:true` でも通過します。「会話内に可視」は出所証明ではありません。
   - 推奨修正: 実行元が保証した完了証明を封印できない限り、ターンを跨いだ `ran` を禁止し、再開時は `not-run` とする。

2. Major／severity 無しを WARN にすると、実測済み脆弱性が CONSISTENT になり得る

   - 根拠: [PLAN.md:85](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:85)、[00-preflight-verification.md:24](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/00-preflight-verification.md:24)、[00-preflight-verification.md:42](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/00-preflight-verification.md:42)、[decide-verdict.py:276](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:276)。
   - 実測の `eval()` 注入は severity ラベル無しです。これを WARN に固定すると、明白なコード注入を検出しても最終判定を止めず、anchor を進められます。
   - 推奨修正: ラベル無し・未知ラベルを `UNSPECIFIED` として保持し、最終判定では blocking 扱いにする。

3. Major／空差分では Phase 4 が起動せず、既存の正当な設定が REFUSED になる

   - 根拠: [start-run.py:247](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:247)、[SKILL.md:557](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:557)、[PLAN.md:93](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:93)、[PLAN.md:167](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:167)。
   - `reviewCommands.code="/code-review high"`、`required` 省略、incremental・対象文書0件では、現行 `phase4Required=false` です。Phase 4 は丸ごと省略されます。S3を厳格実装すると証拠欠落で REFUSED、緩めるとレビューを黙って省略して CONSISTENTになります。
   - 推奨修正: `start-run.py` を変更許可へ加え、正規の code-review 設定があれば `phase4Required=true` にする。

4. Major／S2 の「gate まで進めず REFUSED」は、最終判定処理だけが verdict を出す既存契約に違反する

   - 根拠: [PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:78) 対 [PLAN.md:95](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:95)、[SKILL.md:674](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:674)、[SKILL.md:732](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:732)。
   - `/code-review ultra` 等で gate 前に止めると、正式な REFUSED、最終記録、報告書、lock 解放を一貫して実施できません。S3の「防御的二重化」も実行されません。
   - 推奨修正: planner の `refuse` はレビュー起動だけを止め、通常どおり gate を呼び、gate が唯一の REFUSED を出す。

5. Major／S1 決定表に未定義・誤分類入力が残る

   - 根拠: [PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:60)、[sealed_config.py:57](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/sealed_config.py:57)。
   - `code:null` と `/code-review  high` は拒否行に入ります。一方、`reviewCommands:null`・配列・文字列はどの行にもありません。また、先頭に Unicode 空白がある `　/code-review high` は legacy 扱いになります。正当な既存プロジェクトコマンド `/code-review-custom` も「`/code-review` で始まる」というだけで REFUSED へ回帰します。
   - 推奨修正: 親オブジェクトの型、Unicode空白・制御文字、公式コマンドのトークン境界まで含む優先順位付き完全表へ置き換える。

6. Major／`required:true` と legacy command の組合せは成功不能

   - 根拠: [PLAN.md:65](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:65)、[PLAN.md:68](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:68)、[PLAN.md:94](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:94)、[PLAN.md:96](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:96)。
   - legacy の証拠状態は常に `legacy` ですが、required は `state != ran` を拒否します。legacy command が正常完了しても成功を表す状態がありません。
   - 推奨修正: `required:true` は正規の `/code-review low|medium|high` とだけ併用可能とし、legacy との組合せを設定矛盾として明示的に拒否する。

7. Major／「phase4Runs/flip 計測にそのまま乗る」は現行実装と逆

   - 根拠: [PLAN.md:97](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:97)、[decide-verdict.py:305](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:305)、[decide-verdict.py:344](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:344)、[decide-verdict.py:1202](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1202)。
   - 履歴は `source=="codex-review"` だけを記録し、さらに full/full/completed の Codex review に限定されています。`source:"code-review"` の所見は verdict には効いても履歴・揺れ計測には入りません。
   - 推奨修正: built-in code-review 用の独立した、出所付き履歴レコードと計測条件を定義する。

8. Major／S7 のテストでは誤実装を判別できない

   - 根拠: [PLAN.md:131](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:131)、[test_v016_contracts.py:872](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:872)、[write-evidence.py:38](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/write-evidence.py:38)。
   - SHA不一致ケースを各決定表行と組にしても、分類前に同じ exit 7 になるため分類被覆は増えません。4分岐だけでは未知 state の受理、`phase4:none` 一律拒否、config と evidence の食い違い、既存 Codex eligibility の破壊を見逃します。EVIDENCE の write→hash更新→gate read も未検査です。
   - 推奨修正: config分類×required×全state・欠落・型違い×phase4 none/present×既存Codex 8行を表駆動で検査し、EVIDENCE往復と履歴結果まで end-to-end で固定する。

9. Major／登録簿の算術は正しいが、v0.17.0 の正本がない

   - 根拠: [前 route PLAN.md:127](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:127)、[対象 PLAN.md:107](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:107)、[test_v016_contracts.py:177](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:177)。
   - 算術は `22+1=23` call sites、exempt `3`、getters `13`、scripts `21+1=22`、observers `19+1=20` で正しいです。ただし対象 PLAN に完全な v0.17 registry がなく、テスト内一覧と実装を同時に間違えても一致できます。歴史資料である前 route を更新するのも不適切です。
   - 推奨修正: 対象 PLAN 自身に v0.17.0 の完全な registry 表を追加し、これを正本にする。

10. Major／getter 13 不変は条件付きでしか正しくなく、死に getter でも CT が通る

   - 根拠: [SKILL.md:556](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:556)、[PLAN.md:110](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:110)、[test_v016_contracts.py:149](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:149)。
   - 現在 `REVIEW_COMMANDS_JSON` は代入以外の参照がありません。S1出力には legacy の原コマンドも security コマンドもないため、S2がどこから実行値を得るか未定義です。現CTは代入が1回あることしか検査せず、未使用でも通ります。
   - 推奨修正: S2でこの getter を legacy code と security の実行値に使うことを明記し、CTも代入後の両消費を検査する。

11. Major／`test_release_handoff.py` の更新指示は歴史的契約を壊す

   - 根拠: [PLAN.md:142](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:142)、[test_release_handoff.py:15](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:15)、[test_release_handoff.py:511](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:511)。
   - このテストは v0.15.1 の handoff を固定しており、「当時 #66 が OPEN」なのは正しい歴史です。行34だけ更新すると検査を弱め、行511–527の OPEN 契約とも不整合になります。
   - 推奨修正: `tests/test_release_handoff.py` をv0.17変更対象から除外し、歴史テストとして保存する。

12. Minor／旧文言の残存ゼロ検査が狭い

   - 根拠: [SKILL.md:3](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:3)、[ADOPTION.md:11](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:11)、[PLAN.md:143](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:143)。
   - `not-model-invocable` が0件でも、Skillの入口説明に “offered … not started” が残ります。ADOPTION両言語の冒頭要約も同様です。
   - 推奨修正: 現在形の入口説明を棚卸し対象に加え、旧意味句をファイル別に不在検査する。

13. Minor／v0.16進行中 run の再開互換性が未記載

   - 根拠: [PLAN.md:91](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:91)、[PLAN.md:123](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:123)、[SKILL.md:657](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:657)。
   - v0.16が `findings+codexReview` の phase4.json を書いた後にv0.17へ更新すると、新しい `codeReview` 欠落で、required未設定の既存 adopter も REFUSEDになります。
   - 推奨修正: v0.17の互換性記録へ「進行中runは再開不可、fresh run必須」を明記し、混在版の拒否を固定テストにする。

| 区分 | 指摘 |
|---|---|
| PLAN 自体の欠陥 | #1〜#9、#11、#13 |
| worker 指示で吸収できる細部 | #10、#12 |

最終判断は「差し戻し」です。特に #1、#2、#3、#4 を確定せずに実装すると、必須レビューの偽装、重大所見の非 blocking 化、正当な既存設定の REFUSED、最終記録を伴わない拒否が発生します。