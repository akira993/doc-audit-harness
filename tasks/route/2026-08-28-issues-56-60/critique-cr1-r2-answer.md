結論: rev.2 はまだ実装非承認です。A3 は既存契約と両立しますが、Phase 0 再実行の制御、所見 #4、B6 の共通規則、scope-check に計画上の欠陥があります。

## (A) 計画自体の欠陥

### CR2-1 — A1 は再実行後の確認ゲートと Phase 0.5 の制御が曖昧

PLAN は「Phase 0 を最初から再実行」「Phase 0.5 は繰り返さない」とする。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:9)

しかし reopen が起きる時点では、最初の Phase 0.5 はまだ実行されていない。

- mdq 確認ゲート: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:103)
- harness 質問と reopen: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:264)
- Phase 0.5 開始: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:280)

したがって `Phase 0.5 is not repeated` は、「再実行対象に含めないが、その後一度実行する」と「実行しない」の両方に読める。後者では blocking な pre-flight が欠落し、checkpoint (c) 以降の EVIDENCE 連鎖も欠ける。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:57)

また、Phase 0 を丸ごと戻るなら mdq 確認ゲートも再評価される。同じ監査中に二度質問するのか、最初の承認を引き継ぐのかが明記されていない。probe の冪等性は利用者確認の重複を解決しない。

推奨: 固定文を「新 run で確認ゲートを含む Phase 0 を先頭から再評価し、必要なら新 run の判断として再質問・記録した後、Phase 0.5 をちょうど一度実行する」と明記する。

### CR2-2 — 所見 #4 は対応不十分で、fresh run に虚偽の表示が残る

PLAN は書き込み失敗時の警告を報告へ転記するが、状態行の `state unknown after resume` は維持する。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:14)

fresh run でも `codexReviewState` の記録に失敗すれば、次の経路になる。

1. 書き込み失敗は warning だけで続行する。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:628)
2. rebind の `reviewState` は `null` になる。
3. `state unknown after resume` を表示する。[SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:751)

警告を添えても「再開後」という事実誤認は直らない。さらに警告は保存されず、モデルが以前の標準出力を報告へ転記する規約だけなので、会話圧縮後の決定性もない。公開文書も誤った文言を固定している。[ADOPTION.md](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.md:271)

推奨: 7行の unknown 文言を `state unknown (probe record unavailable)` のような fresh/resumed 共通表現へ変更し、公開文書と契約テストも同時更新する。

### CR2-3 — C8 は `enabled:false` と不正な bin の優先順位を未定義に戻す

既存契約は `enabled:false` を bin 検証より先に確定する。

- 前版 PLAN の評価順序: [PLAN.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md:47)
- codegraph: [codegraph-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codegraph-probe.sh:38)
- graphify: [graphify-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/graphify-probe.sh:42)
- CocoIndex: [cocoindex-probe.sh](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/cocoindex-probe.sh:44)
- 既存複合テスト: [test_codegraph_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:177) [test_graphify_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_graphify_probe.py:184) [test_cocoindex_probe.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_cocoindex_probe.py:194)

rev.2 は「制御文字を含む bin は invalid-config」とするが、`enabled:false` の例外を明記していない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:22)

実装位置により次の二つに分かれる。

- bin 検査を先にすると、従来の `disabled-by-config` が `invalid-config` に変わる。
- 現行順序を維持すると、`enabled:false, bin:"a\nb"` は Python が複数行を出し、Bash が `bin` を `a` に切り詰めて報告する。

推奨: `enabled:false` を先勝ちのまま維持し、その分岐の bin が空・非文字列・対象制御文字入りなら出力上の bin を既定名へ正規化すると固定する。

### CR2-4 — B6 の「各表で invalid-config が先頭」は計画内容と一致しない

PLAN は共通規則として「各 status-line table の invalid-config bullet は先頭」と書く一方、移動対象を mdq・context-mode・ax の3表だけに限定している。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:17)

graph 3表は現在も次の順序である。

1. unknown
2. not-configured
3. invalid-config

根拠:

- symbol-graph: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:770)
- doc-graph: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:779)
- semantic-search: [SKILL.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:789)

DoD も3表しか順序検査しないため、虚偽の共通規則でも green になる。なお、mdq を先頭へ移すこと自体は、既存 S1a の「`MDQ_AVAILABLE false` より前」という検査と矛盾しない。[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:74)

推奨: 共通規則どおり、invalid-config を持つ全 status table でそれを先頭へ移し、全表を同じ方法で順序検査する。

### CR2-5 — DoD (7) は計画記載どおり実行すると正しい実装でも必ず失敗する

`scope-check.py` の比較開始点は、環境変数がなければ `dfdb8a9` である。[scope-check.py](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/scope-check.py:11)

一方、rev.2 の実行式は `BASE_COMMIT` を渡していない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:71)

実測:

```text
SCOPE_COMMIT=b6ee986 BOSS_COMMIT=b6ee986 python3 .../scope-check.py
exit 1
```

PR #61 ですでに変更済みの `docs/ADOPTION*.md`、`probe-record.py`、`mdq-index.sh` など17ファイルを越境として誤検出した。

