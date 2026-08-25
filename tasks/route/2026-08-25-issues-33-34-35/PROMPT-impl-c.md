# boss レビュー結果（段階 B）: 承認。段階 C の指示

段階 B は差し戻しなしで承認した。最終段階 C を実装せよ（PLAN §5.4・§5.5・§5.6 の残り）。

## 段階 C の範囲

1. **バージョン bump（v0.11.0）**: `.claude-plugin/plugin.json` ／ `docs/ADOPTION.md:201` ／
   `docs/ADOPTION.ja.md:186` ／ `docs/ADOPTION.ja.md:237-238`（refresh 到達版 — 「0.10.1 から 0.11.0 へ」
   の移行説明として更新）／ `docs/ADOPTION.md:254`（英語版 refresh 説明・同様に）／
   `tests/test_decide_verdict.py:422`（版数固定値）
2. **engine-shas.json**: 0.11.0 エントリを `check-docs` / `doc-lint` / `check-docs-engine` の
   **3 SHA すべて**で追加（既存エントリは保持）。SHA は**bump 完了後に** scaffold.py の計算関数を
   実行して算出する（手書き禁止。plugin.json の版→SHA の順序依存に注意）。追加後、scaffold 系の
   既存テスト 10 件が green に戻ることを確認。
3. **scaffold refresh テスト（PLAN §5.6 scaffold 節）**:
   - `git show docaudit--v0.10.1:skills/audit/scripts/generic-layers.py` から歴史的 engine 本文を取得し
     `tests/data/` に fixture として配置。テスト冒頭で fixture の stamp 除外 SHA が engine-shas.json の
     0.10.1 エントリ（check-docs-engine）と一致することを assert
   - 0.10.1 stamp の `scripts/check-docs.py` が `--refresh` で 0.11.0 へ更新されること
   - 利用者改変済みの旧 engine が skipped 保存されること
   - 新規生成物 3 種の SHA が 0.11.0 エントリと一致すること
4. **config-schema.md**: 新キー 3 種（`layerGlobs` / `frontMatterOverrides`（globs 配列）/
   `auditReportsInCorpus`）の仕様、#33 の severity 変更（backtick 具体ファイル FAIL 昇格・bare=WARN 検出網）
   と互換性影響（既存 repo で新 FAIL が出うる・緩和は layerGlobs とレポート除外）、既知の限界
   （file/dir 判定で `docs/LICENSE` 型は WARN・bare は非 ASCII パス検出対象外・fence/indented 簡易判定は
   過剰マスク側）、レポートマッチャのテンプレート由来 regex 仕様（suffix 常時許容・位置規則・
   `[0-9]` 限定）
5. **SKILL.md（audit）**: レポート作成手順に suffix 生成契約を明記 —「衝突時はゼロ埋め 2 桁 `_02` から
   開始（`_99` の次は `_100`）。挿入位置は `[_NN]` があればその位置、無ければ日付の直後。既存レポートの
   上書き禁止」
6. **層説明の整合**: `docs/ADOPTION.md:350` / `docs/ADOPTION.ja.md:331`（existence 層＝全 WARN の説明）を
   新 severity へ更新。`skills/audit/SKILL.md` / `skills/init/SKILL.md` / `scaffold.py` 内テンプレートに
   「リンク形式のみ検査」「existence は WARN のみ」等の旧前提記述が無いか grep で確認し、あれば更新・
   無ければ「該当なし」と報告（無理に変更を作らない）
7. **最終検証**:
   - `python3 -m unittest discover -s tests -t . -v` **全 green**（末尾サマリを報告に含める）
   - 版残置ゲート: `grep -rn "0\.10\.1" .claude-plugin/ skills/ docs/` の残置が
     (a) engine-shas.json の履歴エントリ (b) ADOPTION 両言語の移行説明行 のみであることを確認し、
     残置の全行を報告に列挙

拘束は従来どおり（変更範囲は PLAN §7・スコープ外リファクタ禁止・既存テスト期待値変更は意図的差分と
突合して列挙・失敗は隠さず報告）。
