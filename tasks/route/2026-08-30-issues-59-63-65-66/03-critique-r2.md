収束していない。v2 には Critical 1件、Major 12件、Minor 1件の実質的な欠陥が残る。

[R2-1] Critical project 側 harness を検証対象外にすると、実行ファイルを改竄せず config の一時差し替えだけで Phase-4 所見を操作できる

→ 根拠: PLAN は「実行ファイルの差し替え」を脅威境界外とする一方、そこから「harness の config 読みも対象外」と結論している（[PLAN.md:7](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:7)、[PLAN.md:9](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:9)、[PLAN.md:163](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:163)）。しかし生成される `scripts/check-docs.py` は `generic-layers.py` の複製であり（[scaffold.py:164](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:164)）、その正常な実行ファイルが live config を読む（[generic-layers.py:592](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:592)）。攻撃者は実行ファイルを触らず、`docGlobs` 等を一時変更して所見を抑制し、gate 前に復元できる。その所見は verdict に畳み込まれる（[SKILL.md:530](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:530)、[SKILL.md:541](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:541)）。

→ 推奨する修正: project harness にも封印 SHA を渡して config 読みを検証させ、SHA を受け取れない任意 `docAuditCommands` の所見は verdict 根拠から外す。

[R2-2] Major `seal-run.py` の子プロセス再読と既存 release 分岐が taint funnel を迂回する

→ 根拠: pass-through 対象は classify/dispatch/gate だけで、seal-run が抜けている（[PLAN.md:38](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:38)）。現行 seal-run は config path だけを `change-set-sha.py` に渡して再読させ（[seal-run.py:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:49)）、子の失敗を exit 2 に畳む（[seal-run.py:54](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:54)、[seal-run.py:77](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:77)）。さらに SKILL は exit 5 以外を即 release する（[SKILL.md:421](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:421)）。全体 Guardrail を追加するだけでは、この局所分岐が先に動く実装が残る。

→ 推奨する修正: seal-run も EVIDENCE.config を子へ pass-throughして exit 7 を保持し、その token 判定を既存 release 分岐より前に置く E2E テストを追加する。

[R2-3] Major harness decline 後の再 open は古い precheck SHA と未定義の acceptance marker により失敗する

→ 根拠: decline は config を書き換えて release・再openする（[SKILL.md:273](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:273)）。S4 は open 時の SHA と `PRECHECK_CONFIG_SHA` の一致を必須にするが（[PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:41)）、PLAN が再導出すると明記するのは再open後の `CONFIG_SHA` だけである（[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:49)）。旧 SHA のままなら必ず `config-changed-before-open` になる。また `--accept-config` は「marker を解除」とあるだけで消費時点が未定義（[PLAN.md:44](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:44)）。現行は marker を消さず判定を迂回するだけである（[open-run.py:164](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:164)）。

→ 推奨する修正: decline 後の precheck 再実行と、「acceptance は正常な lock 取得時に一度だけ消費する」状態遷移を一つの E2E テストで固定する。

[R2-4] Major history 隔離失敗後も lock を release でき、改竄 history を次 run の正規入力へ昇格できる

→ 根拠: config taint だけは「記録成功後のみ release」と明記されるが、history には同条件がない（[PLAN.md:46](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:46)、[PLAN.md:47](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:47)）。現行 gate は quarantine の `os.replace` 失敗を握り潰し（[decide-verdict.py:990](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:990)）、そのまま release する（[decide-verdict.py:1022](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1022)）。攻撃者は予測可能な `.tainted-<runid>` を directory として先置きできる。live history が残れば、次 run で carry-forward に入るため「効果は DoS のみ」（[PLAN.md:48](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:48)）は成立しない。

→ 推奨する修正: history も隔離成功または live history 消失を確認した場合だけ release し、失敗時は機械的に次 open を止める。

[R2-5] Major lock 非所有時の `--taint-observed` が未定義・未試験である

→ 根拠: S5 は manifest 前でも runid・runDir・lock inode・lock 保持だけで処理する新しい identity 経路である（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:45)）。現行 gate は完全な EVIDENCE を要求し（[decide-verdict.py:316](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:316)）、manifest 読取後に identity を確定する（[decide-verdict.py:676](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:676)）。CT-3/CT-6 は正常所有側しか試さず、lock missing・別 runid・inode 差替え・flock 中を検査しない（[PLAN.md:74](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:74)、[PLAN.md:77](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:77)）。`observed-by` の固定集合も未定義で、直接の `sealed_config.py --get` が列挙に入る保証がない。

