前回指摘との対応（自己申告）。PLAN.md は rev.4 に改訂済み（同パス）。番号は R3 のあなたの指摘に対応:

1. (High, config-changed の not-active 吸収) 受理。`--evidence` 必須・SHA 不一致は**非 0 終了の終端
   エラー**とし、SKILL は Phase-4 evidence を書かず run を release して停止（§5.1-4b）。
2. (High, ax resume 正規化の実装手段) **修正受理**。SKILL 一文での「封印 config 判定」は EVIDENCE に
   SHA しか無く実装不能という指摘を認める。対応: **resume 時は rebind を運用判定に使わず、ax-probe.sh
   を再実行して束縛し直す**（決定論的・ローカル・秒未満。key-gate は probe 単一経路に集約。rebind は
   表示専用と明記）。live config への一時的キー追加で ax を起動させ得る残余リスクは boss 裁定で許容:
   ax は verdict へ一切影響しない advisory であり、repo 書き込み権限を持つ攻撃者は ax を直接実行できる
   ため、封印照合ゲートの追加は釣り合わない（§5.2-5）。異議があれば根拠を示せ。
3. (High, planner 後の生 config 再読) 受理。planner が照合済み bytes から `model`/`timeoutMs` を検証済み
   出力として返し、SKILL.md:583/:605 の再読を廃止（§5.1-4c、テスト §5.3-14e）。
4. (Medium, --evidence 配線) 受理。evidence 欠落＝非 0 終了をテストで固定し、SKILL の実呼び出し行に
   `--evidence "$EVIDENCE"` があること・生 config 再読が無いことを契約テストで assert（§5.3-14d, 15f）。
5. (Medium, 一体テストの mode) 受理。full mode・baseline 無効に固定し、4 構成の
   action/state/reason/promptVariant を完全一致で検査（§5.3-14c）。
6. (Medium, 生 bytes SHA 契約) 受理。空白・改行・キー順のみ異なる config を不一致ケースとして固定
   （§5.3-14d）。
7. (Medium, 相関検証の 1 件拒否) 受理。連動 7 フィールドを 1 つずつ矛盾させる mutation 表で全 7 拒否を
   個別 assert（§5.3-13、§6-2 で ≥ 9 ケース）。
8. (High, test_v0132 :300-306 の隣接断言) 受理。段落 seam 名一致の断言を 5 seam 集合へ更新
   （または v015 へ移設、worker 判断・boss 検収）（§5.3-16）。
9. (High, handoff 安全停止) **修正受理**。既存 v0.14 テストは変更禁止を維持したまま、不正 SHA・別
   branch・dirty tree・HEAD 不一致・範囲外/symlink 同期先の同等ケース群を新ファイル
   `test_release_handoff_v015.py` へ複製して v0.15 script に全件適用（§5.3-18、§6-2 で ≥ 10 ケース）。
   共通化リファクタは歴史ファイル不変の原則を優先して見送り。
10. (Medium, 件数一致の弱さ) 受理。期待 path 集合と走査済み一意 path 集合の**完全一致** assert へ変更
    （§5.3-15e、§6-3）。
11. (Medium, README の行構造) 受理。README Optional 項目を 1 tool = 1 サブ bullet へ分離した上で行単位
    seam 文脈判定（§5.2-8 末尾）。
12. (Low, --config 値欠落) 受理。両判定表へ「値欠落 → invalid-config・tool 0 回・ASCII JSON 1 行・
    exit 0」を追加（§5.3-11,12、§6-2 で ≥ 23 ID）。
13. (Medium, 固定文②と③の矛盾) 受理。②を「新規 run、または codex review 実行前に resume した run」に
    限定（en/ja 双方 — §5.2-8②）。

以上を反映した PLAN rev.4 を再批判せよ。対応済み事項の再指摘は不要。新規の実質的な欠陥のみを
根拠（file:line）・重大度・推奨修正 1 つつきで列挙し、無ければ「新規指摘なし」と明記せよ。
2 と 9 の裁定への異議があれば具体的根拠つきで述べよ。
