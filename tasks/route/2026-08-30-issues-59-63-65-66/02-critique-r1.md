メタ認知: PLAN の説明量を網羅性と取り違える偏りと、依頼文の懸念を再掲するだけのレビューを避け、実際の読み取り・状態遷移・生成物まで追跡した。

結論は明確です。Critical 3件、Major 10件があり、現状の PLAN で実装を開始すべきではありません。

なお前提に誤りがあります。dir-framework は現在 `engineVersion:"0.15.0"` で、最新 history も `contractVersion:"0.15.0"` です（[doc-audit.json:31](</Users/akiratakahashi/Projects/dir-framework/.claude/doc-audit.json:31>)、[docaudit-history.json:1497](</Users/akiratakahashi/Projects/dir-framework/.claude/state/docaudit-history.json:1497>)）。0.15.1 前提だけの移行評価では不足します。

[R1-1] Critical SKILL 自身の暗黙的な config 消費が全数表から漏れ、未検証値が verdict 経路へ入る

→ 根拠: CT-1 は `"$CFG"` を含む行だけを対象にします（[PLAN.md:62](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:62>)）。しかし実際には `phase3Backend`（[SKILL.md:81](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:81>)）、`maxImpactedDocs`・`docGlobs`・`minScore`（[SKILL.md:380](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:380>)）、`boundaryCommand`・`reviewCommands`（[SKILL.md:548](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:548>)）、Codex の model・timeout（[SKILL.md:585](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:585>)）、`reportPath`（[SKILL.md:663](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:663>)）を文章上で直接参照しています。いずれも対象、実行コマンド、モデル、所見を変え得ます。実測では `"$CFG"` は26行ですが、これらの参照は1件も拾いません。

→ 推奨する修正: open・resume・re-open直後に検証済み `CONFIG_JSON` を作り、SKILL レベルの全設定参照をその値だけから取得する設計へ変更する。

[R1-2] Critical harness の verify-before-read は同じ競合窓を残し、さらに Phase 4 の再読経路が全数表から漏れている

→ 根拠: PLAN 自身が別処理による「残余窓」を認めています（[PLAN.md:44](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:44>)）。実消費者は後から config path を開きます（[generic-layers.py:592](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:592>)）。加えて Phase 4 は `docAuditCommands` を再実行し（[SKILL.md:530](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:530>)）、生成された `/check-docs` と `doc-lint` は期待 SHA なしで `scripts/check-docs.py` に live path を渡します（[scaffold.py:81](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:81>)、[scaffold.py:113](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:113>)）。

さらに `generic-layers.py` 自体が harness の複製元です（[scaffold.py:164](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:164>)）。実測 SHA は `fbef5b46…c23a3` で0.15.1 entryと一致しています（[engine-shas.json:47](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/engine-shas.json:47>)）。同ファイルを S2 で変更しつつ、0.16.0 SHAを同じとする [PLAN.md:58](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:58>) は成立しません。

→ 推奨する修正: harness 例外を廃止し、生成済み `check-docs.py` 自身が同じバイト列を検証するよう、生成テンプレート・SHA・refresh移行を変更範囲へ含める。

[R1-3] Critical pre-open の audit-scope 例外により、古い impactMap を封印したまま CONSISTENT に到達できる

→ 根拠: `import-audit-scope.py` は scope SHAだけでなく、翻訳した規則と config の `impactMap` を比較します（[import-audit-scope.py:310](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:310>)、[import-audit-scope.py:633](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:633>)）。攻撃者が pre-check 中だけ正しい config を見せ、open 前に古い configへ戻すと check は通ります。その後の start-run と gate が再確認するのは scope path/SHAだけで、impactMap の意味的等価性ではありません（[start-run.py:141](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:141>)、[decide-verdict.py:203](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:203>)）。S4 の anchorPath 突合では閉じません。importer はすでに `configSha` を返しています（[import-audit-scope.py:286](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:286>)）。

→ 推奨する修正: pre-check の `configSha` を open-run に渡し、封印した config SHA と一致しない限り run を開かない。

[R1-4] Major gate 内の子処理が検知した config mismatch は `config-changed` 記録経路を迂回する

→ 根拠: gate は最初に config を検証しますが（[decide-verdict.py:684](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:684>)）、後で `change-set-sha.py` に path を渡して再読させます（[decide-verdict.py:808](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:808>)）。子が exit 7 になっても、現構造では通常の `Refused` に変換されるだけで `config_taint=True` になりません。結果は stdout JSON の reason に入り、S6 が条件とする「exit 7 または stderr token」にも届きません（[decide-verdict.py:1001](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1001>)、[decide-verdict.py:1027](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027>)）。

