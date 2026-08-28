メタ認知: 最終版という区切りによる承認バイアスを避け、正しい実装が指示を同時に満たせるかと、誤実装を検査が拒否できるかで判定した。

## 結論

rev.5 は実装承認できない。計画自体の欠陥が4件残る。

## (A) 計画自体の欠陥

### CR2-37 — 先頭 `-` の値が正例と負例の両方になっている

B5では先頭 `-` を有効とし、`dash_name` はstubを起動する正例である。[PLAN-cr2.md:23](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:23) [PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)

一方C9は、graph 3本の「制御文字／空白／dash」をenabled・disabled双方でsentinel不起動と要求する。[PLAN-cr2.md:34](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:34)

正しい実装でも両条件を同時に満たせない。

推奨: C9の負例からdashを削除し、`dash_name` はenabled時に起動、disabled時だけ不起動と固定する。

### CR2-38 — DoDに廃止済みIDが残っている

DoD前半は新しい6 IDを固定するが、後半は旧 `bin_ws` を使い続けている。[PLAN-cr2.md:52](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:52)

また「同じ6空白ID」とあるが、`bin_surrogate` は空白ではない。このままでは、lead／trail／both／nbspの片側状態やgraphのsurrogate検査を省略できる。

推奨: `{bin_ws_lead, bin_ws_trail, bin_ws_both, bin_ws_nbsp, bin_wsonly, bin_surrogate} × {enabled, disabled}` と明記し、「空白5種＋surrogate」に訂正する。

### CR2-39 — 正常なテストを `expected failure` と誤認する

§8は結果行ではなくログ全文から裸の文字列を検索する。[PLAN-cr2.md:111](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr2.md:111)

実測では、成功するテストの説明文を `expected failure wording is rendered safely` としただけで、

```text
expected failure wording is rendered safely ... ok
OK
```

という正常結果をPLANの式が拒否した。

推奨: 行末が `... expected failure` または `... unexpected success` の結果行だけを拒否する。

### CR2-40 — 保護ファイルのhardlink置換を検出できない

`scope-check.py` は通常ファイルを内容hash・mode・kindだけで比較し、link数を確認しない。[scope-check.py:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/scope-check.py:35)

保護ファイルを同一内容・同一modeの別ファイルへのhardlinkに置換すると `scope-clean` を維持できる。その後、別名側への書き込みが保護rootへ持ち越されるため、後続runへの汚染経路になる。

推奨: 保護対象の通常ファイルは `st_nlink == 1` を必須にし、複数linkを拒否する。

## (B) worker指示で吸収できる細部

無し。いずれもPLAN本文または検収処理の修正が必要である。

なお、`names(04a0624) ∪ REQ` の実行確認、graph reason集合、schema専用テスト、symlinkディレクトリ検出は前回指摘を解消している。ファイル変更は行っていない。