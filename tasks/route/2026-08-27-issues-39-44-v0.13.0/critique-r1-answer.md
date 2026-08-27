結論：この PLAN は現状では実装着手不可です。特に #39・#42・#44 に fail-open 経路があります。Issue 本文は外部接続制限で取得できなかったため、PLAN §1/§2 と現行コード、#44 のローカル参照実装を根拠にしました。ファイル変更は行っていません。

1. **[BLOCKER] #39 の「内容不変 verdict flip」は、モデルのブレではなく正当なソース変更を数える**

   根拠: PLAN §10 #39 は `contentSha` 一致・verdict 不一致だけを数えます（[PLAN.md:244](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:244>)）。しかし history は `changeSetSha`・`contractVersion`・`backend` も保持します（[docaudit_cache.py:11](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:11>)）。文書を変えずソースだけ修正して FAIL→PASS、またはソース変更で PASS→FAIL になった正常系も「不安定」と誤計上されます。

   推奨修正: 少なくとも `contentSha + changeSetSha + contractVersion + backend` が同一の場合だけブレとして数える。

2. **[BLOCKER] `codexReview.required` を Phase 4 の自己申告から読むため、必須設定を回避できる**

   根拠: PLAN §10 #42 は `phase4.codexReview.required` を gate が読む設計ですが、SHA 固定された config は gate が直接読めます（[decide-verdict.py:629](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:629>)）。証拠に `required:false` を書く、または `codexReview` を省けば従来挙動へ落とせます。

   推奨修正: 必須性は config だけから導出し、証拠は `state` のみ記録する。config が必須なら欠落・型不正も REFUSED にする。

3. **[BLOCKER] impacted 0件では strict mode の判定自体が実行されない**

   根拠: [start-run.py:190](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:190>) は impacted・SSoT・preflight がなく incremental なら `phase4Required:false` にします。その場合 Phase 4 ファイルを作りません（[SKILL.md:514](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:514>)）。PLAN は `start-run.py` を原則変更禁止にしているため、`required:true` でも codex 不実行のまま CONSISTENT が可能です。

   推奨修正: incremental の `codexReview.required:true` を `phase4Required` 条件と封印済み manifest に加える。

4. **[BLOCKER] audit-scope drift を非ブロッキングにすると、古い impactMap で CONSISTENT を出せる**

   根拠: PLAN §9 は drift を WARN のまま継続します（[PLAN.md:210](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:210>)）。実際の対象選定は audit-scope ではなく config の `impactMap` だけです（[resolve-impact.py:188](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:188>)）。正本変更後の古い生成物は対象漏れそのものです。

   推奨修正: `auditScope` 記録済みの drift は Phase 0 で監査を停止させる。

5. **[BLOCKER] `--check` は source SHA しか見ず、生成物の改変・削除を検知しない**

   根拠: PLAN §9 の in-sync 判定は記録 SHA と scope SHA の比較だけです。auto `impactMap` を手編集・削除しても scope SHA が同じなら in-sync になります。また metadata があるのに scope が消えても `absent` exit 0 です。

   推奨修正: scope から管理対象部分を再生成して config と比較し、source 不在・生成物差分・metadata 差分をすべて drift にする。

6. **[BLOCKER] tracked ファイル上の glob 等価検査は、将来の不一致を証明できない**

   根拠: docaudit は `**/` を「0階層も可」と特別扱いします（[docaudit_paths.py:8](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:8>)）。実演すると、fnmatch の `*/foo` は root の `foo` に false ですが、変換後 `**/foo` は true。同様に `**/*` は fnmatch では root ファイルに false、docaudit では trueです。現在そのパスが tracked でなければ PLAN の検査は通ります。

   推奨修正: 現在のファイル集合を合否根拠にせず、意味論的に証明できる限定構文だけ変換し、`**/` を新たに生む形は拒否する。

7. **[BLOCKER] `--write` の安全境界と既存 config の承認手順が未定義**

   根拠: PLAN は任意の `--config`・`--scope` を受けて既存 `.claude/doc-audit.json` を置換しますが、対象の repo 内包含・symlink・通常ファイル検査を明記していません。さらに init は既存 config の編集を `--harness` 以外禁止し、書く前の承認を要求します（[skills/init/SKILL.md:15](</Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:15>)、[同:171](</Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:171>)）。

   推奨修正: `--import-audit-scope` は落とし、変換結果を通常の init draft に統合して、パス検証と承認後に一度だけ書く。

