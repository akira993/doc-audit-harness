あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN.md は rev.5（同じパスを再読）。これが最終ラウンド（上限 5）
- R3-6: 反映。CLI 3 probe は 18 ID、contextMode は 13 ID（`bin_*`・`cfg_omitted`・`cfg_missing` 無し）に分離。§7 ①の `bin` 句を `indexing / webExtract / codexReview` 限定に。
- R4-1: 反映。`invalid-config` の適用範囲を「正常な top-level object 内の seam 不正」に限定。読めない config・top-level 非 object・不在は既存どおり Phase 0 前で停止（§0-5 冒頭、§7 ①末尾）。probe の行 6〜8 は単体防御と明記。
- R4-2: 反映。機械用 JSON は無加工（`json.dumps` 生成）、人向け表示は束縛式で `json.dumps(v)[1:-1][:200]`（改行・制御文字は可視エスケープ）。契約テストが式を抽出し改行入り値で 1 行性を実行 assert。
- R4-3: 反映。codex 行の state は gate stdout の `codexReview.state` のみ。`phase4.json` は再読しない（対応表・契約テスト）。
- R4-4: 反映。seam 別 schema を availability/reason 判別の分岐別 union（余分キー禁止、`available == reason∈OK`）に。矛盾例テスト。
- R4-5: 反映。repo-root は最初に realpath（open-run と同契約）。symlink repo-root 受理テスト。
- R4-6: 反映。fail-open 規約（write 失敗＝警告続行、read 失敗＝7 行 unknown、verdict 不変）を固定文に。
- R4-7: 反映。`--read` の出力に script 算出の `rebind` map（7 行の complete/unknown）を加え、対応表の適用をモデルから外す。算出テスト（完全・mdqHealth 欠損×available 真偽・部分欠損）。
- R1-15: 反映。allowlist は tracked 差分のみ、ignored/untracked（`.envrc .gitignore .claude/settings.local.json data/** .serena/** docs/superpowers/**`）は `baseline-hashes.txt` の sha256 一致、task dir の boss 文書 5 つは直前 boss commit と byte 比較、log/prompt/answer の固定 glob のみ除外。`tasks/` 一括除外は撤去。
- R3-8: 反映。`|| exit 1`。件数は補助、主判定はテスト内の固定 ID 集合。
- R4-8: 反映。3 変数目を DoD (9) に。
- R4-9: 反映。title の範囲表記撤去、notes に完全一致 2 文、旧定数不在を DoD (14)。
- R4-10: 反映。文言を限定。
- R4-11: 反映。additive 例外を明記。
- R4-note-1: 反映。注記を fenced JSON data に、design note 追記。

## 依頼
rev.5 を最終批判せよ。前回指摘の再指摘は不要（対応不十分なら「Rx-N 対応不十分」）。新規は R5-N、根拠と推奨 1 つ。
上限到達につき、残る指摘を **(A) 計画自体の欠陥（PLAN を直してから実装）** と **(B) worker 指示で吸収できる細部** に区分して締めよ。(A) が無ければ「rev.5 で実装承認」と明言せよ。
