メタ認知：指定観点への追従で「検査項目が多い＝十分」と判断しやすいため、未修正でも通る検査と、文書だけで利用者の動作を壊す変更を重点的に疑った。docs-only を低リスクとは見なしていない。

結論は明確で、現 PLAN のまま実装へ進むべきではない。少なくとも high 4件を先に修正する必要がある。

1. **重大度: high — #47 の「seal 失敗 → REFUSED」は通常経路では成立しない**

   根拠: [`tree-digest.py:23`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/tree-digest.py:23) は glob を拒否し、実測でも `.claude/state/**` は `digest excludes may not contain globs`。しかし [`seal-run.py:63`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/seal-run.py:63) はその失敗を exit 2 にし、[`SKILL.md:358`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:358) の通常手順では gate 前に停止する。PLAN は [`PLAN.md:81`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:81) と [`PLAN.md:181`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:181) で REFUSED と断定している。

   推奨: 文書契約を「seal が exit 2 で失敗し、verifier/gate 前に監査停止」に修正する。

2. **重大度: high — copy可能な設定例に `auditScope` を追加すると利用者の監査を壊す**

   根拠: PLAN [`PLAN.md:110`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:110) は `auditScope` の「既定値」例を要求するが、これは importer 専用・手編集禁止である（[`config-schema.md:16`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:16)）。[`start-run.py:142`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/start-run.py:142) は、キーが存在すれば実在path、64桁hash、rules、importedAtを必須にする。有効な静的既定値は存在せず、`{}` や `null` も拒否される。

   推奨: JSON本体には `auditScope` を入れず、`_note` に「import処理が生成するため手書きしない」とだけ記載する。

3. **重大度: high — handoff試験は定数だけの再照準では確実に失敗する**

   根拠: PLAN [`PLAN.md:201`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:201) はdocstringと定数以外の変更を禁止している。しかし試験本体に旧tag直書き（[`test_release_handoff.py:424`](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:424)）、Issue 6件固定（[同:436](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:436)、[同:457](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:457)）、旧Issue番号固定（[同:442](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:442)、[同:449](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:449)）がある。

   推奨: これらの変更を明示的に許可し、tagと件数・Issue集合を `TAG`／`ISSUES` から導出させる。

4. **重大度: high — docs-onlyの検査が実行コードの削除を見逃す**

   根拠: [`PLAN.md:112-114`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:112) と検証コマンド [`PLAN.md:174`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:174) は追加行しか検査しない。既存コードを削除してコメントを1行追加しても通る。対象の [`fix-scope.py:87-106`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:87) は許可・拒否動作そのものである。変更なしでも出力0になり得るため、コメント追加漏れも区別できない。

   推奨: 差分を「追加1行・削除0行・追加行は指定コメント」に完全固定する。

5. **重大度: medium — #49-1 の evidence不正条件が未対応**

   根拠: Issueは、Phase 4の `codexReview` が非object、stateが非stringまたは未知値なら `required:false` でも REFUSED としている。実装は [`decide-verdict.py:786-795`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:786)、既存試験は [`test_decide_verdict.py:1190`](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_decide_verdict.py:1190)。PLAN [`PLAN.md:97-98`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:97) は設定の2条件しか扱わない。

   推奨: en/ja両方に「不正なcodexReview evidenceはrequired値によらずREFUSED」を追加する。

6. **重大度: medium — 日本語refresh行が0.13.0のままでも版試験を通る**

   根拠: `test_j` の英語式は更新先まで同じ行で固定する（[`test_v013_contracts.py:207-211`](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:207)）。日本語式は旧版列挙行だけを検査し（[同:212-216](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v013_contracts.py:212)）、更新先 `0.13.0` は次行の [`ADOPTION.ja.md:262`](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:262) にある。`test_i` もrefresh文は読まない。

   推奨: en/ja両方について、旧版集合と更新先 `0.13.1` を複数行単位で明示検査する。

7. **重大度: medium — 複数のDoDが未修正・誤修正を区別できない**

   根拠:

   - `update-failed` の検索は、既にPhase 0説明の [`SKILL.md:185`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:185) が一致するため、誤ったPhase 5分岐（[同:674-677](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:674)）を残しても通る。
   - 契約試験(f)は、要求された新規キーが全欠落した現行exampleでも「既存キーはschemaにある」として通る。
   - 契約試験(c)を文書全体検索で実装すると、欠落6件中 `codex-dispatch.py`、`codex-review-plan.py`、`read-manifest.py`、`write-template.py` は既に付録外の本文に存在する。
   - `CRITICAL` 1語の存在検査は、完全なseverity集合や未知値REFUSEDを保証しない。

   推奨: 対象節を切り出し、対象件数・期待集合・禁止集合を別々のassertで完全一致させる。

8. **重大度: medium — en/jaパリティの見出し数検査がMarkdown構造を見ていない**

   根拠: [`PLAN.md:115`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:115) の `grep '^#'` はコード例内のshellコメントも数える。実測35/35のうち、実際の `##` 見出しは15/15であり、英語側 [`ADOPTION.md:22-38`](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:22) のコメント等が混入している。§5のキー集合・表行、付録一覧の左右一致も自動検査されない。

   推奨: コードブロックを除外し、見出しレベル列・§5キー列・付録path列をen/jaで比較する。

