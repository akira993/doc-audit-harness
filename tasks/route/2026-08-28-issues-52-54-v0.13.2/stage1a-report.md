# S1a 実装報告

S1a の指定範囲は完了し、指定された 105 件の試験はすべて成功し、fixture 3 点も PLAN の固定 SHA-256 と一致した。

## 1. 変更ファイル一覧と要旨

- `skills/audit/scripts/fix-scope.py`
  - `docGlobs` 省略時の既定を `["docs/**/*.md", "*.md"]` に統一した。
  - `CLAUDE.md` と `AGENTS.md` を任意の深さで拒否する basename 集合を追加し、`casefold()` で大文字小文字を区別せず、`docGlobs` より先に判定するようにした。拒否理由は `agent instruction file` とした。
  - 旧 fail-closed コメントを削除した。
- `skills/audit/scripts/read-manifest.py`
  - SHA-256 一致後に、manifest が object であり `sealed` が厳密に `true` であることを一体で検査するようにした。不成立時は `manifest is not sealed` で exit 2、stdout 空となる。
- `skills/audit/SKILL.md`
  - 組込み拒否の説明に `CLAUDE.md` / `AGENTS.md` の大文字小文字を区別しない basename 保護を追加した。
  - Phase 3 に exit 5、その他の非 0、`read-manifest.py` 失敗の 3 停止分岐を明記し、各分岐に完全な run 解放コマンドを追加した。exit 5 の既存メッセージと `SEALED_MANIFEST=...` 行頭形式は維持した。
- `skills/audit/references/config-schema.md`
  - `docGlobs` の pre-flight fix 既定を共通既定として記述し、組込み拒否の 2 か所に agent 指示ファイル保護を追加した。
- `docs/ADOPTION.md`、`docs/ADOPTION.ja.md`
  - `docGlobs` 行から全拒否/fail-closed 説明を外し、pre-flight fix も同じ既定を使う説明へ更新した。
  - `protectedGlobs` 行に `CLAUDE.md` / `AGENTS.md` の大文字小文字を区別しない組込み保護を追加した。
- `tests/test_read_manifest.py`
  - DoD (6) の固定名 4 ケースを追加した。
- `tests/test_v0132_contracts.py`（新規）
  - DoD (2)〜(5) の S1a 契約テスト 6 件を追加した。S1b の契約テストは追加していない。
- `tests/data/dir-framework-scope/audit-scope.json`、`doc-audit.json`、`paths.txt`（新規）
  - dir-framework commit `951570b` 由来の固定 fixture を作成した。
- `tests/test_import_audit_scope.py`
  - 外部 repo と 46 path に依存する試験を、固定 fixture だけを使う 24 rule / 48 path の固定名試験へ置換した。空ファイル作成後に 2 JSON を上書きする順序を守り、`DIR_FRAMEWORK` と `skipTest` を除去した。
- `tests/test_wp12_contracts.py`
  - 変更不要だったため変更していない。
- `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1a-report.md`（新規）
  - 本報告を記録した。

## 2. PLAN DoD 実測

### DoD (1)

- `grep -c 'get("docGlobs", \[\])' skills/audit/scripts/fix-scope.py`
  - 出力 `0`（一致なしのため grep 自体は exit 1）。
- `python3 -m unittest -v tests.test_v0132_contracts tests.test_read_manifest tests.test_import_audit_scope tests.test_wp12_contracts tests.test_codex_dispatch tests.test_v013_contracts tests.test_v0131_docs_contracts`
  - `test_doc_globs_default_is_shared_across_eleven_call_sites` を含め成功。basename 集合、`casefold()` 判定、理由文字列は契約テストと差分確認で確認済み。

### DoD (2)

- 上記 105 件コマンドで次の固定名 2 件が成功した。
  - `test_omitted_doc_globs_uses_shared_default_and_denies_agent_files`
  - `test_explicit_doc_globs_still_denies_agent_files`
- 実測は省略時 `allowed == ["README.md", "SECURITY.md", "docs/a.md"]`、明示的な広い glob でも agent 指示ファイルを拒否した。

### DoD (3)

- 上記 105 件コマンドで `test_doc_globs_default_is_shared_across_eleven_call_sites` が成功した。
- AST により 7 ファイル、正確に 11 call site、既定値 `["docs/**/*.md", "*.md"]` を確認した。

### DoD (4)

- `grep -Eic 'fail.closed|fails closed' skills/audit/scripts/fix-scope.py`
  - 出力 `0`（一致なしのため grep 自体は exit 1）。
- 上記 105 件コマンドで次の固定名 2 件が成功した。
  - `test_builtin_deny_documented_in_five_places`
  - `test_doc_globs_rows_no_longer_say_fail_closed`
