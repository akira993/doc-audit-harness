あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr1.md は rev.3（同じパスを再読）
- CR2-1: 反映。固定文を「新 run で確認ゲートを含む Phase 0 を先頭から再評価（同一監査でユーザーが既に答えていれば再質問せずその答えを使い MDQ_DEGRADE を束縛）→ Phase 0.5 をちょうど一度（harness 質問は harness.declined 記録済みのため再質問しない）」に。harness 段落内 count==1、`replace RUNID…` の後・`if the reopen fails` の前・Phase 0.5 見出し前の順序 assert。
- CR2-2: 反映。7 行の unknown 文言を `state unknown (probe record unavailable)` に統一（codex の接尾辞も `(caller info unavailable)`）。SKILL 再開段落・ADOPTION §7 ④ en/ja・test_v014 を同時更新、旧文言は grep 0。docs/ADOPTION*.md を許可範囲に追加（§7 ④ のみ）。
- CR2-3: 反映。`enabled:false` 先勝ち維持、disabled 分岐の不正 bin（空・非文字列・制御文字）は既定名へ正規化。複合テスト。
- CR2-4: 反映。共通規則を「unknown → invalid-config → その他」とし 7 表すべてを並べ替え・順序 assert。
- CR2-5: 反映。`BASE_COMMIT=ef995f0` を DoD/§8 に固定。
- CR2-6〜9: 反映（位置・回数、rebind 完全一致、33 文字全走査＋空白パス正例、識別子 `mkdtemp` 0）。

## 依頼
rev.3 を再批判せよ。前回指摘の再指摘は不要。新規は CR3-N、根拠と推奨 1 つ。特に (1) unknown 文言変更が `test_v014_contracts`／`test_v013`／ADOPTION の他の固定文（S1b の `"rebind" map is authoritative` 段落等）と衝突しないか、(2) 7 表の並べ替えが `test_v0132_contracts.py` の graph 3 表テスト（枝の集合・文言を固定）を壊さないか、(3) 確認ゲートの「既回答を再利用」が既存の AskUserQuestion 規約（非対話時の `non-interactive`）と整合するか。
最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、無ければ「rev.3 で実装承認」と明言せよ。
