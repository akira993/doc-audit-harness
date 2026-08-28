あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr1.md は rev.5（同じパスを再読）。これが最終ラウンド（上限 5）
- CR4-1: 反映。reopen 段落を「終了値と成功 JSON の確認 → 失敗なら exit-4/6 で停止 → 成功時のみ新 3 変数を束縛」に整え、再実行文はその束縛文の直後（停止文より後）。順序 assert を更新。
- CR4-2: 反映。固定文に 3 分岐（発火＋質問可＋停止指示なし → 再質問／発火＋質問不可または停止指示 → non-interactive／非発火または codex backend → n/a）と `never reuse an earlier answer`。
- CR4-3: 反映。codex-review 表に whole-record unknown 枝を新設しない。順序は invalid-config → reviewState=null → 4-way、`state=unknown && reviewState!=null` は 4-way＋`(caller info unavailable)`（S1b R4・test_probe_record.py:169 を維持）。共通規則文にこの例外を明記。
- CR4-4: 反映。§8 に「`git show ef995f0:docs/ADOPTION*.md` の旧句をちょうど 1 回置換した期待バイト列と実ファイルの完全一致」python 片（差分 0 件・別改変で失敗）。
- CR4-5: 反映。DoD (3) に enabled 33 件＋disabled 33 件を明記。

## 依頼
rev.5 を最終確認せよ。前回指摘の再指摘は不要。新規は CR5-N。上限到達につき、残る指摘を (A) 計画自体の欠陥 と (B) worker 指示で吸収できる細部 に区分して締めよ。(A) が無ければ「rev.5 で実装承認」と明言せよ。