8. **[MAJOR] #39 が読んだ history と、後段が SHA 固定する history が同じと証明できない**

   根拠: `resolve-impact.py` が history を読み、その後 [plan-dispatch.py:92](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:92>) が別に読み直して後者だけを EVIDENCE に固定します。間で内容が変わっても partition 自体は整った集合として通ります。

   推奨修正: resolve の出力に `historySha` を入れ、plan-dispatch の読取 SHA と一致しなければ中断する。

9. **[MAJOR] provenance が封印されず、Phase 3 の指示だけ後から改変できる**

   根拠: manifest は path しか保持しません（[start-run.py:201](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:201>)）。一方 Codex dispatcher は封印後も SHA 未検証の `impact.json` から provenance を読みます（[codex-dispatch.py:67](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:67>)）。#39 は `regression` に特別な指示を与えるため影響が拡大します。

   推奨修正: path と provenance を manifest に封印し、dispatcher は manifest だけを読む。

10. **[MAJOR] #39 の cap・supplement・cache 統合試験が判別不能**

    根拠: PLAN §6 は partition 統合試験1本だけです。完成済み impact を手書きしても通り、`mapped ≥ regression ≥ heuristic ≥ graphify ≥ semantic`、最新 FAIL が cached ではなく dispatch になること、regression が cap で全落ちするケースを検出できません。

    推奨修正: 全 provenance で cap を満杯にし、resolve→supplement→plan-dispatch→seal→gate を通す統合試験に置き換える。

11. **[MAJOR] `required:true` を full mode だけ免除するのは設定名と保証が矛盾する**

    根拠: PLAN §6/§10 は `skipped-full-run` を required でも許します。最も広い監査だけ adversarial review なしで CONSISTENT・anchor 前進が可能になります。また `enabled:false, required:true` の競合も未定義です。

    推奨修正: full でも未実行なら REFUSED にする。免除したいならキー名を `requiredForIncremental` に変更する。

12. **[MAJOR] REFUSED 採用自体ではなく、REFUSED へ到達しない経路が問題**

    根拠: NEEDS_FIX は有効な監査で欠陥が見つかった意味で、現行では history を更新します（[decide-verdict.py:785](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:785>)、[同:817](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:817>)）。必須層未実行を NEEDS_FIX にすると Phase 3 PASS が履歴に入り得ます。

    推奨修正: 判定値は REFUSED のまま、指摘2・3の fail-open を閉じ、history・anchor非更新を回帰試験で固定する。

13. **[MAJOR] `exec --help` は「実呼び出しと同形状 probe」ではない**

    根拠: 実呼び出しは `exec -C … -s read-only … --output-schema … -o … -`（[SKILL.md:499](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:499>)）ですが、PLAN は `exec --help` だけです。wrapper が個別引数を拒否しても probe は成功します。

    推奨修正: exact parser flags を通す非モデル起動 probe にするか、「CLI存在確認」と名称・保証を縮小する。

14. **[MAJOR] 修飾済み `GATE_VERDICT` が内部状態へ混入する回帰を DoD が防げない**

    根拠: PLAN は `CONSISTENT (codex-review …)` を同じ token に描画します。一方 anchor 前進は `verdict == "CONSISTENT"` の完全一致です（[decide-verdict.py:832](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:832>)）。表示試験だけでは stdout・last-run・anchor の破壊を検出できません。

    推奨修正: 内部 verdict は3値のまま、表示専用文字列を別変数にし、anchor/history/stdoutも検査する。

15. **[MAJOR] 新しい config 値の型・範囲契約がない**

    根拠: 中央 validator は存在せず、現行は各スクリプトが ad hoc に `.get` しています。`saturationWarnRatio` の文字列・bool・負数・1超、`excludeDocPathTokens` の非bool、`regressionRecheck` の非object、`required` の非boolで crash または truthy 誤動作が可能です。

    推奨修正: Phase 0/2で厳密な型・範囲検証を行い、不正値の表形式否定試験をDoDへ追加する。

16. **[MAJOR] `docCorpus ≥ 10` は小規模repoの完全飽和を隠す**

    根拠: PLAN §10 #40では9文書中9文書が heuristic-only でも警告ゼロです。導入初期の小規模repoほど「mapped主」が崩れていても見えません。

    推奨修正: corpus下限を削除し、`heuristicOnly > 0` かつ比率閾値以上で警告する。

