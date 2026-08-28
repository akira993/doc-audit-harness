# PLAN — Issues #52〜#54 → docaudit v0.13.2（rev.8, 2026-08-28 — Sol R1〜R5・Opus O1/O2 反映。実装承認）

## 0. 決定事項（route 手順 1 の代替 — 自律実行につき boss 裁定、ユーザー指示で要件確定）

ユーザー指示: 「Issue を確認し、すべて丁寧に対応し、パッチアップデート、ローカル同期まで完了してください」。

1. **版は 0.13.2（パッチ）。** #52・#53 の Issue 本文と Sol R1-1 は「runtime 変更なので minor 版（v0.14.0）」を主張するが、ユーザーの明示指示
   「パッチアップデート」を採る（boss 裁定。最終報告で Sol の反論とともに明記し、ユーザーが minor を望めば次版で扱う）。対象 Issue は open の
   3 件 `#52 #53 #54` のみ（HEAD `2032e21`、tracked 差分 0）。
2. **#52 — `fix-scope.py` の `docGlobs` 既定を他の config consumer と同値 `["docs/**/*.md","*.md"]` に揃え、同時に agent 指示ファイルを組込み deny に
   加える。** Sol R1-2 実測: 既定 `*.md` は root の `AGENTS.md`・`CLAUDE.md`・`SECURITY.md` にも一致し、組込み deny（`.claude` と path 部分
   `adr`/`decisions`/`logs`、`fix-scope.py:14,89,97`）では agent 指示ファイルを守れない。よって `fix-scope.py` に **basename deny `{"claude.md","agents.md"}`
   （任意の深さ・`casefold()` で大文字小文字を同一視 — Sol R2-1: 既存 deny も `path.lower()` で同一視しており、大小文字非区別 FS では `claude.md` で迂回できる）** を追加し、`docGlobs` の明示有無によらず pre-flight fix から除外する（`.claude` deny と同じ趣旨: 監査中の
   モデルに自分の指示書を書き換えさせない）。`SECURITY.md`・`README.md` は通常文書として許可。v0.13.1 で入れた fail-closed 注記
   （`fix-scope.py:87` コメント、`config-schema.md:10`、`docs/ADOPTION.md:310`、`.ja.md:291`）は撤去し、組込み deny の列挙 **5 か所**
   （`config-schema.md:30` の `protectedGlobs` 行、`config-schema.md:154` の本文、`skills/audit/SKILL.md:281` の Phase 0.5 本文、`ADOPTION.md` の対応行、
   `ADOPTION.ja.md` の対応行）に `CLAUDE.md`/`AGENTS.md`（case-insensitive basename）を加える（Sol R2-2、R3-14）。
   **構造テストの対象は実装前に固定（Sol R2-8）: N = 11**（`resolve-impact.py` 2、`start-run.py` 2、`generic-layers.py` 2、`change-set-sha.py` 1、
   `impact-supplement.py` 1、`import-audit-scope.py` 2、`fix-scope.py` 1）。ファイル別内訳も assert する。
   **構造テストは全 `*.py` 走査ではなく既知の config consumer に限定**（Sol R1-10）: `resolve-impact.py`、`start-run.py`、`generic-layers.py`、
   `change-set-sha.py`、`impact-supplement.py`、`import-audit-scope.py`（`config.get("docGlobs", …)` の literal 既定を持つ箇所のみ。`:588` の
   変数経由は対象外）、`fix-scope.py`。`sibling-scan.py:156`（sealed manifest 由来の `[]`）は別契約として対象外。
3. **#53 — seal 失敗の停止分岐 3 本と `read-manifest.py` の sealed 検査。**
   (a) SKILL.md Phase 3（:365-373）を、**exit 5／その他の非 0／`read-manifest.py` 非 0 の 3 分岐すべて**で SKILL.md:52 の完全な解放コマンド
   `python3 "$SD/scripts/open-run.py" --run-base "$RUN_BASE" --repo-root "$CLAUDE_PROJECT_DIR" --anchor-path "$ANCHOR_PATH" --release --runid "$RUNID"`
   を要求する形に改める（Sol R1-6: 既存の read-manifest 失敗分岐 :371 は stop のみで解放を書いていない）。その他の非 0 分岐の固定句は
   en `Any other non-zero exit`、`read-manifest.py` を呼ばず verifier も起動せず、`seal-run.py` の stderr（接頭辞 `seal-run:`）を利用者へ報告する。
   exit 5 の既存メッセージ「Phase 1 以降にソースが変わりました。監査を再実行してください。」は変えない。
   (b) `read-manifest.py`: hash 一致後に **`isinstance(manifest, dict)` と `manifest.get("sealed") is True` を一体で検査**（Sol R1-7）。不成立は
   `ValueError("manifest is not sealed")` → exit 2・stdout 空。テスト対象: `{"sealed":false}`、`sealed` キー無し、`[]`、`null`（4 件）。
   呼び出し元は SKILL.md:372（seal 後）と `codex-dispatch.py:38,61-63`（seal 後・自前検査は二重防御として残す）のみ。Phase 2 の raw parse
   （SKILL.md:354）は `manifest.json` 直読みで影響なし。
