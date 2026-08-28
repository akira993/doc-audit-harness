メタ認知（着手時）：R2 の対応表が揃ったことで「修正済み」と判断しやすいため、新規規則が中断・複合入力・既存文書で成立するかを独立に検証しました。

結論は「実装未承認」です。`casefold()` deny、AST 11件、`audit-scope.json` の SHA 自体は正しい一方、次の新規・未解消欠陥があります。

1. `*_REASON` が Phase 4 の中断後に復元できない

   - (a) PLAN は Phase 0 で3つの reason を保持し、Phase 5 で使います（[PLAN.md:50](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:50)）。しかし既存の中断規約は、次の turn へ渡す値を `RUNID` と `EVIDENCE` だけに限定しています（[SKILL.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:49)）。実際の `/code-review` 中断もその2値しか記録しません（[SKILL.md:493](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:493)）。`EVIDENCE` に probe reason は含まれないため、再開後の Phase 5 で決定的に復元できません。
   - (b) 深刻度: **high**
   - (c) 推奨: 中断時に3 probe の元 JSON または Phase-5 用状態一式を保存・復元する契約を追加する。

2. reason 束縛の検査は、誤った値を束縛しても通る

   - (a) DoD は3変数名の出現しか確認しません（[PLAN.md:205](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:205)）。別 probe の reason、固定値、説明文中の変数名でも合格します。正しい既存例は、保存した probe JSON の `["reason"]` を明示的に読む形です（[SKILL.md:149](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:149)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: 各 `*_PROBE_JSON["reason"]` から対応する `*_REASON` へ代入する完全な式を検査する。

3. 状態数が reason 数と一致せず、対応表も完全一致になっていない

   - (a) PLAN は doc-graph 6-state、symbol-graph 5-state、semanticSearch 6-state としています（[PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:60)）。実際の reason 数は、追加後にそれぞれ6・6・8です。doc-graph は `ok` が `gitignoreOk` により2表示なので7メッセージです。また DoD は `ok→active` 等の部分一致だけなので（[PLAN.md:198](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:198)）、`ok → not active` や誤った記号でも通ります。
   - (b) 深刻度: **medium**
   - (c) 推奨: 状態数を doc=6、symbol=6、semantic=8へ直し、記号を含む完全な期待文を reason ごとに固定する。

4. `enabled:false` と不正な `bin`／`minScore` が併存した場合の優先順位がない

   - (a) 表の行3と行9・10は同時成立します（[PLAN.md:39](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:39)、[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:45)）。例は `{"enabled":false,"bin":[]}` です。実装順によって `disabled-by-config` と `invalid-config` が変わりますが、複合試験がありません。
   - (b) 深刻度: **medium**
   - (c) 推奨: 後方互換性を優先し、object／enabled 型を確認した後、`enabled:false` を `bin`／`minScore` 検査より先に確定する。

5. `minScore` が `NaN`／`Infinity` の場合を拒否できない

   - (a) Python の `json.loads` は実測で `NaN`、`Infinity`、`-Infinity` を float として受理します。PLAN は「数値以外」しか拒否しません（[PLAN.md:46](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:46)）。後段は `score < min_score` だけで判定するため（[impact-supplement.py:173](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:173)）、NaN／負の無限大は候補を全通過、正の無限大は全排除し得ます。
   - (b) 深刻度: **medium**
   - (c) 推奨: `math.isfinite(minScore)` を必須にする。

6. 判定表9・10などの型境界がテストで固定されていない

   - (a) 表は空 `bin`、boolean `minScore`、整数 `enabled`、`--config` 自体の省略も対象です（[PLAN.md:40](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:40)）。DoD の固定名は非文字列 `bin`、非数値 `minScore`、config ファイル不在しか示しません（[PLAN.md:190](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:190)）。`bin=[]` と `minScore="0.4"` だけ試せば、空文字や boolean を許す誤実装が通ります。現行 probe は `--config` 省略時に既定有効です（[graphify-probe.sh:22](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:22)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: 必須入力を subTest 表として列挙し、少なくとも `bin=[],""`、`minScore="0.4",true`、`enabled="false",1`、`--config` 省略を固定する。

7. 新しい `minScore` 検査が schema の説明と矛盾する

   - (a) rev.3 では probe が `minScore` を検査しますが、schema は semanticSearch の runtime が読む値を `enabled` と `bin` だけと断言しています（[config-schema.md:39](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:39)）。PLAN の文書 DoD は reason 追加だけで、この文言の更新を要求していません（[PLAN.md:196](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:196)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: semanticSearch の schema を「probe が enabled/bin/minScore を検査し、Phase 2 が minScore を使用」に更新して契約化する。