→ 推奨する修正: observer ID と非所有4ケースを registry 化し、全ケースで last-run/history/lock が不変であることを assert する。

[R2-6] Major `impact-supplement.py` の SHA 必須化が既存の config 無し利用を壊す

→ 根拠: PLAN は必須群に置く（[PLAN.md:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:35)）が、現行 `--config` は任意である（[impact-supplement.py:18](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:18)、[impact-supplement.py:193](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:193)）。config 無しの pure passthrough と graphify-only は明示的な既存テスト契約である（[test_impact_supplement.py:135](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_impact_supplement.py:135)、[test_impact_supplement.py:170](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_impact_supplement.py:170)）。

→ 推奨する修正: `fix-scope.py` と同じ「`--config` 指定時のみ SHA 必須」に分類する。

[R2-7] Major `sealed_config.py --get` の JSON 出力は既存の値型・既定値契約を保持しない

→ 根拠: `--get` は常に JSON を出力する（[PLAN.md:33](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:33)）一方、S6 は復号方法とキー別 default を定義していない（[PLAN.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:52)）。文字列 `"workflow"`、model、reportPath は引用符付きでは既存の分岐・CLIを壊す（[SKILL.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:81)、[SKILL.md:585](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:585)、[SKILL.md:663](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:663)）。欠落時 `null` も、既存の `workflow` 等の既定値と異なる（[start-run.py:29](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:29)）。

→ 推奨する修正: 各キーについて default JSON・返却型・復号方法・最終的な束縛値を表にし、下流分岐までテストする。

[R2-8] Major 不正 `phase4Runs` が Phase 2 で `historyStatus:"ok"` として cache に使用される

→ 根拠: parser 利用者は gate と codex-review-plan の2者だけで、plan-dispatch が抜けている（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:61)）。現行 plan-dispatch は `entries` だけを解析して `historyStatus="ok"` にし（[plan-dispatch.py:94](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:94)）、その状態で cache を有効化する（[plan-dispatch.py:108](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:108)）。Phase-4 parser error 時の exit・taint も PLAN にない。

→ 推奨する修正: `entries` と `phase4Runs` を同時に検証する共通 `parse_history_document` を plan-dispatch・gate・codex-review-plan の3者で使う。

[R2-9] Major carry-forward は gate provenance を証明せず、自由文による持続型 prompt injection を追加する

→ 根拠: history SHA が EVIDENCE に入るのは open 時ではなく Phase 2 の plan-dispatch 時である（[plan-dispatch.py:91](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:91)、[plan-dispatch.py:150](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:150)）。したがって run 開始後でも、その読取前に schema-valid history を置けば「gate が書いた history」という前提を満たさず封印される。さらに raw schema は title/file を単なる非空文字列として許し（[codex-review-output.schema.json:12](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/codex-review-output.schema.json:12)）、SKILL は title をそのまま Phase-4 所見へ写す（[SKILL.md:614](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:614)）。200文字・制御文字除去と「data, not instructions」（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:60)、[PLAN.md:63](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:63)）では、バッククォートや命令文を除けない。

→ 推奨する修正: carry-forward は「検証済みの既存 repo path＋固定 severity」だけに縮小し、自由文 title/source は prompt に再投入しない。

[R2-10] Major `<unresolved>` を flip キーに含めるため、異なる所見が同一扱いされる

→ 根拠: 絶対パス・`..`・制御文字をすべて同じ sentinel に畳み（[PLAN.md:59](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:59)）、その値を `blockingFiles` の集合比較に使う（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:60)、[PLAN.md:62](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:62)）。例えば前回 `../../a`、今回 `/tmp/b` は双方 `<unresolved>` となり flip 0 の偽陰性になる。同じ実ファイルが相対表記から絶対表記に変わると逆に偽陽性となる。

→ 推奨する修正: unresolved finding は verdict には残すが `blockingFiles` と carry-forward から除外し、別の `unresolvedFileCount` warning とする。

[R2-11] Major writer が生成可能な record を次回 parser が 64 KiB 超過として corrupt にできる

