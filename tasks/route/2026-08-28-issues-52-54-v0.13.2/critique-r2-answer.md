メタ認知（着手時）：R1 が広く反映されたことで早期に「十分」と判断しやすいため、新設した規則同士の矛盾と、検査の抜け道に絞って再検分しました。

結論は「実装未承認」です。新規の実質的指摘があります。

1. basename deny の大文字小文字区別は、実環境で保護を迂回できる

   - (a) PLAN は `CLAUDE.md`／`AGENTS.md` を大文字小文字区別で拒否します（[PLAN.md:12](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:12)）。一方、既存の組込み拒否は `path.lower()` で大小文字を同一視しています（[fix-scope.py:97](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:97)）。実機ファイルシステムでは `claude.md` を作ると `CLAUDE.md` として参照できることを確認しました。したがって、小文字や混在表記の指示ファイルを修正対象にできてしまいます。
   - (b) 深刻度: **high**
   - (c) 推奨: basename を `.casefold()` して、大小文字を同一視して拒否する。

2. 新しい組込み拒否規則の説明更新先が不足している

   - (a) PLAN と DoD は主に設定表の行だけを更新対象にしています（[PLAN.md:15](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:15)、[PLAN.md:161](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:161)）。しかし実行手順の本文は組込み拒否を ADR・decisions・logs・`.claude/**` だけと列挙しており（[SKILL.md:281](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:281)）、schema 本文も同様です（[config-schema.md:154](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:154)）。正しい実装でも説明が食い違ったまま契約テストを通ります。
   - (b) 深刻度: **medium**
   - (c) 推奨: この2段落も更新対象とし、大小文字を同一視する basename deny を明記する。

3. `invalid-config` のうち3行は通常の監査経路では到達不能

   - (a) PLAN の表 #6〜#8 は、不正 JSON・config 不在・top-level 非 object を probe が `invalid-config` として返す契約です（[PLAN.md:39](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:39)）。ところが config 不在は probe 前に停止し（[SKILL.md:9](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:9)）、不正 JSON／配列は probe 前の `.get()` で失敗します（[SKILL.md:14](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:14)、[SKILL.md:25](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:25)）。`open-run.py` は内容の固定値を取るだけで全体形式を検査せず、`start-run.py` の JSON 読み取りはさらに後です（[start-run.py:215](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:215)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: 通常経路の事前検査と probe 単体の防御を明確に分け、#6〜#8 は「probe 単体呼び出し時のみ」、Phase 5 の `invalid-config` は到達可能なキー単位の不正だけと定義する。

4. `invalid-config` が schema 上の不正値を取りこぼす

   - (a) schema は3 seam の `bin` を文字列、semanticSearch の `minScore` を数値と定義しています（[config-schema.md:37](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:37)）。現行 probe は `bin` が配列等でも `str(...)` に変換するため（[graphify-probe.sh:39](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:39)、[cocoindex-probe.sh:40](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:40)、[codegraph-probe.sh:36](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:36)）、`invalid-config` ではなく `not-installed` 等になり得ます。`minScore` は後段で数値として渡されます（[SKILL.md:330](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:330)、[impact-supplement.py:196](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:196)）。DoD は `enabled` と object 判定しか固定していません。
   - (b) 深刻度: **medium**
   - (c) 推奨: `invalid-config` 判定を、その seam が実際に読む全フィールドへ拡張する。

5. 「3 seam は verdict に一切影響しない」という判別基準は事実と反する

   - (a) PLAN は3 seam を verdict に影響しない補助としています（[PLAN.md:42](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:42)）。しかし graphify／semantic の結果は監査対象文書へ追加され（[impact-supplement.py:271](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:271)、[impact-supplement.py:287](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/impact-supplement.py:287)）、その文書も PASS/WARN/FAIL 判定を受けます（[workflow-template.js:145](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:145)）。追加文書の FAIL は最終結果を `NEEDS_FIX` にします（[decide-verdict.py:850](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:850)、[decide-verdict.py:894](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:894)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: 基準を「probe の利用不能自体は FAIL 根拠にならないが、取得した候補や証拠は verdict に間接影響する」と訂正する。

6. reason 優先表に必要な値を保持する計画がない

   - (a) 現行 Phase 0 は available／bin 等だけを保持し、`reason` を変数として残していません（[SKILL.md:174](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:174)、[SKILL.md:188](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:188)、[SKILL.md:202](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:202)）。PLAN は Phase 5 を reason 優先にするとしていますが、3つの reason を保持する変更を要求していません（[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:49)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: `SYMBOL_GRAPH_REASON`、`DOC_GRAPH_REASON`、`SEMANTIC_SEARCH_REASON` の保持と使用を明示的な契約にする。

