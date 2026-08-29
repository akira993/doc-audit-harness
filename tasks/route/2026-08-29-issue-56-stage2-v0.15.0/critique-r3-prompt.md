前回指摘との対応（自己申告）。PLAN.md は rev.3 に改訂済み（同パス）。番号は R2 のあなたの指摘に対応:

1. (High, 封印でなく生 config) 受理。planner へ `--evidence` を渡し、config bytes の SHA が
   `EVIDENCE.config` と一致する場合のみキー判定、不一致は codex 未起動のまま
   `action:"not-active"/reason:"config-changed"`（§5.1-4b、SKILL.md:577 の呼び出しに `--evidence` 追加、
   テスト §5.3-14d）。decide-verdict は不変（required の fail-closed は既存整合検査に委譲）。
2. (High, Phase-4 完了済み旧 run) **修正受理**。decide-verdict は変更しない。理由: (a) 対象は「v0.14 で
   Phase-4 完走済みの run を v0.15 で checkpoint (h) から resume する」版跨ぎの端点であり、その所見は
   当該 run を開始した v0.14 の意味論下で正当に生成されたもの。(b) 版跨ぎ in-flight resume の機械的禁止は
   `59-design-note.md` の反例 11（manifest への engine version 記録・両方向混在テスト）として既に #59 の
   設計制約に含まれており、ここで decide-verdict へ独立実装すると #59 と二重機構になる。(c) 最高信頼層の
   decide-verdict への変更は本タスクの外科的範囲を超える。対応: ADOPTION 固定文③を「codex review 実行前の
   resume に限り再ゲート。完走済みは所見を保持。版跨ぎ resume は非推奨、新 run を開始せよ（機械的禁止は
   #59 で追跡）」へ書き換え（§5.2-8③ en/ja）。この裁定に反対なら、二重機構を避けつつ decide-verdict を
   変更すべき具体的根拠を示せ。
3. (Medium, 完全同型の過剰) 受理。同型を config 必須化・top-level 検証・キー不在判定の 3 点に限定し、
   disabled 時の既定 bin 名維持（test_ax_probe.py:223-228／test_codex_probe.py:309-315）を明記（§5.1-1,2）。
4. (Medium, 一体テスト構成) 受理。完全 config 4 構成（`{"codexReview":{"required":true}}`／
   `{"codexReview":{"enabled":false,"required":true}}`／`{"codexReview":{}}`／`{}`）に修正（§5.3-14c）。
5. (Medium, 優先順位の実順検査) 受理。codex status block 内 5 条件 bullet の実出現 index 順を直接 assert
   （§5.3-15c、完了条件 §6-2 に 1 本明記）。
6. (High, #59 非 close 負契約) 受理。偽 state で #59 OPEN、初回・再実行後とも close 集合厳密 `{"56"}`・
   #59 OPEN を assert（§5.3-18、§6-2）。
7. (Medium, 手動 grep) 受理。§8 の手動 grep を廃止し test_v015_contracts の直接実行に置換。ゲートは
   mdq/contextMode の正当な auto-used（ADOPTION :81-82 等）を誤検出しない seam 名近接の文脈判定と明記
   （§5.3-15e）。boss 実測により README.md:25 の ax/codex 記述は実残骸と確認し、README.md を変更範囲へ
   追加（§5.2-8 末尾・§7 許可一覧）。
8. (Medium, 保存境界の相関) 受理。probe-record に `reason=="not-configured"` 専用の一括検証
   （available=false・既定 bin・version null・commands []・caller 中立 3 値）を追加、矛盾記録の拒否
   テスト ≥ 1（§5.1-3、§6-2）。
9. (Medium, ADOPTION caller 段落) 受理。en :128-131／ja :113-116 へ「キー不在時は caller 情報を調べず
   中立値」を追記し、固定文①末尾にも同旨を追加（§5.2-8）。
10. (Medium, ja 固定文) 受理。ja 4 文を PLAN に完全な固定文字列として事前定義し、契約テストの期待値に
    指定（§5.2-8）。

以上を反映した PLAN rev.3 を再批判せよ。対応済み事項の再指摘は不要。新規の実質的な欠陥のみを
根拠（file:line）・重大度・推奨修正 1 つつきで列挙し、無ければ「新規指摘なし」と明記せよ。
2 の裁定への異議があれば具体的根拠つきで述べよ。