9. **重大度: medium — #48-6の`bin`注記は更新範囲が不足する**

   根拠: PLANはSKILLとschema表だけを更新するが、詳細説明 [`config-schema.md:216-220`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:216) と [同:260-270](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:260) もvendored `bin` がPhase 3まで効くように読める。実際のWorkflowには可否booleanしか渡らず（[`SKILL.md:419`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:419)）、テンプレートは `ax`／`codegraph` 固定（[`workflow-template.js:123`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/workflow-template.js:123)）。

   推奨: runtimeは変えず、schemaの詳細節も「binはPhase 0 probeのみ」に統一する。

10. **重大度: medium — #50-5を正本だけ直すと利用者向けen/jaとの矛盾が残る**

    根拠: PLAN [`PLAN.md:112`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:112) はconfig-schemaだけを更新する。一方、[`ADOPTION.md:305`](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:305) と [`ADOPTION.ja.md:286`](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:286) は `docGlobs` 省略時に通常既定値が使われるとしか読めない。`fix-scope.py` だけは [`fix-scope.py:87`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/fix-scope.py:87) で空集合となる。

    推奨: ADOPTION en/jaの`docGlobs`行にも「pre-flight fixのみ省略時全拒否」を追加する。

11. **重大度: low — 新handoffに旧版文字列が残っても検査を通る**

    根拠: 前版には9行の `0.13.0` 表記がある（[`release-handoff.sh:2`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh:2)、[同:11](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh:11)、[同:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh:83)、[同:220](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh:220)等）。usage、コメント、一時ファイル名、診断文は現行試験が検査しない。

    推奨: 新handoff単体で `0.13.0` の残存0件をDoDにする。

12. **重大度: medium — `git add -f` の単位とcommit順が再現性・範囲を損なう**

    根拠: PLAN [`PLAN.md:211-212`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:211) はS2 commit後に作業記録ディレクトリ全体を強制追跡する。したがってS2 commit単体は再照準済み試験が参照する新scriptを含まず赤い。現在の同ディレクトリには約173KBのsession log等もあり、ディレクトリ指定では意図しない記録まで同時に入る。

    推奨: 新scriptを試験再照準と同じcommitで、ファイル名を明示して強制追跡する。

13. **重大度: low — Issue/PLANの実装参照に誤りがある**

    根拠: Issue [`issues-46-50.md:39`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/issues-46-50.md:39) の `.claude/worktrees/*` は `*` を含むため実際には拒否される。許可されるのは親prefixまたは個別literal子pathである。またPLAN [`PLAN.md:40`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:40) の `decide-verdict.py:866-869` は現在final-return検査で、codex evidenceの正しい位置は `:786-798`。

    推奨: 実装参照と許可値説明を現HEADに合わせて訂正する。

14. **重大度: low — 契約試験(e)は費用対効果が低い**

    根拠: [`PLAN.md:132`](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md:132) の「です・ます」検査は機能・互換性契約ではなく、引用や例示にも反応する一方、(a)(c)(d)(f)には上記の判別不足がある。

    推奨: 恒久試験(e)を落とし、その1件分を(a)(c)(d)(f)の完全一致検査強化に振り替える。

問題なし（確認した根拠）:

- #46の所見は現HEADで成立する。README最終更新は `a9b8a17` で、[`README.md:25`](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:25)、[同:61-81](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:61)、[同:95](/Users/akiratakahashi/Projects/doc-audit-harness/README.md:95) に記載漏れ・陳腐化がある。
- #48の`--config`必須、`update-failed`、`--available`小文字choices等の所見は成立する。`--available True` は実測exit 2。
- #49のrequired型・enabled衝突およびseverity集合は [`decide-verdict.py:713-718`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:713) と [同:262-279](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:262) に一致する。
- #50のcontent hash条件は [`resolve-impact.py:243-257`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:243) にあり、変更済み文書を除外する既存試験も [`test_resolve_impact.py:381`](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_resolve_impact.py:381) にある。
- 指定の `0.13.0` 全検索は実行時212行。歴史的tasks・互換性節等を除く現行版結合では、上記handoff試験以外にPLAN未収載の赤化箇所は見つからなかった。
- `scaffold.py` に版定数はなく、plugin版を [`scaffold.py:320`](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:320) で読み、engine-shasの存在・hash一致を [同:172-180](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/scaffold.py:172) で検査する。現HEADのdry-runはexit 0、`stampVersion: 0.13.0`。
- `test_j` の許容リストはja側にも存在する。ただし指摘6のとおり更新先版は検査していない。
- runtimeを変更する提案自体は混入していない。`bin`と`fix-scope`は、指摘9・10の文書範囲を補えばdocs-onlyで足りる。
- handoff scriptの再作成は落とすべきではない。承認SHAでの再試験と安全なリリース再開に必要である。
- PROMPTSの新節も到達性欠落を直接埋めるため維持してよい。短い1節で十分である。
- HEADは `3a6068b`、追跡済み差分は0。現在見える未追跡 `.claude/worktrees` は今回の役割分担で生成されたため、開始時cleanという前提を反証しない。
- フル試験は `Ran 487 tests` まで確認したが、読み取り専用環境に利用可能な一時フォルダがなく `FileNotFoundError` となったため、487件greenは独立追認できていない。実装環境での再実行が必要である。

要約:

- **PLAN自体の欠陥（PLANを直してから実装）**: 指摘1〜12、14。特に1〜4は着手阻止事項。
- **worker指示で吸収できる細部**: 指摘13の行番号・表現訂正、翻訳表現、診断文の自然さ。これ以外をworker裁量に任せるべきではない。