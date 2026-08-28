実装と全609テストは通過しましたが、§8 の範囲確認だけは既存の `tasks/.../REVIEW.md` 未保存変更を検知して未達です（禁止範囲のため触れていません）。

## 変更ファイルと要点

- 6 probe の `ensure_ascii=False` を全9か所から除去。
  - `mdq-index.sh`: 64, 97, 103
  - `ax-probe.sh`: 60, 66
  - `codex-probe.sh`: 66
  - `codegraph-probe.sh`: 53
  - `graphify-probe.sh`: 57
  - `cocoindex-probe.sh`: 62
- graph 系の `line.encode("utf-8");` は維持。
- 6テストへ `test_json_emit_is_ascii_one_line` を追加。

## 新テストが通した出力経路

- mdq: not-installed / indexed / index-failed
- ax: not-installed / ok（version に U+2028）
- codex: not-installed / ok（`CODEX_HOME=b"/tmp/h\xffome"`）
- codegraph: not-installed
- graphify: not-installed
- cocoindex: not-installed

各テストは生バイトで ASCII・1行・JSON復元・bin一致を確認しています。codex は不正UTF-8の環境値も復元確認済みです。

## §8 検証結果

```text
Ran 609 tests in 186.364s

OK
```

```text
ensure-ascii-clean
bash-syntax-clean
Ran 609 tests
tests-clean
forbidden-clean
```

追加テストの `... ok` は6回ちょうどでした。

範囲確認の結果:

```text
tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md (boss doc modified)
tasks/route/2026-08-28-issues-56-60/REVIEW.md (boss doc modified)
```

`PLAN-cr3.md` は boss commit より後に更新済みのため想定内ですが、`REVIEW.md` は作業開始時から未保存変更として存在しています。`tasks/**` は変更禁止なので、`scope-clean` にする操作は行っていません。

## PLAN との乖離

実装内容の乖離は無し。最終の `scope-clean` のみ、既存の禁止ファイル変更により未達です。git commit は行っていません。