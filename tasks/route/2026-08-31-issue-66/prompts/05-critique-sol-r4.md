PLAN.md を v4 に改版した。再読して再批判せよ（修正はまだ行わない）。

## 前回指摘との対応(自己申告)
1. (required precedent が事実と逆) → 全面採用。S3 を再設計: start-run.py を変更対象に戻し、「P6 かつ required:true」を phase4Required の計算に codexReview.required と並列で追加(required:false の P6 は影響させない = R2-1 と両立)。gate は "none"×P6×required:true を REFUSED(codexReview :1027 対称)。
2. (optional P6 の黙殺) → 採用。planner 呼び出しを global Phase 4 分岐の前に移し、phase4Required=false でも必ず状態束縛。新状態 `phase4-not-required` と状態行を S5 に追加。
3. (phase4Required の型迂回) → 採用。gate は双方向契約より前に厳密 JSON boolean 検査(欠落・null・数値・文字列 → REFUSED)。
4. (taint/quarantine 無回帰) → 採用。early-taint 経路と「空 impact＋corrupt history＋none の隔離成功」を無回帰テストに追加(S7)。
5. (既存テスト棚卸し) → 採用。test_v0131_docs_contracts(44→46 とADOPTION ファイル一覧)・test_scaffold・test_v013_contracts・test_v016_contracts:829 の 0.17.0 更新を S7 に明記。
6. (§9.2 矛盾) → 採用。security 実行値のみに訂正。
7. (P1/P3+false 行欠落) → 採用。§9.8 を改訂(P1/P3+false 正常行・P6+false は required:false のみ到達可・P6+required:true+false は REFUSED)。

## 再批判の観点
- S3 再設計(planner を Phase 4 分岐前に移す)の副作用: planner の CONFIG_SHA/CFG 束縛タイミング、SKILL の実行順序(Phase 0/0.5 との位置関係)、call site 数への影響(§9.5 の N=23 は維持できるか)。
- §9.8 改訂版の残る穴。
- 新規に見つかる欠陥。既出の再確認は不要。実質的な新規指摘が無ければ「収束」と明言せよ。
