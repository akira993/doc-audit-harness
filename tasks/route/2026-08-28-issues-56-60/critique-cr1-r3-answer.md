結論: rev.3 は実装非承認です。unknown 文言変更と graph 3表の並べ替え自体は既存契約と両立しますが、mdq の既回答再利用と codex-review の優先順位に重大な回帰があります。

## (A) 計画自体の欠陥

### CR3-1 — mdq の「既回答再利用」は復元元がなく、未承認の劣化を承認済みにできる

PLAN は reopen 後、同一監査でユーザーが既に回答していれば再質問せず、その回答から `MDQ_DEGRADE` を束縛するとしている。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:9)

しかし turn-ending checkpoint 後に復元が保証されるのは、`RUNID` と完全な `EVIDENCE` だけである。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:50)

`MDQ_DEGRADE` は EVIDENCE に含まれず、旧 run の `phase0-probes.json` に記録されるだけである。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:122) このため harness 質問からの再開時に会話変数が失われると、回答を復元できない。

さらに「既回答」が存在しない経路がある。

- 初回ゲート非発火: `MDQ_DEGRADE=n/a`
- 質問不可または質問抑止: `MDQ_DEGRADE=non-interactive`

後者はユーザー承認ではない。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:118)

再probeによって初回 `n/a` から新たにゲート発火した場合や、reason/health status が変わった場合に以前の回答を流用すると、説明していない劣化を `user-approved` と記録し得る。

推奨: reopen 後は既回答を再利用せず、現在の probe 結果に対して既存の AskUserQuestion／`non-interactive` 規則を通常どおり適用する。

### CR3-2 — codex-review まで unknown を先頭にすると、確定済みの invalid-config が再び隠れる

PLAN は7表すべてを `unknown → invalid-config → その他` にする。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:19)

codex-review では、probe 本体と Phase 4 state が別々に記録されるため、次の状態が成立する。

```json
{
  "state": "complete",
  "reason": "invalid-config",
  "reviewState": null
}
```

`make_rebind()` は codex probe があれば `state:complete` と reason を返しつつ、`codexReviewState` がなければ `reviewState:null` を返す。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:279)

したがって unknown を先にすると、確定済みの `invalid-config` が generic unknown に隠れる。これは PR #61 最終レビューで明示的に修正した回帰である。[stage1b-feedback3.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/stage1b-feedback3.md:4) [REVIEW.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/REVIEW.md:130)

現行テストも `invalid-config` が `reviewState=null` より前であることを固定している。[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:209)

推奨: codex-review だけは `rebind.state=unknown → invalid-config → reviewState=null → その他` とし、probe 全体不明と Phase 4 state だけの欠落を分離する。

### CR3-3 — C8 の config-schema 指示が実装契約と矛盾する

実装契約は、

- `enabled:false` が先勝ち
- disabled 分岐の不正 bin は既定名へ正規化
- reason は `disabled-by-config`

である。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:24)

一方、schema の変更指示は単に「制御文字を含む bin は invalid-config」としており、`enabled:false` の例外を含まない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:25)

このままでは、例えば次の設定について、実装は `disabled-by-config`、公開 schema は `invalid-config` と読める。

```json
{"enabled": false, "bin": "a\nb"}
```

これは v0.13.2 から固定されている `enabled:false` 先勝ちの互換契約とも衝突する。[PLAN.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:47)

推奨: schema 3行にも「`enabled:false` takes priority; otherwise … control characters report invalid-config; disabled output uses the default bin when the configured bin is invalid」と明記する。

## (B) worker 指示で吸収できる細部

### CR3-4 — caller 接尾辞の旧文言除去が DoD に固定されていない

PLAN は、

```text
(caller info unknown after resume)
```

を、

```text
(caller info unavailable)
```

へ変えるとしている。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:15)

現行の固定箇所は [test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:219) だが、DoD と §8 の grep は `state unknown after resume` しか対象にしていない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:73)

テストの assert を削除したり、新旧両方を残した誤実装でも明示 DoD を通過できる。

