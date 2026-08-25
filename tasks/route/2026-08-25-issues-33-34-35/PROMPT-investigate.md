# 読み取り専用の事前調査（実装・修正は一切禁止）

あなたは調査担当。リポジトリ doc-audit-harness（カレントディレクトリ）を読み、以下を正確に報告せよ。
ファイルは一切変更しないこと。報告は日本語、file:line 付きで。

## 背景
GitHub Issue #33 / #34 / #35 の対策を計画中。対象は主に
`skills/audit/scripts/generic-layers.py` と `skills/audit/scripts/resolve-impact.py`。

## 調査項目

1. `skills/audit/scripts/generic-layers.py` の全体構造:
   - 読んでいる config キー（docGlobs, frontMatterFields, indexFiles 以外にあるか）
   - `list_doc_files` の実装（シグネチャ・呼び出し箇所すべて）
   - `extract_links` / `extract_path_tokens` / `looks_like_repo_path` の実装（正規表現・フィルタ条件を正確に）
   - `check_format` / `check_existence` / `check_semantic` の severity 付与ロジック（どの finding が FAIL / WARN か）
   - CLI 引数（--layer, --format 等）と出力形式（json のスキーマ）
   - exit code の規約（FAIL があると非0か）

2. `skills/audit/scripts/resolve-impact.py`:
   - docGlobs を参照している箇所すべて（heuristic pool / --full / mapped の各経路、Issue #34 が挙げる 145-162 行付近の現況）
   - reportPath / reportPattern に関する処理の有無

3. reportPath の扱い:
   - `compute-baseline.sh` と `sibling-scan.py` / `decide-verdict.py` で report パターン除外がどう実装されているか（パターンの取得元 config キー名・glob 変換方法）
   - config 上の reportPath のデフォルト値がどこで定義されているか

4. config スキーマとドキュメント:
   - `skills/audit/references/config-schema.md` の現在のキー一覧（特に docGlobs, reportPath, `_` プレフィックス規約）
   - `doc-audit.json` を読むその他のスクリプトで docGlobs を参照するものの一覧

5. `/docaudit:init --harness` が生成するテンプレート:
   - `skills/init/` 配下と `scaffold.py` で、doc-lint / doc-reviewer / check-docs テンプレートがどこにあり、
     リンクチェックを「[text](path) 形式のみ」と説明している箇所（Issue #33 が指摘）を file:line で列挙
   - `scripts/check-docs.py` テンプレート（generic-layers.py の複製）の同期機構（テンプレートスタンプ、engine-shas.json の役割と更新手順）

6. テストと品質ゲート:
   - `tests/` の構成、generic-layers / resolve-impact に対する既存テストの有無
   - このリポジトリでテストを走らせる正確なコマンド（README や docs に記載の品質ゲート）

7. バージョン文字列:
   - 現在の版 `0.10.1` を含むファイルすべて（`grep -rn "0\.10\.1" --include='*' .` 相当。.git は除く）と、
     リリース時に bump すべき箇所の一覧

8. severity 変更の影響:
   - check_existence の WARN が verdict（decide-verdict.py）にどう影響するか（WARN は verdict を NEEDS FIX にしないことの確認）

## 出力形式
各項目を見出し付きで、コード断片は最小限の引用のみ。推測は「未確認」と明記。
