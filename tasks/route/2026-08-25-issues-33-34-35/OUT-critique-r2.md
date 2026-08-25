メタ認知：rev.2 が前回指摘を列挙しているため、「対応済み」という表示ではなく、Issue の完了条件と実際の処理順に基づいて再判定した。旧指摘への固執ではなく、新仕様が一貫して実装・検証できるかを基準にした。

1. **BLOCKER — bare=WARN は #33 の severity 不一致を意図的に残している。**  
   同じ `docs/gone.md` が link/backtick なら FAIL、bare なら WARN となり、`PLAN.md:10` の「同一欠陥が構文次第で FAIL/WARN」という問題が解消されない。さらに `PLAN.md:65` の「Phase-3 verifier の入力になる」は処理順と違う。generic layer が実行されるのは Phase 4 であり、Phase 3 はすでに終了している（`skills/audit/SKILL.md:332-355,392-406`）。WARN は report-only で verdict を阻止しないため（`generic-layers.py:335-349`）、bare stale path だけなら `CONSISTENT` で終了できる。可視化は改善するが、#33 の収束保証と合意済み「構文を問わず FAIL」は未達である。

2. **BLOCKER — backtick の FAIL 昇格が、コード例を blocking 誤検出する。**  
   indented code の追加マスクは bare ハーベスタだけに限定され、backtick 抽出は変更しない（`PLAN.md:48-52`）。現行 `extract_path_tokens()` は raw text 全体を走査し、fenced/indented code を除外しない（`generic-layers.py:132-137,198-221`）。したがって次は rev.2 後に FAIL となる。

   ```markdown
   ```markdown
   Use `docs/not-created-yet.md`
   ```
   ```

   4空白字下げの `` `docs/not-created-yet.md` `` も同じである。§5.6 は bare の字下げ例しか検証しない（`PLAN.md:167-170`）。

3. **BLOCKER — 新しい日付 regex は、現行正本が有効と認める `reportPath` を網羅しない。**  
   正本は日付より後の固定文字列を禁止していない（`change-set-sha.py:43-57`）。例えば次は正本では有効である。

   ```json
   {
     "docGlobs": ["docs/logs/*.md"],
     "reportPath": "docs/logs/audit_<YYYY-MM-DD>_final.md"
   }
   ```

   実レポート `audit_2026-08-25_final.md` は `PLAN.md:117` の `日付 + 任意の数字suffix + .md` に一致せず、4つの corpus 経路すべてに残る。#35 が valid config で再発する。

4. **BLOCKER — `impact-supplement.py` は除外判定に必要な設定を受け取れない。**  
   現行 CLI が受け取るのは `--doc-globs` までで、`reportPath`、`auditReportsInCorpus`、config path がない（`impact-supplement.py:148-159`）。呼び出し側も `docGlobs` しか渡していない（`skills/audit/SKILL.md:298-306`）。それにもかかわらず、rev.2 は CLI・呼び出し契約の変更を仕様化せず、同スクリプトでカスタム reportPath と opt-in を判定するとしている（`PLAN.md:133,136-138`）。現行の入力契約では実装不能である。

5. **MAJOR — 正本 glob と corpus regex の二本立てにより、非レポート文書の変更が incremental audit から消える。**  
   rev.2 は `doc_audit_policy.md` を corpus に残す（`PLAN.md:118`）が、正本 `doc_audit_*.md` は同文書を changedSet から除外し続ける（`PLAN.md:119-123`、`change-set-sha.py:60-68`）。同文書自身を編集しても impactMap・heuristic の変更起点にならず、sibling scan からも除外される。契約テストで差を固定しても、「corpus 会員だが変更は監査不能」という運用欠陥は解消しない。

6. **MAJOR — `[_NN]` の有無と桁数を regex が正しく表現していない。**  
   `change-set-sha.py:48-49` の `_01` は `docGlobs` 妥当性確認用サンプルであり、suffix 文法の定義ではない。rev.2 の `(_\d{2,})?` は以下を起こす。

   - `reportPath` に `[_NN]` がなくても `_02` や `_123` をレポート扱いする
   - `NN` の意味が未定義のまま3桁以上を許す
   - suffix の位置を日付直後に固定する

   例えば `reportPath: "audit_<YYYY-MM-DD>.md"` でも、無関係な `audit_2026-08-25_123.md` が corpus から消える。§5.3 のケース表には placeholder 有無、1・2・3桁の境界がない（`PLAN.md:121-123`）。

7. **MAJOR — 明示 `--paths` のレポートが semantic scan からは依然落ちる。**  
   rev.2 は明示 `docs` を残すが、`all_docs` は除外済みの `list_doc_files()` から作られる（現行 `generic-layers.py:314-327`）。semantic は `all_docs` を scan に使い、明示 `docs` を union しない（`generic-layers.py:225-285`）。  
   再現例は、明示 paths に「レポート」と「そのレポートからだけリンクされた文書」を渡すこと。レポートの発リンクが scan されず、後者が偽 orphan になる。mapped pull-back を全層で尊重する仕様と一致しない。

