# REVIEW — Issue #65 ＋ #66 文言是正 → docaudit v0.15.1

## セッション ID
- 計画批判（Sol high・read-only）: 01a051fb-eb23-72a2-88ca-ef544c4a067f
- 実装（Terra medium・workspace-write）: 01a0524f-417a-7dd3-b240-ff1c81596bde

## ベースライン
- main HEAD: e1c0b19（clean）
- フルスイート: Ran 630 tests OK（skip 0、191.8s、boss 実測 2026-08-30）
- 残骸 grep（#66 文言）: README 3・ADOPTION.md 4・ADOPTION.ja.md 4・SKILL.md 1 ＝ 12 行（着手前実測 2026-08-30）

## 計画批判ラウンド

### Sol ラウンド1（差し戻し・11件: HIGH 7 / MEDIUM 4）— 出力 `sol-r1-out.md`
boss が全件を実物照合（codegraph 1.5.0 `directory.js`・scratchpad 実測・grep 実数）。HIGH 7 件は全て事実:
1. HIGH: `codegraph.db` が非通常ファイル（ディレクトリ等）でも codegraph 1.5.0 は存在のみで初期化済み判定し `init` rc=0 → 偽 `ok`。boss 実測: db をディレクトリにして `init` rc=0・`sync` rc=1 → 3 分岐（通常ファイル→sync／不存在→init／存在する非通常→不実行 index-failed）へ（PLAN 5.1 分岐表）
2. HIGH: `CODEGRAPH_DIR` 環境変数（`directory.js codeGraphDirName()`）を probe が無視 → 同じ妥当性規則で解決（5.1 前処理・N10〜N12）
3. HIGH: `.codegraph` 自体が symlink の場合 `-f` も codegraph も追跡 → dir symlink／非ディレクトリも不実行 index-failed（行 1・2）
4. HIGH: テスト実数は 20（PLAN rev.1 の 19 は誤り）・増分条件の矛盾・「.DS_Store だけなら init」の誤実装が通る → N1〜N14 を列挙し ≥32 本・log 実体判定を明記
5. HIGH: 古い記述は 13 行（SKILL.md:3 description、ADOPTION.ja.md:11/79 の変種を rev.1 が見落とし）・`grep; echo exit=$?` は常に exit 0 → 対象行を 13 行に訂正・`! grep -E` の単一ゲート（A4）
6. HIGH: test_scaffold の "0.15.0" は 7 箇所・test_v013_contracts:210,215 の allowlist 正規表現も同期対象 → 5.5 に明記
7. MEDIUM: refresh 列挙文は 0.10.0・0.14.0 を欠く → engine-shas の全キー列挙＋0.15.0→0.15.1 の直接 refresh テスト追加
8. HIGH: `.gitignore:8` が `tasks/` を無視・`git diff main...HEAD` は untracked/staged を含まず自身 exit 0 → force-add（A6）・porcelain 統合スコープ検査（A8）
9. MEDIUM: 複製 handoff の v0.15.0/#56 残骸検出なし・#66 OPEN 事前条件なし → A7 残骸 0 検査・#66 OPEN 条件
10. MEDIUM: v0.15.1 挙動変更ブロックが欠けても通る → test_v015_contracts.py を許可範囲へ・完全一致テスト追加
11. MEDIUM: §6 が機械判定になっていない → A（機械ゲート 10 項目: コマンド・期待）/ B（boss 検収 5 項目: 記録項目）に分離

対応: 11 件全て PLAN rev.2 に反映（rev.1 は `PLAN.rev1.md` に保存）。