→ 根拠: writer 側は findings 50件・title 200文字だけで、file のバイト上限も record-fit 条件もない（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:60)）。reader は record 64 KiB 以下を要求する（[PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:61)）。実測では、正規化可能な1115-byte path＋200文字 title を50件持つ compact JSON が70,473 bytesとなる。さらに parser は `blockingFiles` が findings から正しく導出されたかを検査しないため、構造上validな不整合 record も作れる。

→ 推奨する修正: gate が同じ parser で書込み前 round-trip 検証し、バイト予算内へ決定的に trimするとともに、`blockingFiles` は保存せず検証済み findings から導出する。

[R2-12] Major N=27／K=19 と CT-2 の期待値は、どの数え方でも同時成立しない

→ 根拠: §9.1 だけなら #4〜#28 は25行、#5の二重 call で+1、#15除外で-1、N=25である（[PLAN.md:116](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:116)、[PLAN.md:168](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:168)）。さらに§9.2を一キー一回の `--get` にすると10 call site 増え、全読取を数えるなら35になる。Kも、`--expect-config-sha` を受けるのはS2/S3の17本＋open-run＝18本だが、K=19は同フラグを受けない seal-run/decide-verdict を含み open-run を除いている。加えて CT-2 は全件 exit 7 を要求する一方（[PLAN.md:73](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:73)）、正しい gate taint は exit 3（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:45)）。

→ 推奨する修正: 各 consumer に「SHA供給源・CLI形・直接/子読取・正常exit・mismatch exit・observer ID」を持たせた単一 registry から件数とテストを導出する。

[R2-13] Major CT-1(d) は正しい SKILL を拒否する一方、間接 config 読みを捕まえない

→ 根拠: 「`doc-audit.json` を含む行は Guardrails の禁止文だけ」という条件（[PLAN.md:72](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:72)）は、必須の CFG 束縛、利用説明、承認案内、表示文まで拒否する。現行実測で該当は15行あり、例は [SKILL.md:9](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:9)、[SKILL.md:13](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:13)、[SKILL.md:38](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:38)。逆に `Resolve config phase3Backend` や `From config docAuditCommands` はファイル名を含まず通る（[SKILL.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:81)、[SKILL.md:530](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:530)）。`CFG2="$CFG"` のような別名化も回避可能である。

→ 推奨する修正: ファイル名 grep を廃止し、キー→sealed getter→束縛変数→使用箇所の固定 registry を等値検査する。

[R2-14] Minor path 正規化が正当な POSIX path と Windows 絶対 path を誤分類する

→ 根拠: 末尾 `:<digits>` の無条件除去は、正当な POSIX filename `docs/spec:10` を `docs/spec` に変える（[PLAN.md:59](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:59)）。また既存 `validate_repo_path` は実行OSの `os.path.isabs` を使うため（[docaudit_paths.py:37](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:37)）、POSIX 上では `C:/repo/a.md` を絶対パスとして拒否しない。

→ 推奨する修正: まず exact repo path を安全に検証し、それが存在しない場合だけ locator suffix を除去し、Windows drive/UNC はOS非依存に拒否する。

確認済みで再指摘しない事項:

- `audit-scope` の `absent`／`not-imported` はどちらも `configSha` を返すため、S4との本質的矛盾はない（[import-audit-scope.py:286](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:286)、[import-audit-scope.py:589](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:589)、[import-audit-scope.py:635](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:635)）。
- `workflow-template.js`、`agents/*.md`、references には未列挙の直接 config reader は見つからなかった。
- S4 自体は落とせない。precheck→open の窓を閉じるために必要である。
- phase4Runs の保持20件、findings上限50件は妥当。削るなら、digest が HEAD を含むため未使用の `head` と、全件固定値の per-finding `source` が先である。

総括:

- 計画自体の欠陥（PLANを直してから実装）: R2-1〜R2-13。特に harness 除外、seal-run 子読取、taint失敗時の release、history provenance、共通history parser、registry/count契約は worker の裁量では安全に決められない。
- worker 指示で吸収できる細部: R2-14、history severity を既存と同じ uppercase 4値に固定すること、冗長な `head`／`source` の削除。
- ファイル変更は行っていない。作業ツリーも clean。