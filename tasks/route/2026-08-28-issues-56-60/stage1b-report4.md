差し戻し2点を修正し、全580テスト成功・skip 0を確認しました。

## 変更差分

- `rebind["codex-review"]` に `bin` を追加。
  - complete形: `codexReviewBin`
  - unknown形: `null`
- `codexReviewState` 単独記録時も `bin:null` を確認するテストを追加。
- Phase-5 codex-review 表示で `invalid-config` を最優先に変更。
- `invalid-config` が `phase4-not-required`、`reviewState=null`、既存4-wayより先に評価される順序テストを追加。
- `config-schema.md` は既に ⚠ 状態行を約束しており矛盾がないため変更なし。

## テスト結果

関連テスト:

```text
Ran 74 tests in 7.914s
OK
```

フルスイート:

```text
Ran 580 tests in 156.984s
OK
```

skip:

```text
0
```

構文確認:

```text
python3 -m py_compile skills/audit/scripts/probe-record.py
exit 0
```

`git diff --check` も成功しています。コミットは行っていません。既存の `REVIEW.md` 変更と `.claude/` には触れていません。

## PLAN との乖離

無し。