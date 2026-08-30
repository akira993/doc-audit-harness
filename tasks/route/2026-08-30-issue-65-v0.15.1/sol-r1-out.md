1. 重大度: HIGH — 非通常ファイルで偽の `ok` になる  
   根拠: `PLAN.md:38-39` は DB が通常ファイルでなければ、symlink 以外を `init` に送ります。しかし CodeGraph 1.5.0 は `~/.codegraph/versions/v1.5.0/lib/dist/directory.js:134-141` で種類を確認せず、DB パスの存在だけで初期化済みと判定します。DB パスがディレクトリ等でも `codegraph.js:577-586` の `init` は rc=0 で終了し、probe は `codegraph-probe.sh:75-77` により索引不能なのに `reason:"ok"` を返します。  
   推奨: 「通常ファイル→sync／パスが完全に不存在→init／存在する非通常ファイル→無実行で index-failed」の3分岐にする。

2. 重大度: HIGH — `CODEGRAPH_DIR` を無視して誤った DB を判定する  
   根拠: `PLAN.md:38` は `.codegraph/codegraph.db` 固定ですが、1.5.0 は `directory.js:66-103,127-141` で `CODEGRAPH_DIR` による保存先変更を正式に扱います。例えば `.codegraph-win/codegraph.db` があると、probe は既定 DB 不在として `init`、CodeGraph は変更先を初期化済みとして rc=0 で何も同期せず、偽の `ok` になります。`.gitignore`、WAL/SHM、daemon ファイル自体は初期化根拠ではなく、実際の保存先にある DB 本体だけが根拠です。  
   推奨: 1.5.0 と同じ妥当性規則で有効な `CODEGRAPH_DIR` を解決し、その配下の DB を判定する。

3. 重大度: HIGH — 親ディレクトリの symlink からリポジトリ外を書き換え得る  
   根拠: `PLAN.md:39,49` は `codegraph.db` 自体の symlink だけを拒否します。`.codegraph` 自体が symlink の場合、`-f .codegraph/codegraph.db` と CodeGraph の `statSync` はリンク先を追跡します（`directory.js:134-141`）。CodeGraph 自身も削除時には親 symlink を特別に拒否しています（同:683-687）。  
   推奨: 実際に選んだ CodeGraph 保存ディレクトリ自体が symlink の場合も、コマンドを実行せず `index-failed` にする。

4. 重大度: HIGH — テスト設計と件数条件が矛盾し、誤実装も通る  
   根拠: 実測 `rg -c '^    def test_' tests/test_codegraph_probe.py` は `20` で、`PLAN.md:78` の「現行19」は誤りです。§5.2 は既存2本の改修と新規4本なので増分は +4 にしかならず、`PLAN.md:77` の +5 と両立しません。また `.gitignore` だけ残った状態がなく、「空または `.DS_Store` だけなら init、それ以外の残骸なら sync」という誤実装が全6ケースを通ります。DBがディレクトリのケース、valid/dangling symlink の両方、親ディレクトリsymlinkも未検査です。symlink 分岐の stderr と厳密な3キーJSONも検査されません。  
   推奨: 最終分岐表に基づき必須ケース名を列挙し直し、現行20本を基準に総数・増分・stderr・JSON・非呼出しを固定する。

5. 重大度: HIGH — #66 の置換範囲と残骸ゲートが破綻している  
   根拠: `PLAN.md:62-63,91` は `SKILL.md:778` 等だけを許可しますが、実物の `skills/audit/SKILL.md:3` にも `(not model-invocable)` が残っています。さらに `PLAN.md:80,104` の検索は実測11行で、記載の12行ではありません。`docs/ADOPTION.ja.md:11` の「モデルからは起動できない」と同:79の「モデルからは起動不可」を見落とします。古い記述の実数は README 3、英語ADOPTION 4、日本語ADOPTION 4、SKILL 2の計13行です。加えて `grep ... ; echo "exit=$?"` は残骸があってもコマンド全体が常に exit 0 です。  
   推奨: `SKILL.md:3` を対象・許可へ追加し、全13行を拾って残存時に非0となる単一ゲートへ置き換える。

