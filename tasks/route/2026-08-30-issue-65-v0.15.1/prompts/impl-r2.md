boss 検収の結果: A1 は boss 実行で GATE PASS（G1〜G12）、フルスイート 654 OK、A3 実機再現 4 ケース合格、差分全行読解で差し戻し事項なし。

追加依頼（1 点のみ・変更範囲は `tasks/route/2026-08-30-issue-65-v0.15.1/gate.py` のみ）:
A2（G ごとの違反 fixture で単独 FAIL を確認する boss 作業）を現実的な時間で回すため、gate.py に `--only G2,G8` 形式の引数を追加せよ。指定された G だけを実行し、他は出力しない。未指定なら従来どおり全 G を実行する（既定挙動・出力形式は不変）。`--only` 実行時でも最後の `GATE PASS/FAIL` 行と exit code は指定した G の結果で決める。G1〜G12 のうち存在しない ID が指定されたら usage エラーで exit 2。

実装後: `python3 tasks/route/2026-08-30-issue-65-v0.15.1/gate.py --only G4,G9` と `--only G13`（exit 2）を実行し、出力をそのまま報告に貼れ。git 書き込み操作は引き続き禁止。
