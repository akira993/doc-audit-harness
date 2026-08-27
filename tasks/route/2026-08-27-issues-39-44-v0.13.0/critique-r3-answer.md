メタ認知: rev.3 の記載量に引っ張られて「仕様化済み＝安全」と判断しないよう、実際の値の受け渡しと競合時の動作を優先した。R2の単純な再指摘は除外している。

結論は「新規指摘あり」。変更は行っていない。`re.DOTALL` は通常の改行なしpathには挙動変化を起こさないが、改行path対応が後続工程まで貫通していない。

1. [BLOCKER] finalized impactがplan-dispatch後からstart-run前まで真正性を失う  
   根拠: [PLAN §10 #39:259](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:259) はstart-runがその時点のimpact.jsonをmanifestへ転記するだけ。plan-dispatchはpath集合を読むがprovenanceをSHAで束縛しない（[plan-dispatch.py:74](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:74)）。plan-dispatch後に同一pathのprovenanceだけ変更するとpartitionを通り、改変値が正規値として封印される。  
   推奨: supplement完了後のimpact全体またはprovenance mapのSHAをdispatch/EVIDENCEへ入れ、start-runが照合してからmanifestへ転記する。

2. [MAJOR] provenance不一致の検出が最終判定に接続されていない  
   根拠: [PLAN DoD:137](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:137) はcheck-verdictsによる一致検査だけを要求する。現行check-verdictsは不一致を `manifestMismatch` に表示しても常にexit 0（[check-verdicts.py:216](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/check-verdicts.py:216)）。decide-verdictはimpact.jsonもchecker結果も読まないため、不一致のままCONSISTENTにできる。  
   推奨: decide-verdict自身にmanifestとrun-dir impactのprovenance完全一致をREFUSED条件として追加する。

3. [MAJOR] manifest.provenanceの型・完全性・許可値が未定義  
   根拠: [PLAN §10 #39:259](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:259) は `{path:prov}` としか規定しない。現行checkerは欠落・非文字列を `"unknown"` に丸める（[check-verdicts.py:23](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/check-verdicts.py:23)）。manifestとimpact双方が同じ不正値なら一致試験を通る。  
   推奨: keysをimpacted集合と完全一致させ、値を既知provenance enumの文字列に限定する拒否契約を追加する。

4. [MAJOR] full用Codexプロンプトの「HEAD tree」が封印対象と矛盾する  
   根拠: [PLAN §10 #42:274](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:274) はHEAD treeを指示するが、fullでも未commit・未追跡変更は監査対象に残る（[compute-baseline.sh:48](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:48)）。Codexは現在のworktreeを読むため、指示と実際に読む内容が食い違い、未commitの文書・コードを無視し得る。  
   推奨: 対象を「manifest.headで識別され、worktreeDigestで封印された現在worktree」と明記する。

5. [MAJOR] required/fullの実Codex実行と既存review共存を判別する試験がない  
   根拠: [PLAN DoD:141](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:141) はgateのstateと表示を検査するだけ。現行SKILLのfull skip（[skills/audit/SKILL.md:474](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:474)）を残し、テスト側でcompleted evidenceを直接与えても通る。existence/semantic/format/code/securityをCodexで置換する誤実装も検出しない。  
   推奨: required/fullで既存review群→Codexを各1回・順序固定で呼ぶshim統合試験を追加する。

6. [BLOCKER] importer lockが実行中でも `--break-lock` で解除できる  
   根拠: [PLAN §9:219](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:219) は `O_EXCL` と最後のunlinkしか規定しない。open-runのbreak処理はflockを取得できればunlinkする（[open-run.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:87)）。importerはflockを保持しないため、取込中のlockが消され、新しい監査lock作成後にimporterがその新lockまでunlinkできる。  
   推奨: importerもfdに排他flockを保持し、解放時にfdとpathのinode一致を確認する共通lock方式へ変更する。

7. [MAJOR] importerのlock pathだけsymlink保護がない  
   根拠: [PLAN DoD:120](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:120) のsymlink拒否はconfig/scopeだけ。`.claude/state` がrepo外へのsymlinkなら、[PLAN §9:220](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:220) のlockはrepo外へ作成される。現行open-runはrun-base全体を検証している（[open-run.py:129](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:129)）。  
   推奨: importerもlock取得前にrun-baseの包含と全symlink構成要素を検証する。

8. [MAJOR] config不在の初回initだけSHA封印とlockを迂回する  
   根拠: [PLAN §9:239](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:239) は初回だけスクリプトの `--write` を使わずinitが直接configを書く。承認後にscopeが変化してもexpected SHAを照合せず、並行importとも排他されない。  
   推奨: 初回もdraft configを入力できる同一のimporter書き込み経路へ統合する。

9. [BLOCKER] DOTALL化で採用した改行pathを後続工程が分割・脱落させる  
   根拠: [PLAN S2:81](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:81) は共有 `docaudit_paths.py` だけをDOTALL化する。一方、generic-layersとimpact-supplementは独自の非DOTALL変換を持つ（[generic-layers.py:29](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/generic-layers.py:29)、[impact-supplement.py:45](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:45)）。compute-baseline等は改行区切りでpathを運ぶため、1つのfilenameを複数pathに分割する（[compute-baseline.sh:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:49)）。合成regex試験だけ通っても実監査は一貫しない。  
   推奨: 今回はCR/LFを含むrepo pathをPhase 1で明示的に拒否するfail-closed契約へ縮小する。

10. [MAJOR] `--doc-globs` のカンマ区切りは既存の文字列配列契約を狭める  
    根拠: [PLAN §9:205](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:205) はカンマ区切りだが、docGlobsの各文字列にカンマを禁止する既存契約はない。`docs/a,b/**/*.md` は誤って2規則に分割される。実物検査は単一globなので通る。  
    推奨: カンマ区切りを廃止し、反復可能な `--doc-glob` 引数にする。

11. [MAJOR] 「各Stageで整合を閉じる」とS5で初めて契約試験を追加する構成が矛盾する  
    根拠: [PLAN Stage表:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:80) ではS2〜S4が重要なSKILL・provenance配線を変更するが、`test_v013_contracts.py` はS5（[PLAN:84](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:84)）。S3/S4の配線が壊れていても、そのStage末のフルスイートはgreenになり得る。  
    推奨: 契約試験の骨格をS1で作り、各Stage担当のassertをそのStage内で有効化する。

12. [MAJOR] 契約試験が重要な値の導出元を確認しない  
    根拠: [PLAN DoD:157](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:157) は行順序や単語を確認するが、初回initのdraft由来 `--doc-globs`、承認結果由来の2 SHA、metadata由来のcustom scope path、workflow TASKのmanifest.provenance由来を検査しない。既定pathや古いorchestrator保持値を使っても通る。  
    推奨: 各コマンド行の必須引数だけでなく、その値がどの変数・封印済み入力から来るかまで構造検査する。

13. [MAJOR] 1本の統合試験ではregression採用とcap落ちを判別できない  
    根拠: [PLAN DoD:132](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:132) は同じ試験で「最新FAILがdispatch入り」と「regressionがcapで全落ち」を要求する。最新FAILがmappedとして残り、regression候補が0件でも後者を空集合として通せる。逆に同じregression文書を対象にすると両立しない。  
    推奨: regressionが少なくとも1件残るケースと、少なくとも1件capで落ちるケースを別プロセスに分ける。

14. [BLOCKER] `0.12.0` 残存検査がcommit前には見逃し、handoff時にはPLAN自身で失敗する  
    根拠: [PLAN DoD:164](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:164) は `git ls-files` 対象だが、PLAN/REVIEWは実装中には未追跡で、最終的に `git add -f` される（[PLAN §7:180](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:180)）。両ファイルには多数の `0.12.0` があり、[§12の許容リスト](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:306) にない。S5ではgreenでも、commit済みSHAで実行するhandoffではredになる。  
    推奨: 版残存検査を明示した出荷物path集合だけに限定する。

15. [MAJOR] handoff試験はIssue close回数だけ合えば誤対象でも通る  
    根拠: [PLAN §12:313](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:313) はIssue closeを6回としか固定しない。#39を6回呼ぶ実装でも回数上は合格する。  
    推奨: close対象の完全な集合が `{39,40,41,42,43,44}` で各1回であることを検査する。

16. [MAJOR] 単段handoffの途中失敗からの再開を検証していない  
    根拠: [PLAN §12:313](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:313) は開始状態別の試験で、tag push、Release作成・照会、6件のIssue close途中に失敗した場合を注入しない。部分成功後の再実行で重複操作や永久停止が起きても検出できない。  
    推奨: 各外部変更境界で1回だけ失敗させ、再実行で重複なく成功へ収束する表駆動試験を追加する。

17. [MAJOR] 同期先symlinkを既知のまま公開処理後まで検査しない  
    根拠: [PLAN §12:318](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:318) は同期先symlink時でもtag 1・Release 1・Issue close 6を期待する。同期先pathは開始時点で検査可能なのに、公開操作を完了してから安全違反で停止する設計になっている。  
    推奨: 同期先のsymlink・包含・書込可能性をtag作成前のpreflightへ移す。

18. [MINOR] auto項目の集合比較は重複数のdriftを見逃す  
    根拠: [PLAN §9:228](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:228) は「項目集合」で比較する。同一auto項目が2件ある状態から1件削除しても集合は同じで `in-sync` になる。DoDのauto削除試験が一意項目だけなら誤実装でも通る。  
    推奨: 集合ではなく重複数を保持するmultisetで比較する。

## 計画自体の欠陥（PLANを直してから実装）

1〜11、13、14、17。特に1、6、9、14は実装前に解消すべきBLOCKER。

## worker指示で吸収できる細部

12、15、16、18。いずれも設計方向は維持できるが、現状のDoDでは誤実装を判別できない。