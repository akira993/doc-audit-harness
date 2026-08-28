# PLAN — Issues #56(第1段)・#57・#58・#59(最小案)・#60 → docaudit v0.14.0（rev.7, 2026-08-28 — Sol R1〜R5・Opus O1〜O6/N1〜N3・advisor 反映。#59 ledger は見送り。実装承認）

## 0. 決定事項（route 手順 1 の代替 — 自律実行につき boss 裁定。前回 v0.13.2 §0 と同じ方式）

ユーザー指示: 「Issue を確認し、丁寧に対応してください。」（版・出荷範囲の指示なし）。対象は open の 5 件 `#56 #57 #58 #59 #60`
（HEAD `dfdb8a9`、tracked 差分 0、フルスイート baseline **Ran 551 tests OK, skip 0, 143s** — boss 実測）。
事前調査 `investigate-report.md`（Terra）。計画批判 `critique-r{1..5}-answer.md`（Sol 5 往復＝上限。対応表は REVIEW.md）。**対象 OS は POSIX（macOS/Linux）**（Windows 非対象は既存範囲、文書に 1 文）。

1. **版は 0.14.0（minor）。** probe 永続化ファイル・probe 新キー・`invalid-config` 意味論・新スクリプト 1 本の additive な runtime 変更。PR レビュー時にユーザーが patch を望めば 0.13.3 へ変更可（tag 前）。PR 本文に明記。
2. **#56 は第 1 段のみ**（第 2 段はユーザー判断 — 最終報告で boss 推奨「4 seam は既定有効維持・非対称を意図的と文書化 → close」を添えて諮る）。
3. **#59 は Issue の最小案（運用注記）のみ出荷し、ledger は見送り** — boss 裁定（advisor 同意）。理由と次版の設計制約は `59-design-note.md`。スコープ縮小はユーザー判断につき**最終報告の第 1 項目**で諮る。
   PR は **`Closes #57 #58 #60`** のみ。#56・#59 は「partially addresses（remain open）」。
4. **#58 — `import-audit-scope.py` の `safe_path` のみで、repo-root 配下の絶対パスを相対化して既存検査へ通す。** 共有 `validate_repo_path`（`docaudit_paths.py:37`）と SKILL.md:13/:26 は不変。
   実装: `main()` は `repo = os.path.realpath(args.repo_root)`（:551）の**前に** `repo_apparent = os.path.abspath(args.repo_root)` を保持し `safe_path(repo, repo_apparent, path, errors, label)` へ渡す。
   `safe_path` は `os.path.isabs(path)` のとき**正規化せず** `path.split("/")[1:]` の全成分を検査し `""`／`"."`／`".."` を含めば `errors`（`<label> invalid: absolute path must not contain empty, "." or ".." components`）。
   次に `root ∈ (repo_apparent, repo)` の順で `path == root` または `path.startswith(root + "/")` を照合、`rel = path[len(root)+1:]` を `validate_repo_path(repo, rel, must_exist=False)` へ。不一致は従来どおり拒否。相対入力の経路・保存形式は不変。Windows 形式は非対象（config-schema.md に 1 文）。
   テスト `test_absolute_path_cases_v014`: 明示 symlink fixture、`--config`／`--scope` × {A real/real（受理）、B symlink/symlink（受理）、C symlink root・real path（受理）、D real root・symlink path（拒否 — 文書化）、E repo 外絶対、F `<root>/sub/../.claude/x.json`、G `<root>/../x.json`、H 中間 symlink、I 末尾 `/`、J `//`}（E〜J 拒否）= **20 ID**。`:618` 不変。