4. **#54-1 — キー不在＝`not-configured`／設定不正＝`invalid-config`（どちらも tool を一切起動しない）を 3 probe に適用**: `docGraph`
   （`graphify-probe.sh`）、`semanticSearch`（`cocoindex-probe.sh`）、`symbolGraph`（`codegraph-probe.sh`）。判定表（3 probe 共通、全行をテストで固定）:
   | # | 入力 | 結果（`available:false` のとき外部 tool を起動しない） |
   |---|---|---|
   | 1 | キー不在 | `reason:"not-configured"` |
   | 2 | `{}`（object だが `enabled` 無し） | 有効（`enabled` の既定 true は object 存在時のみ） |
   | 3 | `{"enabled": false}` | `disabled-by-config`（現状どおり） |
   | 4 | `enabled` が JSON boolean 以外（例 `"false"`、`1`） | `invalid-config`（Sol R1-3: 現行は `bool("false")` で起動してしまう） |
   | 5 | キーが object 以外（`true`、文字列、配列） | `invalid-config` |
   | 6 | config が JSON 不正 | `invalid-config`（※） |
   | 7 | `--config` 未指定／ファイル不在 | `invalid-config`（※） |
   | 8 | top-level が object 以外（配列等） | `invalid-config`（※） |
   | 9 | `bin` が存在して非文字列または空文字列 | `invalid-config`（Sol R2-4: 現行は `str(...)` で握りつぶす） |
   | 10 | semanticSearch のみ: `minScore` が存在して有限数値以外（bool・`NaN`・`±Infinity` を含む — `math.isfinite`、Sol R3-5） | `invalid-config`（probe は使わないが seam が後段で読む値。Sol R2-4） |
   **評価順序（Sol R3-4）**: config 解析（6・7・8）→ キー存在（1）→ object 型（5）→ `enabled` 型（4）→ **`enabled:false`（3）を確定** → `bin`（9）→ `minScore`（10）。
   よって `{"enabled":false,"bin":[]}` および semanticSearch の `{"enabled":false,"minScore":"x"}` は `disabled-by-config`（後方互換優先）。複合テストで固定（Sol R4-3）。
   ※ 行 6〜8 は通常の監査経路では probe 前に停止する（SKILL.md:9,14,25 が config を `.get()` で先に読む）ため **probe 単体呼び出し時の防御**であり、
   Phase-5 の `invalid-config` 行は実際には行 4・5・9・10（キー単位の不正）で到達する（Sol R2-3）。SKILL.md の probe 段落にこの旨を 1 句添える。
   `open-run.py` は config をバイト列で hash するだけで JSON 解析しない（boss 実測 `open-run.py:157-162`）。
   **probe JSON の形状（Opus B5）**: 新分岐（`not-configured`／`invalid-config`／`gitignore-modified`）を含む全分岐で **従来と同一のキー集合**を出す
   （graphify: `docGraphAvailable`/`docGraphBin`/`reason`/`gitignoreOk`（常に含む。available:false では `false`）、cocoindex: `semanticSearchAvailable`/`semanticSearchBin`/`reason`、
   codegraph: `symbolGraphAvailable`/`symbolGraphBin`/`reason`）。`<seam>Bin` は設定値が使用不能（キー不在・不正・`bin` 不正）のとき既定名（`graphify`／`ccc`／`codegraph`）。
   全分岐 exit 0・JSON 1 行。
   **`*_PROBE_JSON` の捕捉（Opus B6）**: SKILL.md:174,188,202 の呼び出し行を codex（:149）と同型の `SYMBOL_GRAPH_PROBE_JSON="$(bash "$SD/scripts/codegraph-probe.sh" …)"`／
   `DOC_GRAPH_PROBE_JSON=…`／`SEMANTIC_SEARCH_PROBE_JSON=…` に変え、既存の available/bin 束縛もこの変数から読む。
   **reason の保持（Sol R2-6）**: Phase 0 の 3 probe 段落で、SKILL.md:149 と同型の完全な式（例
   `SYMBOL_GRAPH_REASON="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["reason"])' "$SYMBOL_GRAPH_PROBE_JSON")"` 相当）で
   `SYMBOL_GRAPH_REASON`／`DOC_GRAPH_REASON`／`SEMANTIC_SEARCH_REASON` を束縛し、Phase-5 状態行はこの 3 変数で分岐する（現行は available/bin のみ保持）。
   寿命・再開規約は既存の `*_AVAILABLE` 束縛と同一（SKILL.md:49 の `RUNID`/`EVIDENCE` 限定規約により中断後に復元できない点は `*_AVAILABLE` と
   同じ既往制約で、本変更で悪化しない — Sol R3-1 は不採用、別 Issue 候補「Phase-0 probe 結果の run-dir 永続化」として最終報告に載せる）。
   **判別基準**（Sol R1-4 を受けて書き直し）: 対象は「init が『未検出なら OMIT』とする conditional-force seam のうち、probe が対象 repo の
   worktree に tool 所有の生成物（`.codegraph/`・`graphify-out/`・`.cocoindex_code/` 配下）を作り、かつ **probe の利用不能自体は FAIL の根拠に
   ならない**（取得した候補・証拠は監査対象に加わり verdict に間接影響する — Sol R2-5 訂正）補助 seam（symbolGraph は Phase 3 の corroboration、
   docGraph／semanticSearch は Phase 2 の候補源）」の 3 seam。`indexing`（mdq、`.mdq/` を書く）は
   fan-out の主経路で Phase-0 の mdq 確認ゲート・health probe を持つため据え置き、`contextMode`／`webExtract`／`codexReview` は worktree に
   書かないため据え置き。これら 4 seam のキー不在既定の統一は**別 Issue 候補**として最終報告に載せる。
   **波及先の一掃（Opus B1）**: キー不在＝不起動により偽になる「conditional-force」「auto-used when installed」「導入済みなら自動使用」の記述を全て
   「key-gated（キーが存在し `enabled` が false でなく tool が導入済みのときのみ使用。`enabled:false` で opt out）」の意味に書き換える。対象（boss 追認）:
   `config-schema.md:37,38,39`（3 行の `{enabled:bool=true,…}`＋`conditional-force` 句）、`:259`、`:279`、`:299`、`docs/ADOPTION.md:85,86,87`（tool 表）、`:153-154`、
   `:165-166`、`docs/ADOPTION.ja.md:84,85,86`、`:138`、`:149-150`、`skills/init/SKILL.md:52`。他 seam（`webExtract`/`codexReview`/`indexing`/`contextMode`）の
   conditional-force 記述は変えない。契約テスト `test_three_seams_no_longer_documented_as_auto_used`（**段落単位** — Opus O2-R2: 行単位では
   `ADOPTION.md:153-154,165-166`・`ja:149-150` のハードラップで素通りする）: 上記 4 文書を `re.split(r"\n\s*\n", text)` で段落に割り `" ".join(p.split())` で
   正規化したうえで、`symbolGraph`／`docGraph`／`semanticSearch`／`codegraph`／`graphify`／`CocoIndex`／`ccc` を含む段落に `conditional-force`・
   `auto-used when installed`・`導入済みなら自動使用` が現れない（「キーが存在する場合に限り」等の限定句を同じ段落に伴う場合のみ許容）。表の行は 1 行 1 段落として扱う。
   **移行注記**: ADOPTION §7 の v0.13.2 段落に「キーを省略して自動検出に頼っていた config は、`/docaudit:init` でキーを追加するまで
   3 seam が `not-configured` になる」を明記（既存 config が黙って機能を失う問題を文書で可視化。Sol R1-4）。
   **Phase-5 状態行**（Sol R1-8）: 3 ブロックとも **`reason` 優先の排他表**に書き直す（`AVAILABLE false` だけで拾う catch-all 枝を廃止し、
   各枝を `reason` 集合で限定）。追加枝: `reason:not-configured` → `💡 <seam>: not configured — <key> is absent from doc-audit.json, so the
   tool is not probed; run /docaudit:init to enable it.`（`install:` を含めない・「installed」と言わない）、`reason:invalid-config` →
   `⚠ <seam>: doc-audit.json <key> is invalid — tool not probed this run; fix the key. [non-blocking]`。ラベルを **doc-graph 6-state（7 messages: `ok` は gitignoreOk で 2 行）、
   symbol-graph 6-state、semanticSearch 8-state**（Sol R3-3）へ更新。契約テストは reason ごとの期待行（記号＋固定句）を対応表で検査する（DoD 10）。
