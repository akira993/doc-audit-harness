# `docaudit` を新しいプロジェクトに導入する

docaudit ハーネスを一度インストールし、任意のリポジトリをオンボードするための実践的な
エンドツーエンドガイド。5 分のクイックスタートから、config リファレンス、impact-map の
設計手法、verdict/anchor ライフサイクル、実運用で得た落とし穴までを網羅する。

> 🌐 English version: [ADOPTION.md](ADOPTION.md)

> **docaudit は原則 report-only（報告専用）。** 変更内容を、それを説明するドキュメントへマッピング
> し、検証し、`/security-review` を実行し、`/code-review` はユーザー実行を提案して
> （モデルからは起動できない）、単一の
> **CONSISTENT / NEEDS FIX / REFUSED** verdict を出す。唯一の文書編集例外は、pre-flight の
> FAIL に対して利用者が明示的に「修正して監査」を選んだ場合である。`fix-scope.py` が承認済みの
> 文書パスだけに制限し、非対話実行では編集しない。

---

## TL;DR — 5 分の最短経路

```bash
# 1) 一度だけグローバルにインストール（skills-dir プラグイン）
cp -R /path/to/doc-audit-harness ~/.claude/skills/docaudit
#    Claude Code を新規セッションで起動（または現セッションで /reload-plugins）
#    確認:  claude plugin list   → "docaudit@skills-dir  ✔ loaded"

# 2) 対象 repo で config をブートストラップ（対話式: 提案 → 承認 → 書き込み）
cd ~/code/my-project
/docaudit:init
#    提案された .claude/doc-audit.json をレビューしてコミット

# 3) 初回監査（全コーパス）。report-only → 指摘を外科的に修正。
/docaudit:audit --full
#    CONSISTENT 判定で .claude/state/last-doc-audit.json を生成 — これをコミット

# 4) 以降は単に:
/docaudit:audit
#    incremental: anchor 以降の変更で影響を受けたドキュメントのみ
```

以下はこの 4 ステップの詳細。

---

## 1. メンタルモデル — docaudit は実際に何をするか

docaudit は、多くのドキュメントツールに欠けているレイヤを足す:
**「前回のクリーンな監査以降に変わったコード/設定に対して、いま陳腐化・誤りになっている
ドキュメントはどれか？」** これを各監査で 5 つの phase を回して実現する:

| Phase | 内容 | スクリプト / 仕組み |
|------:|------|---------------------|
| 1 | **Baseline + diff** — anchor を読み、それ以降の変更集合（merge-base diff + 未コミット + 未追跡）を `diffGlobs` で絞って算出。anchor が無ければ full モード。 | `compute-baseline.sh` |
| 2 | **Impact resolution** — 変更ファイル → 影響ドキュメント（明示 `impactMap` ∪ heuristic）、`ssotSources` の再検証対象、`truncated` フラグを解決。 | `resolve-impact.py` |
| 3 | **Change-impact verification** — 影響ドキュメント 1 件ごとに verifier が *「このドキュメントは変更後のソースとまだ整合しているか？」* を敵対的に検証（PASS/WARN/FAIL）。 | 既定は Workflow fan-out、opt-in で `codex-dispatch.py` backend |
| 4 | **既存レイヤ + reviews** — プロジェクト固有のドキュメントチェック（または組込み generic fallback）、boundary コマンド、続いて `/security-review` を実行し、`/code-review` はモデルから起動できないためユーザー実行を提案。 | 委譲コマンド / `generic-layers.py` |
| 5 | **Gate + report + anchor** — 単一 verdict に集約し、run lock を保持したままレポートを書き、（CONSISTENT のときのみ）anchor を更新。 | `write-template.py` + `decide-verdict.py` |

頭に入れておくべき性質:

- **report-only。** どの phase も既存ドキュメントを編集しない。指摘は提案。
- **anchor ベースの incremental。** anchor（`.claude/state/last-doc-audit.json`）は
  *「ドキュメント集合は commit X 時点で CONSISTENT と検証済み」* を記録する。以降の監査は X からの差分。
- **verdict 規則:** **FAIL** が 1 件でも ⇒ NEEDS FIX（anchor は更新しない）。
  **WARN は CONSISTENT を妨げない**（警告は報告するが許容。anchor は「FAIL ゼロ」を意味する）。
- format/existence/semantic レイヤには **2 つのカバレッジ戦略**: プロジェクト固有のドキュメント
  コマンドへ *委譲* する（リッチ・プロジェクト固有）か、組込みの *generic* レイヤに
  *fallback* する（ポータブル・意図的に最小限）。§7 参照。

---

## 2. 前提

