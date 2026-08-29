メタ認知: 最終ラウンドで承認へ寄る圧力を排しつつ、撤回済みSHA層は再審議しないよう境界を限定した。

結論: §0のrescopeと§9への技術的切り出しは妥当。ただし計画欠陥が残るため、rev.5は実装承認不可。

fresh・単体呼び出し、および再probeが正常完了するresumeでは、キー無し時のtool不起動経路は閉じている。

## 計画自体の欠陥

### 1. `probe-record` の「他seamは上書き拒否」が現行契約と正反対

重大度: High

根拠:

- PLANはwebExtract/codexReviewだけ上書きを許し、他seamを拒否するとする（[PLAN.md:64](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:64)、[PLAN.md:128](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:128)）。
- 現行実装はseamを問わない汎用upsertである（[probe-record.py:332](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:332)）。
- 歴史テストもindexingの再記録・上書きを固定している（[test_probe_record.py:84](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:84)、[test_probe_record.py:97](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:97)）。

指定どおり実装すると、既存seamの上書きを新たに拒否する回帰になる。

推奨修正: 汎用atomic upsertは変更せず、webExtract/codexReviewが置換され、他seamが保持される正テストだけ追加する。

### 2. resume再probe自体が失敗した場合の運用値が未定義

重大度: High

根拠:

- resumeではoperational値をrebindから復元せず再probeする（[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:78)）。
- rebindは「表示fallbackのみ」とされる（[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:83)）。
- checkpointはavailability/reason/binを保持しない（[SKILL.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:45)）。
- 再probeが起動不能・非JSON・parse失敗になると、Workflowの`AX_AVAILABLE`（[SKILL.md:481](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:481)）とCodexの3値（[SKILL.md:577](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:577)、[SKILL.md:600](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:600)）に安全な値がない。

旧rebindのtrue値へ戻せばkeyless保証を破り、未束縛のままならresumeが壊れる。

推奨修正: 再probeの起動・JSON・parse失敗は、旧rebindを運用に使用せずrunをreleaseして停止する、と明記して固定する。

### 3. checkpoint (h) resumeで完走済みCodex reviewが表示上隠れる

重大度: Medium

根拠:

- resumeは現在のkeyless configでCodex probe recordを`not-configured`へ上書きする（[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:78)）。
- `codexReviewState=completed`は別seamとして残り、rebindで新probe記録と結合される（[probe-record.py:279](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279)）。
- PLANは`not-configured`をcompletedを含む4-wayより優先する（[PLAN.md:85](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:85)）。
- completed表示は4-way側にある（[SKILL.md:757](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:757)）。

所見はverdictに保持されるのに、状態行は「not configured」となり、固定文の「完走済み所見を保持」と表示上矛盾する（[PLAN.md:102](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:102)）。

推奨修正: `reviewState=completed`ではcompleted表示を優先し、専用not-configured行はnull/not-activeに限定する。

### 4. 再probe成功後の再記録失敗で、旧recordを正常表示してしまう

重大度: Medium

根拠:

- PLANは上書きによってPhase-5とcaller情報が現在のconfigに整合するとする（[PLAN.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:80)）。
- record書込み失敗は既存契約ではnon-blockingである（[SKILL.md:653](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:653)）。
- atomic書込み失敗時は旧recordが残る（[probe-record.py:207](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:207)）。
- Phase-5はrecordのrebindを表示元にする（[SKILL.md:643](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:643)、[SKILL.md:649](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:649)）。

運用上はtoolを起動しなくても、旧`available:true/ok`と旧caller pathが正常値として表示される。

推奨修正: resume再記録に失敗したseamは旧値へfallbackせず、当該runでは`state unknown`表示に強制する。

### 5. handoffの「全件複製」が歴史テストの途中で切れている

重大度: High

根拠:

- PLANの複製範囲は`test_release_handoff.py:289-410`までで、完了条件も14件以上である（[PLAN.md:163](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:163)、[PLAN.md:175](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:175)）。
- その後にも、既存tagからの途中再開（[test_release_handoff.py:413](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:413)）、事前close済みIssue（[test_release_handoff.py:425](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:425)）、公開後の同期拒否（[test_release_handoff.py:440](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:440)）がある。

単純な「成功後にもう一度実行」だけでは、tag作成済み・Release未作成などの部分状態を検証できない。

推奨修正: 複製範囲を`:289-446`の全test method相当へ広げ、上記3ケースを完了条件へ明記する。

### 6. 新Issueが未起票でも#56をclose・出荷できる

重大度: Medium

根拠:

- TOCTOU追跡は「ユーザー承認待ち」で番号がない（[PLAN.md:12](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:12)、[PLAN.md:221](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:221)）。
- 一方、#56 closeとhandoffは無条件に進む（[PLAN.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:23)、[PLAN.md:219](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:219)）。
- handoff試験も新Issueの存在・OPEN状態・Release notes参照を要求しない（[PLAN.md:160](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:160)）。

技術的な切り出し内容は十分だが、既知のverdict-steeringリスクがGitHub上で未追跡のまま残り得る。

推奨修正: 新Issueの起票・番号記録・OPEN確認・Release notes参照をrelease-handoffの前提条件にする。

## worker指示で吸収できる細部

### 7. resume契約テストが文言存在だけで、配線順を証明しない

重大度: Medium

根拠:

- PLANの検査はresume節に両probe名・再記録文言があり、旧restore文言がないことだけを要求する（[PLAN.md:139](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/PLAN.md:139)）。
- 実際のconsumerはaxのWorkflow（[SKILL.md:482](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:482)）とCodex planner（[SKILL.md:577](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:577)）である。

再probeをconsumerより後へ置く、probe stdoutと別の値を記録する、という誤配線でも通る。

推奨修正: worker検収で、同じprobe stdoutから運用3値を束縛・記録し、その処理が各consumerより前にあることを直接assertする。

§9に挙げたTOCTOU対策をv0.15へ戻す必要はない。上記1〜6をPLANで修正後に実装へ進めるべきである。ファイル変更は行っていない。