5. **#54-2 — `cocoindex-probe.sh` の初期化判定を `settings.yml` マーカーにし、`.gitignore` 変化は検出のみ（復元しない）。**
   原因（boss 実測・ソース追跡済み）: `ccc index` は `require_project_root(auto_init=True)`（`cocoindex_code/cli.py:642`）で、`find_project_root` の
   マーカー **`.cocoindex_code/settings.yml`**（`settings.py:333-340`）が無ければ `_auto_init_project` → `_create_project_settings` →
   `add_to_gitignore`（`cli.py:114-128, 301-321`）を走らせ、`_GITIGNORE_ENTRY="/.cocoindex_code/"` が既存行 `.cocoindex_code/` と不一致のため重複追記される。
   dir-framework は旧形式（`cocoindex.db` のみ）の `.cocoindex_code/` が存在し、probe の `-d` 判定（`cocoindex-probe.sh:58`）を通過して自動 init が
   発火した（`settings.yml` mtime 2026-08-27 23:55 と一致）。
   対策: (a) 初期化済み判定を **`[[ -f "$REPO_ROOT/.cocoindex_code/settings.yml" ]]`** に変更（ccc 自身のマーカーと同値。これで今回の経路は閉じる —
   Sol R1-5 と一致）。ディレクトリのみ存在は `not-initialized`（既存の状態行文言で `ccc init && ccc index` を案内）。
   (b) **復元は行わない**（Sol R1-5: 索引中の利用者編集との区別不能・symlink 先の破壊・失敗時未定義）。代わりに **検出のみ**: `ccc index` の前後で
   `.gitignore` の存在有無と sha256 を比較し、変化していれば `semanticSearchAvailable:false, reason:"gitignore-modified"` を返し stderr に 1 行
   （`.gitignore` には一切書かない。git 管理外や `.gitignore` 不在→不在は「変化なし」）。趣旨: マーカーは ccc の内部仕様に結合するため、版が変わって
   別経路で書かれた場合に report-only 契約違反を黙って通さず WARN にする版非依存の安全網。状態行（原因を断定せず checkout も案内しない — Sol R2-7）:
   `⚠ semanticSearch: .gitignore changed while ccc index ran — inspect it manually (git status / git diff -- .gitignore; if .gitignore is a symlink, resolve the target with readlink and review that file's content against your backup or VCS); not available this run. [non-blocking]`（Sol R3-9、R4-8）。
   **`.gitignore` 変化は exit code より優先**: 追記後に非 0 終了しても `gitignore-modified`（Sol R3-8。stub テストで固定）。
   既知の限界（Opus N6、記録のみ）: ccc の自動 init は最も近い親 git root に anchor するため、`--repo-root` が大きな git repo のサブディレクトリの場合は親側の
   `.gitignore` 書き込みを検出しない。cocoindex-probe.sh のヘッダコメントに 1 行記す。
   **削除しない判断（Opus N7・Sol R1-5 の cut 提案に対する boss 裁定）**: 検出は Issue #54 の 2 経路目（report-only 契約違反）を将来 ccc の経路が変わっても黙って
   通さないための版非依存の安全網であり、追加コスト（1 状態・状態行 1 本・テスト 3 本）は小さいので維持する。
   graphify／codegraph は対象 repo の `.gitignore` を書かない（boss がソースで確認: graphify-probe.sh ヘッダ、codegraph は `.codegraph/.gitignore`
   を自己生成）→ 検出は cocoindex のみ。
   (c) `skills/init/SKILL.md:155-158` の「`.cocoindex_code/` already exists」も `settings.yml` マーカーに揃える。
6. **版バンプ 5 面＋engine-shas**: `.claude-plugin/plugin.json`、`docs/ADOPTION.md:224`／`.ja.md:206`（`claude plugin list` 行）、refresh 段落
   （en `ADOPTION.md:284`: `Existing unmodified stamped 0.10.1, 0.11.0, 0.12.0, 0.13.0, or 0.13.1 templates can be updated directly to 0.13.2 with`／
   ja `.ja.md:264-265`: 1 行目 `変更されていない stamp 付きの 0.10.1、0.11.0、0.12.0、0.13.0、または 0.13.1 テンプレートは、`、2 行目冒頭
   `` `/docaudit:init --harness --refresh` で 0.13.2 へ直接更新できる。``、いずれも行単位の完全一致 — Sol R1-12）、
   `skills/audit/references/engine-shas.json` に `0.13.2` entry（テンプレート変更なしのため 0.13.1 と同一 hash の見込み — `scaffold.py --harness --dry-run`
   と `test_scaffold` で確認。max semver が 0.13.2 になること）。`tests/test_v013_contracts.py` test_i の集合 `{"0.13.2"}`、test_j の refresh 行 regex
   （en/ja とも新文言）、`tests/test_v0131_docs_contracts.py` test_g の target 集合に `"0.13.1"` を追加、`tests/test_scaffold.py:214-218, 242-246, 312` を 0.13.2 へ。
7. **ADOPTION §7 に `**v0.13.2 behavior changes:**`／`**v0.13.2 の挙動変更:**` 段落（en/ja、`v0.12.0` 段落と同型）**: (1) `docGlobs` 省略時の
   pre-flight fix 既定が deny-all から共通既定へ、かつ `CLAUDE.md`/`AGENTS.md` は組込み deny、(2) `docGraph`／`semanticSearch`／`symbolGraph` のキー不在は
   `not-configured`・設定不正は `invalid-config`（tool 不起動）＋移行注記、(3) cocoindex の初期化判定は `settings.yml`、`ccc index` による `.gitignore`
   変更は `gitignore-modified` として報告（復元しない）、(4) seal／read-manifest の失敗は run を解放して停止・`read-manifest.py` は未 seal を拒否。
