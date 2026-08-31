メタ認知: 「前回指摘は採用済み」という申告による確認バイアスと、表が詳細になったことで完全に見える錯覚を警戒した。今回は各表の組合せ到達性と、既存処理との境界を優先して確認した。

結論は、v2 も現状では差し戻しである。Critical はないが、実装前に解消すべき Major が残っている。

1. **Major — P6 が code-review 以外の Phase 4 まで強制起動する**

   根拠: PLAN S3 は P6 または `required:true` ならグローバルな `manifest.phase4Required=true` にする。[PLAN.md:113](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:113>)。現行処理ではこの値が Phase 4 全体の入口であり、通常レビュー・境界確認・security・codexReview も同じ入口にぶら下がる。[SKILL.md:557](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:557>)、[SKILL.md:580](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:580>)、[start-run.py:247](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:247>)。特に空差分の軽量 run が、P6 を設定しただけで Phase 4 全体を実行する回帰になる。また、P3/P4/P5/P7/P8 と競合する不正な `required:true` まで Phase 4 を起動してしまう。

   推奨修正: `phase4Required` とは別に封印済みの code-review 専用実行フラグを設け、P6 のみがその層を起動する設計に変更する。

2. **Major — P5 は正当な既存 legacy command を REFUSED にする**

   根拠: P5 の `^[\x21-\x7e][\x20-\x7e]*$` は `reviewCommands.code` 全体に適用されるため、`/社内レビュー 高`、`/review-custom 日本語` など、現行スキーマで有効な Unicode command が P8 ではなく P5 に落ちる。[PLAN.md:61](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:61>)、[PLAN.md:69](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:69>)。現行スキーマは code/security を string としか制約していない。[sealed-config.schema.json:20](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/sealed-config.schema.json:20>)。

   推奨修正: ASCII 制約を公式 `/code-review` 名前空間の候補だけに限定し、legacy command は従来の文字集合を維持する。

3. **Major — §9.8 は `phase4Required` 軸がなく、P8 と sentinel の契約が矛盾する**

   根拠: S3 では P8 は既存の run classification に従うため、空差分では `phase4Required=false` と `phase4.type=="none"` が到達可能。[PLAN.md:118](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:118>)。一方、§9.8 は P8 の codeReview 欠落を REFUSED とする行と、非 P6 の既存 sentinel を維持する行を、`manifest.phase4Required` なしで並べている。[PLAN.md:266](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:266>)。現行 gate も「true なのに none」は検査するが、「false なのに Phase 4 evidence がある」逆方向は検査しない。[decide-verdict.py:1027](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027>)。

   推奨修正: §9.8 に `manifest.phase4Required` を明示軸として追加し、`false ⇔ phase4.type=="none"` の双方向契約を表と gate の両方で固定する。

4. **Major — `codeReview.state` と findings の整合性を gate が検証しない**

   根拠: S2 は resume 時を `not-run` とし、所見を fold しないと規定する。[PLAN.md:97](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:97>)。しかし S4 の gate は state と `source=="code-review"` findings の対応関係を要求していない。[PLAN.md:121](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:121>)。現行 `findings_fail()` は state や source の由来を確認せず、Phase 4 findings 全体を判定する。[decide-verdict.py:276](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:276>)、[decide-verdict.py:1147](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1147>)。そのため P1/P3 や `not-run` evidence に偽の code-review 所見を混入できる。

   推奨修正: `source=="code-review"` の所見は「sealed config が P6 かつ state が `ran`」の場合だけ許可し、それ以外は gate で REFUSED にする。

