あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

前回（R1）の 12 件への対応を PLAN rev.2（`tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`、全面改稿）に反映した。対応の自己申告:

1. 版（minor へ）: **不採用**。利用者の明示指示「パッチアップデート」を維持し、最終報告で貴方の反論を併記する（§0-1）。これは boss の裁定であり再指摘不要。
2. `*.md` 既定の安全性: **部分採用**。既定は揃えるが、`fix-scope.py` に basename 組込み deny `{"CLAUDE.md","AGENTS.md"}`（任意の深さ、docGlobs より優先）を追加（§0-2、DoD 1-4）。
3. 不正設定: 採用。`not-configured` はキー不在のみ、`invalid-config` を新設（`enabled` 非 boolean・キー非 object・JSON 不正・config 不在・top-level 非 object）。判定表 8 行（§0-4）。
4. 判別基準: 採用。基準を「conditional-force かつ worktree に tool 所有物を作り verdict に影響しない 3 seam」に書き直し、§7 に移行注記、残り 4 seam は別 Issue 候補（§0-4）。
5. `.gitignore` 復元: **部分採用**。復元は削除。`settings.yml` マーカーを主対策とし、`ccc index` 前後の `.gitignore` sha 比較で変化を**検出のみ**（書き込み無し、`gitignore-modified` で available:false・WARN）を安全網として残す（§0-5b）。理由: マーカーは ccc の内部仕様に結合するため、版が変わって別経路で書かれた場合に report-only 契約違反を黙って通さない版非依存の網。
6. run 解放: 採用。exit 5／その他非 0／read-manifest 非 0 の 3 分岐すべてに SKILL.md:52 の完全コマンド（§0-3a、DoD 5）。
7. read-manifest 非 object: 採用。dict と sealed を一体検査、`[]`/`null`/`sealed:false`/キー無しの 4 テスト（§0-3b、DoD 6）。
8. 状態行: 採用。reason 優先の排他表、`AVAILABLE` 単独 catch-all 廃止、集合一致テスト（§0-4、DoD 10）。
9. §0-12: 採用（fixture 化: `tests/data/dir-framework-scope/`、外部依存・skip を除去）。ただし「今回から外す」は不採用 — release-handoff.sh は承認 commit でフルスイートを再実行するため main が red のままだと出荷できない（§0-12、DoD 15）。
10. docGlobs 走査: 採用。既知 consumer 7 ファイル限定、AST 走査、call site 数を実数で固定（§0-2、DoD 3）。
11. DoD: 採用。判定表 8 行×3 probe の全件テスト（21 件）、集合一致、件数は「ベースライン 495 から正確に +Δ」（DoD 8-11, 20）。
12. ja refresh 行: 採用。行単位の完全文言を §0-6 に明記。

# 依頼
PLAN rev.2 を再批判せよ。対応済み事項の再指摘は不要。特に:
- 新規に入れた設計（basename deny、`invalid-config`、検出のみの `.gitignore` 網、fixture 化、reason 優先の排他表）が **互いに、または既存コード・文書と矛盾しないか**。
- basename deny の副作用（`docs/CLAUDE.md` のような通常文書扱いの衝突、`resolve-impact`/`generic-layers` が同ファイルを docs として扱う一方 fix だけ拒否する非対称の妥当性）。
- `invalid-config` を probe が返すとき、config 全体の妥当性検査（`open-run.py`/`start-run.py`）と重複・矛盾しないか（不正 JSON は probe 到達前に落ちるなら判定表 6/8 は到達不能か）。
- `gitignore-modified` の検出が偽陽性を生む条件（並行編集・`.gitignore` symlink・CRLF）と、それでも available:false にする是非。
- DoD の各項目が「正しい実装でも誤った実装でも通る」ものになっていないか（0 件検査、存在数のみの検査）。
- 実物（スクリプト・SKILL.md・テスト）で確認できる範囲は確認してから指摘すること。
出力形式は前回と同じ（番号・根拠 file:line・深刻度・推奨 1 つ、最後に「計画自体の欠陥」／「worker 指示で吸収」の区分）。新しい実質的な指摘が無ければ「指摘なし・実装承認」と明記せよ。
