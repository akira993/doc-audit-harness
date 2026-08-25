# 最終レビュー指摘の修正（1 件）

`codex exec review` の指摘 P2 を修正せよ:

`report_pattern()` の妥当性確認が `config.get("docGlobs", [])` と**空配列 fallback** になっているため、
`docGlobs` 省略（既定値 `["docs/**/*.md", "*.md"]` が適用される有効な設定）で `reportPath` だけを
指定した場合、sample が docGlobs に一致せず `report_pattern()` が常に None を返し、レポート除外が
働かない。

修正: **全 5 複製**（generic-layers.py / change-set-sha.py / resolve-impact.py / impact-supplement.py /
start-run.py）で、`report_pattern()` 内の docGlobs 参照を各スクリプトの既定値と同じ
`config.get("docGlobs", ["docs/**/*.md", "*.md"])` に統一する（change-set-sha.py の現行実装が既に
既定値を持つ場合はそれに合わせ、5 実装の判定一致を維持）。

テスト: 契約テストに「docGlobs 省略＋reportPath 指定 → マッチャが導出される」ケースを追加し、
generic-layers の列挙除外が docGlobs 省略時にも働くことを 1 件で固定する。

検証: `python3 -m unittest discover -s tests -t . -v` 全 green の末尾サマリを報告。
変更はこの修正に必要な範囲のみ。