8. `.gitignore` 変化と index 失敗が同時発生した場合の reason が未定義

   - (a) PLAN は `.gitignore` 変化時を `gitignore-modified` としますが（[PLAN.md:74](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:74)）、stub 試験は成功終了時しか想定していません（[PLAN.md:214](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:214)）。実機は設定と `.gitignore` を書いた後に index 本体へ進むため（[cli.py:121](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:121)、[cli.py:642](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:642)）、書き込み後の index 失敗は可能です。
   - (b) 深刻度: **medium**
   - (c) 推奨: `.gitignore` 変化を exit code より優先して `gitignore-modified` とし、「追記後に非0終了する stub」で固定する。

9. symlink の `.gitignore` に対する確認案内が機能しない

   - (a) 状態行は `git status / git diff -- .gitignore` を案内します（[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:78)）。CocoIndex は symlink の参照先を読み書きしますが、Git は symlink 自体の参照文字列を管理するため、参照先本文だけが変化してもこれらのコマンドは clean になり得ます。
   - (b) 深刻度: **low**
   - (c) 推奨: symlink の場合は `readlink` で参照先を確認する旨を案内に含める。

10. `command -v` 契約が PLAN 内で自己矛盾している

   - (a) 判定表の見出しは available:false 時に `command -v` も実行しないとしています（[PLAN.md:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:35)）。一方、DoD はその非実行を契約から外しています（[PLAN.md:194](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:194)）。
   - (b) 深刻度: **low**
   - (c) 推奨: 判定表の見出しから `command -v` 非実行を削除する。

11. fixture 3点のうち2点は由来が固定されていない

   - (a) `audit-scope.json` の SHA `d681…0982d` は commit `951570b` の実物と一致しました（[PLAN.md:113](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:113)）。しかし `paths.txt` は48行、`doc-audit.json` は `auditScope` 不在しか検査しません。任意の広い `docGlobs` と都合のよい48 pathでも期待値を通せます。指定 commit の実測値は paths SHA=`b1a1356…d91d`、`auditScope` 除去後の canonical config SHA=`9723e283…599c` です。
   - (b) 深刻度: **medium**
   - (c) 推奨: 3 fixture 全てについて commit `951570b` 由来の固定値を検査する。

12. §7 の契約は、要求した変更の逆説明でも通る

   - (a) 本文要件には `AGENTS.md` deny、`gitignore-modified`、非復元、run 解放、未 seal 拒否が含まれます（[PLAN.md:89](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:89)）。DoD は `CLAUDE.md`、`gitignore`、`read-manifest.py`、`sealed` 等の単語しか要求せず（[PLAN.md:229](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:229)、「unsealed も受理する」のような逆説明でも通ります。
   - (b) 深刻度: **medium**
   - (c) 推奨: 英日それぞれについて、4変更と移行条件を肯定形の完全な文で固定する。

13. 「固定テスト名の網羅」が一部まだ循環している

   - (a) DoD (2)(3)(6)(15) は具体的な method 名が PLAN にありませんが、完了時にその名前を grep するとしています（[PLAN.md:238](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:238)）。worker が実装後に任意の名前を付け、その名前を確認するだけになります。
   - (b) 深刻度: **low**
   - (c) 推奨: grep 対象にする全 method 名を実装前に列挙する。

14. 組込み deny の文書更新箇所は4ではなく5

   - (a) PLAN の列挙は config-schema 2箇所、SKILL 1箇所、ADOPTION 英日各1箇所で、実数は5です（[PLAN.md:15](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:15)、[PLAN.md:175](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:175)）。「4箇所」の件数だけを基準にすると片言語を落とせます。
   - (b) 深刻度: **low**
   - (c) 推奨: 5箇所として、ファイルと節の集合を完全一致で検査する。

### 総括

「計画自体の欠陥（PLAN を直してから実装）」は #1、#3〜#5、#7、#8、#10〜#12 です。特に #1 は通常の対話経路で再現するため、着手前修正が必須です。

「worker 指示で吸収できる細部」は #2、#6、#9、#13、#14 です。ただし、DoD の誤合格を防ぐには PLAN に反映する方が確実です。

確認済みで新たな指摘がないもの:

- `casefold()` による basename deny
- `docGlobs` の AST 対象11件と内訳
- fixture の作成順
- `audit-scope.json` の固定 SHA
- sealed manifest／run 解放／版更新面

リポジトリの修正は行っていません。