5. **#56 第 1 段 — 適用範囲は「正常な top-level object 内の seam 設定不正」。** 読めない config・top-level 非 object・config 不在は**従来どおり Phase 0 より前（SKILL.md:9,14,25）で停止**し、Phase-5 `invalid-config` 行には到達しない。probe script 側の行 6〜8 は**単体呼び出し時の防御**（SKILL の probe 段落に 1 句）。
   **CLI 3 probe（`indexing`／`webExtract`／`codexReview`）の判定表**:
   | # | 入力 | 結果 |
   |---|---|---|
   | 1 | キー不在 | 有効（既定 true） |
   | 2 | `{}` | 有効 |
   | 3 | `{"enabled": false}` | `disabled-by-config` |
   | 4 | `enabled` が JSON boolean 以外 | `invalid-config` |
   | 5 | キーが object 以外（`null` 含む） | `invalid-config` |
   | 6 | config が JSON 不正 | `invalid-config`（防御） |
   | 7 | `--config` 未指定 → 有効／`--config ""`（明示空）→ `invalid-config`／指定ファイル不在 → `invalid-config`（防御。R5-8: 指定有無は別フラグで保持し、`CONFIG=""` を「未指定」の印に使わない） | |
   | 8 | top-level が object 以外 | `invalid-config`（防御） |
   | 9 | `bin` が存在して非文字列・空文字列・**NUL を含む**（R5-3） | `invalid-config` |
   | 10 | `{"enabled":false,"bin":[]}` | `disabled-by-config` |
   評価順序: config 解析（6・7・8）→ キー存在（1）→ object 型（5）→ `enabled` 型（4）→ `enabled:false`（3）→ `bin`（9）。**`invalid-config`／`compound` の出力 `bin` は seam 既定名（`mdq`／`ax`／`codex`）**（R5-4、値を完全一致で assert）。
   **CLI 用 ID 集合（3 probe 共通、20 ID）**: `absent, empty, disabled, en_str, en_int, en_null, key_null, key_true, key_str, key_list, cfg_omitted, cfg_empty, cfg_missing, cfg_broken, top_list, top_null, bin_int, bin_empty, bin_nul, compound`。
   出力形: 既存分岐のキー集合は不変（**§0-8 の additive 3 キーを codex の全分岐に加える点のみ例外**）。`invalid-config` は not-installed 形。全分岐 exit 0・JSON 1 行。
   **contextMode（`bin` 無し）は 13 ID**: `absent, empty, disabled, en_str, en_int, en_null, key_null, key_true, key_str, key_list, cfg_broken, top_list, top_null` → `true, true, false, invalid×7, invalid×3`。式（SKILL に完全掲載）:
   `CM_ENABLED="$(python3 -c 'import json,sys
try:
    c=json.load(open(sys.argv[1]))
    if not isinstance(c,dict): raise ValueError
    if "contextMode" not in c: print("true")
    else:
        v=c["contextMode"]
        print("invalid" if not isinstance(v,dict) or ("enabled" in v and not isinstance(v["enabled"],bool)) else ("false" if v.get("enabled") is False else "true"))
except Exception:
    print("invalid")' "$CFG")"`
   `invalid` → probe スキップ、`CM_AVAILABLE=false`、`CM_STATUS=invalid-config`。契約テストは SKILL からコードスパンを抽出して 13 ID で実行。
   波及先: (a) mdq 確認ゲート（:95）は `not-installed`／`index-failed`／**`invalid-config`** で発火。(b) Phase 0 で `MDQ_REASON`／`AX_REASON` を束縛し、Phase-5 に `invalid-config` 枝 3 本（mdq 枝は `MDQ_AVAILABLE false` の 💡 行より前）:
   `⚠ mdq: doc-audit.json indexing is invalid — mdq not probed this run; fix the key. [non-blocking]`／`⚠ context-mode: doc-audit.json contextMode is invalid — not probed this run; fix the key. [non-blocking]`／`⚠ ax: doc-audit.json webExtract is invalid — not probed this run; fix the key. [non-blocking]`。
   codex は `not-active (<CODEX_REVIEW_REASON>)` が運ぶ。(c) `required:true`＋`enabled:"false"` → REFUSED: plan 完全一致 `{"action":"not-active","promptVariant":null,"reason":"invalid-config","state":"not-active"}`；gate は既存 `decide-verdict.py:797`（engine 変更なし、テスト追加）。
   (d) `start-run.py:247`／`decide-verdict.py:710` 不変。(e) SKILL の reason 列挙 **3 か所 ＝ mdq 散文（:80-81）・ax（:138）・codex（:151）** に `invalid-config` を加える（symbolGraph/docGraph/semanticSearch の列挙 :175/:194/:212 は不変 — `test_v0132_contracts.py:224-248` が完全一致で固定。Opus N3）。`test_probe_reason_enumerations_match_fixed_sets` は ax/codex 集合のみ更新。
   文書: `config-schema.md:33-36` の 4 行（「`enabled` は JSON boolean 必須。`enabled:false` が最優先で `disabled-by-config`。それ以外で非 boolean `enabled`／非 object キー（`null` 含む）／（CLI 3 seam のみ）非文字列・空・NUL 入り `bin` は `invalid-config`（tool 不起動・⚠ 状態行。`indexing` は確認ゲート）。キー不在は従来どおり有効（意図的な非対称）」）。`skills/init/SKILL.md` 不変。
