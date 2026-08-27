あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド 3

`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md` を rev.3 に更新した。R2 の 21 指摘との対応を自己申告する。
対応済み事項の再指摘は不要。rev.3 を読み直し、**新たに生じた矛盾・取りこぼし・判別不能な検査**だけを指摘せよ。
新規指摘が無ければ「新規指摘なし」と明記せよ。

## R2 指摘との対応（自己申告）

1. config 不在: パス安全（repo 内包含・symlink）と存在検査を分離。config 不在は空 config＋`--doc-globs` で `not-imported`。実物検査コマンドも config 不在前提に修正（§9、§8）。
2. drift×lock: Phase 0 の順序を `--break-lock` 処理 → audit-scope 検査 → open-run に固定。契約テスト (c) で行順序を検査（§9、§6）。
3. 承認→書込封印: `--check` が `configSha`/`scopeSha` を返し、`--write` は `--expect-config-sha`/`--expect-scope-sha` 必須（不一致 exit 4）。lock は `O_CREAT|O_EXCL` で取得し書込後 unlink（既存 exit 3）（§9）。
4. required×full: `required:true` の full では codex review を実行（diff でなく HEAD tree で impacted 全文書 vs code の変種プロンプト）。実行不能時のみ REFUSED。start-run は required なら mode 無関係に `phase4Required:true`（§10 #42）。
5. last-run: 非更新は history・anchor のみ。last-run は REFUSED 理由つき更新（既存契約維持）（§6、§10）。
6. provenance 封印: impactSha を不採用にし、manifest `provenance:{path:prov}` を start-run が書き seal-run が封印。check-verdicts が manifest と impact.json の provenance 一致を検査。codex-dispatch は manifest からのみ読む。SKILL workflow 経路も manifest.provenance から（§10 #39、§6）。
7. 統合試験工程: resolve → supplement → plan-dispatch → start-run → seal-run → returns/phase4 evidence（write-evidence）→ decide-verdict（§6）。
8. Stage 再編: S1 = #43 fixture 保存→修正→版 bump→engine-shas→test_scaffold を同一 Stage。各 Stage 末にフルスイート green（§4）。
9. evidence 厳格検証: `codexReview` が存在すれば required 無関係に object・`state` 文字列・enum 5 値を検証、違反は REFUSED。不在のみ後方互換（§10 #42）。
10. Phase 5 codex 行: 4 状態契約（not-active／skipped-full-run／completed／did-not-run(<state>)）を個別試験（§6、§10）。
11. list 規則: インデントコードは段落を中断できない（直前非空行が段落なら継続）、空行後のみ `ci+4`/`4` でコード、tab は次の 4 列境界へ展開。対テストに「空行なし深インデント継続文」と「非ゼロ列 tab」を追加（§10 #43、§6）。
12. saturationWarnRatio: bool を除く数値、`0` で無効、比較は丸め前（§10 #40、§6）。
13. handoff 期待回数: 分岐別に tag/Release/Issue close/rsync の期待回数表（§12）。
14. 1 ケース 1 故障: SHA 欠落/非 hex、PR 欠落/非数値、HEAD≠SHA と origin/main≠SHA を分離、Release 不正 3 種を分離（§12）。
15. 契約テスト: front matter 解析、Phase 2 コマンド行の `--history`、Phase 0 の行順序（break-lock → scope 検査 → open-run）、Phase 4 evidence の `codexReview`/`state`、7 消費側の列挙箇所、config-schema 表 5 行、版一致、`git ls-files` 限定の残存検査（§6）。
16. custom scope: Phase 0 は `auditScope.path` を唯一の入力（§9）。
17. 所有判定: 構造化 `source:"audit-scope"`。note 文言は無関係。resolve-impact が未知キーを無視することをテストで固定（§9）。
18. 改行名: `docaudit_paths.glob_to_regex` を `re.DOTALL` 化（許可パスに追加）＋改行を含む合成パス集合での等価試験（§2/§6/§7）。
19. 版残存: `git ls-files` 限定、ADOPTION:139/124 を許容リストへ（§12）。
20. 0.12.0 fixture: S1 先頭で `tests/data/engine-0.12.0.py` を保存し正規化 hash == engine-shas 0.12.0 を固定（§10 #43）。
21. report 除外: `auditReportsInCorpus` false/true の対試験（§6 (iii)）。

## 今回特に見てほしい点

- (a) R2 対応同士の組み合わせ: 「required:true の full で codex review 実行」×「full mode の Phase 4 は従来 code/security review を実行する」×「`phase4Required`」の整合。「manifest.provenance 封印」×「impact-supplement が impact.json を書き換える（start-run 前）」×「check-verdicts の照合対象」。「import の lock O_EXCL」×「open-run の lock 形式（runid・inode 検査）」×「`--break-lock` が import lock を扱えるか」。
- (b) `re.DOTALL` 化が既存の `matches_glob` 利用箇所（diffGlobs・docGlobs・layerGlobs・protectedGlobs・report_pattern）に与える影響（改行名以外で挙動が変わらないか）。
- (c) Stage 分割の依存: S2 の `historySha` と S4 の manifest provenance、S3 の Phase 0 配線と S4 の Phase 5 行、S5 の契約テストが S1〜S4 の成果物名に依存する点。各 Stage 末フルスイート green が本当に成立するか。
- (d) DoD にまだ「対象 0 件で合格」「正誤どちらでも通る」検査が残っていないか。

出力形式は前回と同じ（番号・重大度・根拠・推奨 1 つ、最後に「PLAN 欠陥／worker 吸収」の区分）。
