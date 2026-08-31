boss レビュー（差し戻し R1、軽微 1 件）。boss はフルスイート（Ran 739 tests / OK）・CT 実数・grep・版数を追認済みで、実装本体は承認見込み。以下のみ修正せよ。git 操作はしない。

## R1-1 [Minor] CT-2 の「対象 21 本を検査」が実数と乖離
- 対象: `tests/test_v016_contracts.py:369` 付近の `print("対象 21 本を検査")`。
- 問題: CONSUMER_REGISTRY は code-review-plan.py を含む 22 本（+decide-verdict/change-set-sha の扱いは従来どおり）を実際に検査しているのに、表示が旧値 21 のまま。PLAN の「対象 N 件は実数」原則（完了条件 3 と同趣旨）に反する。
- 修正: リテラルをやめ、検査済み集合から導出して出力する（例: `print(f"対象 {len(checked)} 本を検査")`）。従来の文言形式「対象 N 本を検査」は維持。
- 検証: `python3 -m unittest tests.test_v016_contracts` を再実行し、出力の N が実数（22）であることと OK を verbatim で報告。他のファイルには触れない。
