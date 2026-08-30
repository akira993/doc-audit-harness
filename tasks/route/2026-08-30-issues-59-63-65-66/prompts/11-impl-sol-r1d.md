前回の応答は boss 側の実行時間制限で途中終了した（あなたの作業ツリーの変更はそのまま残っている: `git status --short` で 51 行、47 files changed）。まず作業ツリーの現状を `git status --short` と `git diff --stat` で確認し、どこまで完了しているかを把握してから、**続きから**実装を完成させよ（やり直さない・既存の途中変更を破棄しない）。

方針は前回どおり: 方式 1（`generic-layers.py` に最小封印読取を内包）。完成後は 08-impl-sol.md の「完了条件」「検証コマンド一式」「報告形式」に従って報告せよ。全体テスト `python3 -m unittest discover -s tests` は必ず最後に 1 回フルで実行し、結果行（`Ran N tests` と `OK`/`FAILED`）を verbatim で報告に含めること。PLAN に無い判断が新たに必要になったら停止して報告してよい。