8. **MAJOR — ASCII限定 regex は有効なパスを誤抽出し、URLもパスとして拾う。**  
   `PLAN.md:53-57` の文字集合では以下になる。

   - `docs/旧概要.md` → `docs/` だけを抽出し、stale file を見逃す
   - 実在する `docs/foo+bar.md` → `docs/foo` を抽出して偽 WARN
   - `https://docs/gone.md` → `//docs/gone.md` を抽出する

   最後の例は repo に通常の `docs/` があれば、`looks_like_repo_path()` が先頭 `/` を除いて通す（`generic-layers.py:140-146`）。日本語ファイル名・URL・`+`・`@`・percent encoding のテストがない。

9. **MAJOR — repo境界対策は symlink 越境を残している。**  
   rev.2 が拒否するのは `..` セグメントだけである（`PLAN.md:76-78`）。現行の先頭ディレクトリ判定と `os.path.exists()` は symlink を追う（`generic-layers.py:140-146,212-218`）。repo 内の `docs/ext` を外部ディレクトリへの symlink にすると、`docs/ext/secret.md` は外部ファイルで解決済み扱いになる。前回のセキュリティ指摘への対応漏れであり、テストも `..` のみである（`PLAN.md:170`）。

10. **MAJOR — 4経路の matcher と opt-in の同値性を証明できない。**  
    §5.6 は opt-in 復帰を generic/resolve にだけ明記し、impact-supplement/start-run ではデフォルト除外しか要求しない（`PLAN.md:176-180`）。また generic は自己完結複製、残りは共有「してよい」という選択仕様なのに（`PLAN.md:124-127`）、同じケース表を全実装へ投入する契約になっていない。impact-supplement の設定受け渡し漏れや、複製片方だけの乖離をテストが捕捉できない。

11. **MINOR — indented code の簡易判定が未定義で、テストが不足している。**  
    「リスト継続行は除く簡易判定」（`PLAN.md:50-52`）は、blockquote、入れ子リスト、桁数の異なる ordered list、list 内 code をどう扱うか決めていない。`>     docs/gone.md` はコードなのに収穫され得る一方、リスト中の通常文を一律マスクすれば検出漏れになる。§5.6 は root-level の4空白例しかない（`PLAN.md:168`）。

12. **MINOR — bare抽出と severity の境界テストが弱い。**  
    `docs/api.md（旧版）` を「実在・findingなし」とするだけでは、抽出が一切動かなくても合格する。また `cp ...` を「WARN 2件までは許容」とすると、WARN 0件でも通り、bare 検出の退行を許す（`PLAN.md:166-168`）。行番号、missing `path:line` の FAIL、`docs/a.md...` のトリムと ellipsis 判定順も固定されていない。

13. **MINOR — config-level WARN が text の pass 件数を壊す可能性がある。**  
    新しい不正型 finding は特定文書に属さない（`PLAN.md:97-109`）。現行 text 集計は finding の `path` を文書かどうか確認せず、`len(docs) - len(finding_paths)` で pass を減らす（`generic-layers.py:335-346`）。config warning 1件だけで正常文書の pass が1減り得る。新しい不正型テストは warning の存在だけで、件数・path・pass 整合を検証しない（`PLAN.md:172-174`）。

14. **MINOR — consuming repo refresh テストの歴史的 engine fixture 契約が不足している。**  
    `engine-shas.json` が保持するのは SHA だけで、0.10.1 engine 本文ではない（`engine-shas.json:7-10`）。`PLAN.md:182-183` の更新・改変保存テストには、使用する歴史的本文が本当に0.10.1 SHAと一致する事前検証が必要である。それがなければ、最初から不一致の fixture が skipped されるだけで「改変済みを保存」のテストが通る。

15. **MINOR — 公開説明が新しい blocking severity と食い違う。**  
    `docs/ADOPTION.md:350` と `docs/ADOPTION.ja.md:331` は existence の全 non-resolving token を WARN と説明している。rev.2 の文書更新対象は config-schema と条件付きの SKILL/init/scaffold だけで（`PLAN.md:142-146`）、この2箇所を更新しない。利用者向け説明上は、0.11.0 の backtick FAIL 昇格が不可視になる。

計画承認可否：**承認不可**。  
特に 1〜4 は #33/#35 の完了条件または実装可能性を直接破る。mapped→明示 `--paths`、後段再混入、start-run、3 SHA、版残置確認については rev.2 で改善されているが、上記を解消しない限り実装開始は承認できない。