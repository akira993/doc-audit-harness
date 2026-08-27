メタ認知: 前回の23指摘を言い換えて再提出する偏りと、厳格さを優先して仮説まで重大化する偏りに注意した。今回は rev.2 で新しく生じた矛盾か、現行コード・実物で裏づけられる取りこぼしに限定した。

結論は「新規指摘あり」。ファイル変更は行っていない。

実物の `dir-framework` は24規則すべてが新しい構文制限を通過した。追跡済み46ファイルとの1,104組の比較でも差異は0件だった。したがって規則の実用性低下は現時点ではない。ただし同リポジトリには `.claude/doc-audit.json` がなく、PLANどおりの検査手順ではこの確認地点まで到達できない。

1. [BLOCKER] 初期導入と「ファイル必須」検証が両立しない  
   根拠: [PLAN §9:226](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:226) は `--config`/`--scope` を既存通常ファイルとして検証する一方、[PLAN §9:254](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:254) は scope 不在、[PLAN §9:267](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:267) は config 不在で `--check` を要求する。現行 `validate_repo_path()` は既定で不在を拒否する（[docaudit_paths.py:37](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:37)）。実物の `dir-framework` も config 不在なのでDoDが開始直後に失敗する。  
   推奨: パスの安全確認と存在確認を分離し、config不在時はinitが生成したインメモリのdraftを比較元として渡す契約に一本化する。

2. [BLOCKER] drift停止をopen-run前に移すと、古いlockからの復帰経路が閉じる  
   根拠: [PLAN §9:259](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:259) は検査をopen-runより前に置くが、現行 `/audit --break-lock` はopen-run系の処理を入口としている（[skills/audit/SKILL.md:17](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:17)）。driftと古いlockが同時にあると、監査はdriftで停止し、importはlock存在で拒否されるため、正規の回復操作がない。  
   推奨: `--break-lock` の処理だけはscope検査より先に実行し、その後に通常のlock取得とscope検査を行う順序をPLANに固定する。

3. [MAJOR] 差分承認から書き込みまでの内容が封印されていない  
   根拠: [PLAN §9:246](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:246) はlockの「存在確認」だけ、[PLAN §9:265](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:265) は別プロセスの `--check` と `--write` を要求する。承認後にscope/configが変更されたり、存在確認後に監査lockが作成されたりしても別内容を書ける。  
   推奨: `--check` がconfigSha/scopeShaを返し、`--write` がその両SHAを必須照合したうえで同じlockを排他的に取得する方式にする。