推奨: 新接尾辞がちょうど1回、旧 `caller info unknown after resume` が0回であることを固定する。

### CR3-5 — disabled 分岐の正規化テストは33文字中1文字しか判別しない

有効時は33制御文字を全走査する一方、`enabled:false` との複合テストは LF だけである。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:26)

disabled 分岐で LF だけを既定名へ正規化し、TAB・CR・ESC・DEL などをそのまま出す誤実装でも通る。

推奨: disabled 分岐にも同じ33文字ループを適用し、全件で `disabled-by-config`・既定 bin・外部 tool 不起動を完全一致検査する。

### CR3-6 — A1 の DoD は回答状態の遷移を検査しない

DoD (1) は固定文の回数と配置だけで、次を判別しない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:52)

- `n/a → ゲート発火`
- `user-approved → 同じ条件`
- `user-approved → 異なる reason/status`
- `non-interactive → ゲート発火`
- `ゲート発火 → 非発火`

例えば常に `MDQ_DEGRADE=user-approved` とする誤った指示でも、固定文検査だけなら通る。

推奨: prior degrade・現在のゲート結果・質問可否から新 run の degrade を決める全遷移表を固定し、各行の期待値を契約テストで assert する。

### CR3-7 — ADOPTION の「§7 ④だけ変更」を scope-check が保証しない

PLAN は `docs/ADOPTION*.md` の変更を §7 ④ の unknown 文言だけに限定している。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:61)

しかし `scope-check.py` はファイル単位の allowlist だけを検査するため、同じ2ファイルの別節を変更しても通る。[scope-check.py](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/scope-check.py:18)

実測では現在の正しい状態で `scope-clean` になることは確認できたが、段落外変更の検出能力はない。

推奨: `ef995f0` の文書から対象の旧句だけを新句へ置換した期待バイト列を作り、実ファイルと完全一致比較する。

## 指定された互換性確認

指摘なし:

- unknown 7行の変更は `test_v014_contracts.py` の対象期待と ADOPTION en/ja を同時更新すれば整合する。
- `"rebind" map is authoritative` は変更対象部分と独立しており、既存 S1b assert を維持できる。[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:222)
- `test_v013_contracts.py` と `test_v0132_contracts.py` に旧 unknown/caller 文言は存在しない。実測 `rg` は0件。
- graph 3表の枝集合・文言テストは順序非依存であり、並べ替えだけでは壊れない。[test_v0132_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v0132_contracts.py:256)
- `BASE_COMMIT=ef995f0` を含む rev.3 の scope-check は実測 `scope-clean`。

## DoD の判別力

| DoD | 判定 | 理由 |
|---|---|---|
| (1) | 不十分かつ一部有害 | 回答状態遷移を検査せず、codex については正しい `invalid-config` 先勝ち実装を失敗させる。 |
| (2) | 有効 | Unicode 改行文字を含む display の1行性回帰を検出する。 |
| (3) | 部分的 | 有効時33文字・空白パス・キー集合は十分。disabled 時は LF しか検査しない。 |
| (4) | 有効 | `mkdtemp` 識別子全体を対象とし、前版の迂回を解消している。 |
| (5) | 有効 | unittest の終了値と skip 数をともに検査する。 |
| (6) | 単独では部分的 | 追跡済み禁止差分のみだが、ファイル単位では (7) が補完する。 |
| (7) | 部分的 | 正しい比較開始点で動作するが、ADOPTION の段落外変更を検出しない。 |

## 最終区分

PLAN を直してから実装すべき点:

1. CR3-1: 会話上の既回答再利用を撤回し、reopen 後の現在条件で確認を処理する。
2. CR3-2: codex-review の invalid-config 先勝ちを維持する。
3. CR3-3: schema に `enabled:false` の例外と既定 bin 正規化を明記する。

worker 指示で吸収できる細部:

- CR3-4: caller 接尾辞の新旧検査
- CR3-5: disabled 分岐の33文字検査
- CR3-6: mdq 確認状態遷移の検査
- CR3-7: ADOPTION の段落限定検査

以上により、rev.3 での実装承認はできません。