8. **リリース経路**（v0.13.1 と同一）: ブランチ `fix/v0.13.2-issues-52-54` → PR（`pr-body.md`）→ boss が `gh pr merge --merge` →
   `release-handoff.sh <merge-sha> <pr>`（tag `docaudit--v0.13.2`・Release・#52〜#54 close・skills-dir 同期）。auto-mode classifier が
   マージ／push を拒否した場合は、それ以前の成果（push 済み branch・open PR・commit 済み handoff script・green テスト）を durable にしたまま、
   完全な手順「`gh pr merge N --merge` → `git checkout main && git pull --ff-only` → `ps` で docaudit 実行中プロセス無しを確認 →
   `printf 'y\n' | bash tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh $(git rev-parse HEAD) N`」をユーザーへ渡す。
9. **Stage 分割（Opus N8 で事前分割）**: **S1a** = #52（fix-scope・組込み deny 文書 5 か所・docGlobs 行 3 か所）＋ #53（SKILL.md Phase 3・read-manifest）＋ §0-12 fixture
   ＋ 対応する契約テスト（Terra `high` — read-manifest は seal 境界の検査）／**S1b** = #54-1・#54-2（3 probe・SKILL.md Phase 0/5・config-schema 3 節・ADOPTION・
   init SKILL・conditional-force 一掃・cocoindex 文書）＋ 対応する契約テスト（Terra `high`）。S1a → S1b の順で逐次実行し、S1b は S1a 反映後の tree を前提にする
   （同一ファイルを触るが逐次なら競合しない）。`tests/test_v0132_contracts.py` は S1a で新設し S1b で追記／
   **S2** = 版バンプ 5 面・engine-shas・§7 段落・テスト再照準・handoff script＋test 差し替え（Terra `medium`）。
10. CHANGELOG は作らない（本 repo の慣習。release notes は GitHub Release 本文）。
11. **記録コミットの単位**: 新 `release-handoff.sh` と新 fixture は該当 Stage のテストと同一 commit に `git add -f <path>` で追跡し、**追跡後にフルスイートを
    再実行してから commit**（v0.13.1 教訓: test_j は `git ls-files` 走査）。route 記録（PLAN/REVIEW/prompt/answer/report/pr-body）は最後に
    ファイル名を列挙して `git add -f`（`*-session.log`・`baseline-tests.log` は追跡しない）。
12. **既往の red（本タスク無関係・boss ベースライン実測）**: `tests/test_import_audit_scope.py:657-684` が外部 repo `~/Projects/dir-framework` の
    tracked ファイル数を 46 に固定（現在 48）し、同 repo の config が `auditScope` 取り込み済みになったため `state` も `not-imported`→`in-sync` に変わる
    （boss 実測 `{'state':'in-sync','rules':24,'errors':[],'equivalenceChecked':48}`）。release-handoff は承認 commit でフルスイートを再実行するため
    main が red のままでは出荷できない → S1 で **外部依存を repo 内 fixture に置換**する（Sol R1-9 推奨）: `tests/data/dir-framework-scope/` に
    `audit-scope.json`（dir-framework `951570b` の実物コピー、top-level 24 組）、`doc-audit.json`（同、**`auditScope` キーを除去**して常に `not-imported`）、
    `paths.txt`（`git ls-files` 48 行。この 2 つの JSON 自身も含まれる）を置き、テストは **先に paths.txt の各 path に空ファイルを作り、最後に 2 つの
    JSON fixture で `.claude/audit-scope.json`・`.claude/doc-audit.json` を上書き**（順序固定 — Sol R2-13）してから `git init && git add -f .` →
    `--check --json --doc-glob '**/*.md'` を実行し `rc==2`、`state=="not-imported"`、`rules==24`（= `len(json.load(audit-scope.json))`）、`errors==[]`、`equivalenceChecked==48`（= paths.txt 行数）
    を assert。加えて `"auditScope" not in config_fixture` と、`audit-scope.json` fixture の sha256 が dir-framework `951570b` の実物
    （boss 実測 `git -C ~/Projects/dir-framework show 951570b:.claude/audit-scope.json | shasum -a 256` = `d68186952fee273130685b329c1cd4727c34c55065866a054b51ab0629e0982d`）と一致することを PLAN に記録し、テストは
    fixture の sha256 literal を assert する（由来の固定。3 点とも — Sol R3-11）: `audit-scope.json` = `d68186952fee273130685b329c1cd4727c34c55065866a054b51ab0629e0982d`
    （`951570b` 実物そのまま）、`paths.txt` = `b1a1356a14935bbd2aed214dbf7d732c25379213395f14ee4fd98d5689e7d91d`（`git ls-tree -r --name-only 951570b` の
    出力そのまま、48 行 LF 終端）、`doc-audit.json` = `9723e2837c235c75fa28d32eb97f04d884d9a1d12ea001ea7e21bfd4bf44599c`（実物から `auditScope` を除去し
    `json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"` で再シリアライズ）。3 値とも boss 実測。`DIR_FRAMEWORK` 定数と skip 条件は削除（skip 0 を恒久化）。`import-audit-scope.py` 本体は変更しない。
13. dir-framework 側の残骸（`graphify-out/` 884K。`.gitignore` の冗長行は PR #4 で復元済み）は本タスクで触らない（最終報告で利用者フォローアップ）。

## 1. 目的

open Issue #52（`fix-scope.py` の `docGlobs` 既定不一致）、#53（seal 失敗後の停止分岐欠落と backend 非対称）、#54（report-only 監査の
Phase-0 probe が対象 repo の worktree に書き込む）を runtime・手順・文書・テストで解消し、docaudit v0.13.2 として tag・Release・
Issue close・ローカル skills-dir 同期まで完了する。

## 2. 入力・参照資料

- Issue 本文: `issues-52-54.md`（同ディレクトリ）。Sol R1: `critique-r1-answer.md`。
- 実装の正: `skills/audit/scripts/fix-scope.py:14,87-97`、`seal-run.py:63-70`、`read-manifest.py:15-39`、`codex-dispatch.py:38,61-63`、
  `decide-verdict.py:694-695`、`open-run.py:116`（`--release` の必須引数）、`graphify-probe.sh:31-46`／`cocoindex-probe.sh:32-47,58-63`／
  `codegraph-probe.sh:28-40`（config 解釈: `except Exception: pass` で既定有効、`bool(enabled)`）、`skills/audit/SKILL.md:52`（解放コマンド）、
  `:174-215`（probe 3 段落・reason 列挙）、`:365-373`（seal／read-manifest 手順）、`:678-694`（3 状態行）、`skills/init/SKILL.md:147-163`、
  `skills/audit/references/config-schema.md:10,30,37-39,257-320`、`docs/ADOPTION.md:147-172,197-198,310`／`.ja.md:131-156,179-180,291`。