6. **#57 — Phase-0 probe 結果の run-dir 永続化と、Phase-5 状態行入力の一本化（表示専用・fail-open）。** 新 `skills/audit/scripts/probe-record.py`:
   - 共通引数 `--repo-root "$CLAUDE_PROJECT_DIR" --runid "$RUNID" --evidence "$EVIDENCE"`。repo-root は最初に `os.path.realpath`（`open-run.py:129-130` と同契約）し、その fd から `.claude`→`state`→`docaudit-run`→`<RUNID>` を成分ごとに `os.open(name, O_RDONLY|O_DIRECTORY|O_NOFOLLOW, dir_fd=parent)` で辿る。`RUNID` は `start-run.py:17` の正規表現。`EVIDENCE.runDir` の realpath 一致（不一致 exit 2）。
   - `--seam <name> --stdin`: 読み `O_RDONLY|O_NOFOLLOW`＋`S_ISREG`、一時ファイル `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` 0o600＋fsync、`os.replace(..., src_dir_fd=fd, dst_dir_fd=fd)`、失敗時 `os.unlink(dir_fd=fd)`。`--seam` 固定集合 `{indexing, mdqHealth, mdqDegrade, contextMode, webExtract, codexReview, codexReviewState, symbolGraph, docGraph, semanticSearch}`（**10 seam**。`codexReviewState` は Phase 4 の evidence 書き込み直後に `{"state":"<CODEX_REVIEW_STATE>"}` を記録 — Opus O1）。
     **seam 別 schema ＝ availability/reason 判別の分岐別 union、各分岐の必須キーと型を検査（余分キーは許容 — Opus N1: 表示専用ファイルを全 probe の出力形式に強結合させない）**:
     `indexing`: (false,`disabled-by-config`,{mdqAvailable,reason})／(false,`not-installed`|`invalid-config`,{…,bin})／(true,`indexed`,{…,bin,dbDir})／(false,`index-failed`,{…,rc:int,bin})；
     **`mdqHealth`: `mdq-health.py` の実出力 `{files:int≥0, chunks:int≥0, searchSmoke:bool, healthy:bool, status∈{ok,empty-index,search-broken,probe-error}}`（R5-1 — 5 キー verbatim）**；`mdqDegrade`: `{degrade∈{n/a,user-approved,non-interactive}}`；
     `contextMode`: (true,{contextModeAvailable,contextModeHealthy:bool,status∈{ok,degraded,probe-error}})／(false,{…,contextModeHealthy:null,status∈{disabled-by-config,not-installed,probe-error,invalid-config}})；
     `webExtract`: `{axAvailable,axBin:str,axVersion:str|null,reason}`、`axAvailable == (reason=="ok")`、reason∈{ok,not-installed,disabled-by-config,invalid-config}；
     `codexReview`: `codex-probe.sh` の 5 キー＋§0-8 の 3 キー、`codexReviewAvailable == (reason=="ok")`、reason∈{ok,not-installed,disabled-by-config,probe-exec-failed,invalid-config}；`codexReviewState`: `{state∈{completed,execution-failed,ref-invalid,skipped-full-run,not-active}}`（`docaudit_cache.CODEX_REVIEW_STATES` と同一集合）；
     `symbolGraph`／`docGraph`／`semanticSearch`: 各 probe script の分岐どおり（キー集合は v0.13.2 の Opus B5 不変、reason 集合は SKILL の列挙と一致、`available == (reason ∈ OK_REASONS[seam])` — worker が script から表を起こし、テストが SKILL の列挙と照合）。
     違反 exit 2・ファイル不変。stdout に保存後の全体。
   - `--read`: 同じ検査で読み、stdout に `{"schemaVersion":1,"seams":{...},"rebind":{...}}`。**`rebind` は 7 行それぞれの「Phase-5 入力の正規化済み値」を script が算出**（R4-7 — 完全性だけでなく値まで）:
     `mdq`: `{"state":"complete"|"unknown","available":bool,"reason":str,"bin":str,"healthy":bool|null,"chunks":int|null,"status":str|null,"degrade":str}`；`context-mode`: `{state,available,healthy,status}`；`ax`: `{state,available,reason}`；
     `codex-review`: `{state,available,reason,"reviewState":str|null,"callerCodexHomeDisplay":str,"callerCodexHomeSource":str,"callerAuthFile":str}`（`reviewState` は `codexReviewState` 記録から。未記録なら `null`。**`*Display` は表示用に可視エスケープ済み・1 行・200 文字上限。切り詰めは生文字列を 200 文字に切ってからエスケープ**（R5-5）。`json.dumps(v)[1:-1]` 相当。`null` → `(null)`）；
     `symbol-graph`／`doc-graph`／`semantic-search`: `{state,available,reason,bin,(docGraph のみ gitignoreOk)}`。
     完全性条件: mdq は `indexing`＋`mdqDegrade`、`indexing.mdqAvailable:true` なら `mdqHealth` も。他は各 seam 1 件。不在ファイル → 7 行 `unknown`（値は null）exit 0。破損／schema 違反 → exit 2。
   - **Phase 5 は初回・再開を問わず状態行入力を `probe-record.py --read` の `rebind` から取る**（R4-2/R4-7 — 表示用エスケープと対応表の適用を script に一本化し、SKILL の python -c 表示式を置かない）。**唯一の例外（Opus O6）**: mdq 行の Phase-3 refresh 失敗接尾辞 `[Phase-3 refresh failed: <detail>; grep-degrade]` の `<detail>` は従来どおり会話変数（SKILL.md:411）から補い、再開後は接尾辞を省く。
     Phase 0〜4 が使う運用変数（`MDQ_AVAILABLE`、`CODEX_REVIEW_AVAILABLE`、`AX_BIN` 等）は従来どおり probe JSON から束縛（不変）。状態行は既存どおり **gate 起動前**に生成する（SKILL.md:596-599 — gate stdout は使えない。Opus O1）。
   - **codex-review 行の規則（R5-2 改・Opus O1/O2）**: 基本状態（4-way）は `CODEX_REVIEW_STATE` で分岐する既存文言（`test_v013_contracts.py:82-86` が固定するリテラルを温存）。Phase 5 では `CODEX_REVIEW_STATE` を `rebind["codex-review"].reviewState` から再束縛する（初回は Phase 4 で記録した値と同一）。`reviewState` が `null`（記録前に中断・再開）→ `⚠ codex-review: state unknown after resume [non-blocking]`。
     `rebind["codex-review"].state` が `unknown`（probe 記録欠損）で `reviewState` が非 null → 4-way の行は出し、接尾辞を ` (caller info unknown after resume)` にする。
   - **失敗規約（fail-open）**: 記録（write）失敗は `⚠ probe-record: <seam> not recorded (<stderr 先頭行>) [non-blocking]` を Phase-5 に 1 行添えて続行。`--read` 失敗（exit 2）は 7 行すべて unknown 形。いずれも verdict 不変。
   - **EVIDENCE には入れない・gate は読まない・verdict 不変**（`grep -c phase0-probes decide-verdict.py`=0）。
   - SKILL.md Phase 0: 各 probe 直後に記録行（9 seam。`MDQ_PROBE_JSON`／`AX_PROBE_JSON` を新設。mdqHealth は verbatim、mdqDegrade はゲート評価後、contextMode は合成 JSON）。Phase 3 の mdq 再索引（:407-412）後に `indexing`／`mdqHealth` 再記録。
   - **7 行の unknown 文言**: `⚠ mdq: state unknown after resume [non-blocking]`／`⚠ context-mode: …`／`⚠ ax: …`／`⚠ symbol-graph: …`／`⚠ doc-graph: …`／`⚠ semantic-search: …`（codex-review は上記の規則）。7 行の順序は既存どおり。Phase-3 refresh 失敗接尾辞は再開後は付けない（文書化）。code-review 行は対象外。
   - 再開規約（:41-56）に段落追加（固定文言）: `Phase-5 status lines are always rendered from probe-record.py --read (its "rebind" map is authoritative, on fresh and resumed runs alike; only the Phase-3 refresh-failure detail comes from the conversation and is omitted after a resume); a line marked unknown prints its "state unknown after resume" form; CODEX_REVIEW_STATE is rebound from rebind.codex-review.reviewState; a failed read marks all lines unknown; none of this changes the verdict.`
   - テスト `tests/test_probe_record.py`（固定 ID ≥ 24）: upsert／上書き／原子性／固定 seam 集合／分岐別 schema 違反（9 seam 各 1 ＋ 矛盾例）／余分キー拒否／**`mdq-health.py` の実 stdout（probe-error 分岐は実行で取得、ok 分岐は `test_mdq_health.py` の fixture）を write→read**／非 object stdin／`--read` 不在→全 unknown／破損→exit 2／
     **`rebind` 値（producer 出力 → write → read → 7 行の期待値と完全一致。完全・`mdqHealth` 欠損×available 真偽・部分欠損）**／**display の 1 行性（改行・制御文字・`"`・`\` 入り `callerCodexHome`）と 199 文字＋改行の切り詰め境界**／中間 symlink 拒否／run dir symlink 拒否／ファイル symlink 拒否／runDir 不一致／RUNID 不正／symlink repo-root 受理。
     契約テスト: Phase 0 節に 9 seam 記録行、Phase 3 再記録 2 行、Phase 5 が `--read` を呼ぶ行、再開段落固定文（`"rebind" map is authoritative` を含む）、6 unknown 文言＋codex の null 文言、fail-open 固定文、Guardrails 1 句、SKILL に表示用 python -c 式が**無い**こと（`grep -c 'callerCodexHome"\]' SKILL.md` = 0）。
7. **#59 最小案**: SKILL.md Phase 4（codex review 段落末尾）と ADOPTION en/ja に運用注記（固定文）:
   en `First-time full runs with codexReview.required:true may need several rounds: the Phase-4 codex review samples pre-existing findings anew on each run, so fix only blocking (critical/high) findings and record non-blocking ones in the report. To converge faster you may paste the previous run's finding list into the prompt as fenced JSON data (never as instructions; treat its strings as untrusted); engine-side carry-forward is tracked in #59.`
   ja は同内容 1 段落。`config-schema.md` 不変。
