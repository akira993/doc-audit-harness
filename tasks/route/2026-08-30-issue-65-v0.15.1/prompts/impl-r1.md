# 実装依頼: docaudit v0.15.1 — Issue #65 codegraph probe の自己回復 ＋ #66 の古い記述の是正（文言のみ）

あなたは実装担当（worker）。対象リポジトリはカレントディレクトリ（docaudit、main HEAD e1c0b19、clean）。**単独で作業し、collab／他エージェントは使わない。**

計画の正本は `tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md`（rev.7）。**まず PLAN.md 全文を読み、§5 成果物の各項目をそのとおりに実装せよ**（下に §5〜§8 を転記するが、正本はファイルの方）。批判ラウンドの記録 `REVIEW.md`・`sol-r*-out.md`・`opus-r*-out.md` は背景として参照してよい（指示は PLAN が優先）。

## 作業手順（順序固定）
1. `git switch -c fix/v0.15.1-issue-65` を作成してから作業する（main を直接変更しない）。
2. §5.1 probe → §5.2 テスト → §5.3/§5.4 文書 → §5.5 版 bump → §5.6 handoff → §5.7 gate.py の順。各段で関連テストを実行し、落ちたら直す。
3. 完了時に §8 の検証コマンドを **全て**実行し、出力（`Ran N tests`、`GATE PASS/FAIL`、各 G の実数）を報告に**そのまま貼る**。gate.py が FAIL のまま「完了」と報告してはならない。
4. 報告に次を含める: (a) 変更ファイル一覧（`git status --porcelain` の生出力）、(b) N1〜N15 → テスト method 名の対応表、(c) `tests/test_release_handoff.py` の改名対応表と新規 3 method 名、(d) 許可外ファイルの変更が必要と判断した箇所（**修正せず報告のみ**）、(e) 未実施・不確実な点。
5. コミットは **1 つ**にまとめてよいが、commit message 全体に closing keyword（Closes/Fixes/Resolves 等）＋`#N` を書かない。件名例: `fix(probe): branch codegraph init/sync on codegraph.db, honor CODEGRAPH_DIR; correct code-review wording; bump to 0.15.1`。route dir の必須成果物は `git add -f` で個別に追加する（`*-log.txt`・`PLAN.rev*.md` は追加しない）。

## 禁止事項（標準文言）
- 変更範囲（§7）の許可一覧以外のファイルを変更しない。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**
- `docs/superpowers/**`、`tasks/route/2026-08-29-*/**`、`.gitignore`、`skills/audit/scripts/*.py`、他の probe、dir-framework 側は一切触らない。
- 既存テストの削除・無効化・`skip` 化は禁止（改名対応表にあるものだけ改名）。
- テストは「fake の log 実体で判定」を守る。stdout の reason だけで通る検査は書かない。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認

---
以下、PLAN.md §5〜§8 の転記（正本は PLAN.md）:

## 5. 成果物

### 5.1 `skills/audit/scripts/codegraph-probe.sh` — 分岐表（この表が仕様）

