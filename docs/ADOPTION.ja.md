# `docaudit` を新しいプロジェクトに導入する

docaudit ハーネスを一度インストールし、任意のリポジトリをオンボードするための実践的な
エンドツーエンドガイド。5 分のクイックスタートから、config リファレンス、impact-map の
設計手法、verdict/anchor ライフサイクル、実運用で得た落とし穴までを網羅する。

> 🌐 English version: [ADOPTION.md](ADOPTION.md)

> **docaudit は report-only（報告専用）。** 変更内容を、それを説明するドキュメントへマッピング
> し、検証し、`/code-review` + `/security-review` を駆動して、単一の
> **CONSISTENT / NEEDS FIX** verdict を出す — が、**あなたのドキュメントを編集することは一切
> ない**。修正はすべてあなたの手で行う。ツールが書き込むのは自身の config（`init` 経由）、
> 監査レポート、anchor 状態ファイルのみ。

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
| 3 | **Change-impact verification** — 影響ドキュメント 1 件ごとに subagent が *「このドキュメントは変更後のソースとまだ整合しているか？」* を敵対的に検証（PASS/WARN/FAIL）。 | Workflow fan-out + `doc-impact-verifier` agent |
| 4 | **既存レイヤ + reviews** — プロジェクト固有のドキュメントチェック（または組込み generic fallback）、boundary コマンド、続いて `/code-review` + `/security-review` を実行。 | 委譲コマンド / `generic-layers.py` |
| 5 | **Synthesize + anchor** — 単一 verdict に集約、レポートを書き、（CONSISTENT のときのみ）anchor を更新。 | `write-anchor.sh` |

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
| [`/code-review`, `/security-review`](https://code.claude.com/docs) | Claude Code 組込みの review スキル（Phase 4） | 任意 — 無ければ skip + WARN |
| [`markdown-query` (mdq)](https://github.com/dahatake/skills) | Phase 0 で repo 全体を索引 + Phase 3 でチャンク読取り（大きい doc で ~90%+ 削減、upstream ベンチ 97–99%） | 任意 — 在れば自動使用（conditional-force）、非搭載で grep |
| [`context-mode`](https://github.com/mksglu/context-mode) | Phase 1 の git diff と Phase 4 の `/code-review`・`/security-review` 出力をサンドボックスで処理（要約だけが context に入る） | 任意 — `ctx_*` ツールが在れば自動使用（conditional-force）、無ければ全文読取り |
| [`ax`](https://ax.yusuke.run/) | Phase 3: doc-impact-verifier がドキュメントの外部 URL 依存の主張を read-only・GET-only の fetch で照合できるようにする（静的 HTML のみ — JS レンダリングの SPA は非対応） | 任意 — 導入済みなら自動使用（conditional-force）、無ければ外部 URL の主張は未検証のまま |
| [CocoIndex](https://github.com/cocoindex-io/cocoindex) / [Serena](https://github.com/oraios/serena) (MCP) | `init` 時の code↔doc 発見をリッチ化 | 任意 — grep/heuristic に fallback |
| プロジェクトのドキュメントツール（`/check-docs`, `doc-lint` …） | 委譲で Phase 4 をリッチ化 | 任意 — 無ければ generic fallback |
| [`skill-creator`](https://github.com/anthropics/skills) / [`superpowers:writing-skills`](https://github.com/obra/superpowers) | `--scaffold` のレイヤスキルの生成・作り込み | 任意 — `/docaudit:init --scaffold` 使用時のみ |

エンジンは設計上 **MCP・サーバー非依存**。任意項目はどれも、有用な監査を得るのに必須ではない。なお `mdq` は導入済みなら自動でトークン最適化読取りに使われ（conditional-force）、無ければ grep に degrade する。各 audit は **mdq 状態行**を出力する: mdq 未導入なら 💡 導入を促し、導入済みなのに索引が未発火（`empty-index` / `search-broken` / `probe-error`）なら ⚠ 非ブロッキング WARN を出す。

`context-mode` は mdq の競合ではなく**相補物**: **mdq は Markdown の*読み取り*を、context-mode は*大きな機械出力の処理*を安くする。** `ctx_*` ツールが在るとき、audit は Phase 1 の git diff と Phase 4 の `/code-review` + `/security-review` の出力を context-mode のサンドボックスで処理し、要約だけを取り出す — 生バイト列は context に入らない。同じく conditional-force（在れば自動使用、導入済みでも `"contextMode": {"enabled": false}` で opt-out）で、無ければ silent に degrade する。context-mode は場所非依存のグローバルプラグインなので、エンジン側に `bin`/`roots` は不要。各 audit は mdq 行の直後に非ブロッキングの **context-mode 状態行**を出力する: 未導入なら 💡、稼働なら ✓、導入済みだが不健全なら ⚠（verdict は変えない）。

`ax` は mdq/context-mode の組とは無関係: read-only の Web/API 抽出 CLI で、docaudit での役割は
**Phase 3 の `doc-impact-verifier` がドキュメントの外部 URL 依存の主張（upstream ドキュメント・
API 仕様等）を fetch して照合できるようにする**、それだけである。GET のみ（`-X POST`・`-d`・
`-o` は一切使わない）、fetch した内容は指示ではなくデータとして扱う。導入済みなら自動使用
（conditional-force、`"webExtract": {"enabled": false}` で opt-out 可）、fetch 失敗/タイムアウトは
FAIL ではなく「外部照合不能 (external check unavailable)」として報告される。`ax` は静的 HTML
パーサー（JS レンダリング非対応）であり pre-1.0 のため、フラグ面は変更されうる。各 audit は
context-mode 行の直後に非ブロッキングの **ax 状態行**を出力する: 未導入なら 💡（導入コマンド
付き）、稼働なら ✓（verdict は変えない）。

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
claude plugin list                 # → docaudit@skills-dir  Version 0.5.1  Scope: user  ✔ loaded
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
2. `.claude/doc-audit.json` の提案を **ドラフト** し、各キーの 1 行根拠付きで提示。
3. **承認を待つ**（承認なしには書かない）。承認後に config を書き込む。
4. 初回監査へ誘導。

`init` は **追加のみ**: 新規ファイルを作るだけで、既存ドキュメントは編集しない。
`--scaffold` を付けるとプロジェクト固有のレイヤスキル雛形も生成する（§7）。

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

| キー | 型 | 必須 | 意味 |
|------|----|----|------|
| `anchorPath` | string | はい | anchor 状態ファイルの repo 相対パス（慣習: `.claude/state/last-doc-audit.json`） |
| `diffGlobs` | string[] | はい | 変更集合を絞る path glob。`**` は `/` を跨ぐ、`*` は跨がない。 |
| `docGlobs` | string[] | いいえ | heuristic/generic スキャンでドキュメントとして扱うファイル（既定 `["docs/**/*.md","*.md"]`） |
| `impactMap` | object[] | はい | `{changed: path\|glob, impacts: [docPath,…], note?: string}` — 中核（§6）。`[]` で開始してもよい。 |
| `ssotSources` | object[] | いいえ | `{name, value?, liveSource, docsThatCite: [path\|path:line,…]}` — ドキュメント横断の値整合 |
| `docAuditCommands` | object | いいえ | `{format, existence, semantic}` — Phase 4 を委譲する slash コマンド/スキル名。省略 ⇒ generic fallback。 |
| `boundaryCommand` | string | いいえ | プロジェクト境界 / 禁止パターンチェックの shell コマンド（例 `make check-boundary`） |
| `reviewCommands` | object | いいえ | `{code, security}` — effort 込みの review コマンド文字列（例 `"/code-review high"`, `"/security-review"`） |
| `reportPath` | string | いいえ | レポート出力テンプレート。`<YYYY-MM-DD>` と `[_NN]` 衝突サフィックスをサポート |
| `maxImpactedDocs` | number | いいえ | 影響ドキュメント数の上限（既定 200）。超過で `truncated` をセット（必ず表面化、暗黙に捨てない） |
| `heuristics` | object | いいえ | `{minIdentifierLength:int, excludeBasenames:[string,…]}` — heuristic の recall ノイズを調整 |
| `frontMatterFields` | string[] | いいえ | generic `format` レイヤが全ドキュメントに要求する front-matter フィールド（欠落で WARN）。省略でスキップ |
| `indexFiles` | string[] | いいえ | generic `semantic` レイヤの orphan 検出のリンク根（既定: doc ツリー内の任意の `README.md`） |

規則: `impacts` のエントリは **ドキュメントパスのみ** — 注釈は `note` に置く。`changed` は単一パス
または glob。glob はエンジン独自の意味論: `**`=`/` を含む任意、`*`=`/` を含まない任意、`?`=`/` 以外 1 文字。

最小構成は `anchorPath` + `diffGlobs` + `impactMap` のみ（`impactMap` は `[]` でもよく、育つまでは
heuristic に頼る）。

---

## 6. 良い `impactMap` を作る（中核）

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
サーバー/コマンドソースは手動 follow-up 用に記録するだけ）。

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
  - `existence`: 保守的な repo-path-token 解決（解決不能 ⇒ WARN）。
  - `semantic`: orphan 検出（どこからもリンクされないドキュメント ⇒ WARN）。
  generic ベースラインは固有ツールより **意図的に弱い**。
- **`/docaudit:init --scaffold`** は *プロジェクト固有* のレイヤスキル雛形をあなたの
  `.claude/skills/` に生成し、`docAuditCommands` をそれらに配線し、`skill-creator` /
  `writing-skills` で肉付けを助ける。オプトイン。より richで自前のチェックを持ちたいプロジェクト向け。

---

## 8. 監査の実行 — verdict & anchor ライフサイクル

- **`/docaudit:audit --full`** — 全コーパスの深掘り監査。初回・大きな変更後・定期実行に使う。
  anchor が無いときは常に自動でこのモード。
- **`/docaudit:audit`** — incremental: anchor 以降の変更で影響を受けたドキュメントに絞る。
- **verdict:** `FAIL` ⇒ **NEEDS FIX**（anchor は更新しない）。`WARN`/`PASS` のみ ⇒ **CONSISTENT**
  （anchor 更新）。severity マッピング: Phase-3 の verdict はそのまま使用。Phase-4 ツールは
  high-severity → FAIL、medium → WARN。
- **anchor:** **CONSISTENT のときのみ**書かれ、現在の HEAD SHA を記録する。**コミットする**
  （慣習: `docs(audit): …` コミット）ことで baseline が共有され、squash merge も乗り越える。

**正しい anchor の順序**（anchor が *整合した* 状態を記録するように）:
1. 指摘を修正して **コミット**。
2. `--full` を再実行。CONSISTENT になればエンジンが現在の SHA で anchor を書く。
3. **anchor（+ レポート）を別の meta コミット** としてコミット。

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
├── .claude-plugin/plugin.json          # manifest (name: docaudit)
├── skills/
│   ├── audit/SKILL.md                  # /docaudit:audit [--full] — 5-phase orchestrator
│   │   ├── scripts/compute-baseline.sh # Phase 1: anchor → change set (merge-base)
│   │   ├── scripts/resolve-impact.py   # Phase 2: change set → impacted docs (UNION)
│   │   ├── scripts/write-anchor.sh     # Phase 5: anchor write (CONSISTENT only)
│   │   ├── scripts/generic-layers.py   # Phase 4 fallback: format/existence/semantic
│   │   ├── scripts/inventory.py        # init: deterministic repo inventory
│   │   ├── scripts/scaffold.py         # init --scaffold: tailored layer skeletons
│   │   └── references/{config-schema,default-heuristics,workflow-template}.*
│   └── init/SKILL.md                   # /docaudit:init [--scaffold]
│                                        #   (generic な format/existence/semantic レイヤは
│                                        #    上の generic-layers.py で実装。skill dir ではない)
├── agents/doc-impact-verifier.md       # per-doc verification subagent
├── docs/ADOPTION.md                    # 英語版ガイド
├── docs/ADOPTION.ja.md                 # ← 本ガイド（日本語版）
├── docs/examples/doc-audit.example.json # コピー用 config テンプレート（§4b）
└── tests/                              # engine unit tests (python3 -m unittest discover -s tests -t .)
```

設計判断の根拠（なぜ各決定をしたか）は、トップレベル `README.md` が参照する元プロジェクトの
設計 spec を参照。