→ 推奨する修正: gate 内で子の exit 7 を明示判定し、共通の config-taint finalizer へ直接流す。

[R1-5] Major 復元済み taint は CT-3 が要求する次回 exit 6 を発火させない

→ 根拠: S5 は復元後も `expectedConfigSha=evidence.config` を記録し、CT-3 は次回 exit 6 を要求します（[PLAN.md:41](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:41>)、[PLAN.md:64](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:64>)）。ところが open-run は現在 SHA が `expectedConfigSha` と違う場合だけ exit 6 です（[open-run.py:164](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:164>)）。復元後は同じなので通過します。また S5 の record は既存 last-run にある `runid` と `reportStatus` を欠き、永続化失敗後の release 条件も未定義です。

→ 推奨する修正: `configAcceptanceRequired:true` を持つ共通の永続 taint record を定義し、その書き込み成功後だけ release、marker がある間は SHA 一致にかかわらず exit 6 とする。

[R1-6] Major history SHA 不一致を config-taint funnel に流す設計は、history を隔離せず誤った承認要求を残す

→ 根拠: S11 は `sealed-history-mismatch` を「S6 と同じ funnel」に流します（[PLAN.md:53](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:53>)）。その funnel は `--config-taint-observed` であり、historyには触れません（[PLAN.md:41](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:41>)）。現行 gate は history mismatch を別に識別し、所有確認後に `.tainted-<runid>` へ隔離します（[decide-verdict.py:734](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:734>)、[decide-verdict.py:990](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:990>)）。

→ 推奨する修正: identity検査・隔離・releaseを行う専用 `--history-taint-observed` 経路へ分離する。

[R1-7] Major cross-turn 再開時に `CONFIG_SHA` を復元する手順がなく、現行 EVIDENCE 契約とも矛盾する

→ 根拠: S6 が再束縛を指定するのは open成功直後と harness再openだけです（[PLAN.md:43](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:43>)）。現行契約はハッシュを別変数へ持ち出すことを禁止し（[SKILL.md:41](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:41>)）、再開時に復元するのは `RUNID` と `EVIDENCE` だけです（[SKILL.md:50](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:50>)）。その直後には ax/codex を再probeするため、未束縛 SHA で正しい run が停止します。

→ 推奨する修正: resume の最初に復元済み `EVIDENCE.config` から SHA と検証済み config JSON を再導出する手順・checkpoint契約を明記する。

[R1-8] Major `phase4Runs` の構造検査がなく、file キーは決定的キーにも安全な carry-forward 入力にもならない

→ 根拠: PLAN は `file` を「任意の文字列」として受理します（[PLAN.md:50](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:50>)）。元 schema も非空文字列しか要求しません（[codex-review-output.schema.json:12](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/codex-review-output.schema.json:12>)）。したがって `docs/a.md`、`./docs/a.md`、`docs/a.md:10` は同一ファイルでも別の flip になります。

さらに `parse_history` は top-level `entries` しか検査しません（[docaudit_cache.py:44](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:44>)）。実測では `phase4Runs:"not-a-list"` と、`file:"../../outside"`／指示文入り title の両方が `ACCEPT` されました。50件・title 200文字制限は gate が新規生成するデータにしか効かず、Phase 2 前に置かれた history には効きません。「data, not instructions」はモデル出力への間接影響を防ぐ境界ではありません。

→ 推奨する修正: `phase4Runs` 用の共通厳格 parser を追加し、件数・総byte・列挙値・制御文字・title長・正規化済みrepo相対fileを検証し、不正なら history corrupt として隔離する。

[R1-9] Major flip 比較キーが review 契約を含まず、版・設定変更を sampling instability と誤報する

→ 根拠: record は `contractVersion` を保存するのに（[PLAN.md:51](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:51>)）、比較は `worktreeDigest × full × completed` だけです（[PLAN.md:52](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:52>)）。worktree digest は HEAD と repo 状態であり、plugin側のprompt/engineを含みません（[tree-digest.py:37](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/tree-digest.py:37>)）。gitignoreされた config も digest に入りません。現行の文書 verdict flip は contractVersion/backend 一致を要求しています（[decide-verdict.py:230](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:230>)）。

→ 推奨する修正: 比較用 `reviewInputKey` を `worktreeDigest + contractVersion + EVIDENCE.config` として固定する。

[R1-10] Major 最新20件という保持方法は、唯一必要な前回 full record を incremental run が追い出す

→ 根拠: S9 は Phase 4を検査した全runを保存して最新20件にしますが、S10/S11が読むのは full＋completed だけです（[PLAN.md:51](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:51>)）。full 1回の後に incremental が20回続くだけで、その full record は確実に消え、次の full で flip も carry-forward も cold start になります。

