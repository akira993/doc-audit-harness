あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

ラウンド5（最終）。`tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` を v5 に改訂した（再読せよ。S4 の回復規則・S5・S8・S9 parser・§9.1 #10・§9.6 plan-dispatch 行・§9.7 が変更点）。前回指摘との対応（自己申告）:

- R4-1 → 単一の回復規則: 隔離待ちは last_run **または lock holder JSON** の `historyQuarantineFailed:true` で表し（gate は両方に書く。last_run に書けなくても自 run の lock fd で holder に書ける）、open-run は通常 open・`--release`・`--break-lock` のすべてで lock を消す／取る前に隔離待ちを検査し、隔離成功まで続行しない。last_run 不正 JSON は両 marker の可能性ありとみなし、`--accept-config` に加えて live history を隔離（cold start）してからでないと開かない（S4/S5）。
- R4-2 → history parser は字句検査のみ（filesystem 非依存）。存在・通常ファイル・symlink は carry-forward 選択時のみ（S9/S11）。CT-5 の symlink ケースを撤回。
- R4-3 → `impact.historySha` と再読 sha の不一致を exit 7 `sealed-history-mismatch` → `--taint-observed history --observed-by plan-dispatch.py`（§9.6）。
- R4-4 → planner が生成し得る (mode, promptVariant, state) を 8 行で完全列挙、state は `CODEX_REVIEW_STATES` 5 値のみ、それ以外（キー欠落・旧版 evidence を含む）は REFUSED（§9.7）。
- R4-5 → サイズ判定は canonical 直列化（sort_keys、compact separators、ensure_ascii）で固定。history の file は `"`・`\` を禁止（正規化で unresolved 化）、file は直列化後 ≤ 512 bytes、record ≤ 512 KiB。CT-5 の最悪形は非 ASCII 6 倍膨張（S8/S9）。
- 細部 → §9.1 #10 を `== 現 plugin 版` に統一。

最終ラウンドとして: (1) v5 で新たに導入した「lock holder JSON への marker 書き込み」と既存の holder 形式（open-run.py:193-209 の lock 内容、decide-verdict.py:661-672 の holder 読取）との整合、(2) 残る指摘があれば **「計画自体の欠陥（PLAN を直してから実装）」と「worker 指示で吸収できる細部」に必ず区分**して列挙せよ。新しい実質的指摘が無ければ「収束」と明記せよ。対応済み事項の再指摘は不要。出力形式は前回同様。
