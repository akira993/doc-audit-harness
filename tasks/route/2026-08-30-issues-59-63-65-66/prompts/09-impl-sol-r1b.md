boss からの回答（3 点とも PLAN.md に反映済み。再読して実装せよ）:

1. `docs\a.md` → **unresolved（拒否）**。`\` は変換しない。S8 の (2) から `\`→`/` を削除し、CT-5 は `docs\a.md` を unresolved 側に移した。history parser の「`\` 禁止」と整合。
2. flip 一致条件 → **4 項目**（worktreeDigest × contractVersion × configSha × carryForwardSha）。S10 が正。§1 と S12 の「3 キー」記述を 4 キーに修正した。
3. `parse_history_document(data)` → **常に 3 値** `(entries, phase4Runs, warnings)`。正常時 `warnings=[]`、`phase4Runs` 退化時に理由文字列を入れる。`entries` 不正は例外（corrupt）。

編集の承認: **PLAN §7 の許可範囲内の既存ファイルの上書きと、新規 `sealed_config.py`・テストファイルの追加を承認する**。禁止範囲は変えない。git 操作はしない。実装後は 08-impl-sol.md の「完了条件」「検証コマンド一式」「報告形式」に従って報告せよ。PLAN に無い判断が必要になったら、今回同様に実装を止めて報告してよい（ただし今回の 3 点のように PLAN 内で解決済みの事項は再質問しない）。
