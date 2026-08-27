boss レビュー（S4b 差し戻し 1、軽微）— 1 点。git 操作は不要。

`skills/audit/scripts/start-run.py` の `phase4_required` 追加条件 `config.get("codexReview", {}).get("required") is True` は、
`codexReview` が object でない（例: 配列・文字列）config で `AttributeError` の traceback 落ちになる。gate（decide-verdict.py）は
非 object を `{}` 扱いにしているので、start-run も同じく `isinstance(..., dict)` で `{}` に畳んで `required` を読むこと
（非 object なら required=False として扱い、型異常の REFUSED は gate の責務のまま）。`tests/test_start_run.py` に
`codexReview: []` と `codexReview: "x"` で start-run が正常終了し `phase4Required` が従来判定になるケースを追加せよ。

完了後、`python3 -m unittest tests.test_start_run tests.test_decide_verdict -v` とフルスイートを実行し、件数を報告せよ。
