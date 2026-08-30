メタ認知: 最終回なので、既出事項の言い換えや防御過剰なゲート提案を避け、「誤成果物が実際に完了判定を通る経路」があるものだけを HIGH とした。

1／HIGH／計画自体の欠陥（refresh 契約の同期漏れ）

根拠: [tests/test_v0131_docs_contracts.py:90](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0131_docs_contracts.py:90) は refresh 段落の版集合を完全一致で固定している。PLAN の集合には追加で `0.10.0`、`0.14.0`、`0.15.0` が入るが、同テストは [§5.5](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:98)・[§7](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:150)の双方から漏れている。正しい列挙では G1 が必ず失敗する。

誤出荷経路: worker が既存テストを通すため、旧6版のまま更新先だけ `0.15.1` に変えると、互換対象3版が欠けた文書をG1・G5が受理する。

推奨: `tests/test_v0131_docs_contracts.py`を成果物・許可範囲へ追加し、期待集合を `engine-shas.json` の全キーへ同期する。

2／HIGH／計画自体の欠陥（前回のログ偽装対策が不十分）

根拠: [PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:41) は `%q` で常に1行化できるとしているが、Bash は内部の U+2028/U+2029 をエスケープしない。U+2028 の実測出力は `66 6f 6f e2 80 a8 62 61 72 0a` で、Python `splitlines()`では2行になる。N14はLFと通常Unicode名しか検査しない（[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:83)）。

誤出荷経路: 指定どおり `%q` を使った実装は全ゲートを通るが、`CODEGRAPH_DIR="foo<U+2028>bar"`でstderrの行を偽装できる。

推奨: DIRNAMEをASCII限定のエスケープ表現にし、内部U+2028/U+2029をN14へ追加する。

3／HIGH／計画自体の欠陥（不正UTF-8環境でcodegraphとの同値性が崩れる）

根拠: POSIX環境の byte `0xff` はNodeではU+FFFDへ変換されたが、Python `os.environ`では`\udcff`になった。実測では通常のUTF-8エンコードが `UnicodeEncodeError`。PLANのNUL受け渡しとN12はこの境界を定義・検査していない（[PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:41)、[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:78)）。

誤出荷経路: `os.environ.get()`した値をUTF-8でNUL出力する自然な実装は全Nケースを通るが、不正byte環境では前処理が落ち、JSON・exit 0契約を破る。

推奨: OS byte列をNodeと同じ置換方式で復号する規則を明記し、不正byte環境のテストを追加する。

4／HIGH／計画自体の欠陥（前回 #66 公開前停止への対応不十分）

根拠: [PLAN.md:113](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:113) が要求するのは「非0終了・`release create`なし」だけ。複製元の `ensure_tag` は先にlocal tagを作成してremoteへpushする（[release-handoff.sh:90](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-29-issue-56-stage2-v0.15.0/release-handoff.sh:90)）。また、実際のB1はprobeテストだけを対象としており、§5.6が主張するrelease method精読を含まない（[PLAN.md:144](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:144)）。

誤出荷経路: #66確認を `ensure_tag` 後・`ensure_release` 前に置けば、remote tagを公開した後に停止しても、新規必須assert・G1・G3・G12・B1を通る。

推奨: #66負テストにも既存の [`assert_no_release_mutations()`](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:273) を必須化する。

5／HIGH／計画自体の欠陥（前回の具体パス化への対応不十分）

根拠: G8は具体配列のみとする一方（[PLAN.md:127](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:127)）、§7はroute接頭辞を追加許可している（[PLAN.md:157](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:157)）。G10も `prompts/impl-r*.md` 等の無限定globだが、§7はr1〜r5など有限範囲である（[PLAN.md:129](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:129)）。

誤出荷経路: `prompts/impl-r99.md`をforce-addすると、接頭辞方式のG8とglob方式のG10を通り、禁止されたログや秘密をtagへ混入できる。

推奨: 接頭辞許可と無限定globを削除し、G8・G10・force-addで同じ有限パス配列を共有する。

6／MEDIUM／細部（#66状態文と実フローの不整合）

根拠: [PLAN.md:94](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:94) は「before the audit」を完全固定するが、実挙動は監査中に質問し、`/code-review`実行後に監査を再開する（[SKILL.md:551](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:551)）。G11は不正確な説明を強制する。

推奨: 「offer時に実行して監査を再開する、または事前に実行する」と実フローに合わせる。

7／MEDIUM／細部（stdinテスト指示の型不整合）

根拠: [PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:60) は `input=b"STDIN-SENTINEL\n"` を要求する一方、現行helperは [test_codegraph_probe.py:35](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:35) で `text=True`。実測では `AttributeError: 'bytes' object has no attribute 'encode'` となる。

推奨: `text=True`を維持するならsentinelを文字列にする。

計画自体を直すべき HIGH の一覧: **1、2、3、4、5**

このまま実装に進めてよいか: **進めるべきではない。HIGH 1〜5はすべて誤成果物が完了判定を通る具体的経路を持つ。**