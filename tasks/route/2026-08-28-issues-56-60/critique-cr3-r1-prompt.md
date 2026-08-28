あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 状況
PLAN-cr2 の実装は PR #62 に commit `79938a5`（HEAD `af5c09e` 相当）として push 済み。ユーザーの 3 回目 `/code-review xhigh` はセッション上限で途中終了したが、検証サブエージェントが CONFIRMED 所見 1 件（V9）を残した。所見と修正計画は `tasks/route/2026-08-28-issues-56-60/PLAN-cr3.md`（1 件のみ、9 か所の `ensure_ascii=False` 除去＋回帰テスト 6 本）。

## 依頼
`PLAN-cr3.md` を実コード（HEAD）に照らして 1 ラウンドで批判せよ。特に (1) `ensure_ascii=True` に戻すことで cr2 の正例（`PYTHONIOENCODING=ascii` 下の非 ASCII パス、`test_bin_positive_paths`）や `test_bin_boundary_table` が壊れないか（所見は 97 件 green と実測しているが再確認）、(2) 回帰テストの入力（U+2028 bin、surrogateescape の `CODEX_HOME`）が subprocess 経由で確実に再現できるか（env の bytes 渡し方）、(3) `mdq-index.sh` の 3 か所（disabled 分岐は `bin` 無しの printf のまま）を含め emit 箇所が 9 で網羅か、(4) DoD の判別力。指摘は CR3-N。「計画自体の欠陥」が無ければ「rev.1 で実装承認」と明言せよ。
