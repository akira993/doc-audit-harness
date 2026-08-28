あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr1.md は rev.2（同じパスを再読）
- CR1-1: 反映。A1 を撤回。Phase 5 の情報源は rebind のみ、判定不能は常に unknown（変更なし）。
- CR1-2: 反映。A1（旧 A2）を「reopen 後は新 run で Phase 0 を丸ごと再実行（Phase 0.5 は繰り返さない）」に変更。会話変数からの再記録は採らない。
- CR1-3: 反映。validator は据え置き、SKILL の合成説明で正規化（available:false → healthy 常に null、available:true で CM_HEALTHY 未束縛 → false／probe-error）。
- CR1-4: 反映。C7（ensure_ascii=False）は不採用。U+0085/U+2028/U+2029 を含む値の 1 行性回帰テストのみ追加。
- CR1-5: 反映。graph 3 probe の bin に NUL または C0 制御文字（\x00–\x1f, \x7f）を含む場合を invalid-config に（emit 前、キー集合・reason 集合不変）。空白を含むパスは従来どおり許容（read の最終変数は行末まで取る）。NUL/改行/タブのテスト。
- CR1-6〜8: 反映。D10 共有ヘルパー化を本 follow-up から外し、別 refactor route へ（golden 差分実行器を伴う）。テスト衛生（mkdtemp 統一、エイリアス統合）のみ残す。
- CR1-9: 反映。フルスイートは rc 保存＋`|| exit 1`。
- CR1-10: 反映。scope-check.py（cr1 用 allowlist を boss commit に固定、tracked＋未追跡、保護 root hash、exit 1）。
- CR1-11: 反映。graph 3 probe の全 reason 分岐でキー集合完全一致テスト。
- CR1-12: 反映。`grep -c 'mkdtemp()'` 合計 0 を機械判定。
- 所見 #4（codexReviewState 書き込み失敗）は「rebind のみ」を維持し、fail-open 警告行を報告本文に必ず残す規約＋説明文で対応（文言・§7 は不変）。

## 依頼
rev.2 を再批判せよ。前回指摘の再指摘は不要（対応不十分なら「CR1-N 対応不十分」）。新規は CR2-N、根拠と推奨 1 つ。特に: (1) A1 の Phase 0 再実行が既存契約（Phase 0 は open-run 後・確認ゲート・Phase 0.5 の順序、`test_v013/v0132/v014` の固定文言・出現回数）と両立するか、(2) A3 の正規化が `test_probe_record` の既存期待と矛盾しないか、(3) C8 の制御文字判定と `config-schema.md` の記述、graph probe テストの既存 fixture（`bin` にスペースを含むケースの有無）、(4) B6 の「先頭へ移動」が S1a の順序 assert（mdq 枝が `MDQ_AVAILABLE false` より前）と整合するか、(5) DoD の判別力。
最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、無ければ「rev.2 で実装承認」と明言せよ。