17. **[MAJOR] `regressionRecheck.enabled:true` の既定化は互換追加ではない**

    根拠: 全採用者で変更と無関係な過去FAIL文書が毎回dispatchされ、費用とcap消費、impacted集合、verdict機会が変わります。history不在という正常なcold startまでwarningになります。

    推奨修正: v0.13.0では既定falseにし、新規initだけ明示的にopt-inを提案する。

18. **[MAJOR] #43 の list継続規則はMarkdownの字下げ境界を定義していない**

    根拠: PLAN §10 #43の「空行＋4空白」は、list marker幅・content indent・入れ子・引用・tabを無視します。現行もraw 4空白/tabを一律maskします（[generic-layers.py:226](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:226>)）。正例1件だけでは、list後の全字下げをunmaskして本物のコードを検査する誤実装も通ります。

    推奨修正: content-indentと終了条件を定義し、`-`・`10.`・引用内list・tabについて、継続段落と実コードの対になる試験を追加する。

19. **[MAJOR] #41 の「codex reviewが唯一の横断層」は事実と異なる**

    根拠: Phase 4のcode/security reviewも所見をgateへ渡し、gate自身も sibling scan に manifest・returns・phase4を渡します（[decide-verdict.py:94](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:94>)）。固定status行で断言すると、full modeではcodex自体をskipする現在の設計とも矛盾します。

    推奨修正: 「Phase 3単独では保証しない」に縮小し、“唯一”の断言と毎回の固定行は削る。

20. **[MAJOR] audit-scopeの対象文書と `docGlobs` の非対称を検査していない**

    根拠: 実物scopeは `.claude/README.md` を多数の影響先にします（[audit-scope.json:2](</Users/akiratakahashi/Projects/dir-framework/.claude/audit-scope.json:2>)）。init inventoryはhidden `.claude/` を自動追加しません（[skills/init/SKILL.md:165](</Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:165>)）。結果、incrementalではmapped対象、fullではcorpus外という非対称が生じます。

    推奨修正: 全impactsが`docGlobs`に入ることをwrite前に検証し、不一致なら同じ承認draftでglobを拡張するまで拒否する。

21. **[MAJOR] `--write` 後に exit 6／`--accept-config` が必要という説明は現行契約と逆**

    根拠: [open-run.py:164](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:164>) のexit 6は、前runが「実行中config変更」でREFUSEDになった場合だけです。run間の通常変更は新しいSHAとして受け入れます。逆に実行中にimportすれば現在runをREFUSEDにします。

    推奨修正: open run中のimportを拒否し、通常のrun間importでは`--accept-config`不要と文書化する。

22. **[MAJOR] release handoff試験が破壊的操作前の安全条件を固定していない**

    根拠: PLAN §12の8分岐には、非main、HEAD/origin不一致、dirty tree、全試験失敗、同期確認no/EOFがありません。現行防壁は [release-handoff.sh:37](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh:37>)、[同:156](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh:156>)、[同:182](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh:182>) にありますが、試験差し替えで落としても検知できません。

    推奨修正: 既存試験を全面差し替えず共通化し、各安全条件の失敗時にtag・Release・Issue close・rsyncが0回であることを固定する。

23. **[MINOR] 版・成果物の契約検査が曖昧**

    根拠: PLAN §12は設定キー「4件」としますが、`auditScope`、`saturationWarnRatio`、`excludeDocPathTokens`、`regressionRecheck.enabled`、`codexReview.required`の5件です。また旧版grepの「履歴的言及以外」が機械判定不能で、#39の7つのprovenance消費側やinitの`argument-hint`もDoDで固定されません。

    推奨修正: 現行版表示と保存する履歴行を明示し、5設定キー・全provenance消費側・argument-hintを表形式contract testにする。

## 区分

**計画自体の欠陥（PLANを直してから実装）**

1〜22。特に1〜7は実装担当の裁量では安全に吸収できません。

**worker指示で吸収できる細部**

- 23の文言・契約試験更新。
- `impact-supplement.py:5-9` の優先順位説明を `regression`込みにし、同ファイルを変更許可へ追加する。
- #43の複数行link試験では、後続findingのpath・message・line完全一致と、link／inline code／URL由来findingが0件であることを固定する。`_LINK_RE → _INLINE_CODE_RE → _URL_RE`の順序自体には、改行保持置換との直接衝突は確認できません。