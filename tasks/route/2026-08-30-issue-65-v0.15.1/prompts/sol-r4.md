あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド4（上限5のうち4回目）: PLAN rev.4 の再批判

`tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md` を rev.4 に改訂した（rev.3 は `PLAN.rev3.md`）。前回指摘との対応（自己申告）:

1. （HIGH 内部改行・受け渡し）→ codegraph と同じく内部の空白・タブ・改行を有効扱い。python→bash は NUL 区切り（`IFS= read -r -d ''` ×3）で既存の空白区切り `read` を置換。N12 に `"foo bar"`・`"foo\nbar"` を有効入力として追加、N14 は改行入り DIRNAME の `%q` 1 行表示を検査。
2. （HIGH Phase-3 への伝播）→ §5.1 に整合の根拠を明記: verifier は orchestrator と同じ env で同じ生 `CODEGRAPH_DIR` を受け取り codegraph 自身の規則で解決するため、整合は「probe の規則 == codegraph の規則」（N12）に懸かる。export は保険。Workflow の sealed 引数化は本版の範囲外として REVIEW に持ち越し（#63 の凍結設計と同時）。この判断に異論があれば根拠つきで。
3. （HIGH 対話プロンプト・hook）→ codegraph 呼び出しに `</dev/null` を固定。fake が `stdin_eof` を記録し全ケースで true を要求。boss は非 TTY の scratch で hook 未設置・`codegraph.json` 未生成を実測済み。
4. （HIGH 件数）→ 新規状態 17（N1〜N14＋N5b/N8b/N9b）・probe ≥37・handoff ≥27（改名 2＋新規 3 を名指し）・全体 ≥653。
5. （HIGH committed rename）→ G8 を `git diff --name-status -z -M -C` に。
6. （HIGH ignored 禁止範囲）→ G13: boss が着手前に `docs/superpowers`・他 route の manifest（sha256）を作り、完了時に不変比較。
7. （HIGH G10 矛盾・glob）→ 許可・force-add を具体パス配列＋ディレクトリ接頭辞に（`fnmatch` 不使用）。G10 は `git ls-files` 0 件で判定。
8. （HIGH G3 の弱さ）→ base を e1c0b19 に固定、改名対応表を gate の定数に、G12（`ast` で本体が pass/docstring のみの method を 0 件）。
9. （HIGH #66 契約）→ 5 文（:560、:562-563、:778 新文、非対話分岐文、AskUserQuestion 文）を完全文で固定。
10. （HIGH A2 の有効性）→ G1〜G13 それぞれに意図的違反 fixture を 1 つ定義し、boss が単独 FAIL を実測して記録。
11. （MEDIUM N12 fixture）→ 選ばれるべき dir にだけ db を置く規則を明記。
12. （MEDIUM dangling 親 symlink）→ N8b。
13. （MEDIUM N13）→ fake が rc=7 と `FAKE-DIAG-<n>` を出し、`rc=7` と印の転記を検査。
14. （MEDIUM 行範囲）→ G11: `git diff -U0` の hunk ヘッダで許可行範囲外 0 件。

## 依頼

rev.4 を読み直し、**新規の**指摘のみ（対応不十分は番号で）。判定は「その検査が本当に反例を区別できるか」「実装者が仕様どおりに作れるか」に限定せよ。検査を増やす提案は、それが無いと **誤った実装が完了判定を通る**具体的経路を示せる場合に限る（費用対効果の低いゲート追加は不要と明言してよい）。

残る指摘は「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分し、末尾に HIGH 一覧と「実装に進めてよいか」の 1 行を書け。