前処理（probe 冒頭の python3 ブロックで行う。既存の config 解析ブロックと同じ python3 呼び出しに同居させてよい）: `CODEGRAPH_DIR` を codegraph 1.5.0 `directory.js codeGraphDirName()` と同値の規則で解決する — (1) JS `String.prototype.trim()` と同じ文字集合で前後を trim（**明示的な文字クラス**: `\t\n\v\f\r` ・空白・`\u00A0` `\u1680` `\u2000`〜`\u200A` `\u2028` `\u2029` `\u202F` `\u205F` `\u3000` `\uFEFF`。Python の `str.strip()` は使わない — `\x1c`〜`\x1f`・`\x85` を余分に剥がし `\uFEFF` を剥がさない）、(2) 空／`.`／`..` を含む／`/` を含む／`\` を含む／絶対パス のいずれかなら `.codegraph`、それ以外はその値。**内部の空白・タブ・改行は codegraph と同じく有効**（拒否しない）。結果を `DIRNAME` とする。python3 → bash の受け渡しは **NUL 区切りの 4 フィールド** `STATE\0BIN\0DIRNAME\0DIRNAME_ESC\0`（`DIRNAME_ESC = ascii(DIRNAME)` を **python 側で生成** — bash には ASCII 限定エスケープを作る手段が無い）にし、既存の空白区切り `read -r STATE BIN`（:28）を次の 1 行に置き換える: `{ IFS= read -r -d '' STATE; IFS= read -r -d '' BIN; IFS= read -r -d '' DIRNAME; IFS= read -r -d '' DIRNAME_ESC; } < <(python3 -c '...' "$CONFIG")`（同一 fd から 4 回読む）。python 側の **4 本の出口すべて**（`not-configured` :35 の裸 `print`・`disabled-by-config` :45・`enabled` :47・`invalid-config` :49）を同じ 4 フィールド NUL 形式にする（1 本でも漏れると `read -d ''` が EOF まで読んで STATE が壊れる）。`not-configured`/`disabled-by-config`/`invalid-config` でも DIRNAME は既定 `.codegraph` を出す（bash 側の分岐に到達しないが形式を揃える）。**probe は codegraph を起動するとき `CODEGRAPH_DIR="$DIRNAME"` を明示エクスポートする**（解決済みの値は codegraph 側の trim・妥当性検査で変化しないため、probe と codegraph が同じディレクトリを見ることが規則の複製精度に依らず構成的に保証される。無効値のときは codegraph 側のフォールバックと同じ `.codegraph` を渡すので挙動も同じ。差は codegraph の 1 回警告が出ないことだけ）。`DIR="$REPO_ROOT/$DIRNAME"`、`DB="$DIR/codegraph.db"`。stderr に `DIRNAME` を出すときは python が生成した **`DIRNAME_ESC`**（`ascii()`: 非 ASCII・制御文字は `\uXXXX`/`\xNN` に、U+2028/U+2029 も逃がす。bash `printf '%q'` は U+2028/2029 を素通しするため使わない）をそのまま埋め込み 1 行にする（パス操作には生の `DIRNAME` を使う。`ascii()` は前後に引用符を付けるので、分岐表の `<DIRNAME>` は実出力では `'...'` 付きになる — テストは引用符込みで照合）。環境変数の **不正 UTF-8 バイト**は Node と同じく U+FFFD へ置換して復号する（python は `os.environb` から `decode("utf-8", errors="replace")`。`os.environ` の surrogateescape 値を UTF-8 で書き出すと `UnicodeEncodeError` で JSON・exit 0 契約を破る）。

| # | 状態（上から順に最初に一致した行） | 実行 | reason | stderr |
|---|---|---|---|---|
| 1 | `DIR` が symlink（`[[ -L "$DIR" ]]`、dangling 含む） | **実行しない** | `index-failed` | `codegraph dir <DIRNAME> is a symlink; not touching it` |
| 2 | `DIR` が存在するがディレクトリでない（`-e` かつ `! -d`） | 実行しない | `index-failed` | `codegraph dir <DIRNAME> exists but is not a directory` |
| 3 | `DIR` が存在しない | `init .` | 実行結果による | 既存 |
| 4 | `DB` が symlink（`-L`、dangling 含む） | 実行しない | `index-failed` | `codegraph.db is a symlink; not touching it` |
| 5 | `DB` が存在しない（`! -e`。`.DS_Store`/`.gitignore`/WAL/SHM/daemon ファイルだけが残っていてもここ） | `init .` | 実行結果による | 既存 |
| 6 | `DB` が通常ファイル（`-f`、0 バイトを含む） | `sync .` | 実行結果による | 既存 |
| 7 | `DB` が存在するが通常ファイルでない（ディレクトリ・FIFO 等） | 実行しない | `index-failed` | `codegraph.db exists but is not a regular file` |

- 実行する行（3・5・6）は `( cd "$REPO_ROOT" && CODEGRAPH_DIR="$DIRNAME" "$BIN" "${CMD[@]}" </dev/null )` — **stdin を `/dev/null` に固定して非対話化**する（codegraph 1.5.0 の `init` は TTY があると「無視された nested repo を索引するか」「git hook を入れるか」を対話で聞き、承認されると `codegraph.json`／`.git/hooks` を書く — `bin/codegraph.js:472,622`・`installer/index.js:596`。非 TTY では聞かないことを boss が scratch で実測済みだが、probe 側で保証する）。成功 → `ok`、失敗 → `index-failed` ＋ 既存 stderr（`codegraph <cmd> failed (rc=..): <tail>`。**実行した subcommand を含む**）。
- 出力 JSON は既存どおり **厳密に 3 キー** `{symbolGraphAvailable, symbolGraphBin, reason}`・ASCII・1 行・exit 0。reason 集合（`ok/not-installed/disabled-by-config/index-failed/not-configured/invalid-config`）は不変。
- `CODEGRAPH_DIR` の扱いは前処理のとおり（解決済み値を明示エクスポート）。fake/実物いずれの codegraph も、probe から受け取る `CODEGRAPH_DIR` は常に解決済みの妥当な単一ディレクトリ名である。
- **Phase-3 との整合（Sol R3-2 への回答）**: probe の export は自分の子プロセスにしか効かない。verifier の `codegraph impact/node`（`workflow-template.js:131`）は orchestrator と同じ環境（Claude Code の Bash env）で同じ生の `CODEGRAPH_DIR` を受け取り、codegraph 自身の規則で同じディレクトリを解決する。よって整合は「probe の解決規則 == codegraph の規則」（N12 が全 trim コードポイントで検査）に懸かり、export はそれに加えた保険である。**現行出荷版との比較**: 現行 probe は `-d .codegraph` だけを見て codegraph は `CODEGRAPH_DIR` を尊重するため、`CODEGRAPH_DIR` 利用者では「probe は既定 dir を検査し、codegraph は別 dir を操作し、毎 run `init` が走る」状態にある。本版は Phase-0 と Phase-3 の乖離を **厳密に縮小**するのであって新たに導入するのではない。解決済み `DIRNAME` と repo root を Workflow の sealed 引数として Phase-3 に渡す完全な閉鎖は、封印入力の設計そのもの（#63）に属するため **本版の範囲外**（REVIEW.md に持ち越し記録済み）。
- 先頭コメント :12-16 を分岐表の要約へ書き換える: 「codegraph の初期化判定は `codegraph.db` の存在。`init` の冪等性は版で変わった（1.5.0 は受理・旧版は拒否）ので依存しない。symlink／非通常ファイルは codegraph が追跡・上書きし得るので probe は触らない」。

### 5.2 `tests/test_codegraph_probe.py`（現行 20 method → **≥ 38**）
既存方式を拡張する: **fake codegraph は呼び出しごとに JSON 1 行 `{"argv":[...],"cwd":"<realpath>","CODEGRAPH_DIR":<str|null>,"stdin_eof":<bool>}` を log に追記**する（`stdin_eof` は `sys.stdin.read()==""` — `</dev/null` の検査。**fake は argv 記録の前に必ず `sys.stdin.read()` を実行して読み切る**（`</dev/null` を外した実装に sentinel を読ませるため）。**テスト側の規則**: probe を起動する helper は **全ケースで** `input="STDIN-SENTINEL\n"`（helper は `text=True` のため **str**）を明示的に与え、`timeout=30` を必ず設定する。正しい実装だけが sentinel を遮断して fake に `""` を読ませる。親 stdin の継承は禁止 — CI で親が EOF なら `</dev/null` を外した実装が通り、対話端末なら fake が読み待ちで停止するため）（現行は引数のみ。`test_codegraph_probe.py:18-31`）。全ケースで「呼び出し回数（0 または 1）」「argv 完全一致」「cwd == repo の realpath」「`CODEGRAPH_DIR` == 期待する解決済み値」「`stdin_eof` == true」を **完全一致**で判定し、stdout の reason だけで通る検査を禁止する。テストは subprocess の env から **継承した `CODEGRAPH_DIR` を明示的に除去**し（N10〜N12 だけが値を与える）、外部環境で結果が変わらないようにする。
- 改修 1: `test_stub_installed_existing_calls_sync` の fixture を `codegraph.db`（通常ファイル・非空）作成へ改める。
- 改修 2: `test_output_key_sets_per_branch` を N5〜N9・N12 の不実行分岐を含む形へ拡張（既存本体変更の **明示的例外**。stdout JSON が厳密 3 キー・ASCII・1 行）。
- 新規 method（1 状態 1 method 以上。N → method 名の対応表を worker が報告し boss が B1 で照合）:
  - N1 `.codegraph/.DS_Store` のみ → `init .`・`ok`（**#65 再現**）
  - N2 `.codegraph/.gitignore` のみ → `init .`（「`.DS_Store` だけなら init」という誤実装を落とす）
  - N3 `.codegraph/` 空ディレクトリ → `init .`
  - N4 `codegraph.db` 0 バイト → `sync .`
  - N5 `codegraph.db` がディレクトリ → **不実行**（呼び出し 0 回）・`index-failed`・stderr に `not a regular file`
  - N5b `codegraph.db` が FIFO（`os.mkfifo`）→ 不実行・`index-failed`・stderr に `not a regular file`
  - N6 `codegraph.db` が dangling symlink → 不実行・`index-failed`・stderr に `symlink`
  - N7 `codegraph.db` が通常ファイルへの有効な symlink → 不実行・`index-failed`・stderr に `symlink`
  - N8 `.codegraph` 自体が（db を持つディレクトリへの）symlink → 不実行・`index-failed`・stderr に `symlink`
  - N8b `.codegraph` が dangling symlink → 不実行・`index-failed`・stderr に `symlink`（`-L && -d` の誤実装を落とす）
  - N9 `.codegraph` が通常ファイル → 不実行・`index-failed`・stderr に `not a directory`
  - N9b `.codegraph` が FIFO → 不実行・`index-failed`・stderr に `not a directory`
  - N10 `CODEGRAPH_DIR=.codegraph-win` で `.codegraph-win/codegraph.db` あり・`.codegraph/` 無し → `sync .`・fake が受け取る `CODEGRAPH_DIR` は `.codegraph-win`・既定 dir は作られない
  - N11 `CODEGRAPH_DIR=.codegraph-win` で `.codegraph-win/` 無し・`.codegraph/codegraph.db` あり → `init .`・受け取る `CODEGRAPH_DIR` は `.codegraph-win`（既定 dir を見ない）
  - N12 `CODEGRAPH_DIR` の解決表（subTest。各入力について「判定に使う dir」と「fake が受け取る `CODEGRAPH_DIR`」の両方を検査。**fixture 規則: 選ばれるべき dir にだけ `codegraph.db` を置き、選択を誤ると `sync`/`init` が入れ替わる**ようにする — 無効入力では既定 `.codegraph/codegraph.db` のみ、有効入力ではその名前の dir にのみ db。両方不在の fixture は禁止）:
    - 無効 → 既定 `.codegraph`: `../x`、`foo..bar`、`a/b`、`a\b`（バックスラッシュ単独を含む）、`.`、`/abs`、空文字、空白のみ、`\u00A0` のみ
    - 有効 → その値: `" .codegraph-win "`（前後 ASCII 空白 → `.codegraph-win`）、`"\u00A0.codegraph-win\u00A0"`（NBSP → `.codegraph-win`）、`"\uFEFF.codegraph-win"`（BOM → `.codegraph-win`）、`.codegraph`（既定名の明示）、`.CodeGraph-Win`（大文字保持）、`索引`（Unicode 名保持）、`"foo bar"`（内部空白は有効）、`"foo\nbar"`（**内部改行は有効** — codegraph は拒否しない）、
    - **trim 表（表駆動 subTest）**: 先頭に 1 文字付けた `<c>.codegraph-win` について、`c ∈ {U+0009, U+000A, U+000B, U+000C, U+000D, U+0020, U+00A0, U+1680, U+2000〜U+200A（11 個）, U+2028, U+2029, U+202F, U+205F, U+3000, U+FEFF}` は **剥がれて** `.codegraph-win`、`c ∈ {U+001C, U+001D, U+001E, U+001F, U+0085}` は **剥がれず** `<c>.codegraph-win` のまま有効（JS trim の集合と一致。Python `strip()` は後者 5 文字を剥がすので落ちる。**U+FEFF が最重要**: JS が剥がして Python が剥がさない唯一の方向で、export が保険にならない）。末尾付与でも同じ表。`"\x1c.codegraph-win"`（**JS trim は剥がさない → そのまま有効値として保持**。Python `strip()` 誤用を落とす）
  - N13 `sync` 失敗・`init` 失敗（fake が **固有の終了値 7** と固有の stderr 印 `FAKE-DIAG-<n>` を出す）→ `index-failed`・stderr に `codegraph sync failed (rc=7)` / `codegraph init failed (rc=7)` と印（既存の `rc=..`＋末尾転記契約の維持）
  - N14 stderr の `DIRNAME` 表示が ASCII 限定エスケープで **常に 1 行（`splitlines()` で 1 要素）かつ ASCII のみ**: `CODEGRAPH_DIR="foo\nbar"`、`"foo\u2028bar"`、`"foo\u2029bar"`、Unicode 名（`索引`）の各ケースでその dir を通常ファイルにし（行 2）、stderr が 1 行・ASCII・エスケープ表現を含むこと
  - N15 不正 UTF-8 環境: subprocess の env に bytes 値 `b"\xff.codegraph-win"` を与える → probe は落ちず（exit 0・JSON 1 行）、判定 dir と fake が受け取る `CODEGRAPH_DIR` は `"\ufffd.codegraph-win"`（Node と同じ置換復号。fixture 規則どおりその dir にだけ db を置く）
- 既存 method は名称・件数（20）とも全数維持（改修 1・2 を除き本体不変）。新規状態は N1, N2, N3, N4, N5, N5b, N6, N7, N8, N8b, N9, N9b, N10, N11, N12, N13, N14, N15 の **18**。1 状態 1 method 以上なので新規 **≥ 18**、合計 **≥ 38**。

### 5.3 文書（#65）
- `skills/audit/SKILL.md:216-218`（218 行頭の `fast);` は 217 の sync 節の続き — 3 行を **同じ 3 行数のまま**書き換える）、`skills/audit/references/config-schema.md:280-282`（283 行頭が `self-generates ...` で始まるため、282 の置換文は主語 `codegraph` で終える。3 行数を維持）: 分岐説明を「`<dir>/codegraph.db`（`CODEGRAPH_DIR` 尊重）が通常ファイルなら `sync`、無ければ `init`、symlink／非通常ファイルなら実行せず `index-failed`」へ。「bare init は拒否される（確認済み）」は削除し「init の冪等性は版依存のため probe は依存しない」に置換。

### 5.4 文書（#66 文言のみ）— 対象 13 行
置換方針（**挙動の記述は維持**し、根拠だけを真にする）:
- en: 「(it is not model-invocable)」→「(the audit does not start it on its own yet; autonomous invocation is tracked in #66)」相当。「is an expected user-invocation-only layer」→「is not started by the audit itself: in autonomous runs it is an expected skip, in interactive runs it is offered once」相当。表セル（ADOPTION.md:80）の「`/code-review` is user-invocation-only」→「`/code-review` is offered to the user (not started by the audit yet; #66)」相当。
- ja: 「モデルからは起動できない」「モデルから起動できないため」「モデルからは起動不可」→「監査自身は起動しない（自律起動は #66 で追跡）」相当。
- `skills/audit/SKILL.md:3`（description）: 括弧内の `(not model-invocable)` を **`(not started by the audit itself yet)`** に置換（**この文字列に固定**。G11 が行 3 の完全一致を検査）。description の他の語は一切変えない（skill のトリガ文言）。
- `skills/audit/SKILL.md:778` status line: `💡 code-review: not run — the audit does not start /code-review itself yet (tracked in #66); run it when offered in an interactive audit, or before the audit, if you want this layer included. (expected)`。状態トークン `not-model-invocable` と `:560-563` の分岐は不変（**注記の追加は禁止** — G11 は総行数不変を要求する。`disable-model-invocation` は上流の実エラー文字列としてそこに残る）。
- 置換後に **旧意味の残骸**も残さない: `docs/ADOPTION.ja.md:79` の「ユーザー実行のみ」、`docs/ADOPTION.md:80` の「user-invocation-only」も同じ行で是正する（gate.py の残骸リストに含める）。
- **`docs/superpowers/**` は歴史文書（gitignore 対象・追跡外）のため触らない**。

### 5.5 版 bump（0.15.1）
- `.claude-plugin/plugin.json` version、`docs/ADOPTION.md:235` / `docs/ADOPTION.ja.md:214` の `Version 0.15.1`。
- refresh 列挙文（`docs/ADOPTION.md:315` / `docs/ADOPTION.ja.md:289`）: `engine-shas.json` の 0.15.1 以外の **全キー**を昇順で列挙 — 「0.10.0, 0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.13.1, 0.13.2, 0.14.0, or 0.15.0 templates can be updated directly to 0.15.1」（ja も同順）。
- `skills/audit/references/engine-shas.json` に `"0.15.1"` を追加（3 sha は現行生成物の実測値＝0.15.0 と同値。`test_scaffold.test_engine_shas_match_current_generated_bodies` が検証）。
- `tests/test_scaffold.py` の "0.15.0" **7 箇所**（:214,217,218,242,245,246,312）を 0.15.1 へ。**新規**: 0.15.0 stamp の未改変テンプレート 3 種（check-docs / doc-lint / check-docs-engine）が `--harness --refresh` で 0.15.1 stamp へ更新され本文が同一であることを検証する method（`:163-170` の 0.10.0 版に倣う）。
- `tests/test_v013_contracts.py:201` を `{"0.15.1"}` へ、`:210,215` の allowlist 正規表現を新しい列挙文へ同期。**`tests/test_v0131_docs_contracts.py:90` `test_g_refresh_paragraph_versions`** の期待集合（現行 6 版＋plugin 版）を **`engine-shas.json` のキー集合から導出**する（`set(json.loads(read(SHAS))) | {plugin_version}` — **版リテラルを増やさない**。`tests/test_v013_contracts.py:203` `test_j` が `0.12.0` リテラルを含む行を allowlist 外として検出するため、リテラル列挙は G1 を落とす — Opus B-4）。
- ADOPTION en/ja に **v0.15.1 挙動変更ブロック**を v0.15.0 ブロックの直後に追加（en/ja 対訳・各 2 文）: (1) 「symbolGraph probe は `<dir>/codegraph.db` の存在で init/sync を選ぶ（`CODEGRAPH_DIR` 尊重）。ディレクトリだけが残った場合も次回 run で自己回復する。symlink や通常ファイル以外の `codegraph.db`／dir は実行せず index-failed — **従来は有効な symlink 構成でも sync が通っていたが、本版から意図的に非対応**（codegraph が link 先を上書きし得るため）。なお `CODEGRAPH_DIR` で改名した索引ディレクトリは `tree-digest.py` の既知ルート（`.codegraph` 固定）に含まれず `digestExclude` で除外できない（既存の制限、本版では未対応）」 (2) 「`/code-review` に関する記述を上流の現状（Claude が自律起動できる）に合わせて是正。監査の挙動は不変で、自律起動は #66 で追跡」。
- `tests/test_v015_contracts.py`: v0.15.0 ブロックの完全一致テスト（:169-185）と同じ方式で **v0.15.1 ブロックの en/ja 完全一致テスト**を追加（期待文字列は worker が書いた最終文と同一。boss が en/ja の内容対応を検分）。
- `tests/test_v015_contracts.py`: **#66「挙動不変」の回帰契約**を追加 — 件数ではなく **文脈つきの完全文**を個別に固定する（現行 tests に `not-model-invocable` の参照は 0 件 — Sol R2-7 実測）: (a) :560 「If completion cannot be confirmed, do not invent findings and use `CODE_REVIEW_STATE=not-model-invocable`.」、(b) :562-563 「If execution reports the specific `disable-model-invocation` block, bind `CODE_REVIEW_STATE=not-model-invocable` without WARN.」、(c) :778 の status line 全文（新文言）、(d) 「In a non-interactive session, do not offer the question and use that expected state directly.」、(e) 「before the gate and only once, use AskUserQuestion to offer running the configured `/code-review` command.」— 各 1 回以上出現（改行位置の差は空白正規化して比較）。

### 5.6 release handoff
- `tasks/route/2026-08-30-issue-65-v0.15.1/release-handoff.sh`: v0.15.0 版を複製し、`TAG_NEW=docaudit--v0.15.1`、`RELEASE_TITLE="docaudit v0.15.1 — self-healing codegraph probe"`、usage／冒頭コメント／notes ファイル名／notes 本文／`release_is_valid` の必須語／最終表示の **v0.15.0・#56・webExtract/codexReview 固有文言を全て置換**。close 対象は **#65 のみ**。事前条件: **#59・#63・#66 が OPEN でなければ公開前に停止**（v0.15.0 版の #59/#63 検査に #66 を追加）。notes 必須語: `Closes #65.`、`#66 wording corrected; behavior unchanged`、`#59`、`#63`、`#66`、`codegraph.db`、`CODEGRAPH_DIR`。
- **`git add -f`** の対象は G10 の **必須成果物配列＋（存在する場合の）任意生成物配列**に限る（`.gitignore:8` の `tasks/` 無視のため force-add が要るが、ディレクトリ単位では `*-log.txt` 等の作業ログまで公開される — Sol R2-12）。`*-log.txt`・`PLAN.rev*.md` は追跡しない。
- `release-handoff.sh` は **実体の実行可能属性と Git index mode `100755`** の両方を満たす（複製元と同じ。gate.py が検査）。
- commit message 全体と PR body に **closing keyword（`Closes`/`Fixes`/`Resolves` 等）＋ `#N`** を書かない（GitHub の auto-close は keyword+番号で発火する。裸の `#65` 単独は発火しない。v0.15.0 で #59 が `fix(...) issue #59` により誤 close された教訓。#66 が誤 close されると handoff の事前条件で停止する）。
- `tests/test_release_handoff.py`: HANDOFF パス・TAG・TITLE・ISSUES `{"65"}`・**PRECLOSED `{"65"}`**（`test_resume_release_with_preclosed_issues_closes_only_remaining` :428 が `assertTrue(PRECLOSED)` を要求する — v0.15.0 と同じく「唯一の close 対象が事前に閉じていれば resume は何も閉じない」を検査）・REQUIRED_BODY を再ターゲット。既存 24 method は **改名対応表どおり**に維持（gate G3 が e1c0b19 基準でこの表を固定する）: `test_close_calls_target_only_issue_56`→`test_close_calls_target_only_issue_65`、`test_release_notes_close_directive_and_issue_59_continuation`→`test_release_notes_close_directive_and_open_issue_continuation`、他 22 は同名。**新規 3**: `test_issue_66_open_allows_publication_and_remains_open`、`test_issue_66_not_open_stops_before_publication`、`test_no_v0150_residue_in_handoff`。**新規 3 本の必須 assert**（B1 で boss が本文を照合）: (a) #66 OPEN → スクリプトが公開まで進み、fake gh の記録に `issue close 66` が **無く** `issue close 65` が **有る**；(b) #66 が OPEN 以外 → 非 0 終了で、既存 helper **`assert_no_release_mutations()`**（:273）を必ず呼ぶ（tag 作成・push・release create・issue close のいずれも無い。`ensure_tag` の後に検査を置く誤実装を遮断）；(c) 残骸 → スクリプト本文を読み 4 語の出現数がそれぞれ 0（実数を出力）。合計 **≥ 27**。無意味なテスト（`assertTrue(True)` 等）に対する最終防衛は **B1（boss が新規・変更 method の本文を全て読む）**であり、G12 はその補助の tripwire に過ぎない。

### 5.7 `tasks/route/2026-08-30-issue-65-v0.15.1/gate.py` — 機械ゲート（単一スクリプト）
表示用パイプ（`| tail`・`| grep`）は失敗を exit 0 に化かすため **ゲートに使わない**（Sol R2-4 実測）。worker が本スクリプトを書き、boss が全行を読み、**変更前ツリー（main HEAD e1c0b19 の worktree）で FAIL・変更後で PASS の両方を実測**して「常に PASS しない」ことを確認する。Python 3 標準ライブラリのみ。各検査は実数を stdout に出し、1 つでも不一致なら最後に `GATE FAIL` と exit 1、全一致で `GATE PASS` と exit 0。引数 `--repo-root`（既定 cwd）と `--base main`。
引数: `--repo-root`（既定 cwd）、`--base e1c0b19`（**固定 commit**。可変の `main` は merge 後に基準が動くため使わない）。
| # | 検査 | 実装 | 期待 |
|---|---|---|---|
| G1 | フルスイート | `subprocess.run([sys.executable,"-m","unittest","discover","-s","tests"])` の returncode と stderr の `Ran (\d+) tests` を解析 | returncode 0・skip 0・**N ≥ 654**（630＋probe 18＋scaffold 1＋v015 2＋handoff 3。実数を表示） |
| G2 | probe テスト実数 | `tests/test_codegraph_probe.py` の `^    def test_` 行数と、`git show e1c0b19:tests/test_codegraph_probe.py` の 20 名称が全て残存 | ≥ 38 かつ 20 名称残存 |
| G3 | handoff テスト実数 | 同上 `tests/test_release_handoff.py`。e1c0b19 の 24 名称を §5.6 の改名対応表（gate 内に定数として固定）で写像し全て存在、かつ新規 3 名が存在 | ≥ 27 かつ 27 名全存在 |
| G4 | 残骸（#66） | 対象 5 ファイルを読み、旧表現リスト `["not model-invocable","user-invocation-only","モデルから起動できない","モデルからは起動","ユーザー実行のみ"]` の各出現数を表示 | 全て 0（変更前実測: 7・3・2・2・1 ＝ 15 出現／13 行。`config-schema.md` は元から 0 件） |
| G5 | 版整合 | `.claude-plugin/plugin.json` の version、`engine-shas.json` の最大キー（semver）、ADOPTION en/ja の `Version X.Y.Z` 行、`scaffold.py --harness --dry-run` の `stampVersion` | 全て `0.15.1` |
| G6 | handoff 追跡・mode | `git ls-files -s -- <handoff>` が 1 行で mode `100755`、`os.access(X_OK)` | 真 |
| G7 | handoff 残骸 | 同ファイル本文の `v0.15.0`／`#56`／`webExtract`／`codexReview` 出現数 | 全て 0 |
| G8 | 変更集合⊆許可集合 | 変更集合 = `git diff --name-status -z -M -C <base>...HEAD`（R/C は旧新両パス）∪ `git status --porcelain=v2 -z --untracked-files=all`（rename 両端）。ignored は含めない（理由: 追跡されないものは出荷されない。追跡済みの他 route dir（例: 2026-08-29 route は 21 件追跡）の改変は ignore 規則に関係なく `git diff` に出るので本検査がカバーする — Opus S-1 により G13 は廃止）。許可集合は §7 の **具体的パス配列のみ**（接頭辞・glob・`fnmatch` は使わない。route dir の追跡外ログは ignored なので変更集合に現れない）。差集合を表示 | 差集合 0 件（変更集合の件数も表示） |
| G9 | shell 構文 | `bash -n skills/audit/scripts/codegraph-probe.sh` | returncode 0 |
| G10 | 追跡対象 | **必須成果物**（`PLAN.md`, `REVIEW.md`, `release-handoff.sh`, `gate.py`, `prompts/sol-r1.md`〜`sol-r4.md`, `sol-r1-out.md`〜`sol-r4-out.md`, `tasks/route/2026-08-30-issues-59-63-65-66/00-issue-review.md`）が全て `git ls-files` に存在；**任意生成物（有限列挙）**（`prompts/sol-r5.md`, `prompts/opus-r1.md`, `prompts/opus-r2.md`, `prompts/impl-r1.md`〜`impl-r5.md`, `sol-r5-out.md`, `opus-r1-out.md`, `opus-r2-out.md`, `impl-r1-out.md`〜`impl-r5-out.md`, `codex-review-out.md` — glob ではなく配列）は **物理的に存在する場合のみ**追跡済みであること；route dir 配下で `git ls-files` に載るものは上記 2 集合の和に限る（`*-log.txt`・`PLAN.rev*.md` を含む他の一切は 0 件） | 真 |
| G11 | 許可編集の行単位検査 | `git show e1c0b19:<file>` と現ファイルを行列で比較（difflib は使わない）。(1) **総行数が e1c0b19 と同一**；(2) 許可行 `SKILL.md {3, 216-218, 560-563, 778}`／`config-schema.md {280-282}` **以外の全行が完全一致**；(3) `SKILL.md` 行 3 == `old_line3.replace("(not model-invocable)", "(not started by the audit itself yet)")`（gate 内で生成、ハードコード不要）、行 778 == §5.4 の新 status line 全文（リテラル） | 違反 0 行（不一致行番号を表示） |
| G12 | 空テスト禁止 | `ast` で `tests/test_codegraph_probe.py`・`tests/test_release_handoff.py` の `test_*` method を走査し、本体が docstring／`pass`／`...` のみのものを数える | 0 件 |

## 6. 完了条件

### A. 機械ゲート
- **A1** `python3 tasks/route/2026-08-30-issue-65-v0.15.1/gate.py --base e1c0b19` が `GATE PASS`・exit 0（G1〜G12 の実数を REVIEW.md に転記）。
- **A2** 各 G 検査が「常に PASS」でないことを boss が **G ごとに 1 つの意図的違反 fixture** で実測する（各 1 回、`GATE FAIL` と当該 G の失敗表示を確認して元に戻す。REVIEW.md に G 番号と fixture を記録）: G1 テスト 1 本を一時的に `assertTrue(False)`／G2 **e1c0b19 由来の既存 method を 1 本一時改名**（新規 method の削除は下限の余裕に吸収され得る）／G3 改名先 method を 1 本改名／G4 README に旧語を 1 つ戻す／G5 plugin.json を 0.15.0 に／G6 `chmod -x`／G7 handoff に `#56` を 1 つ挿入／G8 **scratch worktree で禁止パス（例: `skills/audit/scripts/ax-probe.sh`）を許可パスへ `git mv` してコミット**（rename 旧パスの検出を直接確認。実ツリーは触らない）／G9 probe に構文誤り／G10 `*-log.txt` を `git add -f`（直後に `git rm --cached`）／G11 SKILL.md の行 3 の直後に frontmatter 行を 1 行挿入（総行数不変の確認）＋ 行 778 を 1 文字変える（期待文字列照合の確認）／G12 method 本体を `pass` に。加えて **変更前ツリー（`git worktree add <scratch> e1c0b19`）で全体が FAIL** することも実測。
- **A3** 実機再現（#65）: boss が scratchpad の git repo で、`PATH` 先頭に「呼び出しを記録してから実物へ exec する `codegraph` ラッパー」を置き、(i) `.codegraph/.DS_Store` のみ → 修正後 probe が `reason:"ok"`・ラッパー記録 1 回（`init .`）、(ii) `codegraph.db` をディレクトリにして → `index-failed`・ラッパー記録 **0 回**、(iii) `CODEGRAPH_DIR=.codegraph-win` で (i) を再実行 → `.codegraph-win/codegraph.db` が生成され `.codegraph/` は不変（着手前 probe では (i) が `index-failed` — 実測済み）。記録ファイルの内容を REVIEW.md に貼る。

### B. boss 検収（人手。判定根拠を REVIEW.md に記録）
| # | 観点 | 記録項目 |
|---|---|---|
| B1 | 5.2 の各テストが fake の log 実体で subcommand／不実行を判定しているか（stdout だけで通る検査は差し戻し）。**加えて `tests/test_release_handoff.py`・`tests/test_scaffold.py`・`tests/test_v015_contracts.py`・`tests/test_v0131_docs_contracts.py` の新規・変更 method 本文を全て読む**（無意味な assert・検査位置の誤りを差し戻す） | 精読した method 名の一覧と、N1〜N15 → method 名の対応表 |
| B2 | 差分全行読解（分岐表 5.1 との一致、JSON 3 キー、stderr 文言） | 差分の行数・所見 |
| B3 | 文書 13 行の置換後文言が挙動（対話 1 回 offer・非対話は期待スキップ）と矛盾しないか、en/ja の対応 | 13 行の新旧対照 |
| B4 | 手順 5 の `codex exec review`（Sol high） | blocking 件数（期待 0）・非 blocking の裁定 |
| B5 | route-close `/docaudit:audit` | verdict（期待 CONSISTENT）・incremental/full の別・runid |

## 7. 変更範囲

**許可（この一覧のみ）**:
- `skills/audit/scripts/codegraph-probe.sh`
- `tests/test_codegraph_probe.py`, `tests/test_scaffold.py`, `tests/test_v013_contracts.py`, `tests/test_v0131_docs_contracts.py`, `tests/test_v015_contracts.py`, `tests/test_release_handoff.py`
- `skills/audit/SKILL.md`（:3 の括弧内、:216-218、:560-563 内、:778 のみ — G11 が行単位で機械検査。**行の挿入・削除は禁止**、許可行の中で書き換える）, `skills/audit/references/config-schema.md`（:280-282 のみ — G11）, `skills/audit/references/engine-shas.json`
- `README.md`, `docs/ADOPTION.md`, `docs/ADOPTION.ja.md`, `.claude-plugin/plugin.json`
- route 記録（**具体パス配列**。gate G8 の許可集合・G10 の force-add 配列は同一の定数）: `tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md`, `.../REVIEW.md`, `.../release-handoff.sh`, `.../gate.py`, `.../prompts/sol-r1.md`〜`sol-r5.md`, `.../prompts/opus-r1.md`〜`opus-r2.md`, `.../prompts/impl-r1.md`〜`impl-r5.md`, `.../sol-r1-out.md`〜`sol-r5-out.md`, `.../opus-r1-out.md`〜`opus-r2-out.md`, `.../impl-r1-out.md`〜`impl-r5-out.md`, `.../codex-review-out.md`, `tasks/route/2026-08-30-issues-59-63-65-66/00-issue-review.md`。同ディレクトリの `*-log.txt`・`PLAN.rev*.md` は ignored の作業ログで変更集合に現れない（追跡は禁止、G10 が検査）。**接頭辞・glob による許可は無い** — G8・G10・force-add は同一の有限配列を共有する。

**禁止**: 上記以外の全ファイル。特に `skills/audit/scripts/*.py`、他の probe、`docs/superpowers/**`、`tasks/route/2026-08-29-*/**`、`.gitignore`、dir-framework 側の一切。
**標準文言**: 許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 8. 検証コマンド一式

```
python3 tasks/route/2026-08-30-issue-65-v0.15.1/gate.py --base e1c0b19   # A1: GATE PASS / exit 0
# A2（boss）: G ごとの違反 fixture（§6 A2 の一覧）で単独 FAIL を実測、および e1c0b19 worktree で全体 FAIL
python3 -m unittest tests.test_codegraph_probe -v                          # 参考表示（ゲートは gate.py）
python3 -m unittest tests.test_v013_contracts tests.test_scaffold tests.test_v015_contracts tests.test_release_handoff -v
```
A3（boss）: scratchpad で codegraph ラッパー（`#!/bin/bash; printf '%s\n' "$*" >> "$LOG"; exec /Users/akiratakahashi/.local/bin/codegraph "$@"`）を PATH 先頭に置き、Issue #65 の repro 手順と「db がディレクトリ」の 2 ケースを実行。
