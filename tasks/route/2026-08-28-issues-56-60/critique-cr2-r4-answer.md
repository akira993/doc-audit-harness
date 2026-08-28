メタ認知: 検査項目が増えたことで十分になったと判断するバイアスを警戒した。特に「テストが存在する」と「正しく実行・判別できる」を分けて確認した。

## 結論

rev.4 は実装承認できない。計画自体の欠陥が8件残る。

## (A) 計画自体の欠陥

### CR2-29 — 必須テストが `ok` 以外でも合格する

§8は実行記録について、テストIDの接頭辞が1回あることしか確認していない。[PLAN-cr2.md:111](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:111)

実測では `@unittest.expectedFailure` を付けた失敗テストが、

```text
... expected failure
OK (expected failures=1)
```

となり、終了値0・skip 0・ID出現1回をすべて満たした。DoD (8) の「各1回 `... ok`」は実装されていない。

推奨: 各完全修飾IDについて、行全体が `... ok` で終わることを正規表現で1回だけ確認し、`expected failure` と `unexpected success` も0件にする。

### CR2-30 — 既存テストを実行対象から外しても合格する

`04a0624` の既存テスト名は削除だけを検出し、実行記録を確認するのは `REQ` の新規名だけである。[PLAN-cr2.md:107](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:107)

実測では、モジュールに `load_tests` を置けば既存メソッドを残したまま新規テストだけを実行できた。この場合も全体検査は終了値0になる。

推奨: `names(04a0624) | REQ` の全テストについて、完全修飾IDの `... ok` が各1回あることを確認する。

### CR2-31 — 無効化時の外部コマンド起動をsentinelが検出できない

sentinelは既定名のstubだけである。[PLAN-cr2.md:58](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:58)

graph 3本の `enabled:false + 妥当カスタム bin` はカスタム値を出力に保持する。誤実装がそのカスタム実行ファイルを起動してから正しいdisabled JSONを返しても、既定名markerは変わらず合格する。現行実装は状態判定直後に終了しており、この非実行性は既存契約である。[codegraph-probe.sh:50](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:50)

空白付き負例でも、誤ってtrim後の名前を起動した場合、seamの既定名と名前が異なれば検出できない。

推奨: 妥当カスタムbin自身と、空白除去後に到達し得る名前もmarker付きstubにし、すべてのdisabled／invalidケースで全marker不変を確認する。

### CR2-32 — 境界値表が前後・途中の誤実装を識別できない

`bin_ws` は `" codegraph "` のように両端へ同時に空白を置く1例だけである。[PLAN-cr2.md:26](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:26)

そのため、先頭だけ、または末尾だけを拒否する誤実装でも通る。現行の制御文字fixtureも常に文字列末尾へ置いているため、末尾だけを検査する誤実装を排除できない。[test_codegraph_probe.py:64](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:64)

また、契約の `bin == bin.strip()` が拒否する非ASCII空白の代表例もない。

推奨: 6 probeすべてで先頭空白・末尾空白・非ASCII空白を別IDにし、33制御文字は文字列途中へ配置する。

### CR2-33 — 保護対象ディレクトリ内のsymlinkディレクトリを検出できない

`scope-check.py` は `os.walk()` が返したファイルだけを列挙し、ディレクトリ項目を記録していない。[scope-check.py:29](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/scope-check.py:29)

`data/`、`.serena/`、`docs/superpowers/` は差分表示から除外される設定である。[.gitignore:5](/Users/akiratakahashi/Projects/doc-audit-harness/.gitignore:5) このため、内部のディレクトリをリポジトリ外向けsymlinkへ置換・追加しても、通常の差分検査にも保護root比較にも現れずDoD (6) を通る。

推奨: root自身を含む全ディレクトリ項目を、symlinkを辿らず `lstat` し、種類・権限・link先を基準値と比較する。

### CR2-34 — ADOPTIONの互換性説明が従来挙動を誤っている

追加予定文は、graph probeが従来 `not-installed` だった値を今後 `invalid-config` にすると断定している。[PLAN-cr2.md:28](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:28)

しかし現行probeはPython出力を `read -r STATE BIN` で受ける。[codegraph-probe.sh:28](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:28) 実測では、

```text
入力:  enabled  codegraph 
結果:  STATE=<enabled> BIN=<codegraph>
```

となり、従来は `ok` に到達し得る。lone surrogateも従来必ず `not-installed` になるわけではない。

推奨: 「新たに拒否される値はtool探索前に `invalid-config` になる」とだけ記載し、旧reasonを断定しない。

### CR2-35 — schema契約の誤実装を現行検証が判別できない

DoD (10) は6 seamの完全一致を要求するが、§8の必須テスト名にはschema用テストがない。[PLAN-cr2.md:80](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:80)

現行テストは4 seamについて一般的な断片だけを確認しており、今回の境界条件やseam別disabled出力を検査しない。[test_v014_contracts.py:135](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:135) このテストを変更しなくても、現在の機械検査は通る。

推奨: 6 seamの行全体・各1行を検証する専用テスト名を `REQ` に追加し、その `... ok` を必須にする。

### CR2-36 — graph 3本の「全reason分岐」が集合として固定されていない

計画は `test_output_key_sets_per_branch` の存在だけを要求し、対象reason集合を列挙していない。[PLAN-cr2.md:34](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:34)

例えばCocoIndexの `not-initialized`、`gitignore-modified`、`index-failed` を省いたテストでもDoDを通る。[cocoindex-probe.sh:69](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:69) [cocoindex-probe.sh:116](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:116)

推奨: probe別reason集合をPLANに固定し、実際に生成したreason集合の完全一致と各reasonのキー集合をassertする。

## (B) worker指示で吸収できる細部

無し。上記はいずれも現在のPLANまたは検収処理のままでは誤実装を合格させるため、workerの注意だけに委ねるべきではない。

なお、再帰的な到達不能文検査、`command -v --`、UTF-8直接出力とbase64経路には新規の問題を確認しなかった。ファイル変更は行っていない。