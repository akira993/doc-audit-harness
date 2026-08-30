メタ認知: 最終ラウンドなので軽微な実装選択を過大評価しない一方、新設した lock holder 機構を設計済みとみなさず、故障途中まで確認した。

結論は、まだ収束していない。履歴・eligibility・件数は概ね閉じたが、lock holder の更新・回復契約に実装前に直すべき穴が残る。

[R5-1] Major 「自runのlock fdを持つ＝holder markerを必ず永続化できる」という前提が成立しない  
→ 根拠: S5はlast_run書込みに失敗してもholderには書けると断定する（[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:49)）。しかしfd所有はdisk full、EIO、部分書込み、fsync失敗を防がない。現holderは単一JSONを一度だけ書く形式で（[open-run.py:191](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:191)）、atomic replaceするとinodeが変わりEVIDENCEの`lockIno`検査に失敗する（[decide-verdict.py:663](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:663)）。単純な上書きでは短いJSONの後ろに旧末尾が残り得る。書込み失敗で旧holderがmarkerなしのまま残ると、last_runもholderも隔離待ちを示さず、break後にtainted historyを利用できる。  
→ 推奨する修正: holderを初期状態から「未清算」とするfail-safeなschemaにし、安全な終了時だけ同一inode上の検証済みrewriteで解除し、書込み・再読失敗や不正holderは常に隔離待ちとして扱う。

[R5-2] Major 隔離回復前のflock・inode・runid検査順と、旧lockの処分が未定義  
→ 根拠: S4は通常open・release・breakすべてでhistoryをrenameさせるが（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:45)）、回復処理をexclusive flock取得後に限定していない。現行通常openは既存lockをflockなしで読む（[open-run.py:193](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:193)）。安全なflock→fd/path inode照合→runid照合はrelease経路にしかない（[open-run.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:87)）。回復成功後に旧lockを残せば、fresh lockの`O_EXCL`が失敗してCT-4の「open成功」と両立しない（[open-run.py:194](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:194)、[PLAN.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:81)）。  
→ 推奨する修正: 全モード共通で `O_NOFOLLOW→exclusive flock→fd/path inode一致→holder object検証→release時runid一致→隔離→同一旧lockをunlink→必要ならfresh lock作成` の順序を固定する。

[R5-3] Major last_runの非object・marker型不正が、不正JSONと同じcold-start回復にならない  
→ 根拠: §1とS4は不正JSONと非objectを同じ`last-run-unreadable`として扱う（[PLAN.md:10](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:10)、[PLAN.md:44](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:44)）。ところが両markerが隠れていた可能性を理由にlive historyを隔離する規則は「不正JSON」にしか適用されない（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:45)）。`[]`、`null`、文字列、markerが非boolの場合は、同じ不読状態なのにhistoryを維持して開くか、`.get`例外になる。CT-4も不正JSONだけを検査する（[PLAN.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:81)）。  
→ 推奨する修正: parse失敗・非object・marker非boolを単一のunreadable状態に正規化し、すべてに同じacceptance＋history cold-start規則を適用する。

[R5-4] Major CT-5がfilesystem非依存parserと正反対のsymlink判定を要求している  
→ 根拠: S9はhistory parserを字句検査だけに限定し、symlink検査をcarry-forward時へ移した（[PLAN.md:65](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:65)）。一方CT-5はsymlink成分を含む`phase4Runs`を4 readerすべてでcorruptにするよう要求したままである（[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:83)）。symlink判定は現在のfilesystemに依存する（[docaudit_paths.py:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:49)）ため、両契約は同時に満たせない。  
→ 推奨する修正: CT-5を「保存後にpathがsymlink化してもhistoryはvalid、carry-forwardからだけ除外」に反転する。

[R5-5] Major S14はv5で新設・変更した主要経路の誤実装を判別できない  
→ 根拠: CT-4/CT-5はlast_run marker成功時しか扱わず、holder-only marker、holder不正JSON、flock競合、inode差替え、releaseのrunid不一致を検査しない（[PLAN.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:81)、[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:83)）。plan-dispatchの新exit 7 funnelにもE2Eがなく、現行テストはexit 3を期待している（[test_plan_dispatch.py:40](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_plan_dispatch.py:40)）。§9.7は8組を完全列挙したが、CT-5はmode×variant不一致だけで、`null×completed`、`full×not-active`、キー欠落を検査しない（[PLAN.md:195](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:195)、[PLAN.md:208](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:208)）。  
→ 推奨する修正: holder回復状態表、plan-dispatch taint funnel、§9.7の8 valid＋各invalid classを直接駆動するtable-driven E2EをS14に追加する。

再計数は N=22／M=4／G=13／K=21／O=19 で一致する。lock holder markerはconfig consumerやobserverを増やさないため、件数変更は不要。

計画自体の欠陥（PLANを直してから実装）:

- R5-1〜R5-3: lock/markerの永続化・同期・回復状態
- R5-4: parser契約とテストの直接矛盾
- R5-5: 新規契約を判別できるテスト不足

worker指示で吸収できる細部:

- 同一inode rewriteのwrite loopや一時bufferの実装方法
- fault injection fixtureやtable-driven testの具体的な構成

これらの実装方法はworkerに委ねられるが、状態・順序・期待結果はPLANで固定する必要がある。ファイル変更は行っていない。