- cocoindex 実機（`~/.local/share/uv/tools/cocoindex-code/lib/python3.13/site-packages/cocoindex_code/`）: `cli.py:80-128, 297-321, 636-646`、`settings.py:333-345`。
- 版バンプの正: memory `docaudit-release-procedure`、`tests/test_v013_contracts.py` test_i/test_j、`tests/test_v0131_docs_contracts.py` test_g、
  `tests/test_scaffold.py:214-218, 242-246, 312`、`tests/test_release_handoff.py`（v0.13.1 固有値 :18, :23-36 ほか）。
- 前版の handoff: `tasks/route/2026-08-27-issues-46-50-v0.13.1/release-handoff.sh`（同型で v0.13.2・#52〜#54 に差し替え）。
- ベースライン: `python3 -m unittest discover -s tests -t .` → **Ran 495, FAILED (failures=1)**（§0-12 のみ。`baseline-tests.log`）。
- 既存 probe テスト（各 5 件）はすべてキー明示で ok を得ている → 既存ケースの改変は cocoindex の `settings.yml` fixture 追加のみ。

## 3. 担当（boss）

Fable（Claude Code）。計画・批判の反映・各 Stage の diff 全行レビュー・検証コマンドの再実行・commit・push・PR・merge・handoff 実行。
コードも文書も boss は書かない（PLAN/REVIEW/プロンプト/pr-body を除く）。

## 4. 実行者（worker）

- S1a・S1b: Terra `high`（`codex exec -m gpt-5.6-terra -s workspace-write -c model_reasoning_effort=high`）。
- S2: Terra `medium`。差し戻しで推論不足なら `high`。
- 各 Stage 末にフルスイート green（skip 0）を worker が報告し、boss が再実行して追認。codex sandbox は `.git` に書けない → commit は boss。
  Terra の sandbox では 30 秒超のフルスイートが完走しないことがある（v0.13.1 実測）→ その場合は対象テストファイル単位の実行報告で代え、フルは boss が実行。

## 5. 成果物

- S1a（runtime）: `skills/audit/scripts/fix-scope.py`、`read-manifest.py`。S1b（runtime）: `graphify-probe.sh`、`cocoindex-probe.sh`、`codegraph-probe.sh`。
- S1a／S1b（手順・文書、両 Stage が触る）: `skills/audit/SKILL.md`（S1a: Phase 0.5 deny 列挙・Phase 3／S1b: Phase 0 probe 段落・Phase 5 状態行・:211）、
  `skills/audit/references/config-schema.md`（S1a: :10, :30, :157／S1b: :37-39, 3 節, :309）、`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`（S1a: docGlobs 行・deny 行／
  S1b: tool 表・seam 段落・状態行要約）、`skills/init/SKILL.md`（S1b のみ）。
- S1a（テスト）: `tests/test_import_audit_scope.py`＋新規 `tests/data/dir-framework-scope/{audit-scope.json,doc-audit.json,paths.txt}`（§0-12）、
  `tests/test_read_manifest.py`、`tests/test_wp12_contracts.py`（fix-scope の deny 追加分、必要時のみ）、**新規** `tests/test_v0132_contracts.py`（#52・#53 分）。
  S1b（テスト）: `tests/test_graphify_probe.py`、`tests/test_cocoindex_probe.py`、`tests/test_codegraph_probe.py`、`tests/test_v0132_contracts.py`（#54 分を追記）。
- S2: `.claude-plugin/plugin.json`、`docs/ADOPTION.md`／`.ja.md`（版行・refresh 段落・§7 段落）、`skills/audit/references/engine-shas.json`、
  `tests/test_v013_contracts.py`、`tests/test_v0131_docs_contracts.py`（test_g）、`tests/test_scaffold.py`、`tests/test_release_handoff.py`、
  **新規** `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`。
- boss: `PLAN.md`、`REVIEW.md`、各プロンプト・報告、`pr-body.md`。

## 6. 完了条件（DoD）— 機械判定可能な形で

### S1-#52
- (1) `fix-scope.py` の `docGlobs` 既定が `["docs/**/*.md", "*.md"]`（`grep -c 'get("docGlobs", \[\])' skills/audit/scripts/fix-scope.py` == 0）。
  `DENIED_PARTS` と並ぶ **basename deny 集合（casefold 比較で `claude.md`／`agents.md`）** があり、分類理由文字列は既存 deny と同型（例 `agent instruction file`）。
- (2) 動作テスト `tests/test_v0132_contracts.py::TestFixScopeDefaults::test_omitted_doc_globs_uses_shared_default_and_denies_agent_files`
  と `test_explicit_doc_globs_still_denies_agent_files`: `docGlobs`・`protectedGlobs` とも無しの config で `--paths` に
  `docs/a.md`／`README.md`／`SECURITY.md`／`src/app.py`／`docs/logs/x.md`／`AGENTS.md`／`CLAUDE.md`／`docs/CLAUDE.md` を渡すと
  `allowed == ["README.md","SECURITY.md","docs/a.md"]`（実装は `sorted(set(...))` — Sol R2-12）、denied 5 件の理由がそれぞれ docGlobs 不一致／
  組込み deny（logs）／agent 指示ファイル×3。さらに `docGlobs: ["**/*.md"]` 明示でも `AGENTS.md`・`docs/CLAUDE.md`・**`docs/claude.md`（小文字）**が denied
  （basename deny は docGlobs より優先、大小文字非区別）。**前提（Opus B7）**: `validate_repo_path` は実在の通常ファイルを要求する（`docaudit_paths.py:37,61-63`）ため
  `--paths` に渡す全 path を空ファイルとして作成する。小文字ケースは `docs/claude.md` のように **同一ディレクトリに case-twin を作らない**（macOS の大小文字非区別 FS 対策）。
