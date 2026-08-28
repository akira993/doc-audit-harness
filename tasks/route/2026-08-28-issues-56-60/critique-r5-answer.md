## 最終判定

**rev.5 のままでは実装承認不可。**  
(A) に該当する計画欠陥が残っている。特に #57 の正常出力拒否と、スコープ検査の常時失敗は実装開始前に修正が必要。

## (A) 計画自体の欠陥

### R5-1 — 正常な `mdqHealth` 出力を必ず拒否する

種別: バグ・回帰

PLAN は全 seam で余分キー禁止とし、`mdqHealth` を `{healthy,chunks,status}` の3キーに限定している。[PLAN.md:59](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:59) [PLAN.md:61](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:61)

しかし記録元の実出力は5キーであり、PLAN はこれを verbatim で保存する。[PLAN.md:71](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:71) [mdq-health.py:7](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-health.py:7) [mdq-health.py:99](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-health.py:99)

```text
files, chunks, searchSmoke, healthy, status
```

したがって正常な mdq run でも記録に失敗し、再開後の mdq 行が unknown になる。

**推奨:** 完全キー集合を `{files,chunks,searchSmoke,healthy,status}` に合わせ、実際の `mdq-health.py` stdout をそのまま write→read するテストを追加する。

### R4-7 対応不十分 — `rebind` は完全性しか決定していない

種別: バグ・テスト不足

`rebind` が返すのは各行の `complete|unknown` だけで、raw seam から Phase-5 変数・表示分岐への変換は依然モデル側に残る。[PLAN.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:67) [PLAN.md:81](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:81)

例えば `webExtract` が完全なら `complete` になるが、`AX_AVAILABLE` や `AX_REASON` を誤束縛しても probe-record のテストは通る。DoD (11) も文言の存在検査だけで、producer→保存→再開表示の接続を検査しない。[PLAN.md:154](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:154) [PLAN.md:155](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:155)

**推奨:** `rebind` に各行の正規化済み値を含め、実producer出力から7行の完全一致までを一続きで検査する。

### R4-2 対応不十分 — 再開時に改行注入が復活し得る

種別: セキュリティ・回帰

可視エスケープ式と一行性テストは初回の `CODEX_PROBE_JSON` 束縛だけを対象にしている。[PLAN.md:90](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:90) [PLAN.md:97](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:97)

再開時は raw `phase0-probes.json` の `codexReview` を使うが、同じエスケープ式を通す契約・テストがない。[PLAN.md:67](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:67) [PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:78) 単純な `json.loads`＋`print` で再束縛すれば、保存されていた改行が実改行に戻る。

**推奨:** 初回・再開の双方を同じ表示用エスケープ処理に通し、raw 改行入りrecordからの再開表示一行性を検査する。

### R5-2 — codex の `complete` と gate state が一致しない

種別: バグ・回帰

PLAN の `rebind["codex-review"]` は probe record の有無で決まる一方、実際の状態は gate stdout だけを使う。[PLAN.md:78](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:78)

反例が二つある。

1. probe record 有りでも、gate が Phase-4 読込み前に REFUSED すると `codexReview.state` は `null` のまま。[decide-verdict.py:609](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:609) [decide-verdict.py:1027](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/decide-verdict.py:1027) `complete` なのに4-way表示のどの枝にも入らない。
2. probe record が欠けても、gate state が `completed` ならレビュー結果は確定済みだが、PLAN は行全体を unknown にして隠す。

**推奨:** codex の基本状態は gate state だけで決定し、probe record 欠損は caller情報の接尾辞だけを unknown にする。gate state が null の場合は明示的な unknown/REFUSED 行にする。

### R1-15 対応不十分 — 新スコープ検査も正常状態で必ず失敗する

種別: テスト不足・セキュリティ

ignored対象は status の変更集合へ先に追加され、allowlist に無ければ `bad` になる。[PLAN.md:201](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:201) [PLAN.md:214](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:214) 後段のhash一致は、既に追加された `bad` を取り消さない。

現環境で同じ処理を再現すると、未変更状態だけで次が違反になった。

```text
.claude/settings.local.json
.envrc
.gitignore
.serena/
data/
docs/superpowers/
```

