## 最終判定

rev.5 は実装非承認です。計画自体の欠陥が2件残っています。

## (A) 計画自体の欠陥

### CR5-1 — `Fix mdq first` を選んだ場合も Phase 0.5 へ進むよう読める

固定文は確認ゲートの3分岐後、無条件に次の指示へ続く。

> then continue with Phase 0.5 exactly once

[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:10)

しかし確認ゲートでユーザーが `Fix mdq first` を選んだ場合、Phase 1へ進まず、lock を解放して監査を終了するのが既存契約である。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:103) [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:112)

`evaluated exactly as on a first pass` から停止を推論できる一方、同じ固定文の後半が Phase 0.5 への進行を明示しており、指示が衝突している。

推奨: 後半を `if that gate evaluation permits the audit to continue, then continue with Phase 0.5 exactly once` と条件付きにする。

### CR5-2 — DoD (1) が codex-review の正しい例外順序を反転させている

本文は codex-review を正しく次の順序としている。

```text
invalid-config → reviewState=null → 4-way
```

`rebind.state=unknown && reviewState!=null` は4-way表示を維持し、caller 接尾辞だけを unavailable にする。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:20)

これは独立した `codexReviewState` を保持する実装と一致する。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279) [test_probe_record.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:169)

一方、DoD (1) は依然として「7表すべてで unknown → invalid-config → その他」と要求している。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:52)

worker が DoD に従うと、codex に whole-record unknown 枝を再導入し、保存済み reviewState の部分回復を壊す。

推奨: DoD (1) を「6表は unknown → invalid-config → その他、codex は invalid-config → reviewState=null → 4-way、部分回復時は4-way＋caller unavailable」と分離する。

## (B) worker 指示で吸収できる細部

### CR5-3 — ADOPTION 検査は「バイト完全一致」ではない

検査は baseline と実ファイルをテキストモードで読み込む。

- `subprocess.run(..., text=True)`: [PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:82)
- `open(..., encoding='utf-8')`: [PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:84)

双方で改行が正規化されるため、文書全体を LF から CRLF に変える限定外変更を見逃す。実測でも同じ内容の CRLF 版はテキスト比較に成功し、バイト比較では不一致になった。

推奨: `git show` の stdout と実ファイルをともに bytes で読み、旧句・新句も bytes として置換・完全一致比較する。

### CR5-4 — reopen の完全な順序を契約テストが固定していない

本文が要求する正しい順序は次のとおり。

```text
open-run
→ failure check/stop
→ success-only RUNID/RUN_DIR/EVIDENCE bind
→ Phase 0 re-run
→ Phase 0.5
```

しかし順序 assert は、再実行文が「停止文より後」「束縛文より後」であることしか要求しない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:11)

誤った `bind → failure check → re-run` でも通る可能性がある。

推奨: 上記5要素の完全な相対順を1本の順序テストで固定する。

## 解消を確認した点

新規指摘なし:

- 確認ゲートの再質問／non-interactive／n/a／既回答不使用の3分岐
- codex-review 本文の部分回復設計
- unknown・caller 文言と既存固定テスト
- schema の `enabled:false` 先勝ち
- enabled 33件＋disabled 33件
- 内部スペース入り bin
- graph 全 reason のキー集合
- scope-check（実測 `scope-clean`）

以上により、rev.5 での実装承認はできません。