`gate.py` に `--only G2,G8` 形式の選択実行を追加しました。未指定時の G1〜G12 全実行は維持し、不明な ID は exit 2 になります。Git 書き込み操作は行っていません。

正常例（exit 0）:

```text
G4: PASS counts={"not model-invocable": 0, "user-invocation-only": 0, "モデルからは起動": 0, "モデルから起動できない": 0, "ユーザー実行のみ": 0}
G9: PASS returncode=0 stderr=''
GATE PASS
```

不明な ID（exit 2）:

```text
usage: gate.py [-h] [--repo-root REPO_ROOT] [--base BASE] [--only ONLY]
gate.py: error: --only contains unknown gate ID(s): G13
```

追加で例示形式も確認済みです。

```text
G2: PASS methods=38 base_methods=20 missing=[]
G8: PASS changed=34 outside=0 paths=[]
GATE PASS
```

`git diff --check` も問題ありません。