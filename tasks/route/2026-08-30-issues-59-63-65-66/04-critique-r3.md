メタ認知: v3 の対応表が詳細なため、「列挙済み＝状態遷移も閉じた」と追認するバイアスに注意した。自己申告ではなく、PLAN 本文と現行コードから分岐・件数・互換性を再構成した。

結論は、まだ収束していない。特に acceptance marker の信頼境界と履歴隔離失敗後の回復経路には、設計レベルの穴が残る。

[R3-1] Critical `configAcceptanceRequired` は攻撃者が書き換えられる場所にあり、強制承認として機能しない  
→ 根拠: PLAN は EVIDENCE と plugin engine だけを改竄不能と定義している一方、marker は repo 内の `docaudit-last-run.json` に書く設計である（[PLAN.md:7](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:7)、[PLAN.md:43](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:43)、[PLAN.md:46](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:46)）。現行 `open-run.py` は marker の欠落だけでなく、不正 JSON も `{}` として扱うため fail-open になる（[open-run.py:163](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:163)）。攻撃者は taint 記録後にファイルを削除・破損・false 化でき、次回の `--accept-config` 要求を消せる。  
→ 推奨する修正: acceptance marker を repo 書き込み者が変更できない run-state に置くか、EVIDENCE 由来の鍵で認証し、欠落・破損を acceptance 必須として fail-closed にする。

[R3-2] Major marker 消費と lock 取得が一つの原子的な状態遷移として定義されていない  
→ 根拠: PLAN は「lock 取得成功時に一度だけ false にする」としか定めず、marker 更新失敗、lock 競合、部分書き込み、既存 `runid/reportStatus` の保持、更新後の open 失敗を定義していない（[PLAN.md:43](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:43)）。現行実装では lock 作成と既存 marker の読取りが別処理で、marker の `previousReportStatus` は lock 取得後にも使われる（[open-run.py:193](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:193)、[open-run.py:224](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:224)）。CT-3/CT-4にも書込み障害や部分更新はない（[PLAN.md:75](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:75)）。  
→ 推奨する修正: 「marker 検証→lock 取得→field-preserving な原子的 marker 更新」を一つのトランザクションとして定義し、更新失敗なら open 不成立とする障害テストを追加する。

[R3-3] Major 履歴隔離失敗後に裸の `--break-lock` を許すと、未隔離の tainted history が次 run で正規履歴になる  
→ 根拠: S5 は隔離失敗時に live history と lock を残し、`--break-lock` を回復手段とする（[PLAN.md:47](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:47)）。しかし現行 `--break-lock` は lock を消すだけで、history を隔離も無効化もしない（[open-run.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:87)、[open-run.py:139](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:139)）。次の run は残った history を新しい EVIDENCE.history として封印し、cache/carry-forward に使える（[plan-dispatch.py:91](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:91)、[plan-dispatch.py:150](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:150)）。  
→ 推奨する修正: 隔離失敗を lock とは別の永続ブロック状態として保存し、実際の隔離成功または明示的な `--accept-history` なしには再 open させない。

[R3-4] Major 方針Bの plugin fallback は旧 stamp しか覆わず、`broken`・stamp 欠落・不正・将来版で検査が消える  
→ 根拠: S6 は stamp `<0.16.0` の複製だけを plugin engine に代替する（[PLAN.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:52)）。現行 installed 分岐は生成物が欠けると `broken` にし、plugin generic は非 evidence の診断としてしか動かさない（[SKILL.md:293](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:293)）。その状態で incremental、impacted docs なし、Codex review 不要なら Phase 4 自体が不要になり、判定に入る決定的 docs 検査がなくなる（[start-run.py:240](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:240)、[start-run.py:250](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:250)）。また scaffold は missing/unknown/modified stamp を別状態として扱っており、PLAN の `<0.16.0`/`≥0.16.0` 二分では尽くせない（[scaffold.py:281](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:281)）。将来の `0.17+` を無条件互換とする根拠もない。  
→ 推奨する修正: 直接起動は現 plugin が明示的に互換と認めた stamp と完全な生成物集合に限定し、`broken`・欠落・不正・未知・将来版はすべて plugin engine を required evidence として実行する。

[R3-5] Major §9.5 の N は誤りで、observer の O は意味上の一意な件数になっていない  
→ 根拠: 現 PLAN は N=21 としている（[PLAN.md:179](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:179)）が、旧 stamp 用に新設した plugin `generic-layers.py` fallback は、既存の3呼出しに加わる4番目の静的 call site である。正しい計算は `1+2+5+1+4+1+7+1=22`。一方 O=22 はラベル数としては数えられるが、`open-run` の mismatch は lock 取得前なのに、S5 の taint 記録は owned lock 必須であり、observer として直接記録できない（[PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:41)、[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:45)）。子プロセス mismatch も子 ID と親 funnel ID のどちらを記録するか未定義である。再計数結果は M=4、G=13、K=21は表の定義下で整合する。  
→ 推奨する修正: Nを22へ直し、Oを「検出元ID」と「実際に taint を書く top-level caller ID」に分割した対応表に置換する。

[R3-6] Major CT-1/CT-2 は direct reread と pass-through 欠落を判別できない  
→ 根拠: CT-1(b) は shell の `"$CFG"` だけを対象にするため、`${CFG}`、別変数への alias、固定パスの再構成を捕捉できない（[PLAN.md:73](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:73)）。Python が sealed helper を一度呼んだ後に `json.load(open(args.config))` で再読しても、wrong-SHA テストは最初の検証で終了するため通る。さらに CT-2 の単純な wrong-SHA 対は、親が先に検証する `classify-change.py`、`plan-dispatch.py`、`seal-run.py` について子への SHA pass-through を証明しない（[classify-change.py:29](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/classify-change.py:29)、[plan-dispatch.py:68](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:68)）。CT-3 の差替え対象は gate/seal に限られる（[PLAN.md:75](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:75)）。  
→ 推奨する修正: config ファイルの open を実行時に計測し、親検証後・子起動前に差し替えるテストを全 pass-through 親に適用して、子 argv と exit を検証する。

