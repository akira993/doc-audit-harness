結論: rev.4 はまだ実装非承認です。計画自体の欠陥が4件残っています。

## (A) 計画自体の欠陥

### CR4-1 — reopen 失敗確認より先に Phase 0 再実行を指示している

PLAN は再実行の固定文を、

1. `RUNID/RUN_DIR/EVIDENCE` の置換文より後
2. `if the reopen fails` より前

に置くよう強制している。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:9)

現行 SKILL は、reopen が失敗した場合に exit 4/6 規則で停止する構造である。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:273)

計画どおり挿入すると、失敗確認前に「新 run で Phase 0 を再実行せよ」という指示が現れる。exit 4/6 の出力には有効な新 `runid/runDir` がないため、旧または未定義の run identity で probe を実行する余地がある。DoD はこの危険な配置を順序 assert で固定してしまう。

推奨: reopen の終了値と成功 JSON を確認し、失敗時停止した後にだけ新しい3変数を束縛し、その後へ Phase 0 再実行文を置く。

### CR4-2 — 確認ゲートの固定文が「質問しない」利用者指示を落としている

固定文は次の二分岐しか示していない。

- ゲート発火かつ `AskUserQuestion` 利用可能なら質問
- それ以外は non-interactive

[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:10)

初回規則には、`AskUserQuestion` が利用可能でも利用者が質問停止を明示した場合は質問せず `non-interactive` とする条件がある。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:118)

また `otherwise apply the non-interactive rule` は、ゲート自体が発火しない場合まで `non-interactive` にするようにも読める。本来その場合は `n/a` である。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:121)

推奨: 固定文に「発火＋質問可能＋質問停止指示なしなら質問、発火＋質問不可または停止指示ありなら non-interactive、非発火または codex backend なら n/a」を明記する。

完全な旧→新遷移表までは不要だが、この3分岐は固定文に必要である。

### CR4-3 — codex の `rebind.state=unknown` 先勝ちが既存の部分回復を到達不能にする

PLAN は codex-review を次の順序にする。

1. `rebind.state=unknown`
2. `invalid-config`
3. `reviewState=null`
4. 4-way state

[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:20)

しかし `codexReview` probe の記録が欠けても、独立した `codexReviewState` があれば、`make_rebind()` は次の形を返す。

```json
{
  "state": "unknown",
  "reviewState": "completed"
}
```

根拠:

- 独立した state の保持: [probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279)
- この部分状態を固定する既存テスト: [test_probe_record.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:169)
- 現行契約は既知の reviewState を4-way表示し、caller 情報だけ unavailable 接尾辞にする。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:762)

`state=unknown` を先頭にすると、既知の `completed`／`execution-failed` 等が generic unknown に退化し、rev.4 が維持する `(caller info unavailable)` 経路も実質到達不能になる。

推奨: codex では whole-record unknown の先頭枝を新設せず、`invalid-config → reviewState=null → 4-way` を維持し、`state=unknown && reviewState!=null` は4-way＋caller unavailable とする。

### CR4-4 — ADOPTION 限定検査は差分0件や同一行の別改変でも通る

DoD は「各ファイル4行以下」とするが、実コマンドは変更行に `state unknown` が含まれるかしか検査していない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:59) [PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:77)

実測では ADOPTION 差分が0件でもこの検査は成功した。さらに対象段落は1物理行なので、その行の他の文章を変更しても、行中に `state unknown` が残れば通る。

行数上限もコマンドでは検査されていない。

推奨: `ef995f0` の各文書で旧句を新句へちょうど1回置換した期待バイト列を作り、en/ja それぞれの実ファイルと完全一致比較する。

## (B) worker 指示で吸収できる細部

### CR4-5 — DoD (3) の要約が disabled 側33文字検査を固定していない

本文は enabled/disabled の双方で同じ33文字ループを要求しており正しい。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:24)

一方、DoD (3) は disabled 側を再び `a\nb` の1件だけとしている。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:54)

本文に従えば問題ないが、DoD だけを満たす worker は残り32文字を正規化しない実装でも完了扱いにできる。

推奨: DoD (3) に「enabled 33件＋disabled 33件を各 probe で実行」と明記する。

## 解消を確認した点

以下は新規指摘なしです。

- unknown 7行・caller 接尾辞・ADOPTION en/ja・`"rebind" map is authoritative` の固定文間に衝突なし。
- graph 3表の並べ替えは `test_v0132_contracts.py` の枝集合・文言検査と両立する。
- schema の `enabled:false` 先勝ち・既定 bin 正規化・otherwise invalid-config は実装契約と一致する。
- 内部スペース入りパス、有効時33文字、全 reason のキー集合検査は十分。
- `BASE_COMMIT=ef995f0` の scope-check は実測 `scope-clean`。

したがって、rev.4 での実装承認はできません。