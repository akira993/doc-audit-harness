P1・P2 を反映し、指定テストとゲートはすべて PASS しました。Git 書き込み操作は行っていません。

1つ目の検証（exit 0）:

```text

OK
handoff residue counts: v0.15.0=0 #56=0 webExtract=0 codexReview=0
v0.15 residue scan: files=102 units=2844 hits=0
```

2つ目の検証（exit 0）:

```text
G3: PASS methods=28 expected=28 missing=[]
G4: PASS counts={"not model-invocable": 0, "user-invocation-only": 0, "モデルからは起動": 0, "モデルから起動できない": 0, "ユーザー実行のみ": 0}
G7: PASS counts={"#56": 0, "codexReview": 0, "v0.15.0": 0, "webExtract": 0}
G9: PASS returncode=0 stderr=''
G11: PASS violations=0 paths=[]
G12: PASS empty_tests=0 methods=[]
GATE PASS
```

grep の生出力:

```text
docs/ADOPTION.ja.md:243:**v0.13.2 の挙動変更:** `docGlobs` を省略した場合、pre-flight fix の分類は `["docs/**/*.md","*.md"]` を既定とする。`CLAUDE.md` と `AGENTS.md` は大文字小文字を区別せず常に拒否される。
docs/ADOPTION.ja.md:249:**v0.14.0 の挙動変更:** `indexing`、`contextMode`、`webExtract`、`codexReview` のキーでは、`enabled` は JSON の真偽値でなければなりません。`enabled:false` 以外の場合、`enabled` が真偽値でない、キーがオブジェクトでない（`null` を含む）、または `indexing`・`webExtract`・`codexReview` の `bin` が文字列でない、空、空白のみ、前後に空白がある、ASCII 制御文字（U+0000–U+001F または U+007F）を含む、または UTF-8 に符号化できないときは `invalid-config` を報告し、ツールを起動しません（キーが無い場合は従来どおり有効で、`bin` の非文字列値は変換されず、読めない設定は従来どおり Phase 0 より前に監査を停止します）。`indexing` キーが不正な場合は、未インストール時と同じく Phase 0 の mdq 確認ゲートが起動します。`codexReview.required:true` と不正な `codexReview` キーを組み合わせた場合は、codex を黙って実行せず `REFUSED` になります。Phase 0 の probe 結果は `$RUN_DIR/phase0-probes.json` に保存されます（表示専用で、verdict の入力にはなりません）。Phase 5 の状態行は初回実行でも再開実行でもその記録から描画され、記録が無いか読めない場合は「state unknown (probe record unavailable)」と表示されます。codex probe は呼び出し元の `CODEX_HOME` と、そこに `auth.json` があるかどうかを報告します（表示専用で、wrapper 自身の環境は観測されません）。`import-audit-scope.py` はリポジトリルート配下の絶対パスの `--config`／`--scope` を受け付けます（POSIX パスのみ）。symbolGraph / docGraph / semanticSearch の probe も同じ bin 検証を適用します。新たに拒否される bin はツール探索の前に invalid-config を報告し、enabled:false のときは不正な bin を既定名で表示します。
docs/ADOPTION.ja.md:355:`audit-scope.json` が正本で、`source:"audit-scope"` の `impactMap` は生成物である。ずれ（drift）があると Phase 0 は停止する。`/docaudit:init --import-audit-scope` で復旧すること。run 間の import に `--accept-config` は不要であり、exit 6 は実行中の設定変更を拒否した場合だけである。実行中は lock により import が拒否される。`{"impact":"none"}` は生成対象から外すが、heuristic が文書を拾うことはある。
```

これらは codegraph と無関係な既存の「拒否される」です。codegraph `init` に関する旧記述は 0 件です。`git diff --check` も成功しています。