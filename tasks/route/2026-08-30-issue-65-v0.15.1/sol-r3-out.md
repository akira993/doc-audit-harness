メタ認知: 対応策の詳細さに引っ張られず、「その検査が本当に反例を区別できるか」と「別プロセスにも契約が届くか」で判定した。

## 計画自体を直す必要がある指摘

1／HIGH（前回 #1・#10 対応不十分）／内部改行の扱いが実物と逆で、安全な値受渡しも未定義  
根拠: [PLAN.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:80) は「改行を含む`CODEGRAPH_DIR`は無効」とするが、codegraphは前後trim後、空・`.`・`..`・`/`・`\`・絶対パスだけを拒否する（[directory.js:85](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/directory.js:85)）。したがって`foo\nbar`や`foo bar`は有効である。既存probeはPython出力を空白・改行区切りの`read`で受けるため（[codegraph-probe.sh:28](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:28)）、同じ呼出しへDIRNAMEを追加すると値を壊し得る。  
推奨: Python→Bashの受渡しをNUL区切り等で明文化し、内部空白・タブ・改行を有効入力として、判定先・fake環境・`%q`の1行stderrを検査する。

2／HIGH（前回 #1 対応不十分）／明示exportはPhase 3へ伝播せず、後段が別索引を見る  
根拠: [PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:41) のexportはprobeが起動する`init/sync`子プロセスだけに有効で、親や別agentには戻らない。現行はWorkflowへavailabilityだけを渡し（[SKILL.md:214](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:214)、[workflow-template.js:94](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:94)）、後段は環境指定なしの固定`codegraph impact/node`を案内する（[workflow-template.js:131](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:131)）。Phase 0が`.codegraph-win`を初期化して`ok`でも、別agentが環境を継承しなければ`.codegraph`を問い合わせる。  
推奨: 解決済みDIRNAMEをsealed Workflow引数へ渡し、後段コマンドにも安全に明示設定する契約とテストを追加する。

3／HIGH／新たに増える`init`経路が不可視プロンプトと計画外書込みを起こし得る  
根拠: [PLAN.md:53](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:53) はstdinを継承したままstdout/stderrだけを隠す既存呼出しを維持する。codegraph 1.5.0の`init`は空索引時に対話確認を行い、承認されると`codegraph.json`を書き換える（[codegraph.js:622](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/bin/codegraph.js:622)、[codegraph.js:472](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/bin/codegraph.js:472)）。watch無効環境ではGit hookの選択・設置も行う（[installer/index.js:596](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/installer/index.js:596)）。N1〜N3によりこの経路へ入る対象が増える。  
推奨: probe実行を明示的に非対話化し、索引ディレクトリ以外のrepoファイルとGit hookが不変であることをPTY付きテストで固定する。

4／HIGH（前回 #3 対応不十分）／テスト下限が再び必須ケース数より小さい  
根拠: [PLAN.md:62-80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:62) の新規状態は、N5b/N9bを含め16個である。「1状態1method」ならprobeは20+16=36件で、33では3件欠落しても通る。handoffも24+ #66正負2+新規残骸検査1=27件で、G3の26は不足する。さらにG1記載の`630+13+1+2+2`自体が648であり647ではない。仕様どおりの最低値は652。  
推奨: G1/G2/G3をそれぞれ`≥652`、`≥36`、`≥27`へ統一する。

5／HIGH／G8はコミット済みrenameの旧パスを取得できない  
根拠: [PLAN.md:123](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:123) は`git diff --name-only -z`からrename両端を得るとするが、scratch実測ではrename commitの出力は`new name\0`だけだった。禁止ファイルを許可パスへrenameすると、旧パス削除を見逃してG8が通る。  
推奨: committed側を`git diff --name-status -z --find-renames --find-copies`等へ変更し、R/Cの旧新両パスを解析する。

6／HIGH（前回 #5 対応不十分）／ignored除外により明示禁止範囲を検査できない  
根拠: G8はignoredを除外するが、[.gitignore:8](/Users/akiratakahashi/Projects/doc-audit-harness/.gitignore:8) は`tasks/`、同9行目は`docs/superpowers/`を無視する。後者や他routeは[PLAN.md:152](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:152) で明示禁止されているのに、変更・新規作成してもG8には現れない。force-addの説明は公開対象だけに効き、禁止ignoredファイルには効かない。  
推奨: 着手前に禁止ignored範囲のmanifest/hashを記録し、完了時に不変比較する別ゲートを追加する。

7／HIGH（前回 #12 対応不十分）／G10と許可globは正しい状態を失敗させるか過剰許可する  
根拠: [PLAN.md:125](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:125) は`*-log.txt`・`PLAN.rev*.md`が「存在しない」ことを要求するが、現物には両方存在し、[PLAN.md:150](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:150) は「追跡されていないこと」としており矛盾する。またPython `fnmatch`は`{...}`を展開しないため、§7のbrace表記は正しい`PLAN.md`にも一致しない。逆に`prompts/*.md`は実測で`prompts/nested/secret.md`にも一致する。  
推奨: 許可・force-add対象を機械可読な具体的パス配列にし、除外ログは「物理不存在」ではなく`git ls-files`一致0件で判定する。

8／HIGH／G3の「改名先が存在」ではrelease安全契約を維持できない  
根拠: [PLAN.md:118](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:118) はworker報告の対応表と改名先の存在だけを要求する。例えば`test_close_calls_target_only_issue_65`を空の`pass`にし、無意味なmethodで件数を補ってもG1/G3は通る。また比較元が可変の`main`なので、merge後は削除された旧methodが基準側からも消える。  
推奨: e1c0b19基準の正確な改名対応をgateに固定し、close集合・release notes・OPEN事前条件を独立した不変契約として直接検査する。

9／HIGH（前回 #7 対応不十分）／#66の出現数テストは分岐削除を見逃す  
根拠: [PLAN.md:103](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:103) は状態トークンを3箇所以上と数えるだけである。現行3箇所（[SKILL.md:560](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:560)、[SKILL.md:563](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:563)、[SKILL.md:778](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:778)）に、許可された注記が1個増えれば、実際の束縛を1個削除しても3件を満たす。`disable-model-invocation`もstatus文だけ残して実分岐を削除できる。  
推奨: 件数ではなく、2つの束縛分岐とstatus行それぞれの完全な文脈を個別に固定する。

10／HIGH／A2は各G検査が「常にPASSでない」証明にならない  
根拠: [PLAN.md:131](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:131) の変更前実行はG2/G4/G5/G6だけでも全体をFAILにする。したがってG3やG8が無条件PASSでもA2は同じ結果になり、個別検査の有効性を証明しない。  
推奨: G1〜G10ごとに1つの意図的違反fixtureを与え、その検査単独がFAILになる自己テストをgate.pyへ持たせる。

## worker指示で吸収できる指摘

11／MEDIUM／N12のfixtureでは判定先を区別できない  
根拠: [PLAN.md:76](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:76) は判定dirも検査するとだけ定める。既定dirと生入力dirがともに不存在なら、どちらを見ても`init .`となる。誤ったdirを判定しつつfakeへだけ正しい環境値を渡す実装が通る。  
推奨: 選択すべきdirだけに通常DBを置き、選択を誤ると`sync`と`init`が逆になるfixtureを各subTestで作る。

12／MEDIUM／danglingな親symlinkが未検査  
根拠: 分岐表は親DIRのsymlinkにdanglingを含める（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:45)）が、N8は有効なsymlinkだけである（[PLAN.md:71](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:71)）。`-L && -d`相当の誤実装はdangling symlinkを不存在扱いしても通る。  
推奨: dangling `.codegraph` symlinkを追加し、不実行・`index-failed`・symlink stderrを固定する。

13／MEDIUM／N13は既存エラー詳細契約を検査しない  
根拠: [PLAN.md:79](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:79) はsubcommandだけをstderrで確認する一方、[PLAN.md:53](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:53) は`rc=..`と元stderr末尾の維持も契約にする。終了値や診断末尾を欠落させても通る。  
推奨: fakeに固有の非1終了値とstderr印を出させ、init/sync双方で`rc`と末尾印を検査する。

14／MEDIUM／G8は§7の行単位制限を検査しない  
根拠: [PLAN.md:148](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:148) は`SKILL.md`と`config-schema.md`の変更可能行を限定するが、G8はパス単位の許可だけである。許可ファイル内の無関係な行を変更しても機械ゲートは通る。  
推奨: この2ファイルについて、許可された差分領域以外がe1c0b19と同一である検査を追加する。

計画自体を直すべき HIGH の一覧: **1、2、3、4、5、6、7、8、9、10**  
このまま実装に進めてよいか: **進めるべきではない。rev.3はDIRNAME伝播とゲートの観測範囲に未解決の欠陥があり、正しい完了判定を保証できない。**