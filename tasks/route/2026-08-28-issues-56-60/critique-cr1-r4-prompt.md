あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr1.md は rev.4（同じパスを再読）
- CR3-1: 反映。既回答の再利用を撤回。固定文は「新 run の probe 結果に対し確認ゲートを初回どおり評価（発火かつ AskUserQuestion 可なら再質問、不可なら non-interactive 規則、既回答は決して再利用しない）」。`never reuse an earlier answer` を DoD で固定。
- CR3-2: 反映。codex-review は `rebind.state=unknown → invalid-config → reviewState=null → 4-way`。共通規則文にこの例外を明記。他 6 表は unknown → invalid-config → その他。
- CR3-3: 反映。schema 3 行を実装契約と同文（`enabled:false` takes priority…default name in the output; otherwise … invalid-config）に。
- CR3-4: 反映。新接尾辞ちょうど 1 回・旧 0 回を DoD と §8 に。
- CR3-5: 反映。disabled 分岐でも 33 文字ループ。
- CR3-6: CR3-1 で通常規則に戻したため遷移表は不要と判断（規則文の固定で足りる）。反論があれば根拠を。
- CR3-7: 反映。ADOPTION の差分行がすべて `state unknown` を含むことを §8 で検査。

## 依頼
rev.4 を最終確認せよ（4 往復目）。前回指摘の再指摘は不要。新規は CR4-N。「計画自体の欠陥」が無ければ「rev.4 で実装承認」と明言し、worker 指示で吸収できる細部があれば列挙せよ。