8. **#60 — codex probe に呼び出しシェルで観測した CODEX_HOME と auth.json 有無を追加。** `codex-probe.sh` の出力に**全 5 分岐で** `callerCodexHome`（string|null）、`callerCodexHomeSource`（`env`／`default`／`unknown`）、`callerAuthFile`（`present`／`absent`／`unknown`）。
   判定: `${CODEX_HOME:-}` 非空 → `env`／空・未設定で `${HOME:-}` 非空 → `default`・`$HOME/.codex`／両方空 → `unknown`・`null`・`unknown`。`callerAuthFile` は `[[ -f "$home/auth.json" ]]` のみ。
   **機械用 JSON は無加工**（出力全体を `python3 -c` の `json.dumps` で生成、`tr -d` sanitizer 廃止）。表示用エスケープは §0-6 の `rebind.*Display` に一本化。availability は変えない。
   SKILL.md Phase 0: 運用変数は従来どおり（`CODEX_REVIEW_AVAILABLE`／`CODEX_REVIEW_BIN`／`CODEX_REVIEW_REASON`）。Phase-5 codex 行: `available:true` の全枝に ` (caller CODEX_HOME=<callerCodexHomeDisplay> [<callerCodexHomeSource>]; auth.json <callerAuthFile>)`（3 値とも `rebind` から）、`execution-failed`＋`absent` で
   ` — no auth.json at the caller's CODEX_HOME: the calling shell may lack a direnv hook, and a wrapper's own environment is not visible to the probe; check the environment before suspecting the config`。Phase 4 実行行直後に env 注記 1 文。
   文書: `config-schema.md:228-236`・`ADOPTION.md:122-126`／ja に wrapper（`direnv exec <repo> codex` 相当）と caller 表示の限界。既定 `~/.codex` の根拠: boss 実測。
   テスト `test_codex_probe.py`: **最小 env ＝ `{"PATH": os.environ["PATH"]}` ＋ ケース別の `HOME`／`CODEX_HOME` のみ**（`python3` と偽 bin を解決できる PATH は必須 — Opus N2。`os.environ` 継承は不可）で 7 ID（`env_auth, env_noauth, default_auth, default_noauth, env_empty, home_unset, env_special_chars`）＋ 5 分岐でキー集合完全一致＋`test_json_escaping_of_bin_and_home`（改行・`"`・`\` を含む値の round-trip）。
9. **Stage 分割とモデル**: S1a（#58・#56 第 1 段・#60・#59 最小案）Terra `medium`／S1b（#57）Terra `high`／S2 Luna `medium`。同一 branch `fix/v0.14.0-issues-56-60`、Stage ごとに commit。
   **スコープ検査の権威元は boss commit**: `allowlist.txt`（tracked 差分の許可一覧）と `baseline-hashes.txt`（保護 root `.envrc .gitignore .claude/settings.local.json data/ .serena/ docs/superpowers/` 配下の全 path について `sha256  mode  type  path`）を `SCOPE_COMMIT` に固定。
   §8 の検査は (1) tracked 差分＋未追跡（`--ignored` 無し）⊆ allowlist、(2) 保護 root を再列挙し **path 集合・種別・mode・hash の完全一致**（追加・削除・symlink 置換を検出 — R1-15 再々対応）、(3) task dir の boss 文書 5 つは直前 boss commit と byte 比較、の 3 段。log/prompt/answer の固定 glob のみ除外。
10. **S2 の固定内容**: `.claude-plugin/plugin.json` → `0.14.0`。`ADOPTION.md:225`／`ja:205` の `Version 0.14.0`。refresh 段落（`ADOPTION.md:295`／`ja:270`）を `… 0.13.2 … to 0.14.0`。`engine-shas.json` に `0.14.0`（テンプレート不変、3 hash 同値）。`tests/test_scaffold.py:214,217,218,242,245,246,312`／`test_v013_contracts.py:201` を `0.14.0`。**`test_v013_contracts.py:210,215`（test_j の refresh 許可 regex、en/ja）の版列挙も新文言に更新**（Opus O3 — 未更新だと正しい S2 で test_j が落ちる）。
   ADOPTION §7 `**v0.14.0 behavior changes:**`／`**v0.14.0 の挙動変更:**`（en/ja 各 1、固定文 6 つ）:
   ① `indexing / contextMode / webExtract / codexReview keys now require a JSON boolean enabled; unless enabled is false, a non-boolean enabled, a non-object key (including null), or — for indexing / webExtract / codexReview — a non-string, empty, or NUL-containing bin reports invalid-config and never runs the tool (an absent key still defaults to enabled; a non-string bin is no longer coerced; an unreadable config still stops the audit before Phase 0 as before)`
   ② `an invalid indexing key fires the Phase-0 mdq confirmation gate like not-installed`
   ③ `codexReview.required:true combined with an invalid codexReview key is now REFUSED instead of silently running codex`
   ④ `Phase-0 probe results are persisted to $RUN_DIR/phase0-probes.json (display-only, never a verdict input); Phase-5 status lines are rendered from that record on fresh and resumed runs and print "state unknown after resume" when it is missing or unreadable`
   ⑤ `the codex probe reports the caller's CODEX_HOME and whether auth.json exists there (display-only; a wrapper's own environment is not observed)`
   ⑥ `import-audit-scope.py accepts an absolute --config/--scope path under the repository root (POSIX paths only)`
   ja は同順の肯定形 6 文。`tests/test_release_handoff.py` を新 script `tasks/route/2026-08-28-issues-56-60/release-handoff.sh` に再標的（旧定数 `docaudit--v0.13.2`／`2026-08-28-issues-52-54-v0.13.2` の不在を DoD）: tag `docaudit--v0.14.0`、close `57 58 60`、
   title `docaudit v0.14.0 — invalid-config for all seams, probe persistence, CODEX_HOME visibility`、notes に完全一致で `Closes #57, #58, #60.` と `Partially addresses #56 (stage 1) and #59 (operational note); both remain open.`。handoff 実行はユーザーの PR merge 後。
   **`0.13.2` 残存は repo 全体を grep し許可 path＋行パターンと固定比較**（R5-7）: 許可 = `engine-shas.json`（`"0.13.2": {` の entry）、ADOPTION en/ja の §7 v0.13.2 段落・refresh 段落列挙、`tasks/**`、`tests/test_v0132_contracts.py`、`tests/data/**`。

