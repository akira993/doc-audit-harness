メタ認知: merge 後の追補計画なので「小修正」と過小評価しやすい点、共有化を無条件に改善と見なしやすい点を警戒した。結論として、rev.1 は実装非承認。決定性を壊す A1/A2 と、誤った状態を許す A4 が計画上の阻害要因である。

## (A) 計画自体の欠陥

### CR1-1 — A1 の「再開していない run」判定は決定不能で、安全側でもない

A1 は、再束縛結果が `unknown/null` なら「再開していない run」に限り会話変数へフォールバックするとしている。しかし、fresh run と resumed run はどちらも `RUNID` と `EVIDENCE` を持つため、その存在では区別できない。

根拠:

- 再開時に復元する変数は `RUNID` と `EVIDENCE` だけである。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:50)
- fresh run でも open 直後から同じ二変数が存在する。
- 現行契約は fresh/resumed とも再束縛値だけで表示する。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:68)
- Phase 5 の `unknown` 分岐が先に評価されるため、A1 の追加文だけではフォールバックが到達不能になり得る。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:725) [PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:16)
- 公開文書も「fresh/resumed とも記録から表示し、読めなければ unknown」と固定している。[ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:271) [ADOPTION.ja.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:247)
- その文言は契約テストで固定されている。[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:23)

会話変数が残っているかは、再開の有無ではなく会話圧縮やモデル状態にも左右される。判定不能時に会話値を採用するのは安全側ではなく、未検証値を正式表示へ戻す経路になる。

推奨: A1 を撤回し、fresh/resumed を問わず再束縛を唯一の情報源とし、判定不能時は常に `unknown` とする。

### CR1-2 — A2 は新 run への書き込みは成立するが、再記録する元データを保証できない

新しい `EVIDENCE` と新 runDir の組み合わせで `probe-record.py` を呼ぶこと自体は成立する。

根拠:

- `open-run.py` は新しい `runDir`、設定情報、lock identity を返す。[open-run.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:210)
- `probe-record.py` は `EVIDENCE.runDir` と実際の runDir の一致を検証する。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:157)
- 書き込みも検証済み runDir に対して行われる。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:319)

問題は、A2 が再記録元を「会話変数」としていること。harness の選択質問は turn-ending checkpoint であり、再開契約が保証するのは `RUNID` と `EVIDENCE` だけで、9 seam の probe JSON ではない。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:70) [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:264)

したがって、古い run を閉じて新しい run を開いた後、再記録すべき値が欠落している場合がある。DoD (1) の固定文言検査ではこの失敗を検出できない。

推奨: reopen 後は必要な probe を新 run 上で再実行し、新しい `EVIDENCE` へ直接記録する契約に変更する。

### CR1-3 — A4 は `available:true, healthy:null` という表示不能状態を正当化する

A4 は `contextModeHealthy` を availability に関係なく `bool|null` とし、`available:true, healthy:null` も受理する。しかし Phase 5 の表示分岐は次の三つしかない。

- `available:false`
- `available:true, healthy:true`
- `available:true, healthy:false`

`available:true, healthy:null` はどれにも一致せず、「必ず1行」の契約を破る。現行 validator が `available:true` のとき bool を必須にしているのは、この不整合を防ぐためである。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:93) [PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:13)

推奨: `available:true` では `healthy` を必ず bool とし、probe-error を表す必要があるなら `false` に決定論的に正規化する。

### CR1-4 — C7 は「1行表示」を Unicode 改行文字で再び破る

計画の `json.dumps(value[:200], ensure_ascii=False)[1:-1]` は LF などをエスケープするが、少なくとも U+0085、U+2028、U+2029を生のまま残す。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:20)

実測では次の三つすべてが Python の `splitlines()` で2行に分割された。

```text
U+0085: ['left', 'right']
U+2028: ['left', 'right']
U+2029: ['left', 'right']
```

DoD は日本語と `\n` しか検査しないため、誤実装でも通る。現行の既定 `ensure_ascii=True` はこの問題を起こさない。

推奨: U+0085・U+2028・U+2029を明示的にエスケープし、その3文字を1行性テストへ加える。

### CR1-5 — C8 は NUL だけを拒否しており、同じ伝送経路の改行破損を残す

graph 系 probe は Python が `print("enabled", bin_name)` で出力し、Bash が `read -r STATE BIN` で読む構造である。

根拠:

