メタ認知：Issue の提案を正解として扱わず、実運用全体での到達経路と配布契約を優先して判定した。軽微な表現問題ではなく、再現可能な誤判定・停止・検査漏れに絞った。

1. **BLOCKER — bare path の空白分割は、通常のコマンドを blocking FAIL に誤判定する。**  
   `PLAN.md:47-56` は、コード部分を隠した後の空白区切り語を現行 `looks_like_repo_path()` に通すだけである。例えば `docs/source.md` が存在し `docs/new.md` が存在しない状態で、文書に `cp docs/source.md docs/new.md` と書くと、出力先 `docs/new.md` が「存在しない具体的ファイル」として FAIL になる。4空白字下げのコード例も現行マスクの対象外である（`generic-layers.py:80-118`）。FAIL は verdict を `NEEDS FIX` に変えるため、許容できない偽陽性である。

2. **BLOCKER — 日本語散文と約物に対する仕様が不十分で、偽陽性と検出漏れの両方を生む。**  
   末尾だけを曖昧な文字集合で削る仕様（`PLAN.md:52-53`）では、`docs/api.md（旧版）` は存在する `docs/api.md` を誤って FAIL にし、`「docs/gone.md」` や `docs/gone.mdを参照` は先頭約物・助詞のため検出できない。`docs/api.md?raw=1` も、existence 層は `#` しか除去しないため、実在ファイルでも FAIL になる（`generic-layers.py:204-218`）。テスト計画はこれらを含まない（`PLAN.md:130-136`）。

3. **BLOCKER — file/dir 判定が、合意済みの「具体的ファイルは FAIL」を満たさない。**  
   basename の `.` の有無だけによる判定（`PLAN.md:58-61`）では、存在しない `docs/LICENSE`、`docs/Makefile`、`docs/CMakeLists` は具体的ファイルなのに WARN となる。逆に `docs/v1.2` や `docs/schema.d` はディレクトリでも FAIL になる。これは境界ケースではなく、合意済み severity 契約そのものとの矛盾である。

4. **BLOCKER — #35 の除外は後段で再混入するため、問題が収束しない。**  
   `resolve-impact.py` の後には `impact-supplement.py` が実行され、graphify/CocoIndex が返した `docGlobs` 一致文書を再び impact に追加する（`impact-supplement.py:90-104,142-144,220-249`、`SKILL.md:298-310`）。ここには report-pattern も `auditReportsInCorpus` も渡らない。ところが計画は同スクリプトを変更禁止にしている（`PLAN.md:172-176`）。監査レポートが後段探索にヒットすれば、そのまま再 dispatch される。

5. **MAJOR — mapped を残す仕様と、明示 `--paths` を除外する仕様が矛盾する。**  
   `resolve-impact.py` の mapped 経路ではレポートを残す一方（`PLAN.md:105-106`、`resolve-impact.py:148-158`）、generic-layers は同じレポートが明示 `--paths` に含まれていても黙って落とす（`PLAN.md:103-105`、`generic-layers.py:314-335`）。`impactMap` で意図的に指定された文書が deterministic check では `docs=0`、finding なしになる。一気通貫の mapped→`--paths` テストもない。

6. **MAJOR — report pattern が広すぎ、監査レポートではない文書まで corpus から消す。**  
   canonical 導出は `doc_audit_<YYYY-MM-DD>...` を `doc_audit_*.md` に変換する（`change-set-sha.py:43-57`）。したがって `docs/logs/doc_audit_policy.md` や `doc_audit_usage.md` も除外される。現在は変更集合などに限定された影響だが、計画はこれを full corpus・heuristic・generic 全体へ拡大する（`PLAN.md:100-107`）。`auditReportsInCorpus: true` では本物の監査レポートもすべて戻るため、誤除外だけを解除する経路もない。

7. **MAJOR — レポートだけのリポジトリでは full audit が停止する。**  
   再現手順は、`docGlobs=["docs/**/*.md"]` で、唯一の文書を `docs/logs/doc_audit_2026-08-25.md` とすること。計画後の resolve-impact は impact を空にするが、`start-run.py` は未除外の `docGlobs` で corpus を数え、corpus 非空・impact 空としてエラーにする（`start-run.py:112-115`）。計画の変更許可範囲に `start-run.py` は含まれていない（`PLAN.md:159-176`）。