## 1. 目的
#56（第 1 段）・#57・#58・#60 を v0.14.0 で解消し、#59 は運用注記を出荷して設計制約を固定する。verdict の判定ロジック（`decide-verdict.py`）は変更しない。

## 2. 入力・参照資料
Issues #56〜#60、`investigate-report.md`、`critique-r{1..5}-answer.md`、`59-design-note.md`、前回 PLAN §4／`release-handoff.sh`、
`skills/audit/SKILL.md`（:9-25, :41-56, :72-247, :405-412, :485-590, :668-720, :756-）、`skills/audit/scripts/{import-audit-scope.py,docaudit_paths.py,mdq-index.sh,mdq-health.py,ax-probe.sh,codex-probe.sh,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh,open-run.py,start-run.py,write-evidence.py,codex-review-plan.py,decide-verdict.py(:797,:970-979)}`、
`skills/audit/references/{config-schema.md,engine-shas.json}`、`docs/ADOPTION*.md`、`tests/{test_import_audit_scope,test_mdq_index,test_mdq_health,test_ax_probe,test_codex_probe,test_codex_review_plan,test_decide_verdict,test_v0132_contracts,test_v013_contracts,test_scaffold,test_release_handoff}.py`。

## 3. 担当（boss）
Fable。計画・レビュー・検証コマンド再実行・PR 作成。実装は書かない。