- 組込み deny 5 か所と docGlobs 3 行を個別に検査した。

### DoD (5)

- 上記 105 件コマンドで `test_phase3_three_stop_branches_release_the_run` が成功した。
- 3 固定句の各 3 行以内に、`--run-base`、`--repo-root`、`--anchor-path`、`--release --runid "$RUNID"` を含む完全な解放コマンドがあることを確認した。
- 既存 `tests.test_v013_contracts.TestV013Contracts.test_f_sealed_manifest_rebinding` も成功した。

### DoD (6)

- 上記 105 件コマンドで以下の固定名 4 件が成功した。
  - `test_sealed_false_is_rejected`
  - `test_missing_sealed_key_is_rejected`
  - `test_array_manifest_is_rejected`
  - `test_null_manifest_is_rejected`
- 各ケースで実バイト列の SHA-256 を evidence に設定し、exit 2、stdout 空、stderr の `manifest is not sealed` を確認した。既存 6 件も成功した。

### DoD (7)

- 上記 105 件コマンド内の `tests.test_codex_dispatch` 14 件はすべて成功した。
- `git diff --name-only -- skills/audit/scripts/codex-dispatch.py`
  - stdout 空、exit 0。`codex-dispatch.py` は変更していない。

### DoD (15)

- `shasum -a 256 tests/data/dir-framework-scope/audit-scope.json tests/data/dir-framework-scope/doc-audit.json tests/data/dir-framework-scope/paths.txt`
  - `audit-scope.json`: `d68186952fee273130685b329c1cd4727c34c55065866a054b51ab0629e0982d`
  - `doc-audit.json`: `9723e2837c235c75fa28d32eb97f04d884d9a1d12ea001ea7e21bfd4bf44599c`
  - `paths.txt`: `b1a1356a14935bbd2aed214dbf7d732c25379213395f14ee4fd98d5689e7d91d`
- 3 点とも PLAN の固定値と一致した。
- 上記 105 件コマンドで `test_dir_framework_fixture_scope_is_not_imported_with_24_rules_and_48_paths` が成功した。`rules==24`、`equivalenceChecked==48`、`state=="not-imported"`、`errors==[]`、config に `auditScope` 無しを確認した。
- `grep -c 'DIR_FRAMEWORK' tests/test_import_audit_scope.py` と `grep -c 'skipTest' tests/test_import_audit_scope.py` はともに出力 `0`。

### DoD (20)

- フルスイートは、再開時の明示指示に従って実行していない。boss が実行する必要がある。
- 代替として指定された 105 件コマンドを実行し、`Ran 105 tests in 19.336s`、`OK`、skip 0 だった。DoD (2)〜(6)、(15) の S1a 固定名はすべて出力に現れた。

### DoD (21)

- `python3 -m py_compile skills/audit/scripts/fix-scope.py skills/audit/scripts/read-manifest.py`
  - stdout/stderr 空、exit 0。
- `bash -n skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh`
  - stdout/stderr 空、exit 0。3 probe は S1b 対象のため変更していない。
- handoff script は S2 対象であり、S1a では作成・検査していない。

### DoD (22)

- `git diff --check`
  - stdout/stderr 空、exit 0。
- `git status --short --untracked-files=all`
  - 追跡済み差分は S1a 許可ファイル 8 点のみ、新規の追跡可能ファイルは `tests/test_v0132_contracts.py` のみ。
  - `tests/data/...` と本報告は `.gitignore` のため status に表示されないが、存在と内容を別途確認済み。
  - `?? .claude/worktrees/...` は依頼前から存在する対象外の `.claude/` 配下として未変更。
- 許可外ファイルの差分は確認されなかった。

## 3. テスト結果

実行コマンド:

```text
python3 -m unittest -v tests.test_v0132_contracts tests.test_read_manifest tests.test_import_audit_scope tests.test_wp12_contracts tests.test_codex_dispatch tests.test_v013_contracts tests.test_v0131_docs_contracts
```

実測結果:

```text
Ran 105 tests in 19.336s
OK
```

skip は 0。フルスイートは再開時の指示に従って未実行であり、boss が実行する。

## 4. 未対応・判断事項・対象外

- S1a の未対応項目や判断保留はない。
- S1b（Issue #54 の 3 probe、状態行、conditional-force 文書等）と S2（版更新、handoff）は変更していない。
- `tests/test_wp12_contracts.py` は新 deny の影響を受けず既存試験が成功したため、最小変更も不要だった。
- 許可外ファイルの変更が必要な箇所は見つからなかった。
- 最初の新規文書契約テストでは節の切り出しが見出し直後の空行で終了し 1 件失敗した。節全体を次の見出しまで切り出すよう最小修正し、再実行後は成功した。
- フルスイートのみ未実行であり、boss 側での確認が残る。