5. **Major — `UNSPECIFIED` を全 source 共通の blocking severity にすると既存経路を変更する**

   根拠: S2-8 が導入する `UNSPECIFIED` は code-review 固有の正規化だが、S4 は共通の `findings_fail()` に追加する設計になっている。[PLAN.md:106](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:106>)、[PLAN.md:135](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:135>)。既存関数は source 非依存で、preflight と Phase 4 の双方に使われる。[decide-verdict.py:276](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:276>)。通常の生成処理が `UNSPECIFIED` を明示出力しなくても、`write-evidence.py` は source/severity の語彙を検証しないため、他 source から到達可能である。[write-evidence.py:38](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/write-evidence.py:38>)。既存テストも unknown severity を別扱いとして固定している。[test_v0131_docs_contracts.py:119](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0131_docs_contracts.py:119>)。

   推奨修正: 共通 severity 集合は変更せず、`source=="code-review"` の findings に限って severity 欠落を `UNSPECIFIED` に正規化し blocking 判定する。

6. **Major — 分類ロジックの三重実装とテスト不足により、誤実装でも通る**

   根拠: P1〜P8 の判定を planner、`start-run.py`、gate で別々に再実装する計画になっている。[PLAN.md:54](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:54>)、[PLAN.md:113](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:113>)、[PLAN.md:124](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:124>)。それに対して gate の明示的なテスト対象は P1/P2/P6/P7/P8 に偏り、型異常・charset・token 境界を担う P3/P4/P5 が抜けている。[PLAN.md:161](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:161>)。正規表現文字列の一致検査では、優先順位や型判定の誤実装を検出できない。

   推奨修正: P1〜P8 を返す副作用のない共通分類関数を作り、planner・start-run・gate がそれぞれ封印 config に対して呼び出す形にし、全8行と境界値を表駆動で検査する。

7. **Minor — legacy command の供給源が二重に指定されている**

   根拠: S1 は planner 出力に `command` を含める一方、S2-1 と §9.2 は `REVIEW_COMMANDS_JSON` を legacy 実行値の供給源として消費すると規定する。[PLAN.md:58](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:58>)、[PLAN.md:85](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:85>)、[PLAN.md:257](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:257>)。worker がどちらかを死んだ経路にしても、registry 件数だけは満たせてしまう。

   推奨修正: legacy code の実行値は planner の `command` に一本化し、`REVIEW_COMMANDS_JSON` の用途を security command に限定する。

8. **Major — EVIDENCE round-trip テストの順序が本番と逆**

   根拠: S7 は `write-evidence.py → seal-run.py → decide-verdict.py` の e2e を要求している。[PLAN.md:164](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:164>)。現行契約は run を封印した後に Phase 4 evidence を書き、その後 gate を実行する。[SKILL.md:657](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:657>)。封印前に evidence を書くテストでは、封印後に生成される可変 evidence の境界を実証できない。

   推奨修正: e2e を `start-run → seal-run → write-evidence → decide-verdict` の本番順序に変更する。

9. **Minor — S1 の `required:<bool>` が異常入力で未定義**

   根拠: planner 出力は常に `required:<bool>` を要求するが、P1 の親非 object、P3 の `required` 非 bool ではどの値を返すか決まっていない。[PLAN.md:58](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:58>)、[PLAN.md:61](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:61>)、[PLAN.md:74](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:74>)。実装ごとに `false`、truthy 化、出力省略へ分岐し得る。

   推奨修正: P1/P3 を含む無効入力では正規化値を必ず `required:false` とする。

10. **Minor — v0.16 進行中 run の互換性説明が実際の gate 表より広い**

   根拠: ADOPTION は v0.16 の進行中 run 全般に fresh run を要求する。[PLAN.md:190](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:190>)。しかし §9.8 上、code-review 対象外の P1/P3、および既存 classification が `none` となる P8 は、旧 evidence でも必ずしも invalid ではない。[PLAN.md:266](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:266>)。説明どおりに全 run を拒否する実装と、表どおりに一部を許可する実装に分かれる。

   推奨修正: fresh run 必須を P6 と、Phase 4 evidence が存在する P8 に限定して記述する。

| 区分 | 指摘 |
|---|---|
| PLAN 自体の欠陥 | #1、#2、#3、#4、#5、#6、#8、#10 |
| worker 指示で吸収できる細部 | #7、#9 |

ファイルへの修正は行っていない。