→ 推奨する修正: `phase4Runs` は full＋completed のみ保存するか、少なくとも最新 full-completed を別枠で必ず保持する。

[R1-11] Major `--expect-config-sha` 必須化の呼び出し側移行が変更範囲から漏れている

→ 根拠: S2 は `--config` を持つ全scriptで SHA を必須化します（[PLAN.md:38](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:38>)）が、変更禁止の `/docaudit:init` は SHAなしで `set-config-key.py` を呼びます（[skills/init/SKILL.md:96](</Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:96>)）。また `fix-scope.py` の snapshot/verify は config を読まない正規モードです（[fix-scope.py:62](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:62>)）。引数を一律必須にすると、audit自身のこの2モードも壊れます。

→ 推奨する修正: 全呼び出し側を移行表に追加して `skills/init/**` を許可範囲へ入れ、任意configのscriptでは「configを実際に読むモードでのみ期待SHA必須」とする。

[R1-12] Major skills-dir と旧版混在の互換性前提が実際の配布手順に反する

→ 根拠: PLAN は plugin単位で同時更新されると仮定します（[PLAN.md:141](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:141>)）。しかし公式手順は Python scriptだけの部分コピーも案内しています（[ADOPTION.md:249](</Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:249>)）。今回は SKILL、Python、shell 7本が同時変更されるため、公式手順そのものが新旧混在を作ります。

また旧0.15 gateは未知キーを読むことはできますが、書き戻し時に history 全体を `{"entries":...}` へ置換するため、0.16の `phase4Runs` を消します（[decide-verdict.py:925](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:925>)）。「旧readerが無視できる＝保持互換」という主張は誤りです。dir-framework が実際には0.15.0である点も移行対象を広げます。

→ 推奨する修正: v0.16では部分コピーを禁止し、全tree同期＋reload＋in-flight run終了確認を必須の移行手順として、downgrade時の `phase4Runs` 消失も明記する。

[R1-13] Major CT-1〜CT-6 は正しい実装と誤った実装を十分に区別できない

→ 根拠:

- CT-1は同一行の文字列検査なので、文章参照、hardcoded path、複数行、別変数、生成 harnessを捕捉しません。コメントに `"$CONFIG_SHA"` を足すだけでも通せます。
- CT-2は `N ≥ 19` だけで一意な19本を証明せず、常にexit 7する誤実装も通ります。`mdq-index.sh` は configを2回（[mdq-index.sh:27](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:27>)、[mdq-index.sh:71](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:71>)）、`compute-baseline.sh` は3回読みます（[compute-baseline.sh:30](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:30>)、[compute-baseline.sh:66](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:66>)）。最初の読みだけ直した実装でもCT-2は通ります。
- CT-3の「復元後に次回exit 6」は現実の述語では成立しません。
- CT-5は不正 `phase4Runs`、異contract/config、path正規化、full recordの追い出しを検査しません。
- CT-6は history mismatch のexit/tokenしか見ず、誤ったconfig-taint記録、未隔離、次runへの再混入を見ません。

→ 推奨する修正: exactな一意consumer集合を固定し、各consumerに「一致SHAで実処理成功／不一致SHAで停止」の対を置き、複数読取の中間差替え、wrapper伝播、history隔離、次run cold startまでをend-to-endで検査する。

## 総括

計画自体の欠陥（PLAN を直してから実装）:

- R1-1〜R1-13すべて。
- 特に R1-1〜R1-3 は #63 の目的そのものを破り、R1-4〜R1-6 は taint 一元化を成立させません。
- #59では R1-8〜R1-10を直さない限り、flip値とcarry-forwardの出所を信頼できません。
- 費用対効果では、S4と findings 50件上限は維持すべきです。一方、非full・非completedの `phase4Runs` は保存対象から落とせます。足りない成果物は、厳格なhistory文書schema、生成harnessの移行、全consumer registry、全tree更新手順です。

worker 指示で吸収できる細部:

- `observedBy` の固定列挙・長さ制限。
- S4でのrepo相対path正規化方法。
- exit 7のstderr文言、JSONのfield順、テストfixtureの整理。

確認の結果、`CODEGRAPH_DIR` の対象外扱い、S4自体の必要性、現在の `workflow-template.js`／`agents/*.md` に直接config読取がない点、Phase 2で封印後からPhase 4までhistoryを正当に書く経路がない点、exit 7が既存終了値と衝突しない点は妥当です。

ファイル変更はしていません。指定の `gh issue view 63/59` は実行しましたが、この環境から `api.github.com` へ接続できず、Issue原文だけは直接再取得できませんでした。