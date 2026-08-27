boss レビュー（S1 差し戻し 1）— 修正 2 点。git 操作（ブランチ作成・`git add -f`・commit）は boss が行うので不要。

1. **範囲外の挙動変更を戻す**: `skills/audit/scripts/generic-layers.py` の既存関数 `_strip_container_markers` 内の引用符正規表現を
   `r"^ {0,3}>[ \t]*"` から `r"^ {0,3}>[ \t]?"` に変えているが、これは #43 の 3 修正に含まれない共有ヘルパ（`_mask_fenced` が
   `:243` で使用）の変更である。`_strip_container_markers` は**元のまま**に戻すこと。新設の `_strip_blockquote_markers`（`[ \t]?`）は
   `_mask_indented` 系の用途に限って使う設計でよい。戻した後も 16 件の新テストと `test_generic_layers` 全 76 件が green であることを
   確認せよ（引用内 list のケースで `[ \t]*` と `[ \t]?` の差が効かないことを確認し、効くなら報告）。
2. **契約テスト (j) の扱い**: `tests/test_v013_contracts.py::test_j_only_allowlisted_0_12_0_references_remain` は、`tests/test_release_handoff.py`
   の 0.12.0 参照（S5 で更新する対象）によって失敗する。S1〜S4 の各 Stage 末フルスイート green を保つため、このテストを
   `self.skipTest("enabled in S5 after release-handoff tests move to 0.13.0")` で保留にせよ（本体の検査ロジックは残す。S5 で skip を
   外す）。許容リストへの追加はしない。

完了後、フルスイートを再実行し、件数（成功／失敗／skip）と `git status --short` を報告せよ。コミットはしない（boss が行う）。
