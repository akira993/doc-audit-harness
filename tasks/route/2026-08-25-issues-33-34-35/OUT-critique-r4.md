メタ認知：過去の自分の指摘を維持したくなる一貫性バイアスを警戒し、rev.4 の最終裁定を新しい前提として、内部整合性と実害だけを再評価した。

bare path を常に WARN とする裁定は受容する。非blocking の検出網と明示すれば、R3 の偽陽性問題と両立する。また、unsuffixed を1件目と数えるなら `_02` 開始は `(_[0-9]{2,})?` と整合する。機構除外と corpus opt-in の分離、`compute-baseline.sh` 変更禁止、3 SHA 同期にも新たな欠陥は確認しなかった。

1. **BLOCKER — 非ASCII backtickの仕様とテスト期待値が両立しない。**  
   `docs/旧概要.md` は basename がドット始まりではなく、拡張子 `md` が定義された形式に一致するため、解決不能なら仕様上は FAIL になる（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:60)、[PLAN.md:89](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:89)）。一方、テスト計画は同じ backtick パスを WARN と要求している（[PLAN.md:189](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:189)）。同一実装で双方は満たせない。

2. **BLOCKER — percent-decode後のNUL文字で監査全体が異常終了する。**  
   `[A-Za-z0-9_./+%@~-]` は `docs/%00.md` を収穫する。復元後は `docs/\x00.md` となり、計画どおり `os.path.realpath()` に渡すと、この環境では `ValueError: lstat: embedded null character in path` が再現する（[PLAN.md:56](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:56)）。文書内容だけで監査を停止できるため、復元後の再検証・例外処理と回帰試験が必須である。`%2e%2e` による復元後の `..` も再検査対象として未定義。

3. **MAJOR — FAIL判定に使う正規化後のパスが未定義である。**  
   解決時には `#`・`?`・`path:line`・percent encodingを処理する一方、具体的ファイル判定を元token、接尾辞除去後、percent-decode後のどれに適用するか決まっていない（[PLAN.md:56](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:56)、[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:60)）。元tokenなら、欠落した `` `docs/gone.md?raw=1` ``、`` `docs/gone.md#x` ``、`` `docs/gone.md:12` ``、`` `docs/gone%2Emd` `` は拡張子判定から外れてWARNへ誤降格する。特に `path:line` はFAILを要求するテスト計画自身と矛盾する（[PLAN.md:194](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:194)）。

4. **MAJOR — fenced codeの簡易拡張は入れ子構造でblocking偽陽性を残す。**  
   blockquoteを剥がしてからlist markerを1個だけ剥がす規則では、list内blockquoteの `- > ```text` や入れ子listを認識できない。またCommonMarkで有効な ordered-list marker `1)` も対象外である（[PLAN.md:43](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:43)）。内部の `` `docs/gone.md` `` がFAILになり得るが、テストはblockquoteとlistの単体だけである（[PLAN.md:191](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:191)）。マーカーの反復・順序か、少なくとも組合せと `数字)` の契約が必要。

5. **MAJOR — レポート作成が並行監査の封印済み証拠を壊す競合が残る。**  
   changedSetからレポートを除外しても、作業ツリー全体の指紋からは除外されない。`docs/**` は指紋除外として許可されず（[tree-digest.py:23](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/tree-digest.py:23)）、gateは指紋を再照合する（[decide-verdict.py:394](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:394)）。ところがlockはgate内で削除され（[decide-verdict.py:520](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:520)）、レポートはgate返却後に書かれる（[SKILL.md:505](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:505)）。

   再現順序は「run Aがlock解放 → run Bが開始・seal → run Aがレポート作成 → run Bがdigest mismatchでREFUSED」。同時に両runが同じ `_02` を選ぶ上書き競合も起こる。rev.4の変更許可範囲にはlock・指紋契約を直すファイルが含まれていない（[PLAN.md:232](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:232)）。

6. **MAJOR — `[_NN]`なしの有効なreportPathは、同日2回目の出力先がない。**  
   `[_NN]` は任意であり（[config-schema.md:18](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:18)）、matcherもテンプレートにある場合だけsuffixを認める（[PLAN.md:110](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:110)）。`audit_<YYYY-MM-DD>.md` が既に存在する場合、上書きは既存docを編集しない契約違反、`audit_2026-08-25_02.md` はmatcher不一致となる。現行のprefix wildcardなら後者も除外されたため、厳密matcher化による互換性回帰でもある（[change-set-sha.py:48](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/change-set-sha.py:48)）。この衝突ケースの試験もない。

7. **MAJOR — suffix生成契約が変更許可範囲と完了条件から落ちている。**  
   §5.3はレポート作成手順への `_02` 契約追加を必須としている（[PLAN.md:119](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:119)）。しかし、SKILL.mdの許可変更はimpact-supplement呼び出しと層説明だけで（[PLAN.md:241](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:241)）、完了条件もimpact-supplement契約しか要求しない（[PLAN.md:226](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:226)）。実装者は変更範囲違反かsuffix対応漏れのどちらかになる。

8. **MINOR — `auditReportsInCorpus`の不正型を4経路で固定する試験がない。**  
   boolの`true`だけを有効にする仕様だが（[PLAN.md:155](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:155)）、テストはtrue/falseだけである（[PLAN.md:198](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:198)）。`"true"`、`1`、`[]`を4つのcorpus経路へ与えないと、いずれかの複製実装が単純な真偽判定を使い、無効設定で除外を解除する回帰を捕捉できない。

9. **MINOR — URLのquery/fragment内パスをbareとして誤収穫する。**  
   URLマスク文字には `?`・`#`・`=`・`&` が含まれないため、`https://example.com/?next=docs/gone.md` はURL前半だけが消え、`docs/gone.md` がWARNになる（[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:49)）。blockingではないが恒久ノイズになる。現在のURL試験はquery/fragmentを含まない（[PLAN.md:185](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:185)）。

10. **MINOR — 廃止したseverity設計が目的・公開文書計画に残っている。**  
    目的は「severity規則の統一」とするが、最終仕様は意図的にbare=WARN、link/backtick=FAILで構文別である（[PLAN.md:10](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:10)、[PLAN.md:71](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:71)）。さらにconfig-schema更新項目には削除済みの「コマンド行降格則」が残る（[PLAN.md:160](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:160)）。bare=WARNへの最終変更は受容するが、旧合意の不存在として扱わず、明示的な上書き決定として記録すべきである。

11. **MINOR — 版残置ゲートが移行説明と衝突し、英語版の更新箇所も漏れている。**  
    日本語版を正しく「0.10.1から0.11.0へrefresh可能」と更新すると、配布文書内の`0.10.1`を禁止するゲートに失敗する（[PLAN.md:171](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-33-34-35/PLAN.md:171)）。また対応する英語版refresh説明（[ADOPTION.md:254](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:254)）がbump一覧から漏れている。旧版からの移行説明は残置ではないため、ゲートの例外として固定する必要がある。

計画承認可否：**承認不可**。  
特に1と2は計画が自己矛盾または監査停止を含むBLOCKERである。bare=WARNの最終裁定を再度覆す必要はなく、残る問題はその周辺契約・安全処理・テストの不足にある。