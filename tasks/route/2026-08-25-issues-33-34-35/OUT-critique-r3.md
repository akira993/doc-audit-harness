メタ認知：rev.3 の追加仕様を「精緻化されたから安全」とは見なさず、判定の単調性、通常の日本語文、既存CLI契約、sealed evidenceとの整合を基準に再評価した。

1. **BLOCKER — 「同一行に2候補ならWARN」はコマンド判定ではなく、通常の stale 参照を簡単に非blocking化する。**  
   `PLAN.md:73-80` の規則では、次の通常文でも旧パスが WARN に落ちる。

   ```text
   移動前 docs/old.md → 移動後 docs/current.md
   ```

   `docs/old.md` が不在、`docs/current.md` が実在していても候補は2つである。Issue #33 の「移動後の古い参照」そのものに近い。さらに `docs/gone.md docs/` のように実在ディレクトリを一つ添えるだけで FAIL を回避できる。  
   候補数を解決後に数えると、`cp docs/source.md docs/new.md` は missing finding が1件なので計画の期待 WARN と矛盾する（`PLAN.md:157-158`）。解決前に数えると上記の回避が成立する。どちらでも安全な規則にならない。

2. **BLOCKER — 1候補の裸コマンドによる blocking 偽陽性は、残余リスクとして受容できる頻度ではない。**  
   `cat` だけでなく、`touch docs/generated.md`、`rm docs/obsolete.md`、`sed -i docs/config.md` など1パスのコマンドは一般的である。出力先や削除対象が存在しないことが正しい例でも FAIL になる。文書化しても CI/verdict の blocking 誤判定は防げず、R1-1 の根本懸念は十分に抑制されていない（`PLAN.md:75-85`）。

3. **BLOCKER — Unicode最長連続と「最長の拡張子境界」は、日本語の複数パスを一つへ融合する。**  
   `\w` は日本語助詞も含むため、次が一候補になる（`PLAN.md:62-69`）。

   ```text
   docs/a.mdからdocs/b.mdへ移動
   ```

   両方が実在しても、最長境界プレフィックスは `docs/a.mdからdocs/b.md` となり、存在しない具体ファイルとして FAIL になる。  
   また `docs/a.mdからdocs/gone.md` のように2番目の `.md` 後に非ASCII文字がない場合、境界は最初の `.md` だけになる。`docs/a.md` が実在すれば後半の missing path が finding なしで消える。複数境界のテストがなく（`PLAN.md:149-163`）、通常の日本語散文で偽陽性・検出漏れの双方が発生する。

4. **MAJOR — blockquote/list 内の fenced code がコードマスクをすり抜ける。**  
   rev.3 は既存 `_mask_fenced()` に indented mask を加えるが（`PLAN.md:39-47`）、既存 fence 判定は行頭0〜3空白の直後しか認識しない（`generic-layers.py:80-109`）。

   ```markdown
   > ```
   > `docs/gone.md`
   > ```
   ```

   ```markdown
   - ```
     `docs/gone.md`
     ```
   ```

   これらは fenced code だが、blockquote/list marker のため fence と認識されず、4空白条件にも当たらない。内部 backtick が FAIL になり得る。§5.6 は通常 fence と blockquote 内 indented しか検証しない（`PLAN.md:159-160`）。

5. **MAJOR — URLマスクが日本語の後続文まで消し、scheme-relative URLは逆にFAILになる。**  
   `scheme://\S+` は空白まで全て取るため（`PLAN.md:46-47`）、次では stale path までマスクされる。

   ```text
   https://example.comを参照。docs/gone.mdを修正する
   ```

   日本語ではURL後に空白を置かないことが一般的であり、検出漏れになる。反対に `//docs/gone.md` はURLマスク対象外で、現行 `looks_like_repo_path()` が先頭 `/` を除くため、repoに `docs/` があれば具体ファイルとして FAIL になり得る（`generic-layers.py:140-146`）。単独の `https://...` テストだけでは捕捉できない（`PLAN.md:155-156`）。

6. **MAJOR — `%` を収穫するがpercent decodeしないため、実在パスがblocking FAILになる。**  
   `docs/foo bar.md` が実在し、文書に `docs/foo%20bar.md` とある場合、候補は完全抽出されるが filesystem path へ復号されない（`PLAN.md:51-68`）。非ASCIIフォールバックも働かず、`.md` によって FAIL となる。`%` をリテラルファイル名とみなすのかURL表現とみなすのかが未定義で、テストもない。

7. **MAJOR — 非ASCII後置フォールバックが正当なUnicodeファイル名の stale を隠す。**  
   `docs/概要.md` が実在し、`docs/概要.md旧` が存在しない具体ファイルを指す場合、全体解決失敗後に短い `docs/概要.md` が解決し、finding なしになる（`PLAN.md:65-69`）。`旧` が散文なのかファイル名の一部なのか判別不能なのに、常に散文側へ倒している。少なくともこの検出漏れは現在の既知の限界・テストに含まれていない。