[R3-7] Major `phase4Runs` 8 KiB 上限は定義済み最大入力と算術的に両立しない  
→ 根拠: S9 は finding 最大50件、file 最大1024文字を許しながら record を8 KiBに固定する（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:61)）。50件すべてが1024文字なら、実測で compact JSON 約53,211 bytes、indent付き約54,543 bytesになり、正当な record が parser round-trip で拒否される。結果は history corruption ではなく、flip/carry-forward の証拠欠落になる。  
→ 推奨する修正: 上限を許容スキーマの実最大以上にするか、書込み前に決定的な byte-budget trimming を行い、最大境界を writer→parser の往復テストで固定する。

[R3-8] Major 50件 cap が flip の観測集合にも適用され、偽陰性・偽陽性を生む  
→ 根拠: S9 は findings を50件に制限し、S10 は保存された record から blocking set を導出する（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:61)、[PLAN.md:63](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:63)）。blocking finding が50件を超えると末尾の解消・再発を観測できない。同順位の選択順・重複排除順も未定義なので、入力順の変化だけで flip が出る可能性がある。CT-5には50件超過や順序変更ケースがない（[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:78)）。  
→ 推奨する修正: carry-forward の表示件数だけを cap し、flip 用集合は完全な canonical set を保持する。完全保持できない場合は `truncated:true` として flip 比較自体を無効化する。

[R3-9] Major 共通 parser 導入後の「履歴 corrupt＝cold start」が全 reader で統一されていない  
→ 根拠: S9 の共通 parser 利用者は plan-dispatch、gate、codex-review-plan の3者だが（[PLAN.md:62](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:62)）、`resolve-impact.py` も history を読み、過去の回帰所見を impacted docs に使う（[resolve-impact.py:243](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:243)）。したがって `phase4Runs` だけ不正で `entries` が正しい履歴は、片方で corrupt、片方で有効という矛盾になる。また既存契約は corrupt history でも監査を継続し gate が隔離するものだが（[config-schema.md:164](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:164)）、codex-review-plan の parse error 時に継続するか exit するかが未定義である。旧版が生成し得る top-level array は現 parser が正当に受理しているが（[docaudit_cache.py:44](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:44)）、CT-6の「keyless history」がこれを含むかも不明。  
→ 推奨する修正: 4 reader 共通の `valid/absent/corrupt` 真理値表をPLANに置き、corrupt は全 reader で cold start＋警告として継続し、gateだけが隔離することと旧 top-level array 互換を固定する。

[R3-10] Major `phase4Runs` への source 選別と `promptVariant` の run mode 整合が未定義  
→ 根拠: Phase 4 evidence は delegated layers、security、code review、codex-review など複数 source の findings を同一配列へ集約する（[SKILL.md:622](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:622)）。S8 は `file` 必須を codex-review に限定する一方、S9は record 作成時に `source=="codex-review"` だけを選ぶとは書いていない（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:60)、[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:61)）。非Codexの file-less finding が record を拒否させるか、flip に混入し得る。また `completed/full` の自己申告と manifest の full/incremental の対応検査がなく、incremental run が full recordを汚染したり、full run が記録されない実装でもCT-5を通り得る。現行 gate は Phase 4 state の列挙検査までである（[decide-verdict.py:786](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:786)）。  
→ 推奨する修正: gate に単一の eligibility matrix を定義し、`source==codex-review` のみを正規化・保存し、manifest mode と `promptVariant` の不一致は REFUSED にする。

[R3-11] Major carry-forward に残る自由文字列と symlink 判定が、構造化した後も注入経路になる  
→ 根拠: S11 は `runid`、`ts`、`file` を prompt に運ぶが（[PLAN.md:64](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:64)）、runid/ts の形式・長さ・制御文字検査は明示されていない。正当な repo path でもバッククォート等を含むファイル名は作れ、「data, not instructions」という文言だけでは Markdown 境界を保証しない。また「現在の worktree に実在する通常ファイル」が `os.path.isfile` 相当なら symlink を追従する一方、既存の `validate_repo_path` は symlink を拒否する（[docaudit_paths.py:37](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:37)）。  
→ 推奨する修正: prompt から不要な runid/ts を落とし、file は symlink 拒否を含む共通 path validator を必須化した上で、Markdown として解釈されない正規エンコードで渡す。

## 総括

計画自体の欠陥（PLANを直してから実装）:

- R3-1〜R3-5: 信頼境界、回復状態遷移、harness compatibility matrix、registry 定義
- R3-7〜R3-10: record 上限、flip 完全性、history reader 契約、Phase 4 eligibility
- R3-11: carry-forward の入力境界

worker 指示で吸収できる細部:

- R3-6の検査実装手段
- 旧 top-level array fixture の具体形
- canonical sort・重複排除の実装方式
- stamp allowlist の比較処理

費用対効果では、削るべきなのは carry-forward prompt 内の `runid`/`ts` と、全 consumer をそのまま observer と数える O の二重用途である。逆に不足している成果物は、acceptance/history の状態遷移表、harness stamp×state の互換表、全 history reader の真理値表、最大 record の writer→parser 境界テストである。方針Bそのものを覆す必要はないが、その適用範囲はまだ閉じていない。