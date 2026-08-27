boss レビュー（S5 差し戻し 1）— handoff 試験の可読性と分岐不足、pr-body の実数、フルスイート完走。git 操作は不要。

## A. `tests/test_release_handoff.py` — 可読性（必須）
偽 `git`/`gh`/`rsync`/`python3` の状態機械で本物のスクリプトを通す設計自体は良い。しかし 61 行に `;` で詰めた 1 行多文（160 文字超が
8 行、`setUp` が 1 行）は保守不能で、本リポジトリの他テストの様式（1 文 1 行・関数分割・意味のある名前）に反する。**挙動を変えず**
通常の Python 様式に展開せよ（FAKE スクリプトも同様に 1 文 1 行、コマンド種別ごとに関数化）。目安 250〜350 行。

## B. 分岐の追加（PLAN §12・1 ケース 1 故障）
現状 6 件に加え、次を**それぞれ独立したテストメソッド**で追加（偽ツールの状態で表現できるものばかり）:
1. 同期先が `DOCAUDIT_SKILLS_ROOT` の**外**（symlink ではない実ディレクトリ）→ 停止、tag/Release/close/rsync 0 回
   （現状のテスト名 `…_or_outside_…` は symlink しか検査していない。symlink と outside を別テストに分ける）。
2. 非 main ブランチ → 停止・0 回。3. dirty tree → 停止・0 回。4. `HEAD ≠ approved SHA` → 停止・0 回。5. `origin/main ≠ approved SHA`
   → 停止・0 回。6. unittest 失敗（偽 `python3` の `suite_fail`）→ 停止・tag 0 回。7. PR 番号欠落／非数値 → 停止・呼出し 0 回。
8. **再開**: tag が local/remote とも正 SHA で存在し Release 未作成の状態から開始 → Release 1・close 6・rsync 1、tag 作成 0 回、
   かつ unittest（偽 python3）が再実行されていること。9. **再開**: Release 済み・Issue 3 件 CLOSED の状態から → 残り 3 件だけ close、
   Release 作成 0 回。10. 同期確認 `n`（`input='n\n'`）→ tag 1・Release 1・close 6・**rsync 0**、exit 非 0。
（既存の `test_success_and_resume_tag_release_issues` の「2 回目実行が exit 0」は冪等性の確認として残してよい。）

## C. `pr-body.md`
「テスト」節を実数で埋めよ: 着手前 368 件（2026-08-27 main）→ 完了後 N 件（フルスイート完走時の `Ran N tests … OK (skipped=0)`
の値）。「skip は 0 件です」は実測で 0 のときだけ書く。

## D. フルスイート完走（必須）
`python3 -m unittest discover -s tests -t . 2>&1 | tail -3` を実行し、`Ran N tests in …` と `OK (skipped=K)` の 2 行を報告に貼る。
前回のように「終了要約が返らない」場合は、`> /tmp/suite.log 2>&1` にリダイレクトして完走後に `tail -3 /tmp/suite.log` を読む。
K=0 であること（(j) を有効化したので skip は残らないはず。残っていれば理由を報告）。

## E. 報告
結論先行・完全な文で。変更ファイル一覧、テスト件数（前後・skip）、A/B の各テスト名、許可外変更の有無。
