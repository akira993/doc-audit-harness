P2指摘を修正し、指定された2ファイルだけを変更しました。

- `release-handoff.sh`: 公開前に #59 と #63 の両方が OPEN か検証
- `test_release_handoff.py`: #59 が CLOSED の場合に公開副作用なしで停止する負テストを追加
- テスト: `Ran 24 tests in 16.707s`、`OK`
- `bash -n`: 成功
- `git diff --check`: 成功
- commit: 未作成

既存の未追跡 `.claude/` は変更していません。