6. 重大度: HIGH — 版更新のテスト修正箇所が不足し、フルスイートが必ず失敗する  
   根拠: `PLAN.md:68` は `tests/test_scaffold.py` の `"0.15.0" 3箇所`としますが、実測は `:214,217,218,242,245,246,312` の7箇所です。また ADOPTION の refresh 文を変えると、`tests/test_v013_contracts.py:210,215` の完全一致許可式が不一致になりますが、計画は同:201しか変更対象にしていません。  
   推奨: 7箇所と `test_v013_contracts.py:201,210,215` を明示的な同期対象にする。

7. 重大度: MEDIUM — refresh の直前版互換性と列挙文が未検証  
   根拠: 同一 SHA の `"0.15.1"` 追加自体は `scaffold.py:286-295` と意味的版順の最新キー判定を壊しません。しかし `engine-shas.json:2-46` は 0.10.0 も持ち、`tests/test_scaffold.py:163-170` はその更新成功を実証しているのに、`PLAN.md:66` の列挙案は 0.10.0 を欠きます。また 0.15.0→0.15.1 の同一本文・stampのみ更新する経路を直接検査していません。  
   推奨: ADOPTION en/ja は 0.10.0〜0.15.0を全列挙し、0.15.0 stampから0.15.1への直接refresh検査を追加する。

8. 重大度: HIGH — 新しい release-handoff が配布差分から消えても検出できない  
   根拠: `.gitignore:8` は `tasks/` 全体を無視し、実測 `git ls-files tasks/route/2026-08-30-issue-65-v0.15.1` は0件です。ローカルの `tests/test_release_handoff.py` は無視されたファイルも読めるため成功し得ますが、追跡し忘れるとクリーンcheckoutで失敗します。さらに `PLAN.md:82,106` の `git diff --name-only main...HEAD` は未commit・staged・untracked・ignoredを含まず、許可外ファイルが出ても自身はexit 0です。main=HEADでの実測出力も0件でした。  
   推奨: handoff の追跡済み確認と、commit差分・staged・working tree・untrackedを統合して許可集合との差があれば失敗する検査を追加する。

9. 重大度: MEDIUM — handoff 複製時の旧版残骸を検出できない  
   根拠: 複製元には v0.15.0固有文字列が `release-handoff.sh:2,8,16-17,71,73,79,130,160,162`、#56固有処理が同:76,111-120,128-132にあります。`PLAN.md:72-73` の検査では、usage、本文先頭、旧機能説明、最終表示の残留を保証できません。また #66 の「OPENでなければ公開前停止」もスクリプト要件として明記されていません。  
   推奨: 新スクリプトの旧版・#56・旧機能文言ゼロ検査と、#59/#63/#66すべてのOPEN事前条件を静的・実行テストに固定する。

10. 重大度: MEDIUM — v0.15.1 挙動変更ブロックは欠落しても全検査を通る  
    根拠: `PLAN.md:69` は ADOPTION en/ja の新ブロックを必須としますが、既存 `tests/test_v015_contracts.py:169-185` は v0.15.0ブロックだけを検査します。§7は同テストを変更許可に含めず、§6にも新ブロックの存在・両言語整合を判定する条件がありません。  
    推奨: `tests/test_v015_contracts.py` を許可範囲へ追加し、en/ja双方のv0.15.1ブロックを契約化する。

11. 重大度: MEDIUM — §6は「機械判定」になっていない  
    根拠: `PLAN.md:78` は精読、同:79は手作業の実機確認、同:83は確率的レビュー、同:84は監査結果の目視であり、期待exit・抽出方法・記録件数がありません。特にprobeケースの合格件数、method実数、最終レビューのblocking件数、route-close結果の取得方法が REVIEW 記録条件に結び付いていません。  
    推奨: 機械ゲートと人手検収を分離し、各項目へ実行方法・期待exit・期待件数・REVIEW記録欄を定義する。

計画自体を直すべき HIGH の一覧: **1、2、3、4、5、6、8**。

このまま実装に進めてよいか: **進めてはいけません。上記HIGHを計画へ反映してから再レビューすべきです。**