8. **BLOCKER — `auditReportsInCorpus` の適用範囲が sealed change-set 契約と矛盾している。**  
   §5.3 は corpus 用 opt-in と読める一方、「true で全経路無効化」「全実装でopt-in true/false」とも記載する（`PLAN.md:115-128`）。

   - true を `change-set-sha.excluded()` にも適用すると、自己生成レポートが次回の changedSet/changeSetSha に入り、毎回のcache資格を変える。これは「report paths は changedSet から機械的に除外される」という現行契約（`skills/audit/SKILL.md:283-288,512-513`）に反する。
   - change-setには適用しないなら、「全実装で同一判定」というテスト仕様と一致しない。
   - sibling-scan は corpus を列挙するが（`sibling-scan.py:154-159`）、opt-in時に regex を渡さないのかも未定義である。

   matcherの一致規則と、各経路で除外を有効にする条件が分離されていないため、実装者が一貫した期待値を選べない。

9. **MAJOR — `impact-supplement.py --config` の必須性が未定義で、既存CLI/no-op契約を壊し得る。**  
   現行CLIはconfig不要で、source指定がなければ byte-identical no-op を保証する（`impact-supplement.py:148-176`）。`PLAN.md:124-125` の追加を必須引数として実装すると、既存の直接呼び出しと全既存テストが argparse exit 2になる。後方互換動作、未指定時の挙動、そのテストが計画にない。

10. **MAJOR — `reportPath` の妥当性条件が曖昧で、既存互換契約を変更し得る。**  
    `PLAN.md:104-105` は「正本と同じ」としながら、列挙するのはplaceholder必須とdocGlobs一致だけである。現行正本はさらに、placeholderがbasename内にあり、日付前prefixが非空であることを要求する（`change-set-sha.py:43-57`）。  
    `docs/<YYYY-MM-DD>.md` を除外しない既存テストもある（`tests/test_wp12_contracts.py:144-151`）。空prefixや日付placeholderがdirectory側にあるケースが§5.3のケース表から落ちており、維持か変更か裁定されていない。

11. **MAJOR — 厳密matcherに対応するレポート生成側のsuffix契約がない。**  
    matcherは `[_NN]` を2桁以上と定義するが（`PLAN.md:99-103`）、実際にレポートを書く手順は依然としてテンプレート例を示すだけで、最初の衝突を `_01` とすることやゼロ埋め規則を定めていない（`skills/audit/SKILL.md:505-513`）。生成側が `_1` を選ぶと、レポートはchangedSetにもcorpusにも残る。matcher単体の1/2/3桁テストでは、生成物がmatcherに必ず一致することを証明できない。

12. **MINOR — `\d` はASCII以外の数字にも一致し、非レポートを全経路から除外する。**  
    Pythonの `\d` は全角数字やArabic-Indic digitsも含む。`doc_audit_２０２６-０８-２５.md` も日付レポート扱いされる（`PLAN.md:99-103`）。実レポートの生成日がASCIIなら、これは changedSet/corpus 双方から正規文書を落とす互換性欠陥である。ケース表に非ASCII数字がない。

13. **MINOR — `\w` はUnicode結合文字を含まず、「Unicodeパスを完全抽出」を満たさない。**  
    NFD表現の `docs/café.md`（`e`＋結合アクセント）は `docs/cafe` と `.md` に分断される。macOSを含むUnicode正規化差の検証がない（`PLAN.md:62-64,155-156`）。

14. **MINOR — compute-baseline本体は変更不要だが、shell経由の回帰試験が不足している。**  
    `compute-baseline.sh` は `change-set-sha.excluded(path, config)` をそのまま呼ぶため、署名維持なら変更禁止で問題ない（`compute-baseline.sh:61-90`）。ただし§5.6はchange-set-sha直接テストだけで、shell経由の `[_NN]` suffix、`doc_audit_policy.md` 残留、`machineryExcludedCount` を固定しない。#31の統合契約に対するテスト不足である。

15. **MINOR — 0.10.1歴史fixtureと版残置確認が衝突する。**  
    refreshテストでは0.10.1 SHAの参照と旧stamp生成が必要であり（`PLAN.md:174-177`）、テストコードまたはfixtureに `0.10.1` が残る。一方、完了条件とgrepは残置をengine-shas履歴だけに限定する（`PLAN.md:145,188,222-224`）。計画どおりテストを追加すると版残置ゲートが常時失敗する。

計画承認可否：**承認不可**。  
特に 1〜3 と 8 は、#33 の収束性または sealed evidence の期待値を直接破るため、現状は条件付き承認にもできない。