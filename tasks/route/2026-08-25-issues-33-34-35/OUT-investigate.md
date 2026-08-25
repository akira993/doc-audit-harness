# 調査結果

実装・修正は行っていません。確認対象はカレントリポジトリ本体です。

## 1. `generic-layers.py`

### 設定キー

実際に参照する設定キーは次の3つです。

- `docGlobs`：対象文書の列挙
- `frontMatterFields`：front matter 必須項目
- `indexFiles`：孤立文書判定の起点

参照箇所：

- `cfg.get("docGlobs", ...)`：`skills/audit/scripts/generic-layers.py:324,326`
- `cfg.get("frontMatterFields")`：`skills/audit/scripts/generic-layers.py:174`
- `cfg.get("indexFiles")`：`skills/audit/scripts/generic-layers.py:228`

`reportPath`、`reportPattern`、`heuristics`、`impactMap` などは参照していません。

### `list_doc_files`

定義は1か所です。

- シグネチャ：`list_doc_files(repo_root, doc_globs)`  
  `skills/audit/scripts/generic-layers.py:48`

処理内容：

- `os.walk(repo_root)` で再帰走査
- `.git`, `.hg`, `.svn`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build` を除外
- `doc_globs` を独自正規表現へ変換
- `**/` は `(.*/)?`
- `**` は `.*`
- `*` は `[^/]*`
- `?` は `[^/]`
- 相対パスに一致したものをソートして返却

実装：`skills/audit/scripts/generic-layers.py:29-58`

呼び出し箇所：

- `--paths` 使用時の全体文書取得：`skills/audit/scripts/generic-layers.py:324`
- 通常時の文書取得：`skills/audit/scripts/generic-layers.py:326`

### リンク・パス抽出

`extract_links`

- 正規表現：`r"\[[^\]]*\]\(([^)]+)\)"`
- コード範囲を先に空白化して除外
- 対象は inline code と fenced code block
- リンク先を `strip()`
- Markdown のタイトル部分を `\s+["'].*$` で除去
- 戻り値は `(target, 行番号)`

`skills/audit/scripts/generic-layers.py:121-129`

コード除外の正規表現：

- fence 開始：`r"^( {0,3})(`{3,}|~{3,})(.*)$"`  
  `skills/audit/scripts/generic-layers.py:82`
- inline code：``r"(`+)[^\n]+?\1"``  
  `skills/audit/scripts/generic-layers.py:85`

`extract_path_tokens`

- 正規表現：``r"`([^`\n]+)`"``
- backtick 内の1行トークンを抽出
- 戻り値は `(token.strip(), 行番号)`

`skills/audit/scripts/generic-layers.py:132-137`

`looks_like_repo_path`

次の条件をすべて満たす場合だけリポジトリパス候補と判定します。

- `/` を含む
- 空白、`|`、`<`、`>` を含まない
- 先頭要素がリポジトリ直下の既存ディレクトリ

`skills/audit/scripts/generic-layers.py:140-146`

### severity

`check_format`

- front matter 全体がない：`WARN`
- 必須 front matter 項目がない：`WARN`
- ローカル相対リンクが存在しない：`FAIL`
- 外部 URL、`mailto:`、ページ内アンカー、`//` 始まりは対象外

`skills/audit/scripts/generic-layers.py:172-195`

`check_existence`

- backtick 内のパス風トークンが存在しない：`WARN`
- `*`, `{}`, `...`, `…` を含む記法は対象外
- `path:line` や `path:symbol` は、基底パスが存在すれば問題なし

`skills/audit/scripts/generic-layers.py:198-222`

`check_semantic`

- 不正な `indexFiles`：`WARN`
- リポジトリ外、存在しない、通常ファイルでない index：`WARN`
- 他文書から参照されない孤立文書：`WARN`

`skills/audit/scripts/generic-layers.py:225-291`

### CLI と出力

引数：

- `--config` 必須
- `--repo-root`
- `--layer {format,existence,semantic,all}`
- `--paths PATH|-`
- `--format {json,text}`
- `--exit-code`