- (3) 構造テスト `test_v0132_contracts.py::TestFixScopeDefaults::test_doc_globs_default_is_shared_across_eleven_call_sites`: §0-2 の 7 ファイルを AST で走査し、`.get("docGlobs", <literal>)` の literal 既定が全て
  `["docs/**/*.md", "*.md"]` であること、**検査した call site 数が正確に 11 件で、対象ファイル集合が §0-2 の 7 ファイル**であることを assert（ファイル別内訳は
  コメントに残すのみで assert しない — Opus N2）。
- (4) fail-closed 注記の撤去: `grep -c 'fail.closed\|fails closed' skills/audit/scripts/fix-scope.py` == 0。`config-schema.md` の `docGlobs` 行・
  ADOPTION en/ja の `docGlobs` 行に `fail-closed`／`rejects every path`／`全パスを拒否` が無く、代わりに「pre-flight fix path も同じ既定」の旨がある。
  組込み deny の列挙 **5 か所**（`config-schema.md:30`・`:154`、`SKILL.md:281`、`ADOPTION.md`・`ADOPTION.ja.md` の `protectedGlobs` 行）すべてに
  `CLAUDE.md`／`AGENTS.md` と case-insensitive（ja: 大文字小文字を区別しない）の旨が含まれる（契約テスト `test_builtin_deny_documented_in_five_places` で
  5 箇所を個別に検査）。

### S1-#53
- (5) SKILL.md Phase 3 節（`## Phase 3` から次の `## ` まで）に、(i) exit 5 分岐、(ii) `Any other non-zero exit` 分岐、(iii) `read-manifest.py` 失敗分岐の
  3 つがあり、**3 分岐すべての文（または直後の文）に `--release --runid "$RUNID"` を含む完全な解放コマンド**（`--run-base`・`--repo-root`・`--anchor-path` を
  伴う）がある。(ii) は `read-manifest.py` を呼ばないこと・verifier を起動しないこと・`seal-run:` の stderr 報告を含む。契約テストは節を切り出し
  3 固定句と解放コマンドの出現を検査（`--release --runid` の出現数 ≥ 3 かつ各固定句の後 3 行以内に出現）。既存 `tests/test_v013_contracts.py:101-103`（test_f）が
  依存する行頭 `` `SEALED_MANIFEST="$(python3 "$SD/scripts/read-manifest.py" `` の行の形は崩さない（Opus N5）。行番号は rev.7 時点で組込み deny 本文が
  `SKILL.md:284`／`config-schema.md:157`（Opus N3。内容一致を優先）。
- (6) `read-manifest.py`: `{"sealed":false}`／`sealed` 無し／`[]`／`null` の 4 入力で exit 2・stdout 空・stderr に `manifest is not sealed`
  （hash は各入力の実バイト列に一致させる）。`tests/test_read_manifest.py` に固定名で 4 ケース追加: `test_sealed_false_is_rejected`、
  `test_missing_sealed_key_is_rejected`、`test_array_manifest_is_rejected`、`test_null_manifest_is_rejected`。既存 6 テストは fixture が `"sealed":true` で改変不要。
- (7) `codex-dispatch.py` は変更しない。`python3 -m unittest tests.test_codex_dispatch` green。

### S1-#54-1
- (8) 3 probe とも §0-4 判定表を満たす。各 probe テストに次の **固定名**で追加（#3 は既存 `test_disabled_by_config`）: `test_absent_key_is_not_configured`、
  `test_empty_object_key_is_enabled`（stub が呼ばれる）、`test_non_boolean_enabled_is_invalid_config`（`"false"`）、`test_non_object_key_is_invalid_config`、
  `test_invalid_json_config_is_invalid_config`、`test_missing_config_file_is_invalid_config`、`test_non_object_top_level_is_invalid_config`、
  `test_non_string_bin_is_invalid_config`（subTest: `[]`・`""`）、`test_omitted_config_flag_is_invalid_config`（`--config` 自体を渡さない）、
  `test_disabled_with_invalid_bin_is_disabled_by_config`（`{"enabled":false,"bin":[]}` → `disabled-by-config`。Sol R3-4）
  （graphify／codegraph／cocoindex 各 10 件）＋ cocoindex のみ `test_non_finite_or_non_number_min_score_is_invalid_config` と
  `test_disabled_with_invalid_min_score_is_disabled_by_config`（`{"enabled":false,"minScore":"x"}` → `disabled-by-config`。Sol R4-3）（2 件）。**計 32 件追加**。
  必須 subTest 入力（Sol R4-4）: `test_non_boolean_enabled_is_invalid_config` は `"false"`・`1`；`test_non_object_key_is_invalid_config` は `true`・`"x"`・`[]`・`null`；
  `test_non_string_bin_is_invalid_config` は `[]`・`1`・`null`・`""`；`test_non_finite_or_non_number_min_score_is_invalid_config` は `"0.4"`・`true`・`null`・
  `NaN`・`Infinity`・`-Infinity`（config は Python `json.dumps` で書き、NaN/Infinity literal を含める）。
  **外部 tool 非起動の検査（Sol R4-5）**: `available:false` の各ケースで、config に有効な `bin` を置けるケースは stub path を `bin` に置き、置けないケース
  （キー不在・キー非 object・不正 JSON・config 不在・top-level 非 object・`bin` 不正）は **既定名（`graphify`／`ccc`／`codegraph`）の記録用 stub を `PATH` 先頭に
  配置**して、**`calls.log` が不在**であることを assert（`command -v` の非実行は契約に含めない — Sol R2-10）。併せて `.codegraph/`・`graphify-out/`・
  `.cocoindex_code/`・`.gitignore` が生成／変更されないことを assert。**cocoindex の非起動系ケースでは fixture repo に `.cocoindex_code/settings.yml` を必ず置く**
  （Opus B4: 置かないと `not-initialized` の早期 return で stub が呼ばれず、判定未実装でも通る偽陽性になる）。`test_empty_object_key_is_enabled` は 3 probe とも
  既定名 stub を `PATH` 先頭に置き（`{}` は `bin` を持てない）、cocoindex 版はさらに `.cocoindex_code/settings.yml` を置く（Opus O2-R4）。config 不在系のケースは既存 `run_script` ヘルパーが
  使えないため別ヘルパーを用意する。
- (9) reason 列挙: SKILL.md の 3 probe 段落（:176, :190, :204 の `reason ∈`）と `config-schema.md` の 3 節に `not-configured`／`invalid-config` を追加。
  契約テスト: 各 probe 段落の列挙集合 == {既存 reason} ∪ {`not-configured`, `invalid-config`}（semanticSearch は `gitignore-modified` も）で**完全一致**。
- (10) Phase-5 状態行: 3 ブロックを `*_REASON` 変数による排他表に書き直し（`AVAILABLE` 単独の catch-all 枝なし）。`not-configured` 枝は `install:` を含まず
  「installed」と言わない。ラベル **doc-graph `6-state`（7 messages）、symbol-graph `6-state`、semanticSearch `8-state`**（§0-4 と同値。契約テストで見出しの
  数値も固定 — Sol R4-1）。契約テスト（Sol R2-9）: 各ブロックの箇条書きを reason ごとに 1 行へ対応付け（**各 reason はちょうど 1 つの箇条書きにのみ現れる**。doc-graph の `ok` は gitignoreOk true/false の 2 行を許容）、各行が
  **`→` の右辺（利用者向けメッセージ）だけを取り出して** reason 固有の **記号＋固定句** を含み、かつ他 reason の固定句を含まないことを対応表で検査
  （Sol R3-3、R4-6: 条件側の `disabled-by-config`／`index-failed` の文字で通らないようにする）: `not-configured`→`💡`＋`not configured`、
  `invalid-config`→`⚠`＋`is invalid`、`not-installed`→`💡`＋`install:`、`disabled-by-config`→`💡`＋`disabled`、`index-failed`/`update-failed`→`⚠`＋`failed`、
  `not-initialized`→`💡`＋`isn't indexed yet`、`gitignore-modified`→`⚠`＋`changed while ccc index ran`、`ok`→ 文脈付き `✓ <seam>: active (`
  （doc-graph の gitignoreOk false 行のみ `⚠ doc-graph: active but`）。`ok` の検査は裸の `active` ではなく上記の文脈付きパターンを使う（Sol R5-1:
  `not active` を含む正しい非稼働行を誤検出しない）。テスト名 `test_phase5_status_lines_map_each_reason_to_one_branch`。`docs/ADOPTION.md:197-198`／`.ja.md:179-180` の状態行要約に `not configured`／`未設定` と
  `invalid`／`不正` を追加。