- `probe-codegraph.sh:28-46`
- `probe-graphify.sh:32-50`
- `probe-cocoindex.sh:34-55`
- C8 は NUL の追加検査だけを計画している。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:21)

`bin` に改行が含まれると、NUL がなくても別行として切断され、設定された実行名と異なる値を実行し得る。空白区切り依存なので先頭・末尾空白やタブも完全な round-trip ではない。

C8 の「既存キー・reason を変えない」という主張自体は、検査を既存 emit の前へ加えるだけなら成立する。実測でも現行の graph 3 probe と `test_v0132_contracts` は75件すべて成功した。しかし、その基準線は改行入力の安全性を証明していない。

推奨: graph 3 probe の state/bin 受け渡しを任意の文字列を保持できる区切り方式に替え、改行・タブ・前後空白の round-trip を検査する。

### CR1-6 — D10 は既存 roots の挙動と完全同値ではない

計画は helper が `indexing.roots` の「string elements」を返すとしている。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:24)

一方、現行 `probe-mdq.sh` は各要素を `str(x)` で文字列化し、空白だけでないものを採用している。さらに改行結合後に Bash で読むため、一要素内の改行も複数 root のように扱われる。新 helper が文字列要素だけを採る、または NUL で正確に保持すると、非文字列・改行入り roots の挙動が変わる。

これは「完全同値」という計画の前提と矛盾し、既存 config の互換性変更である。

推奨: `ef995f0` の入力別 state・bin・roots・終了値を golden 化し、新 helper と全項目を差分比較する。

### CR1-7 — D10 の NUL プロトコルは Bash 3.2 では記述どおり読めない

`read -r -d '' STATE BIN ROOTS` のように一度の `read` で複数 NUL 区切り値を受けると、最初の NUL で1レコードが終了し、後続変数には入らない。

Bash 3.2.57 での実測:

```text
enabled\0codex\0root\0
STATE=enabled, BIN="", ROOTS="", rc=0
```

また、末尾 NUL がない最後の値は代入されても `read` が非0になり、`while read -d ''` の本体が実行されない。空 roots の表現、末尾 NUL、EOF 条件も PLAN に定義がない。root 自体に NUL が含まれる場合は、別 root を挿入したように解釈される。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:25)

推奨: `state\0bin\0(root\0)*` と末尾 NUL を明文化し、同一 fd から state・bin を個別に読み、roots を反復して読む Bash 3.2 実行テストを追加する。

### CR1-8 — D10 は修正対象としての根拠がなく、共有化による共通障害を増やす

code-review #10 は重複と Python 起動回数に関する保守性・性能所見であり、現行の判定表や出力に確認済みの機能障害は示されていない。

加えて計画案は、

1. `probe-config.py` を起動
2. 返された JSON を別の `python3 -c` でNUL列へ展開

という構造なので、「Python 起動を一回にする」という目的も達成しない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:24)

既存3 probe の期待値をそのまま使うだけでは、共有 helper とテスト期待値が同じ誤った判定へ変わる共通原因を排除できない。未知 option、引数不足、特殊文字、終了値の差分も計画された20 ID＋roots 3ケースでは覆えない。

推奨: D10 をこの follow-up から外し、baseline との差分実行器を用意した専用 refactor に分離する。

### CR1-9 — DoD (7) は全テスト失敗を捨てる

§8 のコマンドは概ね次の順序である。

```sh
python3 -m unittest ... >log 2>&1; tail ...; test "$skip" -eq 0 || exit 1
```

最初の unittest が失敗しても、`;` により次へ進み、skip 数が0なら全体が成功する。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:66)

つまり、テスト失敗がありながら DoD (7) を通過できる。

推奨: unittest の終了値を保存して最後に検証するか、成功時だけ後続へ進む接続に変更する。

### CR1-10 — DoD (8)(9) は禁止ファイル・越境変更を拒否しない

根拠:

- DoD (8) の `git diff --quiet` は追跡済み差分しか検査せず、禁止された未追跡ファイルを見逃す。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:72)
- DoD (9) は変更一覧を表示して除外するだけで、許可集合との一致判定も非0終了もない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:73)
- `tasks/` と `.claude/` を一括除外するため、その配下への予期しない変更も成功扱いになる。
- 変更対象が0件でもパイプラインは成功し得る。

