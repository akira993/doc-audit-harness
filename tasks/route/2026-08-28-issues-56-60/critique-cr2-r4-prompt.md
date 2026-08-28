あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr2.md は rev.4（同じパスを再読）
- CR2-22: 反映。既存テスト名の基準を `04a0624`（cr1 実装）に。C10 は改名せず修正。
- CR2-23: 反映。`names()` は `TestCase` 派生クラスのメソッドのみ。§8 でフルスイート `-v` ログの完全修飾 ID が各 1 回実行を確認。
- CR2-24: 反映。`test_bin_positive_paths` は正例 ID 集合 `{space_path, non_ascii_path, quote_backslash, dash_name}`、`test_bin_boundary_table` は `set(range(32))|{127}` を in-test で完全一致。
- CR2-25: 反映。schema／ADOPTION en/ja とも `ASCII-control-character (U+0000–U+001F or U+007F)`／`ASCII 制御文字（U+0000–U+001F または U+007F）` に限定。
- CR2-26: 反映。DoD (10) で schema 6 行の境界条件句と seam 別 disabled 句を契約テストで固定。
- CR2-27: 反映。AST 検査は body/orelse/finalbody/handlers を再帰し、Return/Raise/Continue/Break 後の文を拒否。
- CR2-28: 反映。sentinel は既定名 stub を PATH に置き marker を書かせる。

## 依頼
rev.4 を再批判せよ（4 往復目）。前回指摘の再指摘は不要。新規は CR2-N（続番 29〜）。「計画自体の欠陥」が無ければ「rev.4 で実装承認」と明言し、worker 指示で吸収できる細部があれば列挙せよ。
