結論：この PLAN は実装着手不可です。high 6件を含み、特に `.gitignore` 復元案は新たなデータ消失事故を作ります。

1. パッチ版 `v0.13.2` という前提が互換性契約に反する

   - (a) [PLAN.md:7](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:7) は利用者指示だけで patch と裁定していますが、Issue は #52・#53とも実行時挙動の変更なので minor と明記しています（[issues-52-54.md:11](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/issues-52-54.md:11)、[同:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/issues-52-54.md:35)）。実際に「修正不可→許可」「キー省略時に起動→非起動」「未封印情報を受理→拒否」が変わります。
   - (b) 深刻度: high
   - (c) 推奨: 計画全体を `v0.14.0` に変更する。

2. `docGlobs` 既定変更は、計画が主張するほど安全ではない

   - (a) 現行は省略時に全修正を拒否します（[fix-scope.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:87)）。組込み保護は `.claude` とパス部分が `adr`・`decisions`・`logs` の場合だけで、`protectedGlobs` の既定は空です（[同:14](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:14)、[同:89](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:89)、[同:97](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:97)）。実装の一致判定を実行すると `README.md` に加え、`AGENTS.md`、`CLAUDE.md`、`SECURITY.md` も `*.md` に一致しました。したがって [PLAN.md:9-11](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:9) の「安全側の性質は維持」は誤りです。
   - (b) 深刻度: high
   - (c) 推奨: root の制御文書を保護する方針が決まるまで、省略時 deny-all を維持する。

3. 不正な設定を `not-configured` と扱う判定表は誤り

   - (a) [PLAN.md:24-27](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:24) は、JSON 不正やキーの型不正まで「未設定」に畳みます。しかし Phase 5 文言は “key absent” と断言するため事実と異なります（[同:34](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:34)）。また現行3 probe は `bool(enabled)` を使うため、`{"enabled":"false"}` が有効扱いでツールを起動します（[graphify-probe.sh:39](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:39)、[cocoindex-probe.sh:40](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:40)、[codegraph-probe.sh:36](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:36)）。
   - (b) 深刻度: medium
   - (c) 推奨: `not-configured` はキー不在だけに限定し、不正 JSON・型不正はツールを起動しない独立の `invalid-config` にする。

4. 3 seam だけを変える判別基準が実装と一致しない

   - (a) [PLAN.md:29-31](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:29) は3つを「Phase 2 の補助候補源」としますが、`symbolGraph` は Phase 3 専用です（[config-schema.md:257](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:257)、[ADOPTION.md:147](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:147)）。逆に据え置く `indexing` も init では未検出時に省略され（[init/SKILL.md:120](/Users/akiratakahashi/Projects/doc-audit-harness/skills/init/SKILL.md:120)）、probe は `.mdq/` を書きます（[mdq-index.sh:77](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:77)）。Phase、書込み、副作用、init の省略規則のどれでも現在の境界は成立しません。既存設定で3キーを省略し、自動検出に依存していた利用者は黙って機能を失います。
   - (b) 深刻度: medium
   - (c) 推奨: 対象を「v0.13で追加された3 seam の契約修正」と明記し、旧設定からの移行試験を追加する。

5. `.gitignore` は自動復元せず、報告のみにすべき

   - (a) 実機 CocoIndex は `settings.yml` 不在時だけ自動初期化へ入り（[cli.py:80](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:80)、[同:114](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:114)）、そこで `.gitignore` を変更します（[同:125](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:125)、[同:301](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:301)）。`ccc index` の入口は自動初期化有効です（[同:636](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:636)）。一方、`settings.yml` があれば探索は成功します（[settings.py:333](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/settings.py:333)）。したがってマーカー検査だけで今回の原因経路は閉じます。
     
     [PLAN.md:44-46](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:44) の全バイト復元では、約8.5秒の索引中に利用者が加えた編集と CocoIndex の追記を区別できず、利用者の編集を消します。`.gitignore` が symlink なら CocoIndex の `is_file/read_text/write_text` はリンク先を辿り、外部ファイルを変更し得ます。復元失敗・割込み・同時編集も未定義です。非 git repo や `.git` がファイルの worktree では、実機コードはそもそも `.gitignore` を書きません（[cli.py:307](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:307)）。
   - (b) 深刻度: high
   - (c) 推奨: 復元処理・`gitignore-modified` 状態・復元試験を計画から削り、`settings.yml` の事前確認だけで防止する。

6. seal/read-manifest 停止時の run 解放計画が不完全

   - (a) 全ての gate 前停止は run 解放必須です（[audit/SKILL.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:67)）。ところが既存 `read-manifest.py` 失敗分岐は stop だけで、解放を明記しません（[同:371](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:371)）。PLAN と DoD は seal の非0だけを対象にしており（[PLAN.md:13](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:13)、[同:141](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:141)）、新しい未封印拒否で残る lock を検査しません。また PLAN の省略コマンド `open-run.py --release --runid` は、実CLIで必須の `--run-base` と `--repo-root` を欠きます（[open-run.py:116](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:116)）。
   - (b) 深刻度: high
   - (c) 推奨: exit 5、その他の seal 非0、read-manifest 非0の3枝すべてに、[SKILL.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:52) の完全な解放コマンドを要求する。