推奨: 追跡済み・未追跡を統合した NUL 区切りの実変更集合と明示 allowlist を完全比較し、余分・不足のどちらでも失敗させる。

## (B) worker 指示で吸収できる細部

### CR1-11 — C8 のキー集合不変を全分岐で証明していない

現行 graph probe テストの完全一致集合は主に unavailable 分岐に限られ、成功・実行失敗など全 reason 分岐で Opus B5 のキー集合を比較していない。

根拠:

- [test_codegraph_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:108)
- [test_graphify_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_graphify_probe.py:114)
- [test_cocoindex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_cocoindex_probe.py:114)
- `test_v0132_contracts` は reason 列挙を固定するが、全実行分岐の JSON キーを実測比較していない。[test_v0132_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:224)

推奨: graph 3 probe の全 reason 分岐について、JSON キー集合を Opus B5 の固定集合と完全一致比較する。

### CR1-12 — DoD (6) は cleanup 実装を機械的に判定しない

DoD (6) は `mkdtemp` の cleanup を要求しているが、§8 に実行検査がなく、作業報告だけでも完了扱いにできる。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:52)

一部だけ cleanup を加えた場合や、例外経路で残る場合も検出できない。

推奨: 対象テストを `TemporaryDirectory` に統一し、対象内の裸の `mkdtemp` が0件であることを機械検査する。

## DoD (1)〜(9) の判別力

| DoD | 判定 | 問題 |
|---|---|---|
| (1) | 不十分 | A1/A2 の固定文言しか見ず、再開判定不能・会話変数欠落・旧 `EVIDENCE` 使用を検出しない。 |
| (2) | 不十分 | `available:true, healthy:null` という誤契約自体を正解として固定する。C7 は Unicode 改行を未検査。 |
| (3) | 部分的 | NUL は検出するが、改行・空白伝送と全 reason のキー集合不変を証明しない。 |
| (4) | 不十分 | baseline との差分検査がなく、共有 helper の共通誤りを見逃す。helper 呼び出し回数も実際には検査しない。 |
| (5) | 条件付きで有効 | 既存の完全集合テストと併用すれば判別力がある。ただし DoD (7) が失敗を捨てる現状では保証にならない。 |
| (6) | 不十分 | 実行検査がなく、対象0件・一部だけの cleanup でも通る。 |
| (7) | 無効 | unittest の非0終了を `;` で捨てる。 |
| (8) | 不十分 | 未追跡の禁止ファイルを見逃す。 |
| (9) | 無効 | 一覧表示だけで集合比較・失敗判定がない。対象0件でも通る。 |

## code-review 所見への判断

過小対応または誤読しているもの:

- A1: 記録欠落の修正ではなく、モデル内の未検証値へ戻す経路を新設している。
- A2: 新 runDir への書き込み問題ではなく、再開後に元値が保証されない問題を見落としている。
- A4: validator の非対称性を直す範囲を超え、表示不能な `available:true, healthy:null` を許している。
- C8: NUL だけを扱い、同じ行指向伝送を壊す改行等を残している。
- D10: 保守性所見に対して互換性と共通障害のリスクが大きい変更を入れている。

対応不要と判断できるもの:

- code-review #10 の共有 helper 化は、この版の正しさに必要な修正ではない。現行3 probe の重複は保守性課題として別 route で扱える。
- C7 の「非ASCIIをそのまま表示する」ことも正しさの要件ではない。現行の ASCII escape は少なくとも1行性では安全であり、変更するなら CR1-4 の追加条件が必要。
- C8 による既存キー集合の破壊は、NUL 検査を既存 emit 前に限定する限り発生しない。必要なのは実装変更ではなく CR1-11 の回帰テスト。
- A2 の新 `EVIDENCE`／runDir 検査機構そのものは既存実装で足りる。修正対象は再記録元の確保方法である。

## PLAN を直すべき点

優先順は次のとおり。

1. A1 を撤回し、表示・完全性判定を再束縛だけに限定する。
2. A2 を「会話変数から再記録」ではなく「新 run で probe を再実行」にする。
3. A4 の `available:true` では `healthy` を必ず bool にする。
4. D10 を別 refactor へ分離し、C7/C8 は文字列伝送全体の安全性を定義する。
5. DoD (7)〜(9) を、テスト失敗と越境変更で確実に非0終了する検査へ直す。

以上により、`PLAN-cr1.md` rev.1 は現状のままでは実装承認できない。