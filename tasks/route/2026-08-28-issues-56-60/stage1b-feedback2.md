boss 判定: `test_h_adoption_structures_stay_parallel` の付録行数 51 → 52 の更新を承認する（付録 1 行追加の必然的な追随。他の assert は変えない）。
加えて boss の diff 精読で 1 点の乖離を見つけた。同時に直せ:

- `probe-record.py::make_rebind`: `codexReview` probe 記録が無く `codexReviewState` だけが記録されている場合、現状は `rebind["codex-review"]` が unknown 形のまま `reviewState` が `null` になる。PLAN §0-6（R5-2 改）と SKILL.md の「When `rebind.codex-review.state=unknown` but its `reviewState` is non-null, render the matching 4-way line with the suffix ` (caller info unknown after resume)`」を成立させるため、`codexReview` 記録の有無に関わらず `result["codex-review"]["reviewState"] = review_state` を設定せよ（`state` は `unknown` のまま、caller 3 値は `None`）。`tests/test_probe_record.py` に「codexReviewState のみ記録 → `state:"unknown"`・`reviewState:"completed"`」のケースを追加（固定 ID 集合と `len(CASES)` も更新）。

その後、単独作業・collab 不使用・commit なしで:
1. `python3 -m unittest -v tests.test_v0131_docs_contracts tests.test_probe_record tests.test_v014_contracts tests.test_v013_contracts tests.test_v0132_contracts tests.test_wp12_contracts tests.test_harness_contract`
2. フルスイート `python3 -m unittest discover -s tests -t . -v > /tmp/s1b-full.log 2>&1; tail -3 /tmp/s1b-full.log; grep -c ' \.\.\. skipped' /tmp/s1b-full.log`
3. `python3 -m py_compile skills/audit/scripts/probe-record.py`
4. 報告: 変更差分の要点、テスト結果（`Ran N`・skip 数・失敗は出力ごと）、PLAN との乖離（無ければ「無し」）。