## 4. 実行者（worker）
S1a Terra `medium`／S1b Terra `high`／S2 Luna `medium`（`codex exec -m … -s workspace-write -c model_reasoning_effort=…`）。差し戻しは各セッションへ `resume … -c model_reasoning_effort=medium`。すべて `direnv exec .` 経由・バックグラウンド・`-o` 回収。

## 5. 成果物
- S1a: `import-audit-scope.py`、`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`、SKILL.md（CM 3 値式・`MDQ_REASON`/`AX_REASON`・ゲート・Phase-5 `invalid-config` 3 行・codex 行の caller 接尾辞と診断文・Phase 4 注記 2 つ・reason 列挙・probe 段落の防御 1 句）、`config-schema.md`、ADOPTION en/ja（codex 段落・#59 注記）、
  テスト更新（`test_import_audit_scope`、`test_mdq_index`、`test_ax_probe`、`test_codex_probe`、`test_codex_review_plan`、`test_decide_verdict`(c)、`test_v0132_contracts`）、新規 `tests/test_v014_contracts.py`（S1a 分）。
  ※ S1a 時点では Phase-5 codex 行の caller 接尾辞は `rebind` 参照で書き（S1b が script を供給）、S1a の契約テストは文言のみ検査。
- S1b: `probe-record.py`（新）、SKILL.md（Phase 0 記録 9 行・Phase 3 再記録・Phase 5 の `--read` 行・再開段落・unknown 文言・fail-open 文・Guardrails 1 句）、`config-schema.md`（run dir 節）、`tests/test_probe_record.py`（新）、`test_v014_contracts.py`（追記）。
- S2: `.claude-plugin/plugin.json`、ADOPTION en/ja（版・refresh・§7）、`engine-shas.json`、`test_scaffold.py`・`test_v013_contracts.py`・`test_release_handoff.py`、`release-handoff.sh`（新）、`test_v014_contracts.py`（§7 テスト）。

## 6. 完了条件（DoD）— 機械判定可能な形で（固定テスト名は worker が Stage 報告に列挙、boss が `-v` 出力で全数 grep。件数はテスト内で固定 ID 集合と `len(CASES)` を assert）

### S1a-#58
- (1) `test_import_audit_scope.py::test_absolute_path_cases_v014`（20 ID、明示 symlink fixture）。`:618` 不変。
- (2) `git diff --quiet dfdb8a9 -- skills/audit/scripts/docaudit_paths.py`。

### S1a-#56
- (3) `test_mdq_index.py`／`test_ax_probe.py`／`test_codex_probe.py` 各 `test_config_decision_table_v014`（20 ID）: `invalid-config` 全ケースで偽 bin の sentinel が書かれない、`cfg_*`／`top_*` は helper を通さず直接、`bin` 値は seam 既定名。各 `test_output_key_sets_per_branch`（mdq 5・ax 4・codex 5）。
- (4) `test_codex_review_plan.py::test_invalid_config_reason_passes_through`（完全一致）、`test_decide_verdict.py::test_required_with_not_active_state_is_refused`（engine 変更なし）。
- (5) `test_v014_contracts.py`: `reason ∈` 3 か所に `invalid-config`、ゲート文に `invalid-config`、Phase-5 `invalid-config` 行 3 本が各 1 回だけ＋mdq 枝の順序、`test_cm_enabled_expression_decision_table`（13 ID 実行）、`AX_REASON`／`MDQ_REASON` 束縛が Phase 0 節内、probe 段落の防御 1 句。`test_probe_reason_enumerations_match_fixed_sets` 更新。
- (6) `test_config_schema_four_seams_invalid_config`。

### S1a-#59 最小案
- (7) `test_v014_contracts.py::test_codex_review_convergence_note`（SKILL Phase 4 節・ADOPTION en/ja、段落正規化）。

