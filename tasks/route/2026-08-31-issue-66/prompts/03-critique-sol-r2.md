PLAN.md を v2 に改版した。再読して再批判せよ（修正はまだ行わない）。

## 前回指摘との対応(自己申告)
1. Critical(resume 偽装) → 採用。resume 後の `ran` を禁止(S2-6)。cross-turn 行 (g) を「resume 時 not-run・所見 fold 禁止」に改定。
2. severity 無し → 採用。`UNSPECIFIED` として fold し gate で blocking(S2-8, S4)。
3. 空 diff で phase4 不実施 → 採用。start-run.py を変更許可に加え、run 該当 config は phase4Required=true(S3)。
4. gate 以外の REFUSED → 採用。planner refuse は起動抑止のみ、監査は gate まで進み gate が封印 config から独立導出して正式 REFUSED(§1 設計原則・S2-3・S4)。
5. 決定表の未定義入力 → 採用。優先順位付き 8 行の完全表(P1〜P8)に置換。親 object 型・charset ゲート(`^[\x21-\x7e][\x20-\x7e]*$`)・公式名前空間の token 境界(`^/code-review(\s|$)`)を規定(S1)。
6. required×legacy → 採用。required:true は P6 とのみ併用可、他は refuse(S1)。
7. phase4Runs → 採用(縮小方向)。「そのまま乗る」主張を撤回し、source=="codex-review" 限定を維持・code-review 所見は意図的非対象として明文化＋除外の固定テスト(S4, §10)。独立 record 新設は #66 の要求外として見送り。
8. テスト判別可能性 → 採用。表駆動の全数組合せ・EVIDENCE 往復 e2e・CT-5b 無回帰・phase4Runs 不算入を明記(S7)。
9. registry 正本 → 採用。本 PLAN §9 に v0.17.0 の正本(9.1 追加行・9.5 期待値 23/3/13/22/20・9.8 eligibility 全数表)。
10. 死に getter → 採用。REVIEW_COMMANDS_JSON は security/legacy 実行値の供給源として消費を明記し CT で消費を検査(S2-1, §9.2)。
11. test_release_handoff.py → 採用。変更禁止(S7, §7, 完了条件 9)。
12. 旧意味句の残存 → 採用。SKILL:3 description・ADOPTION 冒頭要約を含む per-file 不在検査(S7, S8)。
13. v0.16 進行中 run → 採用。gate の evidence invalid で確定的に落ち、ADOPTION に fresh run 必須を明記(S4, S8)。

## 再批判の観点
- 上記対応の副作用・組み合わせ矛盾(特に S3 の phase4Required=true が既存の run classification・light routing・phase4 sentinel 契約と衝突しないか)。
- P5 charset ゲートが正当な既存 config を巻き込む可能性。
- S4 の eligibility 表(§9.8)の完全性(gate が到達し得るのに表に無い組合せ)。
- UNSPECIFIED blocking の波及(既存 findings 経路で UNSPECIFIED を出す他 source は本当に無いか)。
- 新規に見つかる欠陥。既出指摘の再確認は不要。

報告形式は前回と同じ(番号・重大度・根拠・推奨修正 1 つ、最後に区分表)。
