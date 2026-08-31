# #66 事前実機検証（PLAN 前・route 手順1）

日時: 2026-08-31。環境: Claude Code **2.1.251**（macOS）。方式 B（`reviewCommands.code` 単一窓口）はユーザー決定済み。
方法: scratchpad `i66/` に 1-commit の scratch repo（`calc.py`、未コミットの植込み欠陥 2 件: `eval()` 注入・`//`→`/` 型退行）を複製し、`claude -p`（headless, model=sonnet, 既定 permission mode）でモデルに `Skill(code-review, args="low")` を起動させた。各アームの生出力は scratchpad `i66/out-*.json`、transcript は `~/.claude/projects/...i66-arm-*/`。

## 行列（実測）

| アーム | 設定 | 結果 |
|---|---|---|
| control | ルール無し・既定 mode | **実行された**。所見 2 件が in-band で返却（植込み欠陥 2/2 検出） |
| allow | project settings に `permissions.allow` | 未信頼 workspace のため **allow 無視の警告**（stderr）→ それでも実行された（= control と同じ） |
| deny | `--settings '{"permissions":{"deny":["Skill(code-review *)"]}}'` | **ブロック**: `Error: Skill execution blocked by permission rules` → マッチャー `Skill(code-review *)` は permission ルールに実効（陽性対照） |
| ask | `--settings '{"permissions":{"ask":["Skill(code-review *)"]}}'` | **実行された（ブロックされない）** — Issue の前提「`-p` では ask が fail-closed」は 2.1.251 で不成立 |
| skillOverrides | project settings `{"skillOverrides":{"code-review":"user-invocable-only"}}` | **ブロック**: `Error: Skill code-review is disabled for model invocation in skillOverrides settings` → project スコープで実効（#50631 は本環境で再現せず）・**無言でなく明示エラー** |
| ask×Bash 対照 | `--settings '{"permissions":{"ask":["Bash(echo:*)"]}}'`, headless | **ブロック**: `Claude requested permissions to use Bash, but you haven't granted it yet.` → ask の headless fail-closed は Bash では機能する |
| high 形状 | control 同等で args="high" | 実行中（severity ラベル付き形状の取得） |

## in-band 返却の生形状（transcript の tool_result、low）

