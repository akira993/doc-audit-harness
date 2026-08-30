あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ。

ラウンド4（上限 5）。`tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md` を v4 に改訂した（再読せよ。§1 末尾・S4・S5・S6・S9・S10・S11・S14・§9.4〜9.7 が変更点）。前回指摘との対応（自己申告）:

- R3-1（acceptance marker の信頼境界）→ **部分採用**。EVIDENCE は run 終了で消えるため、run をまたいで改変不能な置き場は原理的に存在しない（last_run/history/anchor は既存設計から repo 書き込みクラス）。よって marker を「セキュリティ境界ではなく、検知済み改竄をユーザーに可視化し既定で止める運用安全機構」と §1 に明示し、run 内の REFUSED 報告と record を一次の監査痕跡と位置づけた。fail-closed は採用: last_run が存在するが不正 JSON／型不正なら exit 6 `last-run-unreadable`。欠落は cold start（fresh install と区別不能、ADOPTION に明記）。あなたの「改変不能な置き場／EVIDENCE 由来の鍵」は実現不能と判断した。反論があるなら、repo 書き込み者に対して run をまたいで機能する具体的な機構を file:line か既存機構で示せ。
- R3-2（marker 消費の原子性）→ S4 に 4 段のトランザクション（読取検証 → lock → field-preserving atomic 更新 → 失敗時 lock 解放＋exit 2）を定義、CT-4 に書き込み失敗ケース。
- R3-3（隔離失敗後の `--break-lock`）→ last_run に `historyQuarantineFailed:true` marker を書き、open-run が lock 取得後に隔離を再試行、成功時のみ open（S4/S5）。新フラグは追加しない。
- R3-4（harness 互換表）→ 直接起動は「3 生成物が揃い engine stamp == 現 plugin 版（完全一致）」のみ。それ以外（旧版・未来版・欠落・不正・modified）は plugin engine を evidence として起動＋WARN（S6）。`broken`（生成物欠落）は既存契約のまま据え置き（本 route で変更しない旨を明記）。CT-4b。
- R3-5（N・O）→ N=22 に修正（fallback 新設行）。O は「SKILL が起動し lock 取得後に exit 7 を返し得る top-level スクリプト」19 個に再定義（open-run・子・gate を除外）、子は親 ID＋`detail`（§9.4）。
- R3-6（再読・pass-through の判別）→ CT-2b: `PYTHONPATH` の `sitecustomize.py` で config path の open 回数（プロセスごとに 1 回）と子 argv の sha を記録、親検証後・子起動前の差し替えケースを全 pass-through 親に適用。
- R3-7（8 KiB）→ findings ≤ 500・file ≤ 512 bytes、record 上限 512 KiB（最大 ≈ 300 KiB より大きい）、writer→parser 最大境界を CT-5 で往復。
- R3-8（50 件 cap と flip）→ flip 用集合は完全保持（≤ 500）、超過は `truncated:true` で flip 比較対象外＋warning。canonical 順（severity rank desc, file asc）と (file, severity) 重複排除。carry-forward の 50 件は表示上限のみ。
- R3-9（reader 契約）→ §9.6 に 4 reader（resolve-impact を追加）× absent/valid/corrupt/sha 不一致 の真理値表。旧 top-level array は valid。codex-review-plan の corrupt は `carryForward:null`＋warning で継続。
- R3-10（eligibility）→ §9.7 に manifest.mode × promptVariant × state の表。不整合は REFUSED。record は `source=="codex-review"` のみ。
- R3-11（carry-forward 入力境界）→ `runid`/`ts` を prompt から除去、file は共通 validator（symlink 拒否）＋文字種制限（バッククォート・空白・引用符を含むものは除外）、`ensure_ascii=True` の JSON。

再批判を求める。特に: (1) v4 で新設した marker 2 種（`configAcceptanceRequired`、`historyQuarantineFailed`）× `--accept-config` × `--break-lock` × `--release` × decline 再 open の全組み合わせで、開けるべきでないときに開く／開けるべきときに開けない経路、(2) §9.6/9.7 の表の抜け、(3) N=22/M=4/G=13/K=21/O=19 の再計数、(4) 落とす・足りない成果物。

出力形式は前回同様。対応済み事項の再指摘は不要。新しい実質的指摘が無ければ「収束」と明記し、残る指摘があれば「計画自体の欠陥」と「worker 指示で吸収できる細部」に区分せよ。
