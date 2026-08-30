作業用ブランチの作成で権限エラーになり、作業を開始できません。

`git switch -c fix/v0.15.1-issue-65` は `.git` 内にブランチ情報を書き込めず停止しました。

```text
fatal: cannot lock ref 'refs/heads/fix/v0.15.1-issue-65': Unable to create '.../.git/refs/heads/fix/v0.15.1-issue-65.lock': Operation not permitted
```

この環境では Git 管理情報への書き込みが許可されていません。`.git` への書き込み権限を有効にしていただければ、指定された順序で実装を続けます。