比較開始点を明示すると成功した。

```text
BASE_COMMIT=ef995f0 SCOPE_COMMIT=b6ee986 BOSS_COMMIT=b6ee986 python3 .../scope-check.py
scope-clean
```

推奨: DoD (7) と §8 の実行式に `BASE_COMMIT=ef995f0` を固定して渡す。

## (B) worker 指示で吸収できる細部

### CR2-6 — A1 のテストは文言の配置・出現回数・制御順序を証明しない

DoD (1) は A1 の固定文が存在することしか要求していない。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:49)

固定文が、

- `RUNID/RUN_DIR/EVIDENCE` 更新前にある
- reopen 失敗検査より前にある
- 別段落にも重複している
- Phase 0.5 を飛ばす位置にある

場合でも通り得る。既存テストも Phase 0 を見出しで切り出して `assertIn` する形式が中心である。[test_v014_contracts.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v014_contracts.py:50)

推奨: harness 段落内で固定文を `count == 1` とし、reopen 成功確認後、Phase 0.5 見出し前という順序を assert する。

### CR2-7 — A3 は矛盾しないが、正規化から rebind までのテストがない

A3 の正規化は validator と一致する。

- unavailable: `healthy:null`
- available: `healthy` は bool
- `probe-error` は両 availability で許可

根拠: [probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:93)

実測:

```text
available:false, healthy:null, status:not-installed  -> ACCEPT
available:true, healthy:false, status:probe-error    -> ACCEPT
available:false, healthy:false, status:not-installed -> REJECT
```

したがって既存の `bad_context` 期待とは矛盾しない。[test_probe_record.py](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_probe_record.py:94)

ただし DoD (1) は SKILL の説明文しか検査しない。`make_rebind()` は保存値を無加工で返すため、合成側が誤ればそのまま表示へ到達する。[probe-record.py](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:272)

推奨: 正規化後の2形を書き込み、`rebind.context-mode` の完全一致を検査する。

### CR2-8 — C8 のテストは要求した制御文字集合と空白互換を網羅しない

実装要求は U+0000〜U+001F と U+007F の33文字だが、DoD は NUL・LF・TAB の3文字だけである。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:22)

CR、ESC、VT、FF、DEL を許す誤実装でも通る。また「空白入りパスは許容」という正の契約に fixture がない。現行3テストの `binpath` は通常の一時ディレクトリで、空白入りを明示していない。

`config-schema.md` も単に「制御文字」と書くと、実装対象の ASCII 範囲より広く読める。[config-schema.md](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/references/config-schema.md:37)

推奨: 33文字を全走査する拒否テストと、内部スペースを含む実行ファイルが起動され bin 値も完全一致する正例を3 probe に追加する。

### CR2-9 — DoD (4) は cleanup されない別形の mkdtemp を見逃す

検査は完全一致文字列 `mkdtemp()` の件数だけを見る。[PLAN-cr1.md](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-28-issues-56-60/PLAN-cr1.md:52)

例えば次は cleanup を追加していないのに通る。

```python
tempfile.mkdtemp(prefix="probe-")
```

つまり目的である「一時ディレクトリを確実に片付ける」と検査対象が一致していない。

推奨: 対象4ファイルで `mkdtemp` という識別子自体が0件であることを検査する。

## DoD の判別力

| DoD | 判定 | 理由 |
|---|---|---|
| (1) | 不十分 | A1/A3/A4/A5 の文言は確認するが、Phase 0 の制御順、確認の再評価、正規化値、warning の保持を実行検査しない。 |
| (2) | 有効 | 現行 ASCII escape の1行性を U+0085/U+2028/U+2029でも守る回帰検査として妥当。 |
| (3) | 不十分 | 33文字中3文字のみ。`enabled:false` 複合形と空白入りパスがない。 |
| (4) | 不十分 | 引数付き `mkdtemp` へ置き換えた誤実装が通る。 |
| (5) | 有効 | unittest の終了値を保存しており、前版の失敗隠蔽は解消済み。 |
| (6) | 単独では不十分 | 追跡済み禁止差分だけ。未追跡は (7) が正しく動くことに依存する。 |
| (7) | 無効 | `BASE_COMMIT` 欠落により正しい状態でも実測 exit 1。 |

## 最終区分

計画を直してから実装すべき点:

1. CR2-1: Phase 0 再実行、確認ゲート、Phase 0.5 一回の順序を確定する。
2. CR2-2: fresh/resumed 共通の正しい unknown 文言へ改める。
3. CR2-3: `enabled:false` と制御文字 bin の優先順位・出力値を固定する。
4. CR2-4: B6 の共通規則と全 status table を一致させる。
5. CR2-5: scope-check の比較開始点を `ef995f0` にする。

worker 指示で吸収できる細部:

- CR2-6: A1 の位置・回数検査
- CR2-7: A3 の rebind 完全一致検査
- CR2-8: 制御文字全件・空白入りパス検査
- CR2-9: cleanup 検査の対象拡張

以上により、rev.2 での実装承認はできません。