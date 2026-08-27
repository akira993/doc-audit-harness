S3 の主要実装・配線は完了し、重点テストは 13 件成功しました。ただし、PLAN が求める網羅試験群とフルスイートの完走結果は未確認です。

変更ファイル一覧:

- `skills/audit/scripts/import-audit-scope.py`（新規）
- `tests/test_import_audit_scope.py`（新規）
- `skills/audit/SKILL.md`
- `skills/init/SKILL.md`
- `skills/audit/references/config-schema.md`
- `docs/ADOPTION.md`
- `docs/ADOPTION.ja.md`
- `tests/test_v013_contracts.py`

実装内容:

- scope の安全確認、JSON・重複キー・規則検証、fnmatch/docaudit glob 等価性確認
- `--check` の absent / not-imported / drift / in-sync 判定
- `--write` の SHA 照合、lock、原子的 config 更新、`source:"audit-scope"` の差し替え
- audit Phase 0 の drift 停止と init の import 導線
- schema・導入文書・契約テストの追加

検証結果:

- `python3 -m unittest tests.test_import_audit_scope tests.test_v013_contracts -v`
  - 13 件成功、3 件 skip
- `git diff --check`
  - 成功
- フルスイートは開始しましたが、30 秒時点の進行出力のみで完走結果を取得できていません。

未達・要レビュー:

- PLAN §6 #44 (i)〜(viii) の網羅テストは未実装です。特に実プロセスでの lock 保持、故障注入、dir-framework 実物検査は残っています。
- 「ロック内停止・replace 前後の故障注入」の公開的な注入手段は仕様に定義がなく、現状は通常の例外安全性のみです。
- 主要3件の「実装を戻すと赤になる」確認は未実施です。
- 変更前後のフルスイート件数は未取得です。
- 許可外ファイルの変更はありません。`.claude/` は着手前から未追跡で、触れていません。