- (10b) Phase 0 の 3 probe 段落が `SYMBOL_GRAPH_REASON`／`DOC_GRAPH_REASON`／`SEMANTIC_SEARCH_REASON` を **probe JSON の `["reason"]` から代入する完全な式**で
  束縛する（契約テスト `test_phase0_binds_reason_from_each_probe_json` は `<VAR>_REASON=` … `["reason"]` の対応 3 組と、`<VAR>_PROBE_JSON="$(bash "$SD/scripts/<probe>.sh"`
  の捕捉行 3 本を検査。Sol R3-2、Opus B6）。
- (11) `skills/init/SKILL.md:147-163` の symbolGraph／docGraph／semanticSearch の OMIT 文 3 か所に「absent key ⇒ the audit reports `not-configured`
  and never runs the tool」の 1 句（mdq／context-mode／ax／codex の OMIT 文は変更しない）。契約テスト: init SKILL.md 内の `not-configured` 出現が
  ちょうど 3 回で、各出現行（またはその箇条書き）が上記 3 キー名のいずれかを含む。

### S1-#54-2
- (12) `cocoindex-probe.sh`: 初期化済み判定は `[[ -f "$REPO_ROOT/.cocoindex_code/settings.yml" ]]`。テスト追加 `test_legacy_dir_without_settings_is_not_initialized`
  （dir のみ → `not-initialized`、`calls.log` 不在）。既存 `test_stub_installed_reports_ok`／`test_stub_index_failure_reports_index_failed` は fixture に
  `settings.yml` を置いて green に保つ。config-schema.md:39 の「runtime reads only `enabled` and `bin`」は「the probe validates `enabled`/`bin`/`minScore`;
  Phase 2 uses `minScore`」に更新（Sol R3-7、契約テストで文字列検査）。
- (13) `.gitignore` 検出: テスト追加 `test_index_that_modifies_gitignore_is_reported`（stub `index` が `.gitignore` に追記 → `reason=="gitignore-modified"`、
  `semanticSearchAvailable==false`、**`.gitignore` は stub が書いたままで probe は書き戻さない**（バイト列一致））、
  `test_index_that_creates_gitignore_is_reported`（事前に不在 → stub が生成 → 同上、ファイルは残る）、`test_gitignore_change_wins_over_index_failure`
  （追記後に exit 1 → `gitignore-modified`。Sol R3-8）。計 3 件追加（(12) の 1 件と合わせて cocoindex は 4 件 — Opus O2-R5）。
- (14) 文書: SKILL.md:200-215 段落を `settings.yml` マーカー＋自動 init の原因＋検出の記述に更新。`config-schema.md:39` 行と `:297-320` 節、
  `ADOPTION.md:170-172`／`.ja.md:153-156`、`init/SKILL.md:155-158` の「`.cocoindex_code/` 不在／already exists」を `settings.yml` 基準に改める。
  加えて `.cocoindex_code/` の存在だけで初期化済みとする残存記述 4 か所（`skills/init/SKILL.md:52`、`cocoindex-probe.sh:13-17` ヘッダ、`config-schema.md:309`、
  `skills/audit/SKILL.md:211` — Opus N1）も `settings.yml` 基準に改める。契約テスト: 上記 5 文書それぞれで `.cocoindex_code/settings.yml` の literal が ≥1 回、
  かつ **`not-initialized` を説明する同一段落（表では同一行）内**に `settings.yml` が現れ、`.cocoindex_code/` の直後に `already exists`／`不在`／`present` が続く行が
  `settings.yml` を伴わずに残っていない。状態行に `reason:gitignore-modified` の枝（§0-5 文言。`checkout` を含まない）。

### S1-既往 red（§0-12）
- (15) `tests/data/dir-framework-scope/` の 3 fixture が存在し、`tests/test_import_audit_scope.py` の当該テストが fixture のみで green（`DIR_FRAMEWORK`
  参照 0、`skipTest` 呼び出し 0）。テスト名 `test_dir_framework_fixture_scope_is_not_imported_with_24_rules_and_48_paths`。3 fixture の sha256 literal（§0-12 の 3 値）と `"auditScope" not in config` を assert。`python3 -m unittest tests.test_import_audit_scope` green・skip 0。

### S2
- (16) `python3 -m unittest tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff` green。
  5 面の版が `0.13.2`、engine-shas に `0.13.2`（max semver）、refresh 段落 en/ja が `{0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.13.1, 0.13.2}` を含み §0-6 の行文言に一致。
