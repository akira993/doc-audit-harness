あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN.md は rev.3 に更新済み（同じパスを再読すること）
- R1-2: 反映。候補ファイルを廃止し gate が next ledger を自前計算。commit は anchor `atomic()` の後（g6）。I/O 失敗のみ warning。
- R1-3: 反映。`start-run.py` が永続 ledger の sha を manifest `codexLedgerSha` に封印。gate は読み込み時に sha 検証、barrier で `state_unchanged` を history/anchor/config と同列に追加（g5）。破損・不一致・`codexLedgerSha` 欠落は REFUSED（fail-closed）。
- R1-4: 反映。resolved は「knownFindings にちょうど 1 回・未報告・carried・`lastDigest != worktreeDigest`」のときのみ有効。性質 P1（digest 不変なら blocking 単調非減少）をテスト名指定で固定。
- R1-10: 反映。seam schema を probe 全キー＋条件付き必須に拡張（mdqHealth.chunks、contextModeHealthy は available:true で bool、docGraph.gitignoreOk、indexing の dbDir/rc）。codex 行は gate 出力の state/ledger から。
- R1-11: 反映。run dir を `O_DIRECTORY|O_NOFOLLOW` で開き dir fd 基準で open/create/replace/unlink。
- R1-13: 反映。JSON 全体を `json.dumps` で生成（BIN/VERSION の `tr -d` も置換）。
- R1-15: 反映。§8 に NUL 区切り・rename 両 path・未追跡含む・非 0 終了の allowlist 検査。`allowlist.txt` に baseline 未追跡一覧を固定（boss 作成済み）。
- R1-16: 反映。5 分岐（probe-exec-failed 含む）。
- R1-17: 反映。テスト内で `len(CASES)` と ID 集合を assert。
- R2-1: 反映。carried blocking は降格無効（fold 条件）。merge でも severity を下げない。
- R2-2: 反映。codex の生 result を `phase4.codexReview.result` として EVIDENCE 束縛済み `phase4.json` に埋め、gate が (g2) 検証・(g3) fold・(g4) next 計算。orchestrator は合流に関与しない。
- R2-3: 反映。`knownFindings` を required に。
- R2-4: 反映。full 64hex key。重複・矛盾・reported の resolved は無視（保守的に「解決しない」。REFUSE しない理由: モデルの出力ゆらぎで run を落とさず、安全側に倒れるため）。
- R2-5: 反映。式を分離、契約テストが 6 入力で実行。
- R2-6: POSIX のみを文書化し実装しない（エンジンは bash 前提で Windows 非対象 — 既存範囲）。
- R2-7: 部分反映。entry に `basis`/`changeSetSha`/`lastDigest` を記録。carry 条件は contentSha のまま（doc と code の矛盾は doc か code が変わるまで続き、code 変更は digest 変化として resolved 経路を開く）。反論があれば具体的な誤動作シナリオを。
- R2-8: 反映。prompt は blocking 50 件上限、超過分は fold で維持。
- R2-9: 反映。①⑤の文言修正。

## 依頼
rev.3 を再批判せよ。前回指摘の再指摘は不要（対応不十分なら「R1-N/R2-N 対応不十分」と理由）。新規は R3-N。各指摘に根拠（file:line／実測）と推奨 1 つ。
特に: (1) gate 変更 g1〜g7 の挿入位置と既存 barrier/taint/`--accept-config`/report 公開との整合、(2) P1〜P4 が rev.3 の規則で本当に成立するか（反例があれば具体的入力列で）、(3) `phase4.codexReview.result` 埋め込みと既存 `write-evidence.py`（不変）・`findings_fail` の整合、(4) 旧 engine で開いた run／旧 manifest との混在、(5) DoD の判別力。
最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、PLAN を直すべき点を優先順で 5 件以内。無ければ「rev.3 で実装承認」と明言せよ。