7. `.gitignore` の検出結果から原因を断定し、`git checkout` を案内するのは危険

   - (a) 前後の存在有無と sha256 だけでは、`ccc index` の変更と並行した利用者編集を区別できません（[PLAN.md:63](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:63)）。それにもかかわらずメッセージは ccc が変更したと断定し、`git checkout -- .gitignore` を案内します（[PLAN.md:66](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:66)）。新規生成された未追跡 `.gitignore` にはこのコマンドは効きません。実機 CocoIndex は `Path.read_text/write_text` で symlink の参照先を更新するため（[cli.py:310](/Users/akiratakahashi/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/cli.py:310)）、symlink 本体を checkout しても参照先の内容は戻りません。CRLF から LF への変化は偽陽性ではなく実際のバイト変更ですが、原因の断定は同様にできません。
   - (b) 深刻度: **high**
   - (c) 推奨: `available:false` は安全側として維持しつつ、「index 実行中に `.gitignore` が変化したため手動確認が必要」とだけ報告し、原因断定と checkout 指示を削除する。

8. AST 検査の対象数を実装者が後決めできる

   - (a) PLAN は N を 11 または12として実装後に固定するとしています（[PLAN.md:158](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:158)）。実物を数えると `2+2+2+1+1+2+1=11` 箇所です。12で通す検査は対象外の呼び出しを誤算入しています。実装後に N を選べるため、呼び出しの消失や誤追加を基準値へ取り込めます。
   - (b) 深刻度: **medium**
   - (c) 推奨: 実装前に N=11 とファイル別内訳を PLAN に固定する。

9. reason と挙動変更文書の DoD は、単語を並べただけの誤実装でも通る

   - (a) 状態行検査は reason の集合一致だけなので、メッセージの取り違え、重複枝、複数 reason を同じ枝で処理する実装を検出できません（[PLAN.md:182](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:182)）。同様に §7 は4語の存在しか検査せず（[PLAN.md:209](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:209)）、逆の説明や `invalid-config`／移行条件の欠落でも通ります。
   - (b) 深刻度: **medium**
   - (c) 推奨: reason ごとの一意な枝と期待メッセージ、英日それぞれの4変更＋移行条件を対応表で完全一致検査する。

10. `calls.log` では「`command -v` も実行していない」を証明できない

   - (a) PLAN は tool と `command -v` の両方を実行しない契約です（[PLAN.md:32](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:32)）。DoD は stub が作る `calls.log` の不在だけを確認します（[PLAN.md:178](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:178)）。`command -v` はシェル内部の確認処理なので、実行されても stub の記録には残りません。
   - (b) 深刻度: **low**
   - (c) 推奨: 副作用のない `command -v` 非実行要求を契約から外し、「外部 tool を起動しない」ことだけを検査する。

11. フルスイートの `+Δ` が自己申告で循環している

   - (a) Δ に「契約テスト本数」を含め、その値を worker が実装後に報告する設計です（[PLAN.md:217](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:217)）。必要な検査を落としても、小さい Δ を申告すれば整合します。また unittest の `subTest` はケース数ではなく1テストとして数えられるため、「4ケース」等と `Ran N tests` は直接対応しません。
   - (b) 深刻度: **low**
   - (c) 推奨: 総テスト件数ではなく、事前に固定したテスト名と入力行の網羅を検査する。

12. `fix-scope.py` の期待順序が実装の出力順と一致しない

   - (a) DoD は `["docs/a.md","README.md","SECURITY.md"]` の順を要求します（[PLAN.md:154](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:154)）。実装は `sorted(set(allowed))` なので（[fix-scope.py:108](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:108)）、実際は `["README.md","SECURITY.md","docs/a.md"]` です。正しい deny 実装でも失敗します。
   - (b) 深刻度: **medium**
   - (c) 推奨: 期待値を実装の決定的な並び順に合わせる。

13. fixture 作成順が JSON fixture を空ファイルで上書きし得る

   - (a) PLAN は `audit-scope.json`／`doc-audit.json` を配置したうえで、`paths.txt` の各 path に空ファイルを作るとしています（[PLAN.md:97](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:97)）。実測した48行の一覧にはこの2ファイル自身も含まれます。記載順をそのまま実装すると JSON が空になり、狙った `rules==24`／`not-imported` の再現になりません。DoD は fixture の存在だけを確認し、`951570b` 由来であることも検査しません（[PLAN.md:203](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:203)）。
   - (b) 深刻度: **medium**
   - (c) 推奨: path の空ファイルを先に作り、最後に2つの JSON を上書き配置する固定手順と、元 commit／内容の固定値を契約にする。

### 総括

「計画自体の欠陥（PLAN を直してから実装）」は #1〜#11 です。特に #1、#7 は安全性に関わるため、worker の裁量へ残すべきではありません。

「worker 指示で吸収できる細部」は #12、#13 です。ただし現状の DoD をそのまま boss が使うなら、PLAN 側で直した方が確実です。

なお、次は新たな欠陥を確認しませんでした。

- `docs/CLAUDE.md` を文書探索では扱い、修正だけ拒否する非対称は妥当です。修正権限を狭めても finding は残るためです（[SKILL.md:283](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:283)）。
- `read-manifest.py` の sealed 共通検査、Phase 2 の raw parse、3停止分岐の run 解放は整合しています。
- 版更新5面、`engine-shas` の最大版、既存契約テストの更新面に新たな取りこぼしはありません。
- 指定範囲の既存テストは78件を実行し、既知の外部 repo 件数不一致1件だけが失敗しました。

リポジトリの修正は行っていません。