- (17) ADOPTION §7 `**v0.13.2 behavior changes:**`／`**v0.13.2 の挙動変更:**` 段落が en/ja に 1 つずつあり、§0-7 の 4 点と移行注記を含む
  （契約テスト `test_v0132_behavior_changes_paragraph` — Sol R3-12: en 段落は次の **肯定形の固定文 5 つ**をこの文言で含む:
  ① `omitted docGlobs now defaults to ["docs/**/*.md","*.md"] for pre-flight fix classification; CLAUDE.md and AGENTS.md are always denied (case-insensitive)`
  ② `an absent docGraph / semanticSearch / symbolGraph key reports not-configured and never runs the tool; an invalid key reports invalid-config`
  ③ `CocoIndex counts as initialized only when .cocoindex_code/settings.yml exists; a .gitignore change during ccc index reports gitignore-modified and is never reverted by the audit`
  ④ `any seal-run.py or read-manifest.py failure releases the run and stops; read-manifest.py rejects an unsealed manifest`
  ⑤ `configs that relied on auto-detection must add the key via /docaudit:init`。
  ja 段落は同じ順序で次の **肯定形の固定文 5 つ**をこの文言で含む（Sol R4-7）:
  ① `docGlobs を省略した場合、pre-flight fix の分類は ["docs/**/*.md","*.md"] を既定とする。CLAUDE.md と AGENTS.md は大文字小文字を区別せず常に拒否される`
  ② `docGraph / semanticSearch / symbolGraph のキーが無い場合は not-configured を報告し tool を一切起動しない。キーが不正な場合は invalid-config を報告する`
  ③ `CocoIndex は .cocoindex_code/settings.yml が存在する場合のみ初期化済みとみなす。ccc index の実行中に .gitignore が変化した場合は gitignore-modified を報告し、監査は復元しない`
  ④ `seal-run.py または read-manifest.py が失敗した場合は run を解放して停止する。read-manifest.py は未 seal の manifest を拒否する`
  ⑤ `自動検出に頼っていた config は /docaudit:init でキーを追加するまで not-configured になる`
  （検査方法 — Opus B3: 段落を `" ".join(paragraph.split())` で空白正規化しバッククォートを除去してから `assertIn`。既存 `test_v0131_docs_contracts.py:93` と
  同じ正規化。本文は文書慣習どおりハードラップ・コードスパン付きで書いてよい）。
- (18) `tests/test_release_handoff.py` が新 script（`2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`、tag `docaudit--v0.13.2`、Issue 52-54、
  title `docaudit v0.13.2 — report-only probes, docGlobs default, seal stop (#52–#54)`、notes 必須語 `#52 #53 #54 not-configured settings.yml`）を
  対象にして green。`bash -n` 通過。
- (19) test_j: `0.12.0` 残存は allowlist のみ（refresh 行 regex を §0-6 の新文言に更新）。

### 共通
- (20) フルスイート green・skip 0。件数の自己申告ではなく **固定テスト名の網羅**で判定（Sol R2-11、R3-13）: boss が `python3 -m unittest -v` の出力に
  DoD (2)(3)(4)(5)(6)(8)(9)(10)(10b)(11)(12)(13)(14)(15)(17) に列挙した固定テスト名がすべて現れることを grep で確認。契約テストの固定名（上記以外）:
  (4) `test_doc_globs_rows_no_longer_say_fail_closed`、(5) `test_phase3_three_stop_branches_release_the_run`、(9) `test_probe_reason_enumerations_match_fixed_sets`、
  (11) `test_init_skill_marks_three_omit_rules_as_not_configured`、(14) `test_settings_yml_marker_documented_in_five_files`、
  (§0-4 B1) `test_three_seams_no_longer_documented_as_auto_used`（Opus O2-R1）。worker は Stage 報告に `Ran N tests` の実数を添える。
- (21) `bash -n` が 3 probe＋handoff で通り、`python3 -m py_compile` が変更 .py 全てで通る。
- (22) 変更範囲外のファイルに差分が無い（`git status --short` で確認。未追跡 `?? .claude/` は本タスク以前から存在する worktree コピーで対象外 — Opus N4）。

## 7. 変更範囲

- 許可（S1）: `skills/audit/scripts/{fix-scope.py,read-manifest.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh}`、
  `skills/audit/SKILL.md`、`skills/init/SKILL.md`、`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、
  `tests/{test_read_manifest.py,test_graphify_probe.py,test_cocoindex_probe.py,test_codegraph_probe.py,test_import_audit_scope.py,test_wp12_contracts.py}`、
  新規 `tests/test_v0132_contracts.py`、新規 `tests/data/dir-framework-scope/{audit-scope.json,doc-audit.json,paths.txt}`。
- 許可（S2）: `.claude-plugin/plugin.json`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`skills/audit/references/engine-shas.json`、
  `tests/{test_v013_contracts.py,test_v0131_docs_contracts.py,test_scaffold.py,test_release_handoff.py}`、
  新規 `tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh`。
- 禁止: `codex-dispatch.py`、`decide-verdict.py`、`seal-run.py`、`tree-digest.py`、`import-audit-scope.py`、`sibling-scan.py`、`mdq-index.sh`、
  `ax-probe.sh`、`codex-probe.sh`、`references/workflow-template.js`、`README.md`（badge 自動追従）、`agents/**`、`.gitignore`、`docs/superpowers/**`、
  `tasks/route/2026-08-27-*/**`、`.claude/**`、`~/Projects/dir-framework/**`（読み取りのみ可）。CHANGELOG を新設しない。
- 標準文言: **許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 8. 検証コマンド一式

```
python3 -m unittest discover -s tests -t .                       # フル（skip 0・件数を報告）
python3 -m unittest tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe tests.test_read_manifest tests.test_v0132_contracts
python3 -m unittest tests.test_wp12_contracts tests.test_codex_dispatch tests.test_import_audit_scope
python3 -m unittest tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_scaffold tests.test_release_handoff   # S2
bash -n skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh
bash -n tasks/route/2026-08-28-issues-52-54-v0.13.2/release-handoff.sh                                                        # S2
python3 -m py_compile skills/audit/scripts/fix-scope.py skills/audit/scripts/read-manifest.py
python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run | python3 -c 'import json,sys;print(json.load(sys.stdin)["stampVersion"])'  # S2
grep -c 'get("docGlobs", \[\])' skills/audit/scripts/fix-scope.py                                                              # 0
git status --short                                                                                                            # 許可外差分なし
```
