654件の自動確認は通過していますが、公開スクリプトの保存先指定によって他のスキルを削除し得る安全上の欠陥があります。利用案内にも新旧の説明の矛盾が残っています。

Full review comments:

- [P1] 保存先とスキルルートの同一指定を拒否する — /Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/release-handoff.sh:51-54
  `DOCAUDIT_SKILLS_DIR` と `DOCAUDIT_SKILLS_ROOT` が同じ場所を指す場合、この包含検査は通過します。その後の `rsync --delete` がスキルルート全体を置き換え、他のインストール済みスキルを削除するため、`DEST_REAL == ROOT_REAL` を同期前に拒否してください。

- [P2] 旧版依存の init 説明も更新する — /Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:285-285
  v0.15.1 の利用案内ではこの段落がデータベース基準の分岐を説明する一方、同じ文書の165–166行目は「初期化済みディレクトリへの `init` は拒否される」と断定しています。対象の codegraph 1.5.0 では受理され、スクリプト自身も版依存と扱っているため、英語版と日本語版の古い説明も版依存であることが分かる記述へ更新しないと案内が矛盾します。