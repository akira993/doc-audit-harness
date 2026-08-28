# S2 実装報告 — docaudit v0.13.2

S2 の版バンプ、挙動変更の文書化、契約テストの再照準、リリース引き継ぎ手順を実装し、指定した 70 件のテストはすべて成功した。

## 変更ファイルと要旨

- `.claude-plugin/plugin.json`: 版を `0.13.2` に更新した。
- `docs/ADOPTION.md`、`docs/ADOPTION.ja.md`: `claude plugin list` の版、refresh 段落、v0.13.2 の挙動変更 5 文を更新・追加した。
- `skills/audit/references/engine-shas.json`: `0.13.2` の engine hash を追加した。テンプレート本文は不変のため `0.13.1` と一致する。
- `tests/test_v013_contracts.py`: 5 面の版確認を `0.13.2` へ、v0.12.0 の許可リストにある refresh 文を新文言へ更新した。
- `tests/test_v0131_docs_contracts.py`: refresh 段落の対象集合に `0.13.1` を追加した。
- `tests/test_scaffold.py`: 最新 stamp と hash 参照を `0.13.2` へ更新した。
- `tests/test_v0132_contracts.py`: `test_v0132_behavior_changes_paragraph` を追加した。段落を空白正規化し、バッククォートを除去して固定文を検査する。
- `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`: #52〜#54 用の再開可能なリリース手順を追加した。
- `tests/test_release_handoff.py`: 新手順、tag、表題、Issue 52〜54、リリース本文の必須語へ再照準した。

`grep -n '0\\.13\\.1\\|46\\|47\\|48\\|49\\|50' tests/test_release_handoff.py` の該当箇所は変更前に 11 件、変更後に 0 件だった。

## 完了条件と実測

- DoD (16): `python3 -m unittest -v tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff tests.test_v0132_contracts` は成功した。版の 5 面は `0.13.2`、refresh 段落は `{0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.13.1, 0.13.2}`、engine-shas の最大版は `0.13.2` だった。
- DoD (17): 上記テスト内の `test_v0132_behavior_changes_paragraph` は成功した。英語・日本語とも挙動変更段落は各 1 つで、指定の固定文 5 つを含む。
- DoD (18): 上記テスト内の `tests.test_release_handoff` は成功した。`bash -n tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` も成功した。手順書には tag `docaudit--v0.13.2`、指定表題、Issue `52 53 54`、必須語 `#52`、`#53`、`#54`、`not-configured`、`settings.yml` がある。
- DoD (19): 上記テスト内の `test_j_only_allowlisted_0_12_0_references_remain` は成功した。refresh 行の許可正規表現は新文言へ更新済みである。
- DoD (21): `bash -n skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh` は成功した。`python3 -m py_compile skills/audit/scripts/fix-scope.py skills/audit/scripts/read-manifest.py` も成功した。
- DoD (22): `git diff --check` は出力なしで成功した。`git status --short` の対象外は既存の `?? .claude/` のみで、S2 の新規 `tasks/` ファイルは ignore 設定により表示されない。変更済み追跡ファイルはすべて S2 許可範囲内である。

## engine-shas と生成確認

`python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run | python3 -c 'import json,sys; print("stampVersion=" + json.load(sys.stdin)["stampVersion"])'` は `stampVersion=0.13.2` を返した。

`engine-shas-v0132-equals-v0131=True`。したがって 0.13.2 の hash は 0.13.1 と一致している。

## テスト結果

実行コマンド:

```bash
python3 -m unittest -v tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff tests.test_v0132_contracts
```

実測: `Ran 70 tests in 11.776s`、`OK`。

## 未対応・判断事項

- 未対応事項はない。
- フルスイートは S2 の実行範囲外であり、計画の注意どおり boss が実行する。
- git への追加・記録は行っていない。`tasks/` は ignore されるため、リリース手順書と本報告は必要に応じて boss が `git add -f` で追加する。