7. `read-manifest.py` の非 object 入力で traceback が残る

   - (a) 現行は hash が一致すれば任意 JSON を返します（[read-manifest.py:15-28](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/read-manifest.py:15)）。実測でも `[]` を `list []` として受理しました。[PLAN.md:16](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:16) どおり直後に `manifest.get(...)` を置くと、配列や `null` で `AttributeError` になりますが、main の捕捉対象に `AttributeError` はありません（[read-manifest.py:39](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/read-manifest.py:39)）。既存 `codex-dispatch.py` は型確認済みですが（[codex-dispatch.py:60](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-dispatch.py:60)）、CLI単体は壊れます。
   - (b) 深刻度: medium
   - (c) 推奨: `dict` 型と `sealed is True` を一体で検査し、配列・`null` も exit 2 の試験対象にする。

8. Phase 5 の独立枝は方針として正しいが、現在の DoD では到達不能でも通る

   - (a) `symbol-graph` の先頭枝は `AVAILABLE=false` を無条件に拾います（[audit/SKILL.md:678-681](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:678)）。この後ろに `reason:not-configured` を足すだけでは、解釈順によって新枝が隠れます。[PLAN.md:154-156](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:154) は枝の存在しか検査しません。また [PLAN.md:32](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:32) の「導入済み」は、ツール確認前に停止する設計では判定不能です。
   - (b) 深刻度: medium
   - (c) 推奨: `reason` 優先の排他的な対応表にし、各 reason から期待する1行を生成して照合する試験にする。

9. §0-12 の導出値化はそのままでは失敗し、外部依存も解消しない

   - (a) 実測で dir-framework の追跡ファイルは48件、現試験は `48 != 46` で失敗しました（[test_import_audit_scope.py:657-684](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_import_audit_scope.py:657)）。さらに実物 `audit-scope.json` は直下24キーの object で、`rules` キーはありません。したがって [PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:78) の `len(scope["rules"])` は `KeyError` になります。実装もトップレベルの組数を rules と数えます（[import-audit-scope.py:73](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:73)、[同:286](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:286)）。外部 repo 不在時は skip されるため、[PLAN.md:186](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:186) の skip 0 とも矛盾します。
   - (b) 深刻度: high
   - (c) 推奨: §0-12 を今回の成果物から外し、リポジトリ内の固定された最小試験データへ置き換える別修正にする。

10. `docGlobs` の全スクリプト走査は正しい実装も落とす

   - (a) Issue の「他12か所」は列挙すると11か所です。実物には、設定ではなく封印済み manifest を読むため意図的に `[]` を使う [sibling-scan.py:156](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/sibling-scan.py:156) と、同じ既定を変数経由で渡す [import-audit-scope.py:588](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/import-audit-scope.py:588) があります。[PLAN.md:132-134](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:132) の全 `*.py` 走査では、正しい別契約を誤検出するか、対象0件の検査を作れます。
   - (b) 深刻度: high
   - (c) 推奨: `fix-scope.py` の動作試験と、既知の11個の config consumer が完全一致する構造試験だけに限定する。

11. DoD に「誤実装でも通る」検査が複数ある

   - (a) 判定表にある `--config` 未指定・指定先不在・top-level 非 object は、追加12試験に含まれません（[PLAN.md:147-151](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:147)）。新試験数も記載内訳は最低20件なのに `≥19` なので、S2試験を落としても通ります（[同:186](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:186)）。`grep -c ≥6` や各ファイル `settings.yml ≥1` も、誤った節やコメントへの追記で通ります（[同:152](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:152)、[同:167](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:167)）。
   - (b) 深刻度: medium
   - (c) 推奨: 合計件数と単純出現数を捨て、入力表の全ケースと節内の正確な対応を完全一致で検査する。

12. 日本語 refresh 契約の指定が英語形式のまま

   - (a) [PLAN.md:55](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:55) は英日とも `0.13.0, or 0.13.1` 形式を示しますが、日本語実物は日本語句読点かつ複数行です（[ADOPTION.ja.md:264](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:264)）。既存 `test_j` は行単位の完全一致です（[test_v013_contracts.py:239](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:239)）。
   - (b) 深刻度: low
   - (c) 推奨: 日本語専用の完全一致パターンを worker 指示に明記する。

総括

「計画自体の欠陥（PLAN を直してから実装）」は 1〜11 です。特に 1、2、5、6、9、10 は着手阻止事項です。

「worker 指示で吸収できる細部」は 12 のみです。

版更新箇所については、`test_i`、`test_j`、`test_g`、`test_scaffold`、`test_release_handoff`、`engine-shas` の最大版という既知の面は PLAN に収載されており、12以外の明白な取りこぼしは確認しませんでした。`read-manifest.py` の sealed 検査も、有効な既存2呼出し元と Phase 2 の直接 parse 自体は壊しません。

指定試験は書込み禁止環境のため一時フォルダを作れず、大半が環境エラーになりました。ただし外部結合試験の `48 != 46` は実際に再現しています。リポジトリのファイル変更は行っておらず、開始時から存在した未追跡 `.claude/` にも触れていません。