8. **MAJOR — repo-relative の境界を越える既存穴を bare path に拡大する。**  
   `looks_like_repo_path()` は `..`、絶対形、symlink を拒否せず（`generic-layers.py:140-146`）、存在確認も単純な `os.path.join()` である（`generic-layers.py:212-218`）。repo 内に `docs/`、repo 外に対象ファイルがある状態で `docs/../../outside.md` を指定すると、外部ファイルで解決済み扱いになる。計画はこの関数を無変更で bare path に再利用する（`PLAN.md:50,56`）。監査境界違反かつ外部ファイル存在の観測経路である。

9. **MAJOR — v0.11.0 の `engine-shas.json` 契約が不足している。**  
   計画は新 generic engine の SHA だけを要求している（`PLAN.md:118-119`）。実際の scaffold は、現行版エントリに `check-docs`、`doc-lint`、`check-docs-engine` の3 SHAすべてを要求し、一つでも欠ければ `engine-shas.json is stale` で停止する（`scaffold.py:172-180`）。計画どおり単一 SHA のみ追加した場合、`/docaudit:init --harness` が利用不能になる。

10. **MAJOR — 0.10.1 の consuming repo を更新できることが検証されない。**  
    更新処理は旧 stamp の版・SHA・本文が一致した生成物だけを書き換える（`scaffold.py:281-300`）。しかし既存テストは 0.10.0 の `doc-lint` 更新だけであり（`test_scaffold.py:142-168`）、主変更物である 0.10.1 `scripts/check-docs.py` の0.11.0への更新と、利用者が変更した旧 engine の保存を検証しない。新規生成物の SHA 一致テスト（`test_scaffold.py:235-251`）ではこの回帰を検出できない。

11. **MAJOR — report-pattern 複製の正本と一致契約が未定義である。**  
    generic-layers への複製は指定されているが、同じ導出を必要とする resolve-impact 側の実装方法がない（`PLAN.md:100-105`）。正本は `change-set-sha.py:43-57`、`decide-verdict.py` はこれを直接再利用している（`decide-verdict.py:39-43`）。正常形、`.md` 以外、placeholder 欠落、空 prefix、`docGlobs` 不一致について、正本・generic・resolve の結果を比較する契約テストもない。将来、工程ごとに corpus 判定が乖離する。

12. **MAJOR — 新設定の不正型と後方互換性が未定義・未検証である。**  
    `layerGlobs` 本体、各 layer、`exclude` の型不正に対する仕様がない（`PLAN.md:73-80`）。現行 `glob_to_regex()` は文字列前提なので（`generic-layers.py:29-45`）、実装次第で数値要素による異常終了や、文字列を一文字ずつ glob として扱う誤動作になる。`frontMatterOverrides` 自体が配列でない場合、未知キー、未設定・空設定の同値、`auditReportsInCorpus` が真偽値以外の場合もテスト計画にない（`PLAN.md:137-142,148-149`）。

13. **MINOR — 除外後の付随出力を検証していない。**  
    文書本体の除外だけでなく、generic の `counts.docs`・`pass`（`generic-layers.py:335-346`）、resolve の `mapGapCandidates`、`candidatesBeforeCap`、`heuristicOnly`、`truncated`（`resolve-impact.py:203-234`）も新 corpus と一致する必要がある。計画のテストは文書の有無だけで、これらの回帰を捕捉しない（`PLAN.md:140-141`）。

14. **MINOR — 版残置確認が成立せず、実際の bump 漏れもある。**  
    `0.10.1` が残っていないことを確認するコマンド（`PLAN.md:191-192`）は、保持必須の履歴エントリ `engine-shas.json:7` に必ず一致するため、常に偽警報となる。一方、bump 一覧には「0.10.1へ更新できる」と記載する `docs/ADOPTION.ja.md:237-238` が漏れており、v0.11.0後は実際の refresh 到達版と説明が食い違う。

計画承認可否：**承認不可**。  
特に 1〜5 と 9 は、#33/#35 の目的または配布契約を直接破るため、現計画のまま実装へ進むべきではない。