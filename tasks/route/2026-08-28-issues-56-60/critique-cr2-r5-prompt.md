あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr2.md は rev.5（同じパスを再読）。これが最終ラウンド（上限 5）
- CR2-29/30: 反映。§8 で `names(04a0624) ∪ REQ` の全テストについて `<name> (<module>.<Class>.<name>)` 行が `... ok` で終わることをちょうど 1 回（docstring 行を許容する正規表現）、`expected failure`／`unexpected success` 0 件。
- CR2-31: 反映。負例の `bin` 値そのもの・空白除去後の名前も marker 付き stub にし、`enabled:false`＋妥当カスタム bin を含む全負例で全 marker 不変。
- CR2-32: 反映。`bin_ws_lead`/`bin_ws_trail`/`bin_ws_both`/`bin_ws_nbsp`/`bin_wsonly`/`bin_surrogate`（CLI 26 ID）、graph も同じ 6 空白 ID、制御文字は文字列途中に配置。
- CR2-33: 反映。scope-check.py は root と全ディレクトリ項目を lstat（kind に `dir` 追加）、baseline を再生成（boss commit 済み、実測 scope-clean）。
- CR2-34: 反映。ADOPTION ⑦ を「新たに拒否される bin はツール探索の前に invalid-config」に（旧 reason を断定しない）。
- CR2-35: 反映。`test_cr2_config_schema_bin_rows` を REQ（v014）に。
- CR2-36: 反映。graph 3 probe の reason 集合を PLAN に固定し、生成集合の完全一致とキー集合を assert。

## 依頼
rev.5 を最終確認せよ。前回指摘の再指摘は不要。新規は CR2-N（続番 37〜）。上限到達につき、残る指摘を (A) 計画自体の欠陥 と (B) worker 指示で吸収できる細部 に区分して締めよ。(A) が無ければ「rev.5 で実装承認」と明言せよ。
