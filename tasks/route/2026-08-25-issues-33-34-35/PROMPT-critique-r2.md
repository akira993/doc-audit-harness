前回のあなたの指摘 14 件（BLOCKER 1-4, MAJOR 5-12, MINOR 13-14）をすべて裁定し、
`tasks/route/2026-08-25-issues-33-34-35/PLAN.md` を rev.2 に改訂した。改訂版を再読して批判せよ。
（役割は前回と同じ: 厳格なレビュアー。修正はしない。バグ・回帰・セキュリティ・互換性・テスト不足のみ）

裁定の要点（あなたの提案と異なる/解釈を加えた箇所）:

1. R1-1,2: bare path は「空白分割＋トリム」をやめ、`[A-Za-z0-9_.\-/]+` かつ `/` を含む最長連続の
   正規表現抽出に変更。さらに **bare 由来の finding は WARN 固定**とし、FAIL 昇格は構文明示
   （backtick/link）に限定した。`cp docs/a.md docs/b.md` は WARN 2 件までは許容（blocking しない）。
2. R1-3: file/dir 判定は「末尾 `/` でない ∧ basename が `.` 始まりでない ∧ 拡張子が
   `[A-Za-z][A-Za-z0-9]{0,7}`」を FAIL класス定義とし、`docs/LICENSE` が WARN に留まることは
   config-schema.md に既知の限界として文書化する（完全な file/dir 判別は原理的に不可能なため、
   契約を「拡張子付きパスは FAIL」と定義し直した）。
3. R1-6: 正本（change-set-sha.py の `doc_audit_*.md` glob）は変更禁止のまま、新設の corpus 除外 4 箇所
   （generic-layers / resolve-impact / impact-supplement / start-run）だけ日付認識 regex
   （`^prefix\d{4}-\d{2}-\d{2}(_\d{2,})?\.md$`）で絞る。正本と新設で一致範囲が異なることは意図的な差
   として文書化し、契約テストで両者を固定する。
4. R1-5: 明示 `--paths` は除外しない（列挙時のみ除外）。mapped pull-back と整合。

確認してほしいこと:
- 上記裁定で新たに入り込む欠陥・矛盾はないか（特に: bare=WARN への変更が #33 の目的を損なわないか、
  正本 glob と新設 regex の二本立てが運用上の落とし穴にならないか、`[_NN]` の regex `(_\d{2,})?` は
  正本の `_01` 置換仕様と整合するか）
- rev.2 で新規追加した仕様（§5.1(a) の indented code 簡易判定、§5.2 不正型仕様、§5.3 適用箇所、
  §5.6 テスト計画）の穴
- 前回指摘の対応漏れ

出力形式は前回と同じ（severity 付き番号リスト + 承認可否）。新しい実質的指摘が無ければ
「承認」と明言せよ。