### S1a-#60
- (8) `test_codex_probe.py::test_caller_codex_home_and_auth_file`（7 ID）、`test_caller_keys_present_in_every_branch`（5 分岐）、`test_json_escaping_of_bin_and_home`。auth 不在でも `codexReviewAvailable:true`。
- (9) `test_v014_contracts.py`: Phase-5 codex 接尾辞が `rebind` の 3 値を使う固定文、診断文、null 文言、Phase 4 env 注記。`config-schema.md`・ADOPTION en/ja に `CODEX_HOME`＋`wrapper` 段落各 ≥1。

### S1b-#57
- (10) `tests/test_probe_record.py`（固定 ID ≥ 24、§0-6 列挙。`rebind` 値の完全一致・display 1 行性・mdq-health 実出力を含む）。
- (11) `test_v014_contracts.py`: Phase 0 に 9 seam 記録行＋Phase 4 に `codexReviewState` 記録行（計 10 seam）、Phase 3 再記録 2 行、Phase 5 の `--read` 行、`CODEX_REVIEW_STATE=` 既存リテラル 4 つの温存（`test_v013_contracts.py::test_e` green）、再開段落固定文、6 unknown 文言、fail-open 固定文、Guardrails 1 句、SKILL に表示用 python -c 式が無い、`grep -c phase0-probes skills/audit/scripts/decide-verdict.py` = 0。

### S2
- (12) `python3 -m unittest tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff tests.test_v014_contracts` green。5 面 `0.14.0`、engine-shas `0.14.0`、refresh 段落更新。
- (13) `test_v014_contracts.py::test_v014_behavior_changes_paragraph`（en 6 文・ja 6 文）。
- (14) `test_release_handoff.py` 再標的 green、旧定数不在、notes 完全一致 2 文、`bash -n`。`0.13.2` 残存が repo 全体 grep で許可外 0 件（§8）。

### 共通
- (15) フルスイート green・**skip 0 を機械判定**（`-v` 出力に ` ... skipped` が 0 行 — R5-6）。`Ran N` 報告。
- (16) `bash -n`（3 probe＋handoff）、`py_compile`（変更・新規 .py 全部）。
- (17) **スコープ検査（§8、exit 1 で違反）** 3 段すべて clean。
- (18) **禁止ファイルの byte 比較** `git diff --quiet dfdb8a9 -- <§7 禁止一覧>`。

