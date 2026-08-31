PLAN.md を v5 に改版した。これが批判ラウンドの上限(5)である。再読して再批判せよ(修正はまだ行わない)。

## 前回指摘との対応(自己申告)
1. (false でも legacy 実行) → 採用。分岐前は分類と初期状態束縛のみ。P6 の Skill 起動・P8 の project command 実行は phase4Required=true の内側に限定。false は P6/P8 とも phase4-not-required(S3-2)。
2. (legacy findings の表現不能) → 採用。state を legacy-ran/legacy-not-run に分割し、legacy 所見は専用 source "review-command" で fold(severity は現行規則のまま・UNSPECIFIED 非適用)。gate は legacy-ran のときのみ受理(S2-4, S4, §9.8)。
3. (状態行の checkpoint 復元不能) → 採用。gate 出力に codeReviewStatus を追加し、Phase 5 状態行は gate 導出値から描画。会話変数を checkpoint 越しに信用しない(S4, S5)。
4. (library の registry 外証明) → 採用。AST 検査＋隔離単体テストで純粋性を固定(S7)。
5. (REFUSED 優先順位) → 採用。厳密 boolean → config refuse → sentinel 整合 → eligibility の順を明記(S4)。
6. (call-site 表記) → 採用。§9.1 #22 の位置を訂正。

## 判定要求
新規の実質的指摘があれば同形式で。無ければ「収束」と明言し、残る懸念があれば「計画自体の欠陥(PLAN を直してから実装)」と「worker 指示で吸収できる細部」に区分して締めよ。
