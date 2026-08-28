修正と検証が完了し、全579テストが成功、skip 0でした。

## 変更差分

- ADOPTION 英日付録に `probe-record.py` と表示専用用途の説明を追加。
- 付録の固定件数を 42 → 43、行数を 51 → 52 に更新。
- `codexReviewState` だけが記録された場合も、`state:"unknown"` のまま `reviewState` を保持するよう修正。
- 固定ケースを33 IDへ更新し、`reviewState:"completed"` と caller 3値が `None` になるテストを追加。

## テスト結果

関連テスト:

```text
Ran 81 tests in 7.970s
OK
```

フルスイート:

```text
Ran 579 tests in 157.311s
OK
```

skip 数:

```text
0
```

構文確認:

```text
python3 -m py_compile skills/audit/scripts/probe-record.py
exit 0
```

`git diff --check` も成功しています。コミットは行っていません。

## PLAN との乖離

無し。今回の追加変更はすべて boss が追認した許可範囲内です。