```
Skill "code-review" completed (forked execution).

Result:
## Findings

- `calc.py:3` — `parse_amount` now calls `eval(s)` ...
- `calc.py:8` — `apply_discount` switched ... `//` ... to `/` ...
```

- forked subagent 実行で、所見は呼び出しターンの **ツール結果として同期で in-band 返却**される（issue の検証項目 (ii) 充足）。
- **low では severity ラベルが無い**（bullet 羅列のみ）。fold 契約は「ラベル無し所見」の扱いを定義する必要がある。
- 外側モデルは結果を言い換えて再掲することがある → fold は tool_result を直接根拠にできる形（同一会話内可視）で規定する。

## PLAN に効く帰結（暫定）

1. **切り分け確定**: ask は Bash では headless fail-closed に機能し、Skill(code-review) では素通り → 2.1.251 の Skill 起動経路は ask ルールを消費していない（deny は消費する）。Skill はそもそも既定 allow（control が無許可で実行）であり、ask を挟む承認フローが存在しない可能性が高い。よって Issue 提案 2 の「承認は `permissions.ask` に委譲」は実測上成立しない。承認が欲しい adopter への推奨は deny / skillOverrides（両方とも明示エラーで検出可能 = docaudit 側 fail-closed 経路に載る）。ask の対話側挙動（プロンプトが出るか）は **ユーザーによる interactive 実測待ち**（headless では原理的に観測不能）。
2. skillOverrides ブロックは明示エラー文字列を返す → 「無言で失敗」（Issue 制約 2 の想定）ではなく、SKILL.md の `disable-model-invocation` 検出分岐に対応させられる。
3. version 境界: 2.1.251 で feature flag なしに model-invocable（control が素で実行）。

## 追補（high 形状・上流 docs 調査）

- **high の生形状**: `Skill "code-review" completed (forked execution).` + 前置き文 + fenced JSON 配列 `[{file, line, summary, failure_scenario}, ...]`。**severity フィールドは無い**（low の bullet 形式にも無い）。fold 契約は「severity 無しの所見」の既定（非 blocking WARN 扱い等）を定義する必要がある。植込み欠陥 2/2 検出。
- **上流 docs（claude-code-guide 調査、code.claude.com/docs）**:
  - permissions: `Skill(name)` 完全一致／`Skill(name *)` 前方一致は allow/deny の例のみ文書化。ask の Skill 例は上流にも存在しない（実測の「ask 素通り」と整合）。
  - anthropics/claude-code#50631（skillOverrides 不反映）は **closed**。実測でも project settings の skillOverrides は 2.1.251 で実効。
  - code-review docs: `-p` の low〜high は「レビューを待って所見を response に含める」（実測どおり in-band）。`ultra` は待たない。**interactive では low〜high もバックグラウンド実行（所見が後着）と読める記述**あり → docaudit の主戦場は interactive なので、モデル起動時に同期（forked, 同一ターン）か非同期（task 通知で後着）かは interactive 実測が必要。
  - v2.1.246 の release note: `/code-review` のモデル自発起動が Bedrock/Vertex/Foundry・telemetry off 環境等へ一般化。2.1.251 では flag なしで可（実測どおり）。

## 未観測（headless では原理的に不可 → ユーザーの interactive 実測待ち）

1. interactive セッションで ask ルールがプロンプトを出すか（headless では ask が Skill に消費されないため、おそらく出ない見込み）。
2. interactive でモデルが Skill(code-review) を起動したとき、所見が同一ターンの tool_result で返るか、background task 通知で後着するか。

## interactive 実測（ユーザー実施、2026-08-31 10:31、arm-ask、Claude Code 2.1.251 / Fable 5 / auto mode）

1. フォルダ信頼ダイアログは承認済み（headless の trust 交絡を除去した状態）。
2. **ask プロンプトは出なかった**: `ask: ["Skill(code-review *)"]` が project settings にある状態で、Skill(code-review) は許可確認なしに実行された。※セッションは auto mode。既定 permission mode での挙動は未確認だが、headless で ask が消費されない実測と併せ、**ask を承認ゲートとして推奨する根拠は存在しない**（enforcement には使えない）。
3. **interactive のモデル起動は background agent 実行**: `Skill(code-review)` → `Running in the background` → `Waiting for 1 background agent to finish` → `Agent "/code-review low" finished · 12s` → 所見が同セッションに後着し、モデルがそれを引用して報告。同一ターンの同期 tool_result ではないが、**完了待ち（wait）が可能で、所見は同セッション内で fold 可能**。
4. interactive low の所見形状は `calc.py:3 — ...` の行形式（headless low の `## Findings` bullet、headless high の fenced JSON `{file,line,summary,failure_scenario}` とまた異なる）。**返却レイアウトは実行形態・レベルで揺れる** → fold 契約はレイアウト非依存＋severity ラベル無しの既定を定義すること。

## 検証まとめ（PLAN の前提として確定）

| 検証項目 | 結果 |
|---|---|
| model-invocable（2.1.251, flag 無し） | ✅ headless/interactive とも自発起動可 |
| 所見の in-band 返却 | ✅ headless=同期 tool_result／interactive=background agent 完了後に同セッション後着（待機可） |
| `deny: ["Skill(code-review *)"]` | ✅ ブロック（`Error: Skill execution blocked by permission rules`） |
| `skillOverrides: user-invocable-only`（project） | ✅ ブロック（`Error: Skill code-review is disabled for model invocation in skillOverrides settings`）・#50631 再現せず |
| `ask: ["Skill(code-review *)"]` | ❌ headless: 素通り（Bash では fail-closed に機能）／interactive(auto mode): プロンプト出ず → **承認ゲートとして不成立。ADOPTION では推奨しない** |
| `ultra` | 上流 docs: 待たない（起動のみ）→ config 検証で拒否（Issue 制約 5 どおり） |
