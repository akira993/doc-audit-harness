メタ認知（着手時）：rev.4 の採用一覧ではなく、PLAN 内の正本が一本化されているか、誤実装をテストが実際に検出できるかを基準に再確認しました。

結論は「実装未承認」です。boss 裁定済みの中断後復元は再指摘しません。新規・残存欠陥は以下です。

1. Phase-5 の状態数が PLAN 内で矛盾している

   - (a) 決定事項は doc-graph=6-state（7 messages）、symbol-graph=6-state、semanticSearch=8-state です（[PLAN.md:68](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:68)）。しかし DoD は旧値の doc=6、symbol=5、semantic=6 のままです（[PLAN.md:212](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:212)）。worker がどちらに従っても一方へ違反します。
   - (b) 深刻度: **medium**
   - (c) 推奨: DoD も6/6/8へ統一し、状態見出しの数値を契約テストで固定する。

2. probe テスト追加数が31件と25件で矛盾している

   - (a) 固定名の内訳は `3×10+1=31` 件です（[PLAN.md:201](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:201)）。直後には旧値の「計25件追加」が残っています（[PLAN.md:208](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:208)）。
   - (b) 深刻度: **low**
   - (c) 推奨: 件数を最終的な固定テスト名から再計算した一つの値へ統一する。

3. `enabled:false` 優先を semanticSearch 側で検証していない

   - (a) 評価順は `enabled:false` を `bin` と `minScore` の検査より先に確定すると定義しています（[PLAN.md:47](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:47)）。複合試験は不正 `bin` だけで（[PLAN.md:205](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:205)）、semanticSearch だけ `minScore` を先に検査する誤実装でも全試験を通ります。
   - (b) 深刻度: **medium**
   - (c) 推奨: `enabled:false,minScore:"x"` が `disabled-by-config` になる固定試験を追加する。

4. 「全ての不正な型」を拒否する契約に対し、代表入力が不足している

   - (a) 表は「object 以外」「非文字列」「有限数値以外」を包括的に拒否します（[PLAN.md:40](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:40)）。DoD は key 非 object の具体値を固定せず、`bin` は `[]` と空文字、無限大は正の `Infinity` だけです（[PLAN.md:201](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:201)）。`-Infinity` は後段で全候補を通し得ます（[impact-supplement.py:173](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:173)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: key=`true`/文字列/配列/`null`、bin=`[]`/数値/`null`/空文字、minScore=文字列/boolean/`null`/NaN/+Infinity/-Infinity を必須 subTest として固定する。

5. 外部 tool 非起動の `calls.log` 検査が、一部ケースでは実質0件検査になる

   - (a) DoD は各 unavailable ケースで「stub bin を `bin` に置く」としています（[PLAN.md:208](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:208)）。しかしキー不在、キー非 object、不正 JSON、config 不在、空 `bin` では、設定内に有効な stub path を置けません。参照されない stub の `calls.log` が無いことを確認しても、誤実装が既定の `graphify`／`ccc`／`codegraph` を起動していない証明になりません。現行 probe は既定 bin を持ちます（[graphify-probe.sh:33](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:33)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: 設定へ有効な bin を入れられないケースでは、既定名の記録用 stub を `PATH` の先頭に配置して非起動を検査する。

6. reason 固定句の検査が条件側の文字だけで合格する

   - (a) DoD は箇条書き行全体に固定句があるかを検査します（[PLAN.md:214](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:214)）。条件側の `disabled-by-config` は既に `disabled` を、`index-failed`／`update-failed` は既に `failed` を含みます。したがって利用者向け右辺がその状態を説明していなくても、記号だけ合えば通り得ます。
   - (b) 深刻度: **medium**
   - (c) 推奨: `→` の右辺だけを取り出し、記号・固定句・他状態の句の不在を検査する。

7. 日本語版 §7 は、まだ逆の説明でも通る

   - (a) 英語版は肯定形の全文固定ですが、日本語版はコードスパンと一部の固定語だけです（[PLAN.md:247](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:247)）。①を「`AGENTS.md` を許可する」、②を「キー不在でも tool を実行する」と書いても、現在の条件を満たします。
   - (b) 深刻度: **medium**
   - (c) 推奨: 日本語版も5文の肯定形全文を固定する。

8. symlink の確認案内は、変更された本文を確認しない

   - (a) 状態行は `readlink` で参照先を確認するよう案内します（[PLAN.md:82](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:82)）。`readlink` が示すのは参照先のパスだけです。実機 CocoIndex は参照先本文を `read_text/write_text` で変更するため（[cli.py:310](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:310)）、本文の変化は確認できません。
   - (b) 深刻度: **medium**
   - (c) 推奨: `readlink` で実体を特定した後、その実体の内容をバックアップ等と比較する旨まで案内する。

9. deny 更新箇所が同じ文中で4箇所と5箇所になっている

   - (a) 決定事項に旧「4か所」が残り、同じ文末で「5か所」と訂正されています（[PLAN.md:15](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:15)）。実数と DoD は5箇所です（[PLAN.md:184](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:184)）。
   - (b) 深刻度: **low**
   - (c) 推奨: 旧「4か所」を削除して5箇所へ一本化する。

### 総括

「計画自体の欠陥（PLAN を直してから実装）」は #1〜#8 です。特に #3〜#7 は誤実装を green にするため、worker 指示だけでは不十分です。

「worker 指示で吸収できる細部」は #9 だけです。したがって現時点では実装承認しません。

確認済みで問題がなかったもの:

- `casefold()` deny と AST 11件
- `math.isfinite` 方針
- reason の完全代入式
- `.gitignore` 変化を exit code より優先する設計
- 3 fixture の作成順と SHA  
  `d681…0982d`／`b1a1…d91d`／`9723…599c`
- 固定テスト method 名の全体列挙

リポジトリは変更していません。