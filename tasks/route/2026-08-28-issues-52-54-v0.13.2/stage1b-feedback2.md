最終レビュー（codex exec review）で P2 が 1 件。修正せよ（S1b の範囲、`skills/audit/scripts/cocoindex-probe.sh` と `tests/test_cocoindex_probe.py` のみ）。

指摘: `cocoindex-probe.sh:85` 付近の `.gitignore` 指紋計算が `shasum -a 256` に依存している。`shasum` が無い最小構成の Linux では失敗しても実行が継続し、前後の値が両方とも空になって差分を検出できず、既存 `.gitignore` が書き換わっても `reason:"ok"` を返す。必要条件は Python 3 のみ（README.md:23）。

修正方針: 指紋計算を `python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$GITIGNORE"` のように Python 標準の `hashlib` で行う。計算に失敗した場合（python3 が非 0 を返す・出力が空）は「利用不可」として扱い、`ccc index` を実行せずに `semanticSearchAvailable:false, reason:"index-failed"`（または既存 reason のうち最も近いもの。新 reason は追加しない）で degrade し stderr に 1 行出す。`shasum` への依存を完全に除く（`grep -n shasum` が 0 件）。
テスト: `tests/test_cocoindex_probe.py` に `test_gitignore_fingerprint_does_not_depend_on_shasum`（PATH から `shasum` を隠した環境 — 例: PATH を stub bin dir と python3 の dir だけにする、または `shasum` という名前で `exit 127` する stub を PATH 先頭に置く — で `.gitignore` 追記が `gitignore-modified` として検出される）を追加。
実行: `bash -n skills/audit/scripts/cocoindex-probe.sh`、`python3 -m unittest -v tests.test_cocoindex_probe tests.test_v0132_contracts`。結果と `Ran N tests` を `stage1b-report.md` に「最終レビュー P2 への対応」節として追記して終了。git への書き込みは行わない。
