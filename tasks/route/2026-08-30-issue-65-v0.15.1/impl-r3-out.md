6 ファイルを前回の最終内容に復元し、指定された全ゲートが PASS しました。Git の書き込み操作は行っていません。

1つ目のコマンド（exit 0）:

```text

OK
handoff residue counts: v0.15.0=0 #56=0 webExtract=0 codexReview=0
v0.15 residue scan: files=102 units=2843 hits=0
```

2つ目のコマンド（exit 0）:

```text
G2: PASS methods=38 base_methods=20 missing=[]
G3: PASS methods=27 expected=27 missing=[]
G4: PASS counts={"not model-invocable": 0, "user-invocation-only": 0, "モデルからは起動": 0, "モデルから起動できない": 0, "ユーザー実行のみ": 0}
G5: PASS plugin=0.15.1 shas=0.15.1 adoption=0.15.1 adoption_ja=0.15.1 stamp=0.15.1
G9: PASS returncode=0 stderr=''
G11: PASS violations=0 paths=[]
G12: PASS empty_tests=0 methods=[]
GATE PASS
```

復元した6ファイルに対する `git diff --check` も成功しています。