さらに status は後半3つをディレクトリ単位で返す一方、baseline は個別ファイル単位なので対応しない。[baseline-hashes.txt:4](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/baseline-hashes.txt:4)

また既存ファイルのhashだけを確認するため、新規ファイル追加や同内容symlinkへの置換も検出できない。

**推奨:** ignored対象を status 集合から分離し、保護rootを再列挙して「path集合・通常ファイル種別・mode・hash」の完全一致を検査する。

### R5-3 — NUL入り `bin` が別の実行名へ変化する

種別: セキュリティ・互換性

CLI表は非空のJSON文字列を有効な `bin` としている。[PLAN.md:31](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:31) しかしJSON文字列は NUL を含められる一方、Bash変数は保持できない。

実測:

```text
入力bin: "\u0000codex"
Bash read後: "codex"（長さ5）
```

設定した名前とは別の実 `codex` が起動し得る。DoD の特殊文字テストは改行・引用符・backslashだけで、NULを含まない。[PLAN.md:96](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:96)

**推奨:** `bin` に NUL が含まれる場合は `invalid-config` とし、CLI 3 probe 共通ケースに追加する。

## (B) worker 指示で吸収できる細部

### R5-4 — 不正な `bin` 分岐の出力値が未定義

種別: バグ・テスト不足

`invalid-config` は not-installed 形なので `bin:string` が必要だが、不正値を受けた際に既定値へ戻すのか、文字列表現へ変えるのかが未定義。[PLAN.md:35](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:35) [PLAN.md:60](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:60)

`compound` でも ax/codex は文字列のbinキーを出す必要がある。DoD はキー集合だけで値を固定しない。[PLAN.md:141](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:141)

**推奨:** 不正・空binは各 seam の既定値 `mdq`／`ax`／`codex` を出すと固定し、値と型を完全一致で検査する。

### R5-5 — 200文字制限がエスケープ途中で切れる

種別: 表示回帰・テスト不足

`json.dumps(v)[1:-1][:200]` は、エスケープ後に単純切断する。[PLAN.md:91](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:91)

実測では `199文字 + 改行` の結果が単独の `\` で終わった。

```text
escaped_len=200
ends_backslash=True
```

一行性テストは通るが、可視エスケープとして不完全になる。

**推奨:** escape単位を壊さない短縮処理にし、199文字＋改行と `\uXXXX` 境界をテストする。

### R5-6 — `skip 0` を機械判定していない

種別: テスト不足

DoD は skip 0 を要求するが、通常の `unittest` はskipがあっても終了0になる。[PLAN.md:163](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:163) [PLAN.md:179](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:179)

**推奨:** full suite の結果から `result.skipped == []` を明示検査する。

### R5-7 — `0.13.2` 残存ゼロの全体検査がない

種別: テスト不足・出荷互換性

DoD (14) は allowlist外の `0.13.2` が0件とするが、実コマンドは `tests/test_release_handoff.py` 内の旧tag/pathだけを検索する。[PLAN.md:160](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:160) [PLAN.md:189](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:189)

新 handoff の人向け文言などに旧版が残っても通る。

**推奨:** repository全体の `0.13.2` 一致を収集し、許可するpathと行パターンを固定比較する。

### R5-8 — 明示的な空 `--config ""` が未検査

種別: 互換性・テスト不足

判定表は「未指定」と「指定ファイル不在」を区別するが、空文字引数を定義していない。[PLAN.md:29](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN.md:29) 現行3 script は `CONFIG=""` を未指定の印として使うため、`--config ""` を省略扱いする。[mdq-index.sh:17](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/mdq-index.sh:17) [ax-probe.sh:14](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/ax-probe.sh:14) [codex-probe.sh:15](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-probe.sh:15)

**推奨:** 引数の指定有無を別フラグで保持し、空パスを `invalid-config` またはCLI errorとして固定テストする。

## 指摘なし

- #58 のPOSIX絶対パス三段検査
- #59のfenced JSON運用注記とdesign note追記
- repo-root realpath化・中間symlink拒否
- `phase4.json` 再読廃止
- probe-record read/writeのfail-open方針
- handoffのclose集合とpartial表記
- 件数不足時の `|| exit 1`
- #60と既存 `test_codex_probe.py`／`test_v013_contracts.py` の固定契約との直接衝突

ファイル変更は行っていない。