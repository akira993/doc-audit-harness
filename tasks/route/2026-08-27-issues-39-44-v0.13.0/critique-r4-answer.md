メタ認知: 追加された安全策の「存在」ではなく、取得順序・検証時点・失敗時の状態を基準に評価した。R3の単純な再指摘は除外している。

結論は「新規指摘あり」。変更は行っていない。

1. [BLOCKER] 封印済みmanifestを検証処理が読む直前にSHA照合していない  
   根拠: [PLAN DoD:115](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:115) はseal後のgate検証を定めるが、現行codex-dispatchは `sealed:true` しか確認しない（[codex-dispatch.py:47](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:47)）。seal後にmanifestを書き換えると、最終gateが拒否する前に、改変されたpath/provenanceでCodex・workflow・Phase 4を起動できる。run ledgerはworktreeDigestの対象外なので検出が遅い。  
   推奨: 全manifest消費側が起動直前に `EVIDENCE.manifest` SHAを照合し、不一致時は検証処理を0回で止める契約を追加する。

2. [MAJOR] `impactSha` がdispatch.jsonとEVIDENCEの二重の正になっている  
   根拠: [PLAN §10 #39:216](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:216) は両方への記録を要求するが、gate条件はdispatch側だけを使う。現行 `validate_evidence()` は追加された `impactSha` を必須・SHA型として検証しない（[decide-verdict.py:252](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:252)）。二値不一致時の参照元も未定義。  
   推奨: `impactSha` はSHA封印済みdispatch.jsonだけに保持し、EVIDENCEへの直接追加を削除する。

3. [BLOCKER] full+required分岐を到達不能にした実装でも文言契約を通る  
   根拠: [PLAN DoD:126](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:126) はrequired分岐とskip分岐が別行にあることしか要求しない。現行の無条件full skip（[skills/audit/SKILL.md:477](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:477)）の後ろにrequired分岐を追記すれば、テストは通るが実行されない。またfull側がincremental専用のbaseline commit検査（[skills/audit/SKILL.md:485](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:485)）を迂回する契約もない。  
   推奨: `full&&required → 実行`、`full&&optional → skip`、`incremental → baseline検査後実行` の排他的順序と、model/retry/state処理の共有を明記する。

4. [BLOCKER] 承認SHAをlock取得前に確認するため、並行importで古い内容を上書きできる  
   根拠: [PLAN §9:185](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:185) はexpect SHA照合後にlockを取得する順序。Aが照合後に停止し、Bが更新・解放した後でAがlockを取ると、Aは古い承認結果でBのconfigを上書きできる。  
   推奨: lock取得後にconfig/scopeを読み直してexpect SHAを照合し、生成からrenameまで同じlock内で行う。

5. [BLOCKER] 初回initがauto impactなしのdraft configを一時公開する  
   根拠: [PLAN §9:198](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:198) はdraftを先に書き、その後importerを呼ぶ。この間にauditが開始すると、Phase 0は `not-imported` として継続し、open-runがdraftのSHAを固定する。importerはaudit lockで拒否されるため、auto impactなしのまま監査が完了し得る。  
   推奨: importerへbase draftを入力し、lock内でauto項目を加えた完成configを一度だけ原子作成する。

6. [MAJOR] `O_EXCL` からflock取得までの窓を `--break-lock` が破壊できる  
   根拠: [PLAN §9:185](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:185) はinode確認を解放時にしか行わない。lock作成直後・flock前にbreak-lockがunlinkすると、importerは削除済みfdでflockを取得してconfigを書ける。「flock保持中」の試験ではこの窓を検出しない。  
   推奨: flock取得直後かつconfig変更前にもfd/path inode一致を確認し、不一致なら無変更で停止する。

7. [BLOCKER] CR/LF拒否は現在の非NUL出力では検出不能で、clean fullも覆わない  
   根拠: [PLAN §10 #39:223](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:223) は変更集合中のCR/LFを拒否するが、現行Git出力は非NUL形式（[compute-baseline.sh:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:49)）。Gitは改行名を引用・エスケープして出すため後段のCR/LF検索では判別できない。clean fullでは全tracked pathを変更集合へ入れないため、未変更文書も漏れる。さらに全利用者のcompute-baseline変更は「audit-scope未導入プロジェクトは無影響」（[PLAN §0:8](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:8)）と矛盾する。  
   推奨: Phase 1でaudit-scope有無・modeに関係なく全対象pathをNUL形式で列挙して拒否し、全利用者向け互換性変更として明記する。

8. [MAJOR] check-verdictsの非0化後にSKILLがどう終了するか未定義  
   根拠: [PLAN DoD:119](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:119) は不一致時非0を要求する一方、現行SKILLはstdoutを解析してPhase 4/gateへ進む（[skills/audit/SKILL.md:379](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:379)）。通常エラーとして中断すると、gateのREFUSED記録もlock解放も保証されない。gate自身が同じ不一致を検査するため、非0化は安全性を増やしていない。  
   推奨: checkerはexit 0で診断を返す従来契約を維持し、REFUSEDはdeterministic gateだけに担当させる。

9. [MAJOR] `auditScope` metadataの型異常をfail-closedにする契約がない  
   根拠: [PLAN §9:190](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:190) はmetadata照合を要求するが、非object、path非文字列・絶対path、sha/rules/importedAtの不正型をどう扱うか未定義。誤実装がこれらをmetadata不在として `not-imported` で継続できる。  
   推奨: `auditScope` の必須フィールド・型・SHA形式・安全なrelative pathを定義し、不正時はerrorで監査停止する。

10. [MAJOR] 新しい `impactMap.source` と既存resolverの互換試験がrev.4で脱落した  
    根拠: importerは `source:"audit-scope"` を生成する（[PLAN §9:187](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:187)）が、rev.3にあった「resolve-impactが未知キーを無視する」試験がDoDから消えている。importer単体が成功しても、将来の厳格化で生成configをresolverが拒否する回帰を検出できない。  
    推奨: source有無以外が同じconfigでresolve-impact出力が完全一致する互換試験を戻す。

11. [BLOCKER] 「同期先repo外を拒否」は正規の同期先を拒否する  
    根拠: [PLAN §12:260](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:260) の同期先はskills-dir、すなわち通常はリポジトリ外である。一方、分岐 (xi) は「同期先repo外」を0/0/0/0で拒否する（[PLAN §12:263](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:263)）。文字どおり実装すると正常成功経路が存在しない。  
    推奨: containment基準をsource repoではなく、承認済みskills root配下の正規化された期待destinationに変更する。

12. [MAJOR] handoffの現行版・Release内容を正確に検査する契約がない  
    根拠: tasksは版残存検査から除外され、[PLAN §12:255](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:255) は `test_release_handoff.py` の旧版参照を「あれば」許可する。handoff script/testのactive tagやRelease titleが0.12.0のままでも、操作回数だけ合えば通り得る。  
    推奨: 成功・再開全ケースでtag `docaudit--v0.13.0`→approved SHAと、ReleaseのtagName/title/body必須要素を固定する。

13. [MAJOR] provenance enum否定試験が別のSHA違反だけで通る  
    根拠: [PLAN DoD:120](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:120) はseal後にmanifestとimpactを `"unknown"` へ変更するが、manifestを変えた時点で既存のEVIDENCE.manifest SHA検査が先にREFUSEDを発生させる。enum検査を未実装でも合格する。  
    推奨: manifest SHA・dispatch SHA・impactShaを再構成して整合させ、唯一の異常をprovenance enumにしたfixtureで固定reasonを検査する。

14. [MAJOR] 反復 `--doc-glob` が最後の1件しか使われなくても試験を通る  
    根拠: [PLAN DoD:100](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:100) は反復指定で `not-imported` を確認するだけで、全値が使われたことを検査しない。カンマを含む単一値試験もlast-wins実装を落とせない。  
    推奨: 2つのglobそれぞれにだけ属する影響先を用意し、両方が同時に翻訳・受理されることを検査する。

15. [MAJOR] handoff再開表がno/EOF後の同期再開と失敗点を判別しない  
    根拠: [PLAN §12:265](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:265) はno/EOFの初回結果だけで、次回yの `0/0/0/1` を検査しない。また[再開表:268](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:268) は「境界で失敗」としか書かず、変更系コマンド失敗か直後の読取失敗かで期待呼出回数が変わる。  
    推奨: 各失敗コマンドを明示した二回実行の状態遷移表にし、各runの呼出回数と最終外部状態を別々に検査する。

16. [MAJOR] 空corpus時の `heuristicSaturation` が未定義  
    根拠: [PLAN DoD:107](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:107) は9/9しか固定せず、`docCorpus==0` を扱わない。単純な `heuristicOnly/docCorpus` 実装は0除算する。対象0件で正常完了する監査の回帰になる。  
    推奨: corpus 0ではratioを `0.0`、warningなしと定義して試験する。

17. [MINOR] Phase 5 audit-scope status行は費用に見合わない  
    根拠: [PLAN §9:197](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:197) はstatus行を追加するが、判定には使われず、契約試験にも表示内容がない。Issue #44の単一owner化・drift停止にも不要である。  
    推奨: 成果物から削除し、Phase 0の停止・通知だけに集約する。

18. [MAJOR] config書き込み失敗時のimport lock解放が保証されない  
    根拠: [PLAN §9:185](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:185) は正常系の「原子書き込み→unlink」しか定めない。`os.replace` やfsync失敗時にlock pathを残す実装でもDoDを通り、以後のaudit/importが手動breakまで停止する。  
    推奨: lock取得後の全例外をinode安全なfinally解放の対象にし、置換失敗注入でlock不在を確認する。

## 費用対効果

安全に落とせるのは次の3点。

- EVIDENCE直下の重複 `impactSha`。dispatch.json内だけで封印できる。
- check-verdictsの非0終了。最終REFUSEDはgateへ集約できる。
- Phase 5 audit-scope status行。Phase 0の通知で十分。

`counts.heuristicSaturation` 自体はIssue #40の「coverage ratioを報告する」という中心要件なので落とすべきではない。ただし「表示3桁丸め」は単なる表現規則であり、縮小するなら削除可能。handoff再開試験は外部状態を途中まで変更する処理の回帰防止なので、削除は不適切。

## 計画自体の欠陥（PLANを直してから実装）

1〜9、11、12、17。

## worker指示で吸収できる細部

- 10: 「`impactMap` の各項目に `source:"audit-scope"` を追加した場合と省略した場合で、resolve-impactのJSON出力が完全一致する互換試験をS3に追加せよ。」
- 13: 「全SHAを再計算して整合させたsealed fixtureを作り、唯一の不正値をprovenance=`unknown`にして、enum専用の固定reasonでREFUSEDになることを検査せよ。」
- 14: 「異なる2つの `--doc-glob` にだけ属する文書を各1件用意し、反復指定した両方が翻訳・検証対象になることをassertせよ。」
- 15: 「no→y、EOF→y、および各指定コマンド失敗→再実行を二回実行し、run別の変更呼出回数と最終tag/Release/Issue/sync状態を別々にassertせよ。」
- 16: 「docCorpus=0ではheuristicSaturation=0.0、warningなし、正常終了になる否定試験を追加せよ。」
- 18: 「原子置換失敗を注入し、例外経路でもinodeを照合したfinallyでimport lockが解放されることを検査せよ。」