前回指摘との対応（自己申告）。PLAN.md は rev.5 に**全面改訂**済み（同パス、§0 に rescope 裁定を明記）。

## boss rescope 裁定（R4 への包括回答）

あなたの R4-2 の異議は正当と認める（ax は workflow-template.js:122,153,156 経由で verifier prompt に
影響し、verifier FAIL は verdict に至る — boss の「advisory＝verdict 非影響」前提は誤りだった）。
その上で、R2-1 以降積み増した EVIDENCE SHA 照合層（planner --evidence・config-changed 終端・
model/timeout 検証済み出力・taint 連携）は**今版から全て撤回**する:

- 防御対象の「run 途中の config 一時改竄（TOCTOU）」は、v0.13.2 の graph 系 key-gate・mdq の bin 解決を
  含む**全 seam の既存露出**であり（graph probe も live config を無照合で読み bin を実行する）、#56 第2段が
  新設する脅威ではない。
- あなた自身が R3-1・R4-3・R4-4 で示したとおり、部分的な照合層は新たな迂回路（not-active 吸収・Phase-0
  bin 窓・taint 迂回）と新 terminal path を生む。この機構は docaudit-history/anchor と同じ信頼クラス
  （封印・barrier・taint 一元化・全 seam 一括）を要し、1 リリースの外科的変更では正しく作れない。
- よって TOCTOU 耐性は**新 Issue（PLAN §9）として起票**し（あなたの R2-1・R4-2/3/4 を証拠として転記）、
  専用 route で全 seam 一括設計する。本版の key-gate の正しさは決定論で完結させる:
  **運用値は「key-gated probe の実行結果」単一経路** — fresh は Phase-0 probe、resume は probe 再実行＋
  probe-record 上書き再記録（あなたの R4-1・R4-10 はこれで解消: 3 値束縛と表示・caller 整合が同時に立つ）。
  probe が読む live config の信頼水準は既存 v0.13.2/v0.14 と同一（変更なし）。

## R4 個別対応

1. (High) resume 再 probe＋再記録へ変更（§5.2-5・§5.1-3）。planner 前に 3 値が束縛される。
2. (High) 異議を認め前提を訂正。TOCTOU 対策自体は新 Issue へ（§9 に R4-2 を証拠転記）。
3. (High) 同上 — Phase-0 bin 窓は graph 系・mdq と共通の既存露出として新 Issue へ。
4. (High) SHA 層撤回により消滅（taint 一元化の要件として新 Issue へ転記）。
5. (High) 同上（終端経路自体を導入しない）。
6. (High) 受理。test_v014:222/:227 の rebind 文言断言を更新対象に明記（§5.3-16）。
7. (High) 受理。既存 16 行判定表の削除・縮小禁止を明記、追加はキー不在系のみ（§5.1-4・§5.3-14）。
8. (High) 受理。安全停止＋境界ケース（fetch 失敗・origin/main 不一致・スイート失敗・誤既存 tag・不正既存
   Release を含む全件）を新ファイルへ複製（§5.3-18、§6-2 で ≥14）。
9. (Medium) SHA 層撤回により消滅（model/timeout の責務は planner に移さない — SKILL:583/:605 は現状維持）。
10. (Medium) resume 再 probe＋上書き再記録で解消（§5.2-5）。
11. (Medium) 受理。not-configured record はキー集合の正規 8 フィールド完全一致・未知フィールド拒否
    （§5.1-3・§5.3-13）。
12. (Medium) SHA 層撤回により消滅（planner 責務は「キー判定の追加」のみ＝文書は既存説明に 1 句追加で足る。
    §5.2 の変更範囲に planner 段落の 1 句追記を含める）。
13. (Medium) 受理。Release notes 内 close directive 集合も厳密 {"56"}＋#59 継続文固定（§5.3-18）。

## 依頼（本ラウンドが上限 5 回目 — 締めのラウンド）

rev.5 を再批判せよ。特に検証してほしいのは:
(a) rescope により本版の key-gate 保証（キー無し config で ax/codex が起動しない — fresh・resume・単体
    呼び出しの全経路）に穴が残っていないか
(b) resume 再 probe＋上書き再記録の設計が既存の probe-record/resume 契約と矛盾しないか
(c) 新 Issue への切り出し（§9）に、本版で最低限塞ぐべきものが混ざっていないか

新規の実質的指摘は根拠（file:line）・重大度・推奨修正つきで列挙せよ。上限到達につき、残る指摘は
「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に区分して締めよ。
新規指摘が無ければ「新規指摘なし・実装承認」と明記せよ。