4. [BLOCKER] `required:true` とfull REFUSEDは、baseline喪失後に永久ループする  
   根拠: anchor不在・履歴から消失時は必ずfullになる（[compute-baseline.sh:33](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/compute-baseline.sh:33)）。一方、[PLAN §10 #42:323](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:323) はfullでもCodexを実行せずREFUSED、かつanchorを更新しない。以後も毎回full→REFUSEDとなる。「最初のbaseline後に有効化」では、anchor破損・履歴書き換え・明示fullを救えない。  
   推奨: `required:true` のfullではCodex reviewも実行し、実行不能時だけREFUSEDにする。

5. [MAJOR] 「REFUSEDではlast-run非更新」は既存の拒否記録を壊す  
   根拠: [PLAN DoD:147](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:147) はlast-run非更新を要求するが、現行REFUSEDは理由・時刻・report状態を `docaudit-last-run.json` に記録し、それを拒否report生成にも使用する（[decide-verdict.py:875](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:875)）。非更新化すると利用者には以前の成功状態が残る。  
   推奨: 非更新対象をhistoryとanchorに限定し、last-runは固定理由付きREFUSEDへ更新する契約に戻す。

6. [MAJOR] `impactSha` がCodex経路しか保護せず、workflow経路のprovenanceは未封印  
   根拠: [PLAN §10 #39:300](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:300) は `codex-dispatch.py` の照合だけを規定する。workflowはSKILL内で保持したprovenanceを使い（[skills/audit/SKILL.md:389](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:389)）、`check-verdicts.py` はmanifestとimpactのpath集合しか比較しない（[check-verdicts.py:96](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/check-verdicts.py:96)）。同一pathのprovenanceだけ変更されても検出されない。  
   推奨: provenanceをmanifestへ封印し、workflow/Codexの両方が封印済みmanifestから読む契約にする。

7. [BLOCKER] 統合試験の工程が実コードと一致せず、gateまで到達できない  
   根拠: [PLAN DoD:140](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:140) は `start-run（seal）` とするが、start-runは `sealed:false` を書くだけ（[start-run.py:201](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:201)）。封印は別の `seal-run.py`（[seal-run.py:34](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:34)）であり、returns/Phase 4 evidenceの作成も工程にない。  
   推奨: `resolve → supplement → plan-dispatch → start-run → seal-run → returns/phase4 evidence → decide-verdict` を実プロセス試験の固定工程にする。

8. [BLOCKER] S1でengineを変更し、S4までversion/hashを更新しない分割は各Stage全試験と矛盾する  
   根拠: [PLAN Stage表:87](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:87) でS1が `generic-layers.py` を変更し、versionとengine-shasはS4（[PLAN:90](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:90)）。しかし各Stageで全試験を要求し、既存試験は現versionに対応するhashとの完全一致を検査する（[test_scaffold.py:278](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_scaffold.py:278)）。S1完了時点は必ず赤になる。  
   推奨: #43本体・plugin version・engine-shas・scaffold契約試験を同じStageへ移す。

9. [MAJOR] `required:false` なら壊れた `codexReview` evidenceを黙認できる  
   根拠: [PLAN §10 #42:318](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:318) はstate型を定めるが、拒否条件はrequired時に偏っている。`write-evidence.py` は変更禁止で、既存の所見判定も追加キーを検証しないため、optional時には `{codexReview: []}` や未知stateを含む破損evidenceでもCONSISTENTになり得る。  
   推奨: `codexReview` が存在する場合はrequired値に関係なくobject型・キー・enumを厳格検証し、不在だけを後方互換として許可する。

10. [MAJOR] Phase 5の「3状態」契約と、列挙された表示状態が4つある  
    根拠: [PLAN §10 #42:331](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:331) は `not-active / skipped-full / completed / failed` の4状態を列挙する一方、[PLAN契約試験:167](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:167) は「3状態」を要求する。どちらを正としても片方の試験が誤る。  
    推奨: Phase 5表示を4状態契約として明記し、4分岐を個別に試験する。

11. [MAJOR] list継続規則は通常文をインデントコードとして過小マスクする  
    根拠: [PLAN §10 #43:340](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:340) は `content indent + 4` 以上を無条件にコード扱いする。しかしインデントコードは段落を中断できないため、空行なしの深い継続文まで隠してしまう。またtabは常に4列加算ではなく、次の4列境界まで進む。現在の対テストは簡単なtab位置なら誤実装でも通る。  
    推奨: 空行・段落状態を追跡し、tabを列境界展開する規則へ変更して、空行なし深インデントと非ゼロ列tabを反例に加える。

12. [MAJOR] `saturationWarnRatio` の型契約が自己矛盾している  
    根拠: [PLAN §10 #40:280](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:280) は「float、0〜1」とする一方、JSON整数の `0` を無効化値とする。厳格なfloat検査なら文書どおりの `0` を拒否し、数値一般として扱えば型契約試験と食い違う。丸め前後どちらで閾値比較するかも未定義。  
    推奨: boolを除く数値型を受理し、ゼロを比較前に無効化、閾値比較は丸め前の比率と明記する。

13. [BLOCKER] handoffの「全安全分岐で外部変更0回」は処理順と両立しない  
    根拠: [PLAN DoD:172](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:172) は各分岐でtag/Release/Issue close/rsyncがすべて0回とするが、[PLAN §12:379](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:379) の順序ではtag・Release・Issue close後に同期確認を行う。確認no/EOFではrsyncだけ0回で、先行3操作は既に実行済みでなければならない。  
    推奨: 分岐別の期待回数表に変更し、事前失敗は全0、no/EOFはrsyncのみ0、成功・resumeは必要操作の正確な回数を検査する。

14. [MAJOR] handoff否定試験が複合故障のため判別不能  
    根拠: [PLAN §12:385](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:385) はHEAD不一致とorigin不一致を同時にし、Release不正もdraft/prerelease/notes不一致を一括する。一項目しか検査しない誤実装でも通る。PR番号の欠落・非数値も分岐にない。  
    推奨: 1ケース1故障に分解し、各条件を単独で壊したサブテストにする。

15. [MAJOR] `test_v013_contracts.py` は文字列の存在だけで誤配線を見逃せる  
    根拠: [PLAN契約試験:163](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:163) は7消費側やargument-hintの検査対象を挙げるが、値の流れや実行順を規定していない。例えばコメント中に `regression` がある、本文に引数名がある、到達不能なPhase 5表示があるだけでも単純grepは通る。scope check→停止、Phase 2へのhistory、Phase 4 evidenceへのstateという重要な接続も対象外。  
    推奨: front matterは構造解析し、各SKILLはコマンド・引数・順序・分岐を一意な意味単位で検査する。

16. [MAJOR] custom `--scope` が次回監査へ引き継がれない  
    根拠: [PLAN §9:247](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:247) はmetadataにscope pathを保存するが、[PLAN §9:259](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:259) のPhase 0呼び出しは既定path前提で、保存したpathを読む契約がない。custom scopeへimportした直後から別ファイルを検査し得る。  
    推奨: Phase 0はconfig metadata内の保存済みscope pathを唯一の入力として再検証する。

17. [MAJOR] コメント接頭辞によるauto所有判定は手書き規則を削除できる  
    根拠: [PLAN §9:247](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:247) はnoteの接頭辞でauto項目を識別する。利用者が同じ文言から始まるnoteを書いた場合、それも再生成対象として置換・削除される。「手書き項目保持」試験だけではこの衝突を検出できない。  
    推奨: 人間向けnoteではなく、予約済みの構造化ownershipフィールドでauto項目を識別する。

18. [MAJOR] globの形式的等価性は改行を含むファイル名で破れる  
    根拠: [PLAN §9:238](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:238) は許可構文内で意味論同一を主張するが、Python `fnmatch` のstar変換は改行も対象にする一方、現行 `glob_to_regex()` の `.*` は通常の正規表現設定では改行に一致しない（[docaudit_paths.py:20](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:20)）。追跡済み集合の比較では将来追加される特殊名を検出できない。  
    推奨: 両エンジンを同一の正規表現フラグに統一し、改行を含むpathを形式テストへ入れる。

19. [MAJOR] 版残存検査が正しい履歴記述と作業用worktreeを誤検出する  
    根拠: [PLAN §12:374](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:374) の全体検索は追跡ファイルに限定されておらず、`.claude/worktrees/**` も対象になり得る。さらに許容リストには正当なv0.12.0履歴である [ADOPTION.md:139](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:139) と [ADOPTION.ja.md:124](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:124) がない。正しい実装でも失敗する。  
    推奨: `git ls-files` で追跡ファイルだけを検索し、両ADOPTION履歴行を許容リストへ追加する。

20. [MAJOR] 0.12.0→0.13.0 engine-shas更新試験の入力fixtureがない  
    根拠: [PLAN §12:372](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:372) は旧stampからの更新を要求するが、保存済みengine fixtureは0.10.1だけで、現行0.12.0のengine本文とhashを固定する成果物がない。S1で本文を変更すると、旧stampを再現できなくなる。  
    推奨: S1開始前に現行0.12.0 engineを不変fixtureとして保存し、その正規化hashが現行engine-shasと一致することを固定する。

21. [MINOR] report除外後corpusの検証に対応する否定試験がない  
    根拠: [PLAN §9:231](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:231) は `auditReportsInCorpus:false` 時のreport除外後corpusを要求するが、[PLAN DoD:126](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:126) は単にdocGlobs外の影響先しか試していない。report除外を無視する誤実装でも通る。  
    推奨: 同一設定を `auditReportsInCorpus:false/true` で対にし、前者だけ拒否される試験を追加する。

## 計画自体の欠陥（PLANを直してから実装）

1〜13、16〜20。特に1、2、4、7、8、13は実装開始前に解消すべきBLOCKER。

## worker指示で吸収できる細部

14、15、21。いずれも設計の方向自体は維持できるが、誤実装を通さないようテスト入力と検査方法を具体化する必要がある。