| 必要なもの | 理由 | 必須? |
|------------|------|-------|
| [Claude Code](https://code.claude.com/docs) | `/docaudit:*` スキルを実行 | はい |
| 監査ルートが **git リポジトリ** であること | エンジンは git で diff を取る | はい（subdir は §10 参照） |
| [Python 3](https://www.python.org/)（標準ライブラリのみ） | エンジンのスクリプト。`pip install` 不要 | はい |
| [`git`](https://git-scm.com/) | diff/anchor | はい |
| [`/code-review`, `/security-review`](https://code.claude.com/docs) | Claude Code 組込みの review スキル（Phase 4）。`/security-review` は監査で実行し、`/code-review` はユーザー実行のみ | 任意 — `/security-review` は利用可能なら実行、`/code-review` はユーザーに提案（モデルからは起動不可） |
| [`markdown-query` (mdq)](https://github.com/dahatake/skills) | Phase 0 で repo 全体を索引 + Phase 3 でチャンク読取り（大きい doc で ~90%+ 削減、upstream ベンチ 97–99%） | 任意 — 在れば自動使用（conditional-force）、非搭載で grep |
| [`context-mode`](https://github.com/mksglu/context-mode) | Phase 1 の git diff と Phase 4 の `/code-review`・`/security-review` 出力をサンドボックスで処理（要約だけが context に入る） | 任意 — `ctx_*` ツールが在れば自動使用（conditional-force）、無ければ全文読取り |
| [`ax`](https://ax.yusuke.run/) | Phase 3: doc-impact-verifier がドキュメントの外部 URL 依存の主張を read-only・GET-only の fetch で照合できるようにする（静的 HTML のみ — JS レンダリングの SPA は非対応） | 任意 — 導入済みなら自動使用（conditional-force）、無ければ外部 URL の主張は未検証のまま |
| [`codex`](https://github.com/openai/codex)（`@openai/codex` CLI） | 任意の Phase-3 文書別 backend と Phase 4 の第4敵対的レビュー。どちらも `codex exec -s read-only` | 任意 — Phase 3 は `phase3Backend:"codex"` の明示指定が必要。Phase 4 review は conditional-force。**完走した `critical`/`high` review 所見は verdict をブロックし得る**（下記参照） |
| [`codegraph`](https://github.com/colbymchenry/codegraph) | Phase 3: doc-impact-verifier が変更ファイル自身のシンボルに依存する主張を read-only の `codegraph impact`/`node` で照合できるようにする | 任意 — `symbolGraph` キーが存在し、無効化されておらず、tool が導入済みの場合に限り使用。`ax` 同様に純粋な補助情報 |
| [`graphify`](https://github.com/Graphify-Labs/graphify) | Phase 2: `mapGapCandidates` へのグラフ隣接ベースの第二候補源（provenance `graphify`） | 任意 — `docGraph` キーが存在し、無効化されておらず、tool が導入済みの場合に限り使用。無ければ `mapGapCandidates` は token heuristic のみ |
| [CocoIndex](https://github.com/cocoindex-io/cocoindex-code)（`ccc`） | Phase 2: `mapGapCandidates` への意味検索ベースの第三候補源（provenance `semantic`） | 任意 — `semanticSearch` キーが存在し、無効化されておらず、tool が導入済みで `.cocoindex_code/settings.yml` がある場合に限り使用。**docaudit 自身は `ccc init` を絶対に実行しない**（下記参照） |
| [Serena](https://github.com/oraios/serena) (MCP) | `init` 時の code↔doc 発見をリッチ化 | 任意 — grep/heuristic に fallback |
| プロジェクトのドキュメントツール（`/check-docs`, `doc-lint` …） | 委譲で Phase 4 をリッチ化 | 任意 — 無ければ generic fallback |
| [`skill-creator`](https://github.com/anthropics/skills) / [`superpowers:writing-skills`](https://github.com/obra/superpowers) | `--scaffold` のレイヤスキルの生成・作り込み | 任意 — `/docaudit:init --scaffold` 使用時のみ |

エンジンは設計上 **MCP・サーバー非依存**。任意項目はどれも、有用な監査を得るのに必須ではない。なお `mdq` は導入済みなら自動でトークン最適化読取りに使われ（conditional-force）、無ければ grep に degrade する。各 audit は **mdq 状態行**を出力する: mdq 未導入なら 💡 導入を促し、導入済みなのに索引が未発火（`empty-index` / `search-broken` / `probe-error`）なら ⚠ 非ブロッキング WARN を出す。

`context-mode` は mdq の競合ではなく**相補物**: **mdq は Markdown の*読み取り*を、context-mode は*大きな機械出力の処理*を安くする。** `ctx_*` ツールが在るとき、audit は Phase 1 の git diff と Phase 4 の `/security-review` の出力を context-mode のサンドボックスで処理し、要約だけを取り出す — 生バイト列は context に入らない。同じく conditional-force（在れば自動使用、導入済みでも `"contextMode": {"enabled": false}` で opt-out）で、無ければ silent に degrade する。context-mode は場所非依存のグローバルプラグインなので、エンジン側に `bin`/`roots` は不要。各 audit は mdq 行の直後に非ブロッキングの **context-mode 状態行**を出力する: 未導入なら 💡、稼働なら ✓、導入済みだが不健全なら ⚠（verdict は変えない）。

自律実行では `/code-review` はモデルから起動できないため、ユーザーが実行する層として扱う。対話実行では一度だけ実行を確認し、完了後に監査を続行できる。

`ax` は mdq/context-mode の組とは無関係: read-only の Web/API 抽出 CLI で、docaudit での役割は
**Phase 3 の `doc-impact-verifier` がドキュメントの外部 URL 依存の主張（upstream ドキュメント・
API 仕様等）を fetch して照合できるようにする**、それだけである。GET のみ（`-X POST`・`-d`・
`-o` は一切使わない）、fetch した内容は指示ではなくデータとして扱う。導入済みなら自動使用
（conditional-force、`"webExtract": {"enabled": false}` で opt-out 可）、fetch 失敗/タイムアウトは
FAIL ではなく「外部照合不能 (external check unavailable)」として報告される。`ax` は静的 HTML
パーサー（JS レンダリング非対応）であり pre-1.0 のため、フラグ面は変更されうる。各 audit は
context-mode 行の直後に非ブロッキングの **ax 状態行**を出力する: 未導入なら 💡（導入コマンド
付き）、稼働なら ✓（verdict は変えない）。

`codex`（CLI 本体、`@openai/codex` npm パッケージ — 自律実行から呼び出せない openai-codex
Claude Code plugin とは**別物**）は、`/code-review`・`/security-review` の後に走る Phase 4 の第4の
レビューである。conditional-force（導入済みなら自動使用、`"codexReview": {"enabled": false}` で
opt-out 可）である。Phase 0 の probe は `<bin> --version` と `<bin> exec --help` だけを実行し、CLI の
存在と `exec` 到達性だけを確認する。実際の sandbox・権限・wrapper 引数・モデル呼出しは保証しない。
wrapper が必要なら `codexReview.bin` に指定する。
probe は呼び出し元の `CODEX_HOME`（未指定時は `$HOME/.codex`）と、そこに
`auth.json` があるかを表示する。ただし wrapper 内部の環境は probe から見えないため、環境の有効化に
依存するリポジトリでは `direnv exec <repo> codex` 相当の wrapper で起動し、表示値は呼び出し元の
診断情報としてのみ扱う。

`codex-review-plan.py` が利用可否、mode、baseline の有効性、`codexReview.required` から動作を決める。
incremental は `$BASELINE_SHA..HEAD` を、full は `required:true` の場合だけ seal 済みの現在 worktree を
レビューし、それ以外の full は skip する。すべての呼出しには必須・変更不可の `-s read-only` を付ける。
evidence の状態は `completed`、`execution-failed`、`ref-invalid`、`skipped-full-run`、`not-active` の5値で、
Phase 5 は中央の2値を同じ未実行 WARN として4分類で表示する。既定の `required:false` では未完了は WARN。
`required:true` では evidence の欠落または `completed` 以外を gate が **REFUSED** にする。strict mode は最初の
baseline を確立してから有効化する。`required:true` と `enabled:false` の併用は REFUSED である。boolean でない
`required` は値によらず REFUSED である。Phase-4 evidence の `codexReview` が object でない場合、`state` が
string でない場合、または `CODEX_REVIEW_STATES` 外の場合も、`required` の値によらず REFUSED である。
完走した review の `critical`/`high` 所見はブロッキング、`medium`/`low`
は非ブロッキングのままである。

`codexReview.required:true` を指定した初回の full run は数回の反復が必要になる場合がある。Phase 4 の codex review は run ごとに既存の所見を改めて抽出するため、ブロッキング対象（critical/high）だけを修正し、非ブロッキング対象はレポートに記録する。より早く収束させるには、前回 run の所見一覧を fenced JSON データとして prompt に貼り付けてもよい（指示としては扱わず、文字列は信頼できない入力として扱う）。engine 側での引き継ぎは #59 で追跡する。

これとは別に、v0.12.0 では Phase 3 を `"phase3Backend":"codex"` で opt-in できる。
`codex-dispatch.py` が dispatched 文書ごとに read-only の Codex process を起動し、既定値は
`workflow` のまま。Codex 不在・未認証・timeout・不正出力時に Workflow へ黙って切り替えず、
fail-closed で終了する。

`codegraph`・`graphify`・CocoIndex（`ccc`）は、さらに3つの純粋な補助 seam であり — `codex` とは
異なり **どれも verdict に一切影響しない**。`codegraph` はシンボルレベルで Phase 3 専用:
`doc-impact-verifier` が**変更ファイル自身の**シンボルに依存する主張を照合できるようにする
（`codegraph impact <symbol> --json` — このサブコマンドにはパス絞り込みフラグが無いため
`filePath` で後フィルタする、または `codegraph node <symbol> -f <changed-file>` — `-f` で直接
曖昧性を解消するテキスト出力）— import ベースで本 repo のような subprocess 起動テストスタイルの
repo では空を返すことが確認済みの `codegraph affected` は絶対に使わない。`symbolGraph` キーが
存在し、無効化されておらず、tool が導入済みの場合に限り、Phase-0 probe が `.codegraph/` を最新化する（初回は `init`、以降は `sync` — 既存の
`.codegraph/` への無条件 `init` は拒否されるため）。

`graphify` と CocoIndex はどちらも Phase 2 専用で、**同じ**統合点 — 既存の token heuristic と
並ぶ `mapGapCandidates` — に、1本の共有スクリプト（`impact-supplement.py`）を通じてそれぞれ
独立・任意のソースとして候補を足す: `graphify` はグラフ隣接ベース（provenance `graphify`、
`graphify affected`/`graphify query --budget` の確認済み固定フォーマットのテキスト出力を
パース — どちらも `--json` 非対応）、CocoIndex はローカル埋め込みの意味検索ベース
（provenance `semantic`、`ccc search --json` から `score >= minScore`（既定 `0.4`）を満たす
ものだけを採用 — `ccc search` には**足切りが無い**ことが確認済みで、無関係なクエリでも
exit 0・limit 件を、目に見えて低いスコア帯で返す）。どちらもキーが存在し、無効化されておらず、tool が導入済みの場合に限り使用され、どちらも
`resolve-impact.py` 自身の cap 適用後に残った枠にのみ、優先順位 `mapped` ≥ `regression` ≥ `heuristic` ≥
`graphify` ≥ `semantic` を厳守してマージする — 既存候補を1件たりとも押し出すことはない
（Issue #8 の再発防止）。**CocoIndex について最も重要な規則: docaudit 自身は `ccc init` を
絶対に実行しない** — `ccc init` は対象 repo の `.gitignore` に `/.cocoindex_code/` を自動追記する
（実機確認済みの副作用）。report-only な audit フェーズがこの書き込みを実行中に誘発してはならない
ため、`.cocoindex_code/settings.yml` 不在は「未導入」とは別の、静かな `not-initialized` degrade 状態として
扱う。初期化は `/docaudit:init` の中でのみ、`.gitignore` への書き込みを明示したユーザー承認を
経て行われる。probe は `ccc index` の前後で `.gitignore` を比較し、変化した場合は
`gitignore-modified` を報告するだけで復元しない。

impact provenance は、`impactMap` のみなら `mapped`、現在の内容ハッシュが履歴と一致する前回 FAIL の再検証なら `regression`（impactMap-gap 候補ではない）、heuristic のみなら `heuristic`、両方が同じ
文書へ到達した場合は `both`、任意の補完元なら `graphify` / `semantic`、anchor が無いか明示的な
`--full` の全文書 run では各 `docGlobs` 文書が `full` になる。

健全な設定では、選択された文書の大半が `mapped` で到達し、token `heuristic` はまだ
`impactMap` に昇格していない結び付きの残差になる。監査コストの主因は
`maxImpactedDocs` ではなく anchor の古さである。このリポジトリの実測では、古い anchor
で約 92 文書（約 3.6M tokens）、単一 commit 窓の中央値で約 18 文書だった。

`regressionRecheck.enabled` は opt-in である。現在の内容ハッシュが履歴と一致する前回 FAIL を provenance `regression` として
追加するもので、`impactMap` の不足候補ではない。単発の検証結果にはブレがあるため、報告された指摘
N 件を直して再実行すれば `CONSISTENT` になるとは保証されない。gate は文書内容・契約版・backend が
同じで verdict が変わった件数を `verdictFlipsUnchangedContent` に出す。文書内容が不変でもコード側の
変更で verdict が正当に変わり得る。`verdictFlipsUnchangedContentSameChangeSet` は同じ change set でも
変わった M 件の部分集合で、純粋なブレの下限である。1件の欠陥を見つけたら、報告箇所だけでなく、
同じ欠陥クラスを対象文書全体で横断的に掃除することを推奨する。

各 audit は codex-review 行の直後にさらに3つの非ブロッキング状態行を出力する:
**symbol-graph**（💡 未設定 / ⚠ 不正 / 💡 未導入 / ✓ 稼働 / ⚠ 索引構築失敗）、**doc-graph**（💡 未設定 / ⚠ 不正 / 💡 未導入 / ✓ 稼働 +
`graphify-out/` gitignore 済み / ⚠ 稼働だが `graphify-out/` が gitignore されていない —
追加せよ）、**semanticSearch**（💡 未設定 / ⚠ 不正 / 💡 未導入-未インストール / 💡 未導入-未初期化（`/docaudit:init`
への案内付き） / ✓ 稼働（設定済みの `minScore` を明記） / ⚠ 索引更新失敗 / ⚠ gitignore-modified）— いずれも verdict を
変えない。

---

## 3. インストール

### 3a. グローバル（推奨）— "skills-dir" プラグイン

```bash
cp -R /path/to/doc-audit-harness ~/.claude/skills/docaudit
# 任意: コピーから開発用ゴミを除去
rm -rf ~/.claude/skills/docaudit/.git ~/.claude/skills/docaudit/tests
```

**`~/.claude/skills/<name>/`** 配下で `.claude-plugin/plugin.json` を含むディレクトリは、
次セッションで `<name>@skills-dir` として自動ロードされ、**すべての**プロジェクトでスキル +
エージェントを公開する。

> ⚠️ **`~/.claude/plugins/` ではなく `~/.claude/skills/` を使う。** `~/.claude/plugins/` は
> `installed_plugins.json` が追跡する marketplace cache 領域であり、そこへ素のコピーを置いても
> **自動検出されない**。（インストールの落とし穴 No.1）

**確認:**
```bash
claude plugin list                 # → docaudit@skills-dir  Version 0.14.0  Scope: user  ✔ loaded
claude plugin details docaudit     # コンポーネント一覧 + token コスト
```
既に起動中のセッションでは **`/reload-plugins`** を実行すると slash コマンドが今すぐ登録される
（さもなくば次セッションで現れる）。

### 3b. 開発 / セッション限定（インストールなし）

```bash
cd ~/code/my-project
claude --plugin-dir /path/to/doc-audit-harness   # このセッションのみロード
```

### 3c. 既存のグローバルインストールを更新する

グローバルのコピーは **スナップショット** — ソース repo を編集しても **反映されない**。
新版を pull したら再 sync する:
```bash
cp -R /path/to/doc-audit-harness/. ~/.claude/skills/docaudit/
# 変わったのがスクリプトだけなら:
cp /path/to/doc-audit-harness/skills/audit/scripts/*.py ~/.claude/skills/docaudit/skills/audit/scripts/
```

**v0.12.0 の挙動変更:** 決定論的 gate が run lock を保持したままレポートを書く。orchestrator は
先に placeholder 付き本文を `write-template.py` へ渡し、次回 open では前回レポートの
`pending`・`failed`・`written-durability-unknown` が `previousReportStatus` として表面化される。
Phase 3 には明示的かつ fail-closed な `phase3Backend:"codex"` opt-in も追加された。レポートの
ファイル名と front matter の日付は run ID 由来の **UTC 基準**なので、日付境界ではローカル日付と
異なる場合がある。

**v0.13.2 の挙動変更:** `docGlobs` を省略した場合、pre-flight fix の分類は `["docs/**/*.md","*.md"]` を既定とする。`CLAUDE.md` と `AGENTS.md` は大文字小文字を区別せず常に拒否される。
`docGraph` / `semanticSearch` / `symbolGraph` のキーが無い場合は `not-configured` を報告し tool を一切起動しない。キーが不正な場合は `invalid-config` を報告する。
CocoIndex は `.cocoindex_code/settings.yml` が存在する場合のみ初期化済みとみなす。`ccc index` の実行中に `.gitignore` が変化した場合は `gitignore-modified` を報告し、監査は復元しない。
`seal-run.py` または `read-manifest.py` が失敗した場合は run を解放して停止する。`read-manifest.py` は未 seal の manifest を拒否する。
自動検出に頼っていた config は `/docaudit:init` でキーを追加するまで `not-configured` になる。

**v0.14.0 の挙動変更:** `indexing`、`contextMode`、`webExtract`、`codexReview` のキーでは、`enabled` は JSON の真偽値でなければなりません。`enabled:false` 以外の場合、`enabled` が真偽値でない、キーがオブジェクトでない（`null` を含む）、または `indexing`・`webExtract`・`codexReview` の `bin` が文字列でない、空、NUL を含むときは `invalid-config` を報告し、ツールを起動しません（キーが無い場合は従来どおり有効で、`bin` の非文字列値は変換されず、読めない設定は従来どおり Phase 0 より前に監査を停止します）。`indexing` キーが不正な場合は、未インストール時と同じく Phase 0 の mdq 確認ゲートが起動します。`codexReview.required:true` と不正な `codexReview` キーを組み合わせた場合は、codex を黙って実行せず `REFUSED` になります。Phase 0 の probe 結果は `$RUN_DIR/phase0-probes.json` に保存されます（表示専用で、verdict の入力にはなりません）。Phase 5 の状態行は初回実行でも再開実行でもその記録から描画され、記録が無いか読めない場合は「state unknown (probe record unavailable)」と表示されます。codex probe は呼び出し元の `CODEX_HOME` と、そこに `auth.json` があるかどうかを報告します（表示専用で、wrapper 自身の環境は観測されません）。`import-audit-scope.py` はリポジトリルート配下の絶対パスの `--config`／`--scope` を受け付けます（POSIX パスのみ）。

---

## 4. プロジェクトをオンボードする

### 4a. 自動 — `/docaudit:init`（推奨）

```bash
cd ~/code/my-project
/docaudit:init
```
実行内容:
1. repo を **inventory**（doc ディレクトリ、front-matter 規約、code ディレクトリ、既存
   ドキュメントツール、code→doc の「言及」、index ファイル）— grep/find ベースで決定論的。
2. **ローカルハーネスについて一度質問する。** 既存候補が無ければ `/check-docs` +
   `doc-lint` + `scripts/check-docs.py` を入れるか選ぶ。候補があれば、統合・調整・そのまま・
   新規導入から選ぶ。保存される状態は `installed`、`declined`、`integrated`、`adjusted`、
   `existing-untouched` の 5 つ。
3. `.claude/doc-audit.json` の提案を **ドラフト** し、各キーの 1 行根拠付きで提示。
4. **承認を待つ**（承認なしには書かない）。承認後に config を書き込む。
5. 初回監査へ誘導。

`init` は **追加のみ**: 新規ファイルを作るだけで、既存ドキュメントは編集しない。
`--scaffold` を付けるとプロジェクト固有のレイヤスキル雛形も生成する（§7）。config が既に
ある場合のハーネス操作は `--harness`、判断の聞き直しは `--reask`、変更されていない生成物だけの
更新は `--harness --refresh` を使う。`installed` を選んだら、config と次の 3 本をまとめて
コミットする: `.claude/commands/check-docs.md`、`.claude/skills/doc-lint/SKILL.md`、
`scripts/check-docs.py`。

変更されていない stamp 付きの 0.10.1、0.11.0、0.12.0、0.13.0、0.13.1、または 0.13.2 テンプレートは、
`/docaudit:init --harness --refresh` で 0.14.0 へ直接更新できる。利用者が変更したテンプレートは
そのまま残る。

> inventory は **実際に**ドキュメントが存在するディレクトリから `docGlobs` を導出するので、
> 非標準レイアウト（`guide/`、`vps/` … 配下の docs）にも対応する。symlink された doc ディレクトリ
> や `node_modules`/`.venv` は自動的に除外される。とはいえ提案はレビューすること — repo の
> 結合関係は grep よりあなたの方が詳しい。

### 4b. 手動 — `.claude/doc-audit.json` を自分で書く

`docs/examples/doc-audit.example.json` を `your-repo/.claude/doc-audit.json` にコピーして編集する。
スキーマは §5、impact map は §6 を参照。

---

## 5. config リファレンス — `.claude/doc-audit.json`

プロジェクトごとのアダプタ。**プロジェクト固有の知識はすべてここに置く。プラグインは
プロジェクト知識を一切同梱しない。**（正本スキーマ: `skills/audit/references/config-schema.md`）

この表は主要キーの抜粋である。完全な一覧は `skills/audit/references/config-schema.md` を参照すること。

| キー | 型 | 必須 | 意味 |
|------|----|----|------|
| `anchorPath` | string | はい | anchor 状態ファイルの repo 相対パス（慣習: `.claude/state/last-doc-audit.json`） |
| `diffGlobs` | string[] | はい | 変更集合を絞る path glob。`**` は `/` を跨ぐ、`*` は跨がない。 |
| `docGlobs` | string[] | いいえ | heuristic/generic スキャンでドキュメントとして扱うファイル（既定 `["docs/**/*.md","*.md"]`）。pre-flight fix path も同じ既定を使う。 |
| `impactMap` | object[] | はい | `{changed: path\|glob, impacts: [docPath,…], note?: string, source?: string}` — 中核（§6）。`source:"audit-scope"` は生成物。`[]` で開始してもよい。 |
| `auditScope` | object | いいえ | importer が書く `{path,sha256,importedAt,rules}`。手編集しない。 |
| `ssotSources` | object[] | いいえ | `{name, value?, liveSource, docsThatCite: [path\|path:line,…]}` — ドキュメント横断の値整合 |
| `docAuditCommands` | object | いいえ | `{format, existence, semantic}` — Phase 4 を委譲する slash コマンド/スキル名。省略 ⇒ generic fallback。 |
| `boundaryCommand` | string | いいえ | プロジェクト境界 / 禁止パターンチェックの shell コマンド（例 `make check-boundary`） |
| `reviewCommands` | object | いいえ | `{code, security}` — effort 込みの review コマンド文字列（例 `"/code-review high"`, `"/security-review"`） |
| `reportPath` | string | いいえ | レポート出力テンプレート。`<YYYY-MM-DD>` と `[_NN]` 衝突サフィックスをサポート |
| `maxImpactedDocs` | number | いいえ | 影響ドキュメント数の上限（既定 200）。超過で `truncated` をセット（必ず表面化、暗黙に捨てない） |
| `heuristics` | object | いいえ | `{minIdentifierLength:int, excludeBasenames:[string,…], saturationWarnRatio:number=0.5, excludeDocPathTokens:bool=false}` — heuristic の recall ノイズを調整。`0` で飽和 WARN を無効化。 |
| `regressionRecheck` | object | いいえ | `{enabled:bool=false}` — 内容不変の直近 FAIL を再検証する opt-in。 |
| `frontMatterFields` | string[] | いいえ | generic `format` レイヤが全ドキュメントに要求する front-matter フィールド（欠落で WARN）。省略でスキップ |
| `layerGlobs` | object | いいえ | `format`・`existence`・`semantic` ごとの generic 除外設定。 |
| `frontMatterOverrides` | object[] | いいえ | glob の一致順で選ぶ generic `format` フィールド上書き。 |
| `indexFiles` | string[] | いいえ | generic `semantic` レイヤの orphan 検出のリンク根（既定: doc ツリー内の任意の `README.md`） |
| `auditReportsInCorpus` | boolean | いいえ | literal `true` の場合のみ、一致する監査レポートを corpus scan に残す。 |
| `harness` | object | いいえ | `{state,decidedAt,engineVersion}`。state は上記 5 状態のいずれか。未設定は互換用の `unset`。 |
| `verdictCache` | object | いいえ | `{enabled:true,minConsecutivePasses:2}`。連続 PASS 数は 2..10。範囲外なら WARN とともに cache 無効。 |
| `phase3Backend` | string | いいえ | `"workflow"`（既定）または `"codex"`。不正値は run の seal 時に拒否。 |
| `phase3CodexTimeoutSeconds` | number | いいえ | Codex 文書別実行 timeout。整数 60..3600、既定 600。Codex Phase-3 backend のみで使用。 |
| `models` | object | いいえ | ネストした `{light:{enabled,maxChanged,maxImpacted,maxDiffLines,maxDiffBytes,sensitiveTokens}}`。light run の決定論的な上限。 |
| `codexReview` | object | いいえ | `{enabled,required:bool=false,bin,model?,timeoutMs?}`。`required:true` は未完了 review を REFUSED にする。baseline 確立後に有効化する。 |
| `digestExclude` | string[] | いいえ | glob ではない literal path のみであり、受理された各プレフィックス自体とその配下 path を許可する（末尾 `/` は正規化で除かれる）。`*`、`?`、`[` を含む値は `tree-digest.py` が拒否し、`seal-run.py` が失敗（exit 2）して run は seal されない。`digestExclude` で受理されるプレフィックス: `.claude/state`, `.claude/worktrees`, `.mdq`, `.codegraph`, `graphify-out`, `.cocoindex_code`. |
| `protectedGlobs` | string[] | いいえ | pre-flight 修正を禁止する追加パス。組込みの ADR/decisions/logs/`.claude` と、大文字小文字を区別しない `CLAUDE.md`/`AGENTS.md` basename 保護は解除不可。 |

規則: `impacts` のエントリは **ドキュメントパスのみ** — 注釈は `note` に置く。`changed` は単一パス
または glob。glob はエンジン独自の意味論: `**`=`/` を含む任意、`*`=`/` を含まない任意、`?`=`/` 以外 1 文字。

最小構成は `anchorPath` + `diffGlobs` + `impactMap` のみ（`impactMap` は `[]` でもよく、育つまでは
heuristic に頼る）。

---

## 6. 良い `impactMap` を作る（中核）

### `audit-scope.json` がある場合

`audit-scope.json` が正本で、`source:"audit-scope"` の `impactMap` は生成物である。ずれ（drift）があると Phase 0 は停止する。`/docaudit:init --import-audit-scope` で復旧すること。run 間の import に `--accept-config` は不要であり、exit 6 は実行中の設定変更を拒否した場合だけである。実行中は lock により import が拒否される。`{"impact":"none"}` は生成対象から外すが、heuristic が文書を拾うことはある。

impact map こそが監査を *change-driven* にする。各エントリは
**「このソースパスが変わったら、これらのドキュメントを再チェックせよ」** を表す。

```json
{ "changed": "src/api/**", "impacts": ["docs/api-reference.md", "README.md"],
  "note": "public API surface documented in api-reference.md + README quickstart" }
```

**2 つのシグナルを UNION で結合:**
- **Mapped（精度）:** 明示 `impactMap` エントリ → 高信頼の結合。
- **Heuristic（再現性）:** 変更ファイルの basename/stem がドキュメント本文に現れれば、その
  ドキュメントを候補に追加し **`mapGapCandidate`** として表面化する — 実マッピングを足すヒント。
  heuristic は *追加* のみで、mapped ドキュメントを除外することはない。

**育て方:**
1. トップレベルの code/config ディレクトリと主要ファイルを列挙（`src/`, `scripts/`, `Makefile`,
   設定ファイル, schema/migration, IaC, CI）。
2. それぞれについて、何がそれを説明しているかをドキュメント中で grep して見つける。
3. 実在する結合に `{changed, impacts, note}` エントリを書く。小さく始める — heuristic +
   `mapGapCandidates` が残りを時間とともに明らかにする。
4. 各監査後、繰り返し出る `mapGapCandidates` を明示マッピングへ昇格させる。

**`ssotSources`** はドキュメント横断で繰り返される *値*（バージョン・IP・サイズ）向け。
**変更ファイル** が `docsThatCite` のいずれか、または `liveSource` のファイルであるとき再チェックを
立てる。ハーネスは値を **ドキュメント横断でテキスト比較** する（`liveSource` は **実行しない** —
サーバー/コマンドソースは手動 follow-up 用に記録するだけ）。URL の `liveSource`（http/https）も
同様に非対応 — 取得・検証は行われず、audit 時に警告が出るので値は手動で追跡すること。

---

## 7. 委譲 vs generic fallback（Phase 4）

- **プロジェクトに既にドキュメントツールがある場合**（例 `/check-docs`, `doc-lint`,
  `/review-docs`）は配線する:
  ```json
  "docAuditCommands": { "format": "/review-docs", "existence": "/check-docs", "semantic": "doc-lint" }
  ```
  監査は全ツリーでそれらに委譲する。名前どおりに正確に呼ぶ（`doc-lint` のような *スキル* は
  先頭スラッシュなし、*コマンド* は付ける）。
- **無い場合** は `docAuditCommands` を省略する。Phase 4 は組込みの `generic-layers.py` に
  fallback する — ポータブルなベースライン:
  - `format`: 相対リンク解決（壊れ ⇒ FAIL）+ 任意の `frontMatterFields`（欠落 ⇒ WARN）。
  - `existence`: backtick と bare ASCII path からの repo-path-token 解決
    （解決不能な具体的 backtick ファイル ⇒ FAIL、それ以外の解決不能 path ⇒ WARN）。
  - `semantic`: orphan 検出（どこからもリンクされないドキュメント ⇒ WARN）。
  generic ベースラインは固有ツールより **意図的に弱い**。
- **v0.10 ハーネスを `init` で導入した場合** は、pre-flight と Phase 4 で使う次の固定配線を
  書き込む:
  ```json
  "docAuditCommands": {
    "existence": "/check-docs --only existence",
    "format": "/check-docs --only format",
    "semantic": "doc-lint"
  }
  ```
  複製されたエンジンは `scripts/check-docs.py --format text --exit-code` にも対応し、機械処理可能な
  `SUMMARY` と `VERDICT` 行を出力する。
- **`/docaudit:init --scaffold`** は *プロジェクト固有* のレイヤスキル雛形をあなたの
  `.claude/skills/` に生成し、`docAuditCommands` をそれらに配線し、`skill-creator` /
  `writing-skills` で肉付けを助ける。オプトイン。より richで自前のチェックを持ちたいプロジェクト向け。

---

### Phase 3 の構造的盲点

**Phase 3 単独ではこれらを保証しない。** たとえばガイドが `.dev.vars` と書く一方で
`.env.example` と source は `.env.local` と書くような複数文書間の矛盾、src コメント・dotfile・
生成物ヘッダにある `X.md §N` 型参照、開発サーバーなど手順の前提条件を満たせるかどうかである。
Phase 4 の code/security review、codex review（incremental、または `codexReview.required` を伴う full）、
gate の sibling scan は横断的な補完層である。codex review のプロンプトもこの3観点を明示的に確認する。

---

## 8. 監査の実行 — verdict & anchor ライフサイクル

- **`/docaudit:audit --full`** — 全コーパスの深掘り監査。初回・大きな変更後・定期実行に使う。
  anchor が無いときは常に自動でこのモード。`docGlobs` の全文書を impacted とし、cache は無効。
- **`/docaudit:audit`** — incremental: anchor 以降の変更で影響を受けたドキュメントに絞る。
- **run 台帳と lock:** 監査の最初に `.claude/state/docaudit-run/<runid>/` を作り、隣の `lock` を
  排他的に作成する。TTL や自動奪取はない。古い lock は、停止だけを行う明示操作
  `/docaudit:audit --break-lock` で解除する。gate が保持中の lock は解除できない。
- **pre-flight（Phase 0.5）:** run を開いた後、baseline と seal より前に script-backed の稼働中
  ハーネスを全ツリーへ実行する。model-driven は `preflight.commands` に skip として記録し、Phase 4 で一度だけ実行する。FAIL 時は「修正して監査／修正せず続行／停止」から選ぶ。編集できるのは
  最初の選択だけで、`fix-scope.py` が承認済み文書へ限定する。非対話実行は FAIL を evidence に
  残すだけで編集しない。
- **seal 済み evidence:** orchestrator は SHA を含む 1 個の `EVIDENCE` を保持する。fan-out 前に
  `seal-run.py` が HEAD、変更集合全体の hash、worktree digest、解決済み Phase-3 backend を固定する。`decide-verdict.py` は
  evidence を各 1 回だけ読み、verifier の返却と割当パスを突き合わせ、history、last-run、anchor を
  書く唯一の処理になる。旧式の flat な `docaudit-run/` ファイルは無視する。
- **決定論的 cache:** `plan-dispatch.py` は、同じ文書内容・`changeSetSha`・契約版で、設定数
  （既定 2）の連続 PASS があり、backend も一致する文書だけ Phase 3 を省略する。backend 欄の無い
  旧 history は `workflow` とみなす。history が無い／壊れている場合は cold start。`--full` は
  常に cache を使わない。
- **run class:** `classify-run.py` が mode、件数、diff サイズ、機密パストークン、前回 verdict から
  `light` / `standard` を決める。Workflow の light は `doc-impact-verifier-light`（Haiku）、standard と
  全 retry は Sonnet。Codex Phase-3 backend は light=Luna、standard=Terra、effort は medium。
  Codex review も `codexReview.model` 未指定時は同じ既定値を使う。
- **verdict:** `FAIL` ⇒ **NEEDS FIX**（anchor は更新しない）。`WARN`/`PASS` のみ ⇒ **CONSISTENT**
  （anchor 更新）。evidence や状態を検証できなければ **REFUSED**。Phase-3 の verdict はそのまま使用する。
  CONSISTENT と NEEDS FIX の両方で、30 秒上限・non-blocking の `sibling-scan.py` が verifier 所見、
  Phase 4 title、変更集合の削除行から句を取り、status line で sibling 候補を報告する。
- **レポート:** `reportPath` 設定時、orchestrator は gate 前に完全な placeholder template を
  `write-template.py` へ渡す。gate は run lock を保持したまま置換・公開し、`reportPath`、固定 warning
  code、`reportStatus` を返す。次回 open は未解決の `pending`・`failed`・
  `written-durability-unknown` を報告する。レポート日付はローカル暦日ではなく run ID 由来の UTC。
- **anchor:** **CONSISTENT のときのみ**書かれ、現在の HEAD SHA を記録する。**コミットする**
  （慣習: `docs(audit): …` コミット）ことで baseline が共有され、squash merge も乗り越える。
  `sha` だけの旧 anchor と互換で、v0.10 は run/digest 情報を追加する。

Phase-4 severity の写像:

| severity | gate への効果 |
|---|---|
| `PASS` | `non-blocking` verdict をブロックせず受理する |
| `WARN` | `non-blocking` verdict をブロックせず受理する |
| `MEDIUM` | `non-blocking` verdict をブロックせず受理する |
| `LOW` | `non-blocking` verdict をブロックせず受理する |
| `INFO` | `non-blocking` verdict をブロックせず受理する |
| `FAIL` | `blocking` ブロッキング所見として扱う |
| `HIGH` | `blocking` ブロッキング所見として扱う |
| `CRITICAL` | `blocking` ブロッキング所見として扱う |
| 上記以外の値 | `REFUSED`（`unknown finding severity`） |

**正しい anchor の順序**（anchor が *整合した* 状態を記録するように）:
1. 指摘を修正して **コミット**。
2. `--full` を再実行。CONSISTENT になればエンジンが現在の SHA で anchor を書く。
3. **anchor（+ レポート）を別の meta コミット** としてコミット。

### v0.13.0 の互換性影響

- gate に provenance/audit-scope の整合性と strict Codex-review evidence に関する **REFUSED** 条件が加わった。
  manifest は `provenance` と `auditScopeSha` を、dispatch は `impactSha` を持つ。
- この版をまたぐ実行中 run は `--break-lock` で停止してから再実行する。Phase 3 と Phase 4 は seal 済み
  manifest を `read-manifest.py` 経由で読み、`codex-dispatch.py` は `--evidence` を必須とする。
- Phase 4 の Codex 分岐は決定論的な判定表を経由し、Phase 5 の Codex 行は4分類で表示する。`check-docs` には
  3つの正しさ修正がある。新しい `counts` と任意の `regressionRecheck`、`excludeDocPathTokens`、
  `codexReview.required`、`auditScope` は、既定で無効または不在の後方互換な追加である。

---

## 9. 初回監査プレイブック

実際のオンボードを反映したもの。初回 `--full` は本物のドリフトを見つけるはず — それが狙い。

1. `/docaudit:audit --full` を **実行**。`reportPath` のレポートを読む。
2. **すべての指摘を文脈で triage する — 生の件数を信用しない。** fenced code block 内の
   「broken link」は誤検出。歴史的な plan/log や「将来ロードマップ」節の中の
   「stale 予定/TODO」は陳腐化では *ない*。触る前に必ず検証する。
3. **本物の FAIL のみ外科的に修正** — 指摘が名指しした箇所だけを変える。ADR や歴史的ログを
   書き換えない（代わりに上書きの注記を追記）。隣接箇所を「整形」しない。
4. `--full` を **再実行**。verdict = **CONSISTENT** になるまで繰り返す。
5. **anchor を書いてコミット。** これで incremental に移行。
6. **WARN は別途 triage**（anchor は妨げなかった）: orphan ドキュメントを index に追加、前向きな
   「予定/future」表現が正当か（たいてい正当）を判断、将来の再フラグを抑えるよう config を調整（§11）。

---

## 10. 実運用で得た落とし穴（必読）

- **サブディレクトリのターゲットは git ルートではない。** *独立した git repo ではない*
  サブプロジェクトに docaudit を向けると、git は親 repo に解決し親相対のパスを返すため、
  サブディレクトリ相対の config と食い違い、**incremental/anchor の差分が壊れる**。対処は 2 つ:
  (a) **full-mode 専用**: サブディレクトリ自身のコンテンツに絞った config を書き、anchor を省略
  （毎回 `--full`）し、`_note` キーに制約を明記する。 (b) **親 repo の config にサブプロジェクトを
  畳み込む**（その doc glob + impact-map エントリを親側に足す）。小さなサブプロジェクトなら
  full-mode で十分。
- **symlink された doc ディレクトリは辿られない**（`os.walk(followlinks=False)`）。`docs/ → ../docs`
  の symlink はサブプロジェクトからはスキャンされない。symlink の *実体* を、その実 repo から監査する。
- **`node_modules`/`.venv`/`dist`/… は doc スキャンから prune される。**（古いビルドを使う場合は、
  vendored markdown を拾わないよう `docGlobs` を厳しく絞る。）
- **共通ファイル名での heuristic 過剰カウント。** 変更された `*/SKILL.md`, `*/README.md` などは、
  その basename トークンが多数のドキュメントに現れるため heuristic を氾濫させる。正しいのは mapped
  ドキュメント。ノイズの多い basename は `heuristics.excludeBasenames` に足すか
  `minIdentifierLength` を上げる。`truncated` は常に表面化される — 暗黙に捨てない。
- **前向きの表現は「stale」ではない。** ロードマップ・提案書・要件・歴史的な plan/spec/log
  ディレクトリ内の「予定 / future / TODO / 将来拡張」は正当。それらのディレクトリは stale-claim
  スキャンから除外する。heuristic を満たすためにロードマップ文面を書き換えない。
- **ADR とログは append-only。** 監査は report-only で、書き換えではなく *新規* ADR / 上書き注記を
  提案する。修正時もそれに従う。
- **`/security-audit` は存在しない** — 実コマンドは `/security-review`（ハーネスが正規化する）。
  `/code-review` は working diff に対して動作する。両者ともクリーンで同期済みのツリーでは
  **no-op**（保留 diff なし） — これは失敗ではなく想定どおり。
- **グローバルインストールはスナップショット** — ソース更新後は再 sync する（§3c）。
- **lock は自動で奪わない。** exit 4 は別 run が lock を所有している意味。holder を確認し、その
  run が確実に終了済みの場合だけ `/docaudit:audit --break-lock` を使う。この操作は lock を解除して
  停止するので、その後に監査をもう一度開始する。
- **config 変更は明示承認する。** run 中の `.claude/doc-audit.json` 変更を検知すると REFUSED になり、
  次の open は exit 6 になる。差分を確認し、承認した場合だけ `/docaudit:audit --accept-config` を使う。
- **`REFUSED` は「文書が誤り」ではなく「この run は無効」と読む。** 代表例は evidence の欠落／
  変更、lock の識別不一致、未 seal manifest、HEAD/worktree や `changeSetSha` の drift、返却パス不一致、
  history/anchor/config の変更。reason が示す状態を確認・復元して新しい監査を始める。evidence や
  anchor を手作業で捏造しない。
- **`--refresh` は同梱 hash を使う。** `engine-shas.json` は導入済みプラグイン版ごとに管理される。
  `/docaudit:init --harness --refresh` が上書きするのは、stamp があり、正規化後の本文がその版の
  同梱 SHA と一致する生成物だけ。変更済み・stamp 無し・未知版は保持して skip 理由を報告する。
- **CONSISTENT anchor を捏造しない。** 整合を実際に検証できない場合（例: あるレイヤをスキップ
  した）は anchor を書かない。正直なレポート付きの NEEDS FIX が正しい結果。

---

## 11. カスタマイズ & チューニング

- **heuristic ノイズ:** `heuristics.minIdentifierLength`（既定 5。ノイズの多い repo は 6–7 に上げる）
  と `heuristics.excludeBasenames`（`readme.md`/`index.md`/`skill.md` などの組込み generic と merge）。
- **上限:** `maxImpactedDocs`（既定 200）が fan-out を制限。超過は報告される。
- **スコープ:** `diffGlobs` は実ソース/設定に絞る。`docGlobs` は実ドキュメントに絞る（生成物/ビルド
  出力・vendored ツリーを除外）。
- **レポート:** `reportPath`（例 `docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md`）。ディレクトリが存在し、
  index 化するならレポートが repo の front-matter 規約を備えていることを確認。
- **generic format の厳しさ:** front-matter 契約を強制するなら `frontMatterFields` を設定。orphan 検出で
  「リンクされている」の定義を決めるなら `indexFiles` を設定。

---

## 12. トラブルシューティング

| 症状 | 想定原因 | 対処 |
|------|----------|------|
| `/docaudit:*` が使えない | インストール場所 / 未リロード | `~/.claude/skills/docaudit` を使う。`/reload-plugins` か再起動。`claude plugin list` を確認 |
| "this repo has no adapter" | `.claude/doc-audit.json` が無い | `/docaudit:init` を実行、または手動作成（§5） |
| 監査が常に full / `changed` 集合が巨大 | anchor が無効、または `diffGlobs` が広すぎ | クリーンな `--full` で anchor を書く。`diffGlobs` を絞る |
| heuristic「影響」ドキュメントが氾濫 | 共通 basename トークン | `excludeBasenames` に追加 / `minIdentifierLength` を上げる。実結合は `impactMap` へ昇格 |
| 「broken link」指摘が大量 | code fence 内のリンク、または生成ドキュメントをスキャン | 文脈で検証（code-fence 誤検出）。`docGlobs` を絞る |
| 「stale 予定」指摘が多数 | 歴史的/ロードマップ文書をスキャン | plan/spec/log ディレクトリを stale スキャンから除外。たいてい正当 |
| サブディレクトリの変更を incremental が拾わない | サブディレクトリが git ルートでない | full-mode 専用にするか親へ畳み込む（§10） |
| `/code-review` / `/security-review` が「何もしなかった」 | クリーンで同期済みのツリー（保留 diff なし） | 想定どおり — review 対象の変更を残す/コミットする、または無視 |
| プラグインを更新したのに挙動が変わらない | グローバルインストールはスナップショット | 再 sync（§3c） |
| audit open が exit 4 / `locked:true` | 別 run が `.claude/state/docaudit-run/lock` を所有 | holder を確認。確実に stale なら `/docaudit:audit --break-lock` の後、新しい監査を開始 |
| audit open が exit 6 / `config-change-unaccepted` | 前 run が config 変更を検知 | `git diff .claude/doc-audit.json` を確認し、承認後に `/docaudit:audit --accept-config` |
| verdict が `REFUSED` | gate が run の snapshot を検証できなかった | `reason` に従う。代表例: evidence SHA、lock/run 識別、未 seal manifest、HEAD/worktree、`changeSetSha`、return、history/anchor/config の不一致 |
| installed harness が `broken` / refresh が skip | 生成物 3 本の欠落、変更、stamp 無し、未知の template 版 | 意図を確認して復元、または `/docaudit:init --harness --refresh`。`created`、`skipped`、`skipReasons` を確認 |

---

## 13. プロジェクト導入チェックリスト

- [ ] docaudit をグローバルインストールし `claude plugin list` でロード確認
- [ ] `/docaudit:init` 実行（または `.claude/doc-audit.json` を手書き）し **レビュー済み**
- [ ] `anchorPath`, `diffGlobs`, `impactMap` がある。`docGlobs` を絞った（vendored/build ツリー除外）
- [ ] `docAuditCommands` を配線（ドキュメントツールがある場合）または省略（generic fallback）
- [ ] `reviewCommands` + `reportPath` を設定。レポートのディレクトリが存在
- [ ] config をコミット
- [ ] `/docaudit:audit --full` 実行。指摘を **文脈で** triage し外科的に修正
- [ ] verdict = CONSISTENT。anchor を書いて **コミット**
- [ ] WARN をレビュー。本物のノイズを抑えるよう config を調整
- [ ] （任意）プロジェクト固有レイヤに `--scaffold` を使用
- [ ] （サブディレクトリのターゲットのみ）full-mode の `_note` を記録、または親へ畳み込み

---

## 付録 — プラグインのファイルマップ

```
doc-audit-harness/
├── .claude-plugin/plugin.json
├── skills/audit/SKILL.md
├── skills/init/SKILL.md
├── skills/audit/scripts/ax-probe.sh
├── skills/audit/scripts/change-set-sha.py
├── skills/audit/scripts/check-verdicts.py
├── skills/audit/scripts/classify-run.py
├── skills/audit/scripts/cocoindex-probe.sh
├── skills/audit/scripts/codegraph-probe.sh
├── skills/audit/scripts/codex-dispatch.py
├── skills/audit/scripts/codex-probe.sh
├── skills/audit/scripts/codex-review-plan.py
├── skills/audit/scripts/compute-baseline.sh
├── skills/audit/scripts/decide-verdict.py
├── skills/audit/scripts/docaudit_cache.py
├── skills/audit/scripts/docaudit_paths.py
├── skills/audit/scripts/fix-scope.py
├── skills/audit/scripts/generic-layers.py
├── skills/audit/scripts/graphify-probe.sh
├── skills/audit/scripts/harness-command-kind.py
├── skills/audit/scripts/impact-supplement.py
├── skills/audit/scripts/import-audit-scope.py
├── skills/audit/scripts/inventory.py
├── skills/audit/scripts/mdq-health.py
├── skills/audit/scripts/mdq-index.sh
├── skills/audit/scripts/open-run.py
├── skills/audit/scripts/plan-dispatch.py
├── skills/audit/scripts/probe-record.py
├── skills/audit/scripts/read-manifest.py
├── skills/audit/scripts/resolve-impact.py
├── skills/audit/scripts/scaffold.py
├── skills/audit/scripts/seal-run.py
├── skills/audit/scripts/set-config-key.py
├── skills/audit/scripts/sibling-scan.py
├── skills/audit/scripts/start-run.py
├── skills/audit/scripts/tree-digest.py
├── skills/audit/scripts/write-anchor.sh
├── skills/audit/scripts/write-evidence.py
├── skills/audit/scripts/write-template.py
├── skills/audit/scripts/write-verdict.py
├── skills/audit/references/codex-phase3-verdict.schema.json
├── skills/audit/references/codex-review-output.schema.json
├── skills/audit/references/config-schema.md
├── skills/audit/references/default-heuristics.md
├── skills/audit/references/engine-shas.json
├── skills/audit/references/workflow-template.js
├── agents/doc-impact-verifier-light.md
├── agents/doc-impact-verifier.md
├── docs/ADOPTION.md
├── docs/ADOPTION.ja.md
├── docs/examples/doc-audit.example.json
└── tests/
```

`probe-record.py` は表示専用の Phase-0 probe 結果を run directory に記録し、Phase-5 の状態行向けに再束縛する。

設計判断の根拠（なぜ各決定をしたか）は、トップレベル `README.md` が参照する元プロジェクトの
設計 spec を参照。