### Sol ラウンド2（差し戻し・12件: HIGH 7 / MEDIUM 5）— 出力 `sol-r2-out.md`
1. HIGH: `CODEGRAPH_DIR` の trim/妥当性規則を bash で複製しても同値性は保証できない（JS trim の文字集合、`foo..bar`、`\` 単独、NBSP/BOM 等）→ **解決済み値を codegraph へ明示エクスポート**して構成的に同値化＋JS trim と同じ明示文字クラス＋N12 を無効/有効の入力表に拡張
2. HIGH: FIFO 等の非通常ファイル一般化が未検査 → N5b（db FIFO）・N9b（dir FIFO）追加
3. HIGH: 件数基準の矛盾（probe 20→≥33、handoff 実測 24、全体 ≥647）・N14 は既存本体変更 → 数値を統一、改修 2 として明示例外
4. HIGH: A1〜A8 がパイプ経由で失敗を exit 0 に化かす → 単一 `gate.py`（G1〜G10、明示比較、実数表示）に集約し、変更前ツリーで FAIL を実測する A2 を新設
5. HIGH: A8 の porcelain 解析（空白パス・rename・/tmp 固定）→ gate.py G8 で `-z`・porcelain=v2・rename 両端・tempfile
6. HIGH: fake が cwd/env を記録しない → JSON 行 `{argv,cwd,CODEGRAPH_DIR}` を記録し完全一致、継承 `CODEGRAPH_DIR` を除去
7. HIGH: #66「挙動不変」の自動契約なし → test_v015_contracts に状態トークン 3 箇所・上流文字列・分岐文の回帰契約
8. MEDIUM: 「ユーザー実行のみ」「user-invocation-only」の旧意味残骸 → G4 の残骸リストに追加
9. MEDIUM: handoff の実行属性未検査 → G6 で index mode 100755 ＋ X_OK
10. MEDIUM: stderr への `DIRNAME` 生埋め込み → `printf '%q'` で 1 行エスケープ（N14）
11. MEDIUM: A10 が不実行を証明できない → 記録ラッパーを PATH 先頭に置き呼び出し 0 回を確認（A3）
12. MEDIUM: route dir の force-add が広い → 追跡ファイルを名指し（`*-log.txt`・`PLAN.rev*.md` は追跡外、G10）

対応: 12 件全て PLAN rev.3 に反映（rev.2 は `PLAN.rev2.md`）。G4 の変更前実測（5 語の出現数）は下記ベースライン欄に追記。
- G4 変更前実測（`grep -o`、対象 5 ファイル）: not model-invocable 7・user-invocation-only 3・モデルから起動できない 2・モデルからは起動 2・ユーザー実行のみ 1 ＝ 15 出現／13 行

### Sol ラウンド3（差し戻し・14件: HIGH 10 / MEDIUM 4）— 出力 `sol-r3-out.md`
boss 照合: codegraph 1.5.0 の `init` は TTY があると対話プロンプト（nested repo 索引・git hook 設置）を出す（`bin/codegraph.js:472,622`、`installer/index.js:596`）。非 TTY の scratch 実測では hook 未設置・`codegraph.json` 未生成。`init` に `--yes` は無い。committed rename は `--name-only` では新パスのみ（Sol 実測）。
1. HIGH: 内部改行・空白を含む `CODEGRAPH_DIR` は codegraph では有効／既存の空白区切り `read` が値を壊す → NUL 区切り受け渡し・内部空白/改行を有効扱い・N12/N14 に追加
2. HIGH: export は Phase-3 verifier に伝播しない → 「同じ env で同じ規則」により整合、export は保険と位置付け、Workflow 引数化は範囲外（#63 と同時）として REVIEW に持ち越し
3. HIGH: `init` の対話プロンプト・hook 設置 → `</dev/null` で非対話化、fake が `stdin_eof` を記録して検査
4. HIGH: 件数下限の不足 → 新規状態 17・probe ≥37・handoff ≥27・全体 ≥653
5. HIGH: committed rename の旧パス → `--name-status -z -M -C`
6. HIGH: 禁止 ignored 範囲（docs/superpowers・他 route）が G8 に現れない → G13（着手前 manifest との不変比較）
7. HIGH: G10 の「存在しない」と §7 の矛盾・brace glob・`prompts/*.md` の過剰一致 → 具体パス配列＋接頭辞、G10 は `git ls-files` 0 件
8. HIGH: G3 の改名先存在判定が弱い → base を e1c0b19 に固定・改名対応表を gate 定数に・G12（空 method 禁止）
9. HIGH: #66 契約が件数のみ → 5 文の完全文固定
10. HIGH: A2 が G ごとの有効性を証明しない → G ごとに違反 fixture 1 つで単独 FAIL を boss が実測
11. MEDIUM: N12 fixture → 選ばれるべき dir にだけ db（誤選択で init/sync が反転）
12. MEDIUM: dangling 親 symlink → N8b
13. MEDIUM: N13 の rc/末尾契約 → fake が rc=7 と印を出し検査
14. MEDIUM: 行範囲制限が未検査 → G11（hunk ヘッダ解析）

対応: 14 件全て PLAN rev.4 に反映（rev.3 は `PLAN.rev3.md`）。持ち越し: 解決済み DIRNAME の Workflow sealed 引数化（#63 route）。

### Sol ラウンド4（差し戻し・10件: HIGH 7 / MEDIUM 3）— 出力 `sol-r4-out.md`
boss 判定（advisor 助言を踏まえ、rev.5 を Sol 主導の最終改訂とする）: R4 の大半は gate.py 自体の堅牢化（gate-of-gate）であり、**成果物（probe/テスト/文書）に欠陥が残る経路**を示すものだけを採用する。
1. HIGH 採用: N12 を全 trim コードポイント（U+0009〜000D・0020・00A0・1680・2000〜200A・2028・2029・202F・205F・3000・FEFF）＋非対象 U+001C〜001F の表駆動に
2. HIGH **却下（根拠つき）**: 現行出荷版は probe が既定 dir・codegraph が `CODEGRAPH_DIR` dir を見る乖離状態。本版は乖離を厳密に縮小するのであって導入しない。完全閉鎖（sealed 引数化）は #63 の封印入力設計に属する → 持ち越し維持
3. HIGH 採用: テストは全ケースで sentinel を stdin に与え timeout 必須。`</dev/null` を外した実装だけが sentinel を fake に読ませる
4. HIGH 採用: G10 を必須成果物／任意生成物（存在時のみ追跡）に分離、§5.6 の glob 表記を配列参照に統一
5. HIGH 採用（一部）: PRECLOSED={"65"}（rev.4 の「空」は :428 と矛盾する実バグ）。新規 3 テストの必須 assert を固定。無意味テストの最終防衛は B1（boss 精読）と明記。AST の一般判定拡張は不採用
6. HIGH 採用: G11 を内容検査に（行 3・778 は完全一致、他は replace のみ、insert/delete は位置を問わず 0）。行 3 の新文字列を PLAN で固定
7. HIGH 一部採用: G13 に `.envrc` と種別/mode/symlink 先を追加。ignored 全体への拡張は却下（`tests/__pycache__` は G1 自身が書き換える／`.mdq/` SessionStart／`.serena/`・`.brv/` 自発変化 → 偽 FAIL）。`AGENTS.md` は本 repo に存在しない（`git check-ignore` は y だが実体なし）
8. MEDIUM 採用: G8 の接頭辞許可を削除（ignored のログは変更集合に現れない）
9. MEDIUM 採用: G2 fixture は既存 method の一時改名
10. MEDIUM 採用: G8 fixture は scratch worktree での禁止→許可パス `git mv` コミット

対応: 8 件採用・1 件一部採用・1 件却下。PLAN rev.5（rev.4 は `PLAN.rev4.md`）。

### Sol ラウンド5（最終・上限到達・7件: HIGH 5 / MEDIUM 2）— 出力 `sol-r5-out.md`
停止規則どおり「誤成果物が出荷される経路」を持つものを判定。5 HIGH は全て経路が具体的（boss 照合: `tests/test_v0131_docs_contracts.py:90` の版集合固定は実在）。
1. HIGH 採用: `test_v0131_docs_contracts.py:90` の refresh 版集合を同期（許可範囲・成果物に追加）
2. HIGH 採用: `%q` は U+2028/2029 を素通し → ASCII 限定エスケープ（`ascii()` 相当）、N14 に追加
3. HIGH 採用: 不正 UTF-8 env → `os.environb` を `errors="replace"` で復号（Node と同じ U+FFFD）、N15 追加
4. HIGH 採用: #66 負テストに `assert_no_release_mutations()` 必須、B1 の精読対象を handoff/scaffold/v015/v0131 の新規・変更 method に拡張
5. HIGH 採用: §7 の接頭辞残骸を削除、G10 の任意生成物を有限配列に
6. MEDIUM 採用: status line の文言を実フロー（offer 時に実行→再開、または事前）に合わせる
7. MEDIUM 採用: sentinel は str（helper が `text=True`）

対応: 7 件全て PLAN rev.6（rev.5 は `PLAN.rev5.md`）。Sol 5 往復で上限到達。未収束の残余は無し（R5 は全件採用で閉じた）。次: Opus 全体敵対レビュー（手順 3.5）。

### Opus ラウンド1（change-reviewer・差し戻し・ブロッキング 4＋縮小提案 5＋実行可能性 4＋軽微 3）— 出力 `opus-r1-out.md`
boss 照合: SKILL.md:218 の `fast);` は 217 の続き（実測）。difflib の 1 行挿入は `insert`（Opus 実測）。`test_j`（test_v013_contracts:203）は `0.12.0` リテラルを走査（実測）。
- B-1 採用: 許可範囲 216-218、config-schema 282 は主語 `codegraph` で終える、行数維持
- B-2 採用: 注記許可を削除、G11 を行単位比較（総行数不変・許可行以外完全一致・行 3 は replace で生成・行 778 はリテラル）へ
- B-3 採用: 4 フィールド `DIRNAME_ESC` を python 側で生成、read イディオムと python 4 出口の明記（(d)1・(d)2 も同時に反映）
- B-4 採用: v0131 の版集合は engine-shas キーから導出
- S-1 採用（boss 判断）: G13 削除。根拠: `docs/superpowers`・`.envrc` は追跡 0 件で出荷されず、追跡済み route dir の改変は G8 が捕捉
- S-2 採用: trim 表は維持（table-driven で安価）＋U+0085 を「剥がれない」側に追加。U+FEFF が最重要と明記
- S-3 維持: `CODEGRAPH_DIR` 尊重は維持（無いと silent staleness が恒久化）
- S-4/S-5 維持
- (d)3 採用: fake は argv 記録前に stdin を読み切る／(d)4 採用: 行 3 期待行は gate 内で生成
- 軽微 1〜3 採用: auto-close は keyword+番号／symlink 構成の非対応を ADOPTION に明記／G4 の config-schema 注記
- repo 外の波及（範囲外・要フォローアップ）: dir-framework `docs/runbooks/initial-setup.md:50` の回避手順が v0.15.1 後に stale → 最終報告でユーザーへ

対応: PLAN rev.7（rev.6 は `PLAN.rev6.md`）。同一 Opus エージェントへ resume で再確認を依頼。

### Opus ラウンド2（**実装承認**・非ブロッキング 5）— 出力 `opus-r2-out.md`
rev.6→rev.7 の差分 70 行を全行読解し、B-1〜B-4・S-1/S-2 の反映を確認、新規の組み合わせ矛盾 7 点を実測して「無し」。非ブロッキング 5 件: (1) PLAN:21 の `:216-217` 残存 → 修正、(2) `tree-digest.py:12` KNOWN_ROOTS が `.codegraph` 固定で `CODEGRAPH_DIR` 改名 dir は digestExclude 不可（既存制限）→ ADOPTION ブロックに但し書き、(3) A2 G11 fixture に行 778 改変を追加、(4) `ascii()` の引用符 → テストは引用符込みで照合と明記、(5) PLAN:41 の理由文に U+0085 → 修正。全て PLAN rev.7a に反映。

## 実装（手順 4）
- モデル: Terra `medium`（仕様確定済みの通常実装）。プロンプト: `prompts/impl-r1.md`（ヘッダ＋PLAN §5〜§8 転記）
- 実装 R1: codex の workspace-write サンドボックスが `.git` への書き込み（`git switch -c`）を拒否し停止（`impl-r1-out.md`）。boss がブランチ `fix/v0.15.1-issue-65` を作成し、同一セッションを resume（`prompts/impl-r1b.md`: git 書き込み操作禁止・コミットと `git add -f` は boss が実施・G6/G8/G10 は worker 実行では FAIL 許容）。

### Worker 実装結果（git add 前）
- probe: `codegraph.db` 状態分岐、symlink／非通常ファイル拒否、`CODEGRAPH_DIR` 解決と明示 export、stdin 非対話化を実装。N1〜N15 の 18 method を追加し、既存 20 method を維持。
- 文書／版: #65 分岐説明、#66 の 13 行の古い根拠、v0.15.1 の en/ja 変更ブロック、version／engine-shas／refresh 契約を更新。
- handoff: #65 のみ close、#59/#63/#66 OPEN を公開前に確認、#66 は close しない契約を実装。
- 最終 gate 実数: `G1 PASS returncode=0 Ran 654 tests skipped=0`; `G2 PASS methods=38 base_methods=20 missing=[]`; `G3 PASS methods=27 expected=27 missing=[]`; `G4 PASS counts=0,0,0,0,0`; `G5 PASS 5 surfaces=0.15.1`; `G6 FAIL index_lines=0 mode=missing executable=True`; `G7 PASS counts=0,0,0,0`; `G8 PASS changed=14 outside=0`; `G9 PASS returncode=0`; `G10 FAIL required_missing=13 optional_present=7 optional_missing=7 unexpected=0`; `G11 PASS violations=0`; `G12 PASS empty_tests=0`; `GATE FAIL`.
- G6/G10 は worker が git 書き込みを禁止されているため想定どおり。boss が G10 の有限配列だけを `git add -f` し、handoff の index mode 100755 を確認した後に gate を再実行する。
- 指定テスト: probe `Ran 38 tests in 43.540s` / `OK`; v013+scaffold+v015+handoff `Ran 67 tests in 19.056s` / `OK`.
- boss 未実施: A2 各 G 違反 fixture、A3 実機 codegraph ラッパー再現、B1〜B5。

## 検収ラウンド1（boss）— 実装 R1（`impl-r1b-out.md`）
- 差分: 14 ファイル（+489/−85）＋route 新規 `gate.py`・`release-handoff.sh`。boss が全行読解（B2）。probe 本体は分岐表 7 行と一致、4 フィールド NUL 受け渡し・`ascii()` エスケープ・`</dev/null`・`CODEGRAPH_DIR` 明示 export を確認。
- B1: probe テスト 38 method（既存 20 名称残存）。N1〜N15 → method 対応表は worker 報告どおり実在し、全て fake の JSON log（argv/cwd/CODEGRAPH_DIR/stdin_eof）で完全一致判定。N12 は無効 9・有効 8＋trim 26 文字×前後＋keep 5 文字（U+0085 含む）×前後の表駆動。handoff 新規 3 method の必須 assert（#66 OPEN→close 66 無し/65 有り、非 OPEN→`assert_no_release_mutations()`、残骸 4 語 0）を確認。scaffold の 0.15.0→0.15.1 refresh テスト、v0131 の SHAS 由来集合、v015 の 5 文固定を確認。
- B3: 13 行の置換文言は挙動（対話 1 回 offer・非対話は期待スキップ）と矛盾なし。en/ja 対応あり。ADOPTION の v0.15.1 ブロックは 1 文が長い（軽微・許容）。
- A1（boss 実行）: `gate.py --base e1c0b19` → **GATE PASS**。G1 Ran 654 skip 0／G2 38（missing 0）／G3 27／G4 全 0／G5 全 0.15.1／G6 100755・X_OK／G7 全 0／G8 changed=34 outside=0／G9 OK／G10 required 0 missing・optional 7 present 0 missing・unexpected 0／G11 violations 0／G12 empty 0。記録: `gate-a1.txt`。
- フルスイート（boss 単独再実行）: Ran 654 tests OK（237.6s、skip 0）。ベースライン 630 → +24。
- A3（boss、codegraph 1.5.0 実物＋記録ラッパー）: (i) `.codegraph/.DS_Store` のみ → `ok`・呼び出し 1 回 `init .`（着手前は `sync .` → index-failed）；(ii) `codegraph.db` がディレクトリ → `index-failed`・呼び出し **0 回**・stderr `codegraph.db exists but is not a regular file`；(iii) `CODEGRAPH_DIR=.codegraph-win` で (i) → `.codegraph-win/codegraph.db` 生成・既定 dir は `.DS_Store` のまま不変；(iv) (iii) の 2 回目 → `sync .`。
- 実装 R1 で許可外変更の要求なし。差し戻し事項なし。A2 のため gate.py に `--only` を追加依頼（実装 R2、`prompts/impl-r2.md`）。

## 検収ラウンド2（boss）— A2 fixture と boss の作業ミス
- 実装 R2（`impl-r2-out.md`）: gate.py に `--only` を追加（guard で各 G を囲む素直な変更、`--only G13` は exit 2）。
- A2 実行（`a2-fixtures.sh`、scratchpad）で **boss のミス**: 各 fixture 後の復元に `git checkout -- <file>` を使ったが、worker の変更は未ステージだったため index＝HEAD 版へ巻き戻り、README.md・plugin.json・SKILL.md・codegraph-probe.sh・test_codegraph_probe.py・test_release_handoff.py の 6 ファイルの実装が作業ツリーから消失（証拠: G1 fixture の `Ran 633`・終了後の `git status`）。ステージ済みの route 成果物と fixture 対象外の 7 ファイルは無事。
- A2 の有効な結果（復元前に各 fixture が正しい内容に適用されたもの）: G2 FAIL（missing=[test_not_installed_degrades]）／G3 FAIL（missing=[…issue_66_open…]）／G4 FAIL（not model-invocable: 1）／G5 FAIL（plugin=0.15.0, stamp=0.15.0）／G6 FAIL（executable=False）／G7 FAIL（#56: 1）／G8 FAIL（outside=[ax-probe.sh]）／G9 FAIL（rc=2 syntax error）／G10 FAIL（unexpected=[sol-r1-log.txt]）／G11(a) FAIL（line-count 912→913 ＋ 778:exact）。**無効（要再実行）**: G11(b)（巻き戻し後の SKILL.md で実行され 3:exact/778:exact 両方 FAIL — 汚染）、G12（fixture が適用できず PASS 表示）、G1（巻き戻し後のファイルで実行、FAIL 自体は妥当だが件数 633）。
- 復旧: worker セッションを resume（`prompts/impl-r3.md`）し 6 ファイルを最終内容で再作成させる。復旧後、boss が差分を再読・A1 再実行・A2 の G1/G11(b)/G12 を**安全な手順**（全変更を先に `git add` してから fixture → `git checkout --` で index 版へ復元）で再実行する。
- 教訓（boss）: 未ステージの worker 変更がある作業ツリーで `git checkout --`／`git restore` を復元に使わない。fixture 前に必ず `git add -A`（許可ファイル）でスナップショットを取るか、`git stash`／バックアップコピーを使う。

## 検収ラウンド3（boss）— 復旧・A2 完了・A1 最終
- 実装 R3（`impl-r3-out.md`）: worker が 6 ファイルを最終内容で再作成。boss が `git diff e1c0b19` で再読し、検収ラウンド1 で読んだ内容と同一であることを確認（probe 本体・README・plugin.json・SKILL.md・handoff テストは全行、probe テストは構造検査: fake の JSON 記録／sentinel＋timeout／`os.environb`／trim 26＋keep 5 文字／不実行 assert 10 箇所／`assert_call` 16 箇所、method 38）。
- A2 再実行（安全な runner: 全変更を先に `git add` → fixture → `git checkout --` で index 版へ復元、各復元後に `git diff --quiet` で確認）: G11(b) 行 778 改変 → FAIL（`778:exact`）／G12 本体 `pass` → FAIL（`test_n1_...`）／G1 class 内に `assertTrue(False)` を挿入 → FAIL（`Ran 655`・`AssertionError`）。※最初の G1 fixture は `if __name__` ブロック末尾に追記したため discovery に載らず無効だった（fixture 側の誤り）ので、class 内挿入でやり直した。
- **A2 総括: G1〜G12 の 12 検査（G11 は 2 ケース）全てが各自の違反 fixture で単独 FAIL** し、正常状態では PASS。常に PASS する検査は無い。
- A1 最終（boss 実行、`gate-a1-final.txt`）: G10 のみ FAIL（impl-r2/r3 の任意生成物 4 件が未追跡）→ `git add -f` 後に `--only G10` PASS（optional_present=11・missing 0）。他 11 検査は PASS（G1 Ran 654 skip 0・G8 changed=34 outside=0）。
- 差し戻し事項なし。手順 5 の最終 `codex exec review`（Sol high）へ。

## 最終レビュー（手順 5）— `codex exec review --uncommitted -m gpt-5.6-sol high`（`codex-review-out.md`）
- 1 回目は `--uncommitted` 未指定で即エラー（`Specify --uncommitted, --base, --commit ...`）→ 付けて再実行。
- 指摘 2 件（boss 実物確認済み・両方採用）:
  - P1（安全・**差し戻し**）: `release-handoff.sh:51-54` の包含検査は `DEST_REAL == ROOT_REAL` を通し、`rsync --delete` が skills ルート全体を消し得る（v0.15.0 版から継承した欠陥）→ 等値拒否＋テスト追加＋gate G3/G1 下限更新（実装 R4、`prompts/impl-r4.md`）
  - P2（文書）: `docs/ADOPTION.md:165-166`／`docs/ADOPTION.ja.md:148` の「初期化済みへの `init` は拒否される」が v0.15.1 ブロックと矛盾 → 版依存・db 基準の説明へ（実装 R4）
- ADOPTION の当該段落は PLAN §5.4 の 13 行に含まれておらず、boss の波及走査（`is rejected`／`拒否される`）の漏れ。

## 検収ラウンド4（boss）— 実装 R4 の検収と承認
- R4（`impl-r4-out.md`）: handoff に `DEST_REAL != ROOT_REAL` の等値拒否を `DEST_REAL` 算出直後（:52、公開前）に追加、`test_destination_equal_to_root_stops_before_publication`（非 0・`not the root itself`・`assert_no_release_mutations()`・rsync 呼び出し 0）を追加、gate の G3 期待集合＋下限 28・G1 下限 655 を更新、ADOPTION en:165-166／ja:148 を db 基準・版依存の説明へ。boss が差分を全行読解、`grep 'is rejected|拒否される'` の残骸は codegraph 無関係の 3 件のみ。
- A1 最終（boss 実行、`gate-a1-final2.txt`）: **GATE PASS** — G1 Ran 655 skip 0／G2 38／G3 28／G4 全 0／G5 全 0.15.1／G6 100755／G7 全 0／G8 changed=41 outside=0／G9 OK／G10 required 0・optional 14 present 0 missing・unexpected 0／G11 0／G12 0。
- **判定: 承認**（PLAN §6 A1〜A3・B1〜B4 充足。B5 route-close は下記）。

## route-close（手順 7・close marker）
- 対象タスク: Issue #65（codegraph probe の自己回復・`CODEGRAPH_DIR` 尊重）＋ Issue #66 の古い記述の是正（文言のみ・挙動不変）→ docaudit v0.15.1（patch）。ブランチ `fix/v0.15.1-issue-65`。
- 記録時点の HEAD: `6aa539b2433b26fa034b63569864f2b5ec2371f3`（実装 commit。本 route-close 記録の commit はこの直後）。base = main `e1c0b19`。
- 確定した変更ファイル（`git diff --name-only e1c0b19..HEAD`、41 件）: engine 1（`skills/audit/scripts/codegraph-probe.sh`）／skill 文書 2（`skills/audit/SKILL.md`, `skills/audit/references/config-schema.md`）／版 2（`.claude-plugin/plugin.json`, `skills/audit/references/engine-shas.json`）／利用者文書 3（`README.md`, `docs/ADOPTION.md`, `docs/ADOPTION.ja.md`）／テスト 6（`test_codegraph_probe.py` 20→38, `test_release_handoff.py` 24→28, `test_scaffold.py` +1, `test_v0131_docs_contracts.py`, `test_v013_contracts.py`, `test_v015_contracts.py` +2）／route 記録 27（PLAN・REVIEW・gate.py・release-handoff.sh・prompts 10・critique/impl/review 出力 13、および `2026-08-30-issues-59-63-65-66/00-issue-review.md`）。作業ツリー clean。
- audit verdict: `.claude/doc-audit.json` 未導入（本 repo は docaudit 自身）のため `/docaudit:audit` は不実行（v0.15.0 と同じ扱い）。代替 = 機械ゲート gate.py **GATE PASS**（G1 Ran 655 skip 0／G4 古い記述 5 語 0 件／G11 許可行以外は e1c0b19 と同一）＋契約テスト（`test_v015_contracts` の v0.15.1 ブロック完全一致・#66 挙動不変 5 文、`test_v0131` refresh 版集合、`test_v013` 版整合）＋Opus (c) 波及走査（repo 内の古い記述は 13 行で完全、`~/.claude/skills/docaudit/` は handoff 同期で追随）＋codex review P2 で発見した ADOPTION en:165/ja:148 の是正。
- SSoT 更新: AGENTS.md／PROJECT.md は本 repo に存在せず、durable 規約の変更もない → **0 ファイル更新**。
- 検査系成果物の実数: gate.py 12 検査（A2 で 12 検査全てが違反 fixture で単独 FAIL を実測、G11 は 2 ケース）／probe テスト 38 method（N1〜N15 の 18 状態）／handoff テスト 28 method／フルスイート 655（ベースライン 630、+25）／A3 実機 4 ケース（codegraph 1.5.0）。
- 出荷（handoff）は未実施: push・PR・merge はユーザー、その後 `release-handoff.sh <merge-sha> <pr>`（tag `docaudit--v0.15.1`・Release・#65 close・skills-dir 同期。#59/#63/#66 が OPEN であることが事前条件）。
- 持ち越し: (1) dir-framework `docs/runbooks/initial-setup.md:50` の「init は拒否される」回避手順は stale（別途）、(2) dir-framework の `harness.engineVersion` を 0.15.1 へ（release 後）、(3) 解決済み DIRNAME の Workflow sealed 引数化は #63 route、(4) #63+#59 合同 route・#66 方式 B route は `00-issue-review.md` の決定に従い次に着手。

- PR: https://github.com/akira993/doc-audit-harness/pull/67（2026-08-30、head `a6d8e8e`、本文に closing keyword なし。マージはユーザー）