## 7. 変更範囲
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/{import-audit-scope.py,mdq-index.sh,ax-probe.sh,codex-probe.sh,probe-record.py(新)}`、`skills/audit/references/{config-schema.md,engine-shas.json}`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`.claude-plugin/plugin.json`、
`tests/{test_import_audit_scope.py,test_mdq_index.py,test_ax_probe.py,test_codex_probe.py,test_codex_review_plan.py,test_decide_verdict.py,test_v0132_contracts.py,test_v013_contracts.py,test_scaffold.py,test_release_handoff.py,test_v014_contracts.py(新),test_probe_record.py(新)}`、
`tasks/route/2026-08-28-issues-56-60/release-handoff.sh(新)`。
**禁止**: `skills/audit/scripts/{decide-verdict.py,start-run.py,docaudit_paths.py,write-evidence.py,docaudit_cache.py,mdq-health.py,graphify-probe.sh,cocoindex-probe.sh,codegraph-probe.sh,scaffold.py,write-template.py,open-run.py,seal-run.py,read-manifest.py,tree-digest.py,codex-dispatch.py,plan-dispatch.py}`、
`skills/audit/references/codex-review-output.schema.json`、`data/**`、`tests/data/**`、`skills/init/SKILL.md`、`agents/**`、`.gitignore`、`.envrc`、`.serena/**`、`docs/superpowers/**`、`.claude/**`、`tasks/route/2026-08-28-issues-52-54-v0.13.2/**`、
`tasks/route/2026-08-28-issues-56-60/{PLAN.md,REVIEW.md,allowlist.txt,baseline-hashes.txt,59-design-note.md}`。
**標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 8. 検証コマンド一式
```
python3 -m unittest discover -s tests -t . -v > /tmp/full.log 2>&1; tail -3 /tmp/full.log; test "$(grep -c ' \.\.\. skipped' /tmp/full.log)" -eq 0 || exit 1   # フル・skip 0
python3 -m unittest -v tests.test_import_audit_scope tests.test_mdq_index tests.test_ax_probe tests.test_codex_probe tests.test_codex_review_plan tests.test_decide_verdict tests.test_v0132_contracts tests.test_v014_contracts   # S1a
python3 -m unittest -v tests.test_probe_record tests.test_v014_contracts                                                              # S1b
python3 -m unittest -v tests.test_v013_contracts tests.test_scaffold tests.test_release_handoff tests.test_v014_contracts             # S2
bash -n skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh tasks/route/2026-08-28-issues-56-60/release-handoff.sh
python3 -m py_compile skills/audit/scripts/import-audit-scope.py skills/audit/scripts/probe-record.py
python3 skills/audit/scripts/scaffold.py --repo-root "$(mktemp -d)" --harness --dry-run | python3 -c 'import json,sys;print(json.load(sys.stdin)["stampVersion"])'  # S2 → 0.14.0
test "$(grep -c phase0-probes skills/audit/scripts/decide-verdict.py)" -eq 0 || exit 1
test "$(grep -c 'callerCodexHome"\]' skills/audit/SKILL.md)" -eq 0 || exit 1
test "$(grep -c 'docaudit--v0.13.2\|issues-52-54' tests/test_release_handoff.py)" -eq 0 || exit 1                                    # S2
git grep -n '0\.13\.2' -- . ':!tasks' ':!tests/test_v0132_contracts.py' ':!tests/data' | grep -v 'engine-shas.json:.*"0.13.2": {\|ADOPTION.*v0.13.2 behavior changes\|ADOPTION.*v0.13.2 の挙動変更\|ADOPTION.*0.13.1, 0.13.2\|ADOPTION.*0.13.1, or 0.13.2\|ADOPTION.ja.*0.13.1、または 0.13.2\|ADOPTION.ja.*0.13.1、0.13.2' ; test $? -eq 1 || exit 1   # S2 残存 0（ja は読点区切り — Opus O4）
git diff --quiet dfdb8a9 -- skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/docaudit_paths.py skills/audit/scripts/write-evidence.py skills/audit/scripts/docaudit_cache.py skills/audit/scripts/mdq-health.py skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh skills/audit/scripts/scaffold.py skills/audit/scripts/write-template.py skills/audit/scripts/open-run.py skills/audit/scripts/seal-run.py skills/audit/scripts/read-manifest.py skills/audit/scripts/tree-digest.py skills/audit/scripts/codex-dispatch.py skills/audit/scripts/plan-dispatch.py skills/audit/references/codex-review-output.schema.json skills/init/SKILL.md agents tests/data && echo forbidden-clean
SCOPE_COMMIT=<boss commit> BOSS_COMMIT=<直前の boss commit> python3 - <<'EOF'                                                        # スコープ検査 3 段（exit 1 で違反）
import subprocess,sys,os,hashlib,fnmatch,stat
T='tasks/route/2026-08-28-issues-56-60/'
def show(c,p): return subprocess.run(['git','show',f'{c}:{p}'],capture_output=True,text=True,check=True).stdout
def z(cmd): return [p for p in subprocess.run(cmd,capture_output=True,text=True,check=True).stdout.split('\0') if p]
allow={l.strip() for l in show(os.environ['SCOPE_COMMIT'],T+'allowlist.txt').splitlines() if l.strip() and not l.startswith('#')}|{T+'release-handoff.sh'}
logs=[T+'*-session.log',T+'*-prompt.md',T+'*-answer.md',T+'investigate-*',T+'*.log']
boss_docs=[T+n for n in ('PLAN.md','REVIEW.md','allowlist.txt','baseline-hashes.txt','59-design-note.md')]
bad=[]
# (1) tracked 差分＋未追跡（ignored は含めない）
changed=set(z(['git','diff','--name-only','-z','dfdb8a9','HEAD']))
st=z(['git','status','--porcelain=v1','-z','--untracked-files=all']); i=0
while i<len(st):
    code,path=st[i][:2],st[i][3:]; changed.add(path)
    if 'R' in code: i+=1; changed.add(st[i])
    i+=1
for p in sorted(changed):
    if p.startswith(('.mdq/','.claude/worktrees/')) or '__pycache__/' in p or any(fnmatch.fnmatch(p,g) for g in logs): continue
    if p in boss_docs:
        if open(p,'rb').read()!=subprocess.run(['git','show',f"{os.environ['BOSS_COMMIT']}:{p}"],capture_output=True).stdout: bad.append(p+' (boss doc modified)')
        continue
    if p not in allow: bad.append(p)
# (2) 保護 root の完全一致（path 集合・種別・mode・hash）
roots=['.envrc','.gitignore','.claude/settings.local.json','data','.serena','docs/superpowers']
def enum():
    out={}
    for r in roots:
        paths=[r] if not os.path.isdir(r) else [os.path.join(d,f) for d,_,fs in os.walk(r) for f in fs]
        for p in paths:
            if not os.path.lexists(p): continue
            s=os.lstat(p); kind='symlink' if stat.S_ISLNK(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'other'
            h=hashlib.sha256(open(p,'rb').read()).hexdigest() if kind=='file' else hashlib.sha256(os.readlink(p).encode() if kind=='symlink' else b'').hexdigest()
            out[p]=(h,oct(stat.S_IMODE(s.st_mode)),kind)
    return out
base={}
for line in show(os.environ['SCOPE_COMMIT'],T+'baseline-hashes.txt').splitlines():
    h,m,k,p=line.split('  ',3); base[p]=(h,m,k)
cur=enum()
for p in sorted(set(base)|set(cur)):
    if base.get(p)!=cur.get(p): bad.append(p+' (protected root changed: %s -> %s)'%(base.get(p),cur.get(p)))
print('\n'.join(bad) or 'scope-clean'); sys.exit(1 if bad else 0)
EOF
```
