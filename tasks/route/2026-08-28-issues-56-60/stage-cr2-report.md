実装は完了し、全体テスト603件は成功しました。最終の契約テスト修正後も関連12件は成功していますが、スコープ検査は boss 側の未保存 `tasks/**` 変更と保護対象ディレクトリの検出により失敗しました。

(1) 変更ファイルと要点

- `skills/audit/SKILL.md`：CM JSON 指示、codex-review の5条件、mdq 分岐例外、優先規則の配置を更新。
- 6本の probe：bin の境界検証、UTF-8 バイト出力、`command -v --` を実装。
- `config-schema.md`、ADOPTION en/ja：bin の新条件と graph 3 seam の説明を反映。
- 8本のテスト：fixture 修復、制御文字・空白・surrogate・正例のテスト、契約テストを追加。

(2) DoD ごとの検証

- (1) `test_cr2_codex_state_table_and_cm_shape`、`test_v014_behavior_changes_paragraph`：Ran 12、OK
- (2) `test_bin_boundary_table`、`test_bin_positive_paths`、`test_output_key_sets_per_branch`：対象テスト Ran 44、OK
- (3) `test_setup_creates_corpus`、`test_disabled_by_config`：対象テスト Ran 44、OK
- (4) 全体テスト：Ran 603、OK。shell 文法検査も OK
- (5) 禁止ファイル差分検査：OK
- (8) AST・必須テスト名・cr1 テスト名保持：OK
- (9) CM 合成文：AST 検査内で確認、OK
- (10) `test_cr2_config_schema_bin_rows`：Ran 12、OK

(3) §8 検査結果

```text
Ran 603 tests in 178.539s

OK
```

```text
tests-ast-clean
adoption-paragraph-clean
scope-clean
```

`scope-check.py` は次の理由で失敗しました。

```text
tasks/.../PLAN-cr2.md (boss doc modified)
tasks/.../REVIEW.md (boss doc modified)
tasks/.../baseline-hashes.txt (boss doc modified)
tasks/.../scope-check.py (boss doc modified)
.serena ... protected root changed
data ... protected root changed
docs/superpowers ... protected root changed
```

(4) PLAN との乖離・許可外変更・未実施

- 許可外ファイルは変更していません。
- git commit はしていません。
- `scope-check.py` の失敗は、作業前からある boss 管理の `tasks/**` 未保存変更と保護対象ディレクトリに起因します。これらは指示どおり変更していません。
- 最終の契約テスト1行修正後、全体603件の再実行は未実施です。ただし、その修正を含む `tests.test_v014_contracts` 12件は成功しています。