未完了（実装前の PLAN 内矛盾 3 点について boss 判断待ち）です。ファイルはまだ変更していません。

事前確認結果:

- ブランチ: `fix/v0.16.0-issues-63-59`
- 開始時の作業ツリー: 変更なし
- 基線試験:

```text
Ran 655 tests in 237.338s

OK
```

失敗・スキップなし。既存テスト由来の `ResourceWarning` は出ましたが、終了値は 0 です。

実装前に確定が必要な点:

1. `docs\a.md` の扱い  
   S8 は「元の文字列に `\` があれば unresolved」としていますが、CT-5 は `docs\a.md` を `docs/a.md` と同一に正規化するよう要求しています。受理か拒否かをご指定ください。

2. flip の一致条件  
   §1・S12 は 3 項目（worktreeDigest・contractVersion・configSha）、S10 は carryForwardSha を加えた 4 項目一致を要求しています。どちらを採用するかご指定ください。

3. `parse_history_document` の返り値  
   S9 は `(entries, phase4Runs)` の 2 値と記載する一方、退化時は `(entries, [], warning)` の 3 値です。常に 3 値を返す契約でよいかご指定ください。

併せて、回答後に PLAN §7 の許可範囲内にある既存ファイル群を上書きし、新規 `sealed_config.py` とテスト 2 本を追加します。これらの編集を実行してよいか確認をお願いします。