`skills/audit/scripts/generic-layers.py:297-306`

JSON の形：

```json
{
  "findings": [
    {
      "layer": "...",
      "severity": "FAIL|WARN",
      "path": "...",
      "line": 1,
      "message": "..."
    }
  ],
  "counts": {
    "docs": 0,
    "findings": 0,
    "fail": 0,
    "warn": 0
  }
}
```

`skills/audit/scripts/generic-layers.py:335-340`

終了コード：

- 設定・入力エラー：`2`
- 通常は `0`
- `--exit-code` 指定時、`FAIL` が1件以上なら `1`
- `WARN` だけでは非0にならない

`skills/audit/scripts/generic-layers.py:309-322,348-350`

なお text 出力の `VERDICT NEEDS FIX` も `FAIL` の有無だけで決まります。`WARN` だけなら `VERDICT CONSISTENT` です。

`skills/audit/scripts/generic-layers.py:341-347`

---

## 2. `resolve-impact.py`

### `docGlobs` の参照箇所

`--mode full` 経路：

- 全 `docGlobs` 文書を `provenance="full"` で追加  
  `skills/audit/scripts/resolve-impact.py:143-146`

mapped 経路：

- `impactMap` の `changed` に一致した項目の `impacts` を追加
- この経路自体は `docGlobs` を参照しない  
  `skills/audit/scripts/resolve-impact.py:148-158`

heuristic 経路：

- `docGlobs` から文書一覧を取得
- 変更ファイルの basename と stem を検索
- ヒット文書を `provenance="heuristic"` で追加  
  `skills/audit/scripts/resolve-impact.py:160-175`

Issue #34 の145-162行付近の現況：

- 145行：`docGlobs` による full 走査
- 149行以降：mapped
- 161-162行：heuristic 用の `docGlobs` 走査

したがって、`--mode full` と heuristic の両方が `docGlobs` を参照しています。

### CLI

`--full` という引数はありません。

現行の指定は次の形式です。

- `--mode incremental`
- `--mode full`

`skills/audit/scripts/resolve-impact.py:99-105`

### report 処理

`resolve-impact.py` には以下の処理はありません。

- `reportPath` の参照
- `reportPattern` の生成
- レポート文書の除外

---

## 3. `reportPath` の扱い

### パターン生成

共通処理は `change-set-sha.py` にあります。

- `reportPath` を取得：`skills/audit/scripts/change-set-sha.py:43-45`
- `<YYYY-MM-DD>` を `2000-01-01` に置換
- `[_NN]` を `_01` に置換
- そのサンプルが `docGlobs` のいずれかに一致しなければ無効
- ファイル名に `<YYYY-MM-DD>` がなければ無効
- 日付部分より前の prefix に `*.md` を付けてパターン化

`skills/audit/scripts/change-set-sha.py:46-57`

例：

```text
docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md
→ docs/logs/doc_audit_*.md
```

glob の一致には `docaudit_paths.matches_glob` を使用しています。

### `compute-baseline.sh`

`compute-baseline.sh` 自身の対象絞り込みは `diffGlobs` 用です。

- `diffGlobs` を取得：`skills/audit/scripts/compute-baseline.sh:30-31`
- 独自の `g2r` で正規表現化：`skills/audit/scripts/compute-baseline.sh:61-80`
- `change-set-sha.py` の `excluded()` も呼び出し、state・worktree・probe・report を除外：`skills/audit/scripts/compute-baseline.sh:64-85`

`reportPath` の除外本体は次です。

- `skills/audit/scripts/change-set-sha.py:60-68`

### sibling scan

- `decide-verdict.py` が `report_pattern(config)` を作成：`skills/audit/scripts/decide-verdict.py:39-43`
- sibling scan に `reportPattern` として渡す：`skills/audit/scripts/decide-verdict.py:63-69`
- `sibling-scan.py` が `docGlobs` 文書を列挙：`skills/audit/scripts/sibling-scan.py:154-156`
- `.claude/state/` と report pattern 一致文書を除外：`skills/audit/scripts/sibling-scan.py:157-159`

CLI からは `--report-pattern` も指定できます。

`skills/audit/scripts/sibling-scan.py:187-195`

### reportPath のデフォルト

初期化手順上のデフォルト値は次です。

```text
docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md
```

`skills/init/SKILL.md:157-159`

「docs/logs がない場合はリポジトリ直下」と記載されています。

スキーマ上は任意キーです。

`skills/audit/references/config-schema.md:18`

---

## 4. 設定スキーマと docGlobs 利用箇所

### スキーマのキー一覧

`skills/audit/references/config-schema.md:8-32`

- `anchorPath`
- `diffGlobs`
- `docGlobs`
- `frontMatterFields`
- `indexFiles`
- `impactMap`
- `ssotSources`
- `docAuditCommands`
- `boundaryCommand`
- `reviewCommands`
- `reportPath`
- `maxImpactedDocs`
- `harness`
- `verdictCache`
- `models.light`
- `digestExclude`
- `protectedGlobs`
- `heuristics`
- `indexing`
- `contextMode`
- `webExtract`
- `codexReview`
- `symbolGraph`
- `docGraph`
- `semanticSearch`

`_` で始まる設定キーを予約する規約は、現在の `config-schema.md` では確認できません。  
確認できた `_` は `reportPath` の衝突回避用 suffix `[_NN]` です。

`skills/audit/references/config-schema.md:18`

### `docGlobs` を参照するスクリプト

確認できたもの：

- `skills/audit/scripts/generic-layers.py:324,326`
- `skills/audit/scripts/resolve-impact.py:145,162`
- `skills/audit/scripts/sibling-scan.py:156`
- `skills/audit/scripts/decide-verdict.py:65-68`  
  manifest から sibling scan へ渡す
- `skills/audit/scripts/change-set-sha.py:45,49`  
  report pattern の妥当性確認
- `skills/audit/scripts/impact-supplement.py`  
  `docGlobs` を文書候補の絞り込みに使用
- `skills/audit/scripts/graphify-probe.py` 等の関連処理は、現ツリーでは該当なし／未確認

---

## 5. `/docaudit:init --harness` テンプレート

### テンプレートの定義場所

`skills/init/` 配下にはテンプレート本体はありません。`skills/init/SKILL.md` は手順説明のみです。

テンプレート本体は `scaffold.py` 内です。

- `/check-docs`：`CHECK_DOCS_TEMPLATE`  
  `skills/audit/scripts/scaffold.py:69-102`
- `doc-lint`：`DOC_LINT_TEMPLATE`  
  `skills/audit/scripts/scaffold.py:104-122`
- `scripts/check-docs.py`：`generic-layers.py` の内容を読み込む  
  `skills/audit/scripts/scaffold.py:164-169`

生成先：

- `.claude/commands/check-docs.md`：`skills/audit/scripts/scaffold.py:249-252`
- `.claude/skills/doc-lint/SKILL.md`：同上
- `scripts/check-docs.py`：同上

### `[text](path) 形式のみ` の説明

現行ツリーでは、`[text](path)` 形式だけをリンクチェック対象と明記した説明は確認できません。

確認できる関連記述：

- generic engine が Markdown リンクを検査する説明  
  `skills/audit/scripts/generic-layers.py:8-14`
- `check-docs` が engine 出力をそのまま引用する説明  
  `skills/audit/scripts/scaffold.py:79-101`
- `doc-lint` が deterministic semantic check を先に実行する説明  
  `skills/audit/scripts/scaffold.py:111-121`

したがって、Issue #33 が指摘する文言は現行ファイルには存在しないか、別ブランチ・過去版由来です。未確認です。

### 同期機構

テンプレート stamp：

- stamp 正規表現：`skills/audit/scripts/scaffold.py:124-126`
- Markdown stamp：`skills/audit/scripts/scaffold.py:145-153`
- Python stamp：`skills/audit/scripts/scaffold.py:156-161`

SHA 計算：

- stamp 行を除外して SHA-256：`skills/audit/scripts/scaffold.py:139-142`
- `engine-shas.json` の現在版と実体を比較：`skills/audit/scripts/scaffold.py:172-180`

更新処理：

- `engine-shas.json` の版エントリを読み込む
- 現在のテンプレート SHA と一致しなければ生成を中止
- `--refresh` は、stamp があり、版と SHA が一致し、本文が未変更のファイルだけ更新
- 変更済み・stamp なし・未知版は保存して `skipped`

`skills/audit/scripts/scaffold.py:247-300`

版数は `.claude-plugin/plugin.json` から取得します。

`skills/audit/scripts/scaffold.py:319-327`

---

## 6. テストと品質ゲート

### テスト構成

`tests/` には次のテストがあります。

- `tests/test_generic_layers.py`
- `tests/test_resolve_impact.py`
- `tests/test_decide_verdict.py`
- `tests/test_compute_baseline.py`
- `tests/test_sibling_scan.py`
- `tests/test_scaffold.py`
- その他、全体で26ファイル

`generic-layers.py` の主なテスト：

- リンク抽出
- fenced code / inline code 除外
- 行番号
- broken link の `FAIL`
- semantic orphan

`tests/test_generic_layers.py:250-329`

`resolve-impact.py` の主なテスト：

- mapped
- glob mapped
- heuristic
- `mapGapCandidates`
- full mode
- `docGlobs`
- node_modules / nested clone / linked worktree 除外
- provenance `both`

`tests/test_resolve_impact.py:46-179`

追加の統合契約テスト：

- `tests/test_wp12_contracts.py:200-232`
- `tests/test_wp12_contracts.py:384-394`

### 品質ゲートのコマンド

README に記載されている正確なコマンドは次です。

```bash
python3 -m unittest discover -s tests -t . -v
```

`README.md:83-86`

---

## 7. `0.10.1` の出現ファイル

`grep -rl --exclude-dir=.git '0\.10\.1' .` で確認したファイルは以下です。

### 実際の版数・同期に関係するファイル

- `.claude-plugin/plugin.json:3`
- `skills/audit/references/engine-shas.json:7`
- `docs/ADOPTION.md:201`
- `docs/ADOPTION.ja.md:186`
- `tests/test_decide_verdict.py:422`

### 監査・作業記録

- `.mdq/index-ja-jp-heading.sqlite`
- `tasks/route/2026-08-18-harness-integration-and-issues/` 配下の review・implementation log 5ファイル
- `tasks/route/2026-08-19-issues-27-31-patch-0.10.1/` 配下の PLAN、REVIEW、各種 prompt/result/log、`pr-body.md`、`release-handoff.sh`
- `tasks/route/2026-08-25-issues-33-34-35/PROMPT-investigate.md`
- `tests/__pycache__/test_decide_verdict.cpython-314.pyc`

### bump 対象

次回リリースで実質的に確認・更新対象となるのは、少なくとも次です。

- `.claude-plugin/plugin.json`
- `skills/audit/references/engine-shas.json`
- テンプレート版を表示する `docs/ADOPTION.md`
- `docs/ADOPTION.ja.md`
- 版数を固定値として使うテスト・契約箇所

`tasks/` の記録、`.mdq`、`__pycache__` は版数の配布元ではありません。

---

## 8. `WARN` と verdict の関係

`decide-verdict.py` は blocking severity を次だけに限定しています。

```python
FAIL_SEVERITIES = {"FAIL", "HIGH", "CRITICAL"}
```

`skills/audit/scripts/decide-verdict.py:25-26`

`WARN` は許可される非 blocking severity です。

`skills/audit/scripts/decide-verdict.py:167-193`

最終 verdict は、`FAIL` 相当がある場合だけ `NEEDS_FIX` になります。

- `WARN` のみ：`CONSISTENT`
- `FAIL`、`HIGH`、`CRITICAL`：`NEEDS_FIX`

`skills/audit/scripts/decide-verdict.py:475-480`

したがって、`check_existence` の現在の `WARN` を維持する限り、存在しないパス風トークンだけでは verdict は `NEEDS_FIX` になりません。