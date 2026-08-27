# S3 実装依頼 — #44 `import-audit-scope.py`（audit-scope.json → impactMap 生成・照合）＋ init/audit SKILL Phase 0 配線（PLAN rev.8 §9）

あなたは実装者（worker）。boss（Fable）が計画とレビューを担当する。計画の正本は
`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md`（rev.8、Opus 承認済み）。**§9 を仕様として一字一句従う**。本依頼の範囲は
**S3 のみ**。start-run の `auditScopeSha` 封印・gate の再照合（S4a）、#42（S4b）、handoff（S5）は行わない。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアスや定型回答を1〜2行で自己申告してから始める。
与えられた前提・常識・スキーマを疑う。依頼文の前提が怪しければ、黙って従わず先に指摘する。

包括承認（boss）: 読み取り・テスト実行・許可パス内の編集は事前承認済み。個別確認を求めずに完了まで進めよ。**git 操作
（checkout/add/commit）は sandbox の制約で失敗するため行わない — boss が行う。** 許可パス外・`git push`・`rm -rf`・パッケージ
導入は禁止（必要なら報告のみ）。

## 0. 事前準備
1. 現在のブランチが `feat/v0.13.0-issues-39-44`（S1・S2 のコミットが載っている）であることを `git log --oneline -5` で確認。
   `git status --short` が空（`.claude/` を除く）であること。
2. フルスイートを実行し着手前の件数と結果を記録。
3. 参照実装を読む（read-only、書き込み禁止）: `~/Projects/dir-framework/.claude/audit-scope.json`（24 規則）と
   `~/Projects/dir-framework/scripts/resolve-audit-scope.py`（重複 key 検出・`validate_map`・fnmatch 方言）。**同 repo には
   一切書き込まない**。テストで使う場合は一時 dir にコピーする。

## 1. 新規 `skills/audit/scripts/import-audit-scope.py`
stdlib のみ。`docaudit_paths` の `validate_repo_path` / `list_doc_files` / `matches_glob` を再利用（`resolve-impact.py` の
`matches` と同じ意味論であること）。

### 1.1 引数
`--repo-root`（既定 cwd）、`--config`（既定 `.claude/doc-audit.json`）、`--scope`（既定 `.claude/audit-scope.json`）、`--doc-glob`
（反復可。config 不在時の docGlobs）、`--check`（既定）｜`--write`、`--json`、`--expect-config-sha <sha256:64hex|none>`・
`--expect-scope-sha <sha256:64hex>`（`--write` で必須）、`--base-config -`＋`--expect-base-config-sha <sha256:64hex>`（初回作成。
config が存在すれば拒否。stdin bytes を lock 内で一度だけ読む）。

### 1.2 検査順序（PLAN §9「検査順序」— この順で、早期 return）
(0) `--config`/`--scope` のパス安全: repo 内包含・symlink 非経由（`validate_repo_path(must_exist=False)` 相当。存在検査は分離）。
(1) scope 不在 **かつ** config に `auditScope` metadata 不在 → `state:absent` exit 0。**この時点まで git を 1 回も呼ばない**。
(2) `auditScope` metadata の型契約: object／`path` は repo 内 relative 文字列（絶対・`..`・repo 外は違反）／`sha256` は
`^[0-9a-f]{64}$`／`rules` は int ≥ 0 かつ **bool でない**／`importedAt` は文字列。違反は `errors[]`＋exit 1（`not-imported` に
落とさない）。
(3) scope 読み込み・規則検証: `json.loads(..., object_pairs_hook=...)` で重複 key 検出→error。最上位非 object→error。値は
「非空の文字列配列」または `{"impact":"none"}`（この 1 組のみの object）だけ。裸 catch-all（`*`・`**`・`**/*`）→error。規則キー・
影響先文字列に CR/LF があれば→error。
(4) 影響先: `validate_repo_path` で実在の通常ファイル、かつ docGlobs（config の `docGlobs`、config 不在時は `--doc-glob`、いずれも
無ければ既定 `["docs/**/*.md","*.md"]`）に一致し、`auditReportsInCorpus` が `true` でない限り report 除外後の corpus に含まれる
こと。外は「`docGlobs` を拡張してから再実行」の指示つき error。
(5) `git ls-files -z` と `git ls-files -z --others --exclude-standard` を NUL 区切りで列挙し、CR/LF を含む名前は error
（`unsupported filename`）。規則ごとに `fnmatch.fnmatchcase` の一致集合と変換後 glob の `matches_glob` 一致集合を比較し、不一致は
error（規則・差分例 3 件）。`equivalenceChecked` = 列挙件数。0 件は error。
(6) 変換・再生成・照合（1.3／1.4）。
error ≥ 1 のとき何も書かず exit 1、`errors[]` を列挙。

### 1.3 glob 変換（構文限定、PLAN §9「変換」）
各 `*` の連続 → `**`。次は拒否（error、規則名つき）: 置換後 `**` の直後が `/`（元の `*/`・`**/`）、`?`、`[`、先頭 `./`、末尾 `/`、
空文字、裸 catch-all。許可範囲では fnmatch と docaudit の正規表現が同一であることをテストで固定する（1.6）。

### 1.4 `--write`（PLAN §9「`--write` 順序」— この順で）
1. run-base `.claude/state/docaudit-run` が不在なら、各構成要素（`.claude`、`.claude/state`、`.claude/state/docaudit-run`）の
   symlink 検査（`os.lstat`）を経て 0o700 で作成。既存構成要素が symlink なら error。
2. lock `.claude/state/docaudit-run/lock` を `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` で作成（既存は exit 3「run in progress」）→
   fd に `fcntl.flock(LOCK_EX|LOCK_NB)` → `os.fstat(fd).st_ino == os.lstat(path).st_ino` を確認（不一致は無変更で exit 3）。
   holder として `{"owner":"import-audit-scope","runid":null,"startedAt":<UTC ISO>}` を書く。
3. **lock 内で** config（または `--base-config -` の stdin bytes を一度だけ読む）と scope を読み直し、`--expect-config-sha`
   （config 不在は `none`）・`--expect-base-config-sha`・`--expect-scope-sha` と照合。不一致は exit 4。
4. 生成: `impactMap` から `source == "audit-scope"` の項目を全削除し、変換結果を `{changed, impacts, source:"audit-scope",
   note:"generated from <scope path>"}` として末尾に追加（他項目は `note` の内容にかかわらず順序・内容保全）。`{"impact":"none"}` は
   `skippedNoImpact[]`。`auditScope: {path, sha256, importedAt, rules}` を config に記録。完成 config を一時ファイル（同 dir）に書き
   `os.replace` で原子作成（indent=2・ensure_ascii=False・末尾改行）、dir fsync。
5. `finally`: fd/path の inode 一致を確認して unlink・flock 解放。例外経路でも同じ。

### 1.5 `--check`（PLAN §9「`--check`」）
scope から auto 項目（multiset: `(changed, tuple(impacts))` の Counter）を再生成し、config の `source == "audit-scope"` 項目の
multiset・`auditScope` metadata（`sha256` が scope の現 sha と一致、`path` が `--scope` と一致）と照合。
- `absent`（metadata なし・scope なし）exit 0／`not-imported`（metadata なし・scope あり）exit 2／`drift`（metadata ありで scope
  消失、または sha 不一致、または multiset 不一致）exit 2／`in-sync` exit 0。
- `--json` 出力: `{state, rules, translated:[{changed, impacts, from}], skippedNoImpact[], errors[], equivalenceChecked, configSha,
  scopeSha, diff:{missing[], extra[]}}`（`configSha` は config bytes の `sha256:<hex>`、不在は `none`）。非 `--json` は人間向け要約。

### 1.6 テスト `tests/test_import_audit_scope.py`（PLAN §6 #44 (i)〜(viii) を**すべて**）
- (i) 変換の正例（リテラル、`*`、`**`、末尾 `/**`、`prefix-*.py`、`dir/*.json`、`.claude/*.json`）と反例（`*/foo`、`**/*`、`?`、`[`、
  `./x`、`x/`、空、catch-all）。反例には**両方言で食い違う具体パス**を assert に含める（`*/foo` は fnmatch で root `foo` 不一致・
  docaudit `**/foo` で一致、`?` は fnmatch で `a/b` 一致・docaudit で不一致）。許可範囲で `fnmatch.translate` の regex と
  `matches_glob` の一致集合が合成パス集合（`a.md`、`d/a.md`、`d/e/a.md`、`d/a.mdx`、`.a.md`、`d/.a.md`、`a-b.md` 等 ≥ 12 件）で等しい。
- (ii) `scope absent && metadata absent` で git を 1 回も呼ばない（PATH に偽 `git` を置き呼び出し回数を記録。CR/LF 名の存在に
  かかわらず exit 0）。導入時は tracked＋untracked の CR/LF 名が error。`equivalenceChecked ≥ 1`、0 件は error。
- (iii) 重複 key／空影響先／不在影響先／非文字列／不正値／`docGlobs` 外／`impact:none` 以外の object を拒否。report 除外の対試験
  （同一設定で `auditReportsInCorpus:false` → report path の影響先だけ拒否、`true` → 受理）。規則キー・影響先の CR/LF 拒否。
- (iv) `{"impact":"none"}` のスキップと `skippedNoImpact[]`。
- (v) `--write` の順序契約: fresh repo（`.claude/state` 不在）で run-base が 0o700 で作られる／symlink 化した `.claude/state` で
  exit 1・無変更／既存 lock で exit 3／flock 保持中に `open-run.py --break-lock` が拒否される（実プロセス: importer を故障注入で
  lock 内停止させ、その間に open-run を実行）／flock 前 unlink（inode 不一致）で無変更停止／expect SHA 不一致で exit 4・無変更／
  故障注入 replace 前（旧 config 不変・lock 不在）と replace 後 dir fsync（完成 JSON のみ存在・lock 不在）／`source` 項目の全置換と
  他項目保全（`note` が `auto: audit-scope` で始まる手書き項目を含む）／初回作成 `--base-config -`＋`--expect-base-config-sha`
  （既存 config があれば拒否、stdin sha 不一致で exit 4、成功時に完成 config が一度で現れ auto なしの中間状態が観測されない）。
- (vi) `--check`: 4 経路の drift（scope 変更／auto 手編集／auto 削除／metadata ありで scope 消失）、重複 auto 項目 1 件削除の drift
  （multiset）、`absent`／`not-imported`／`in-sync`。metadata 型異常 6 種（非 object、`path` 絶対、`path` repo 外、`sha256` 形式違反、
  `rules` bool、`importedAt` 非文字列）が error。反復 `--doc-glob`: 2 つの glob にだけ属する影響先を各 1 件用意し両方受理／
  `--doc-glob 'docs/a,b/**/*.md'` がカンマを含む 1 glob として扱われる。
- (vii) `--config`/`--scope` の repo 外・symlink 拒否（存在検査と分離: 不在 config は許容）。custom `--scope` の metadata 保存。
- (viii) `source` 互換は S2 で作成済み — 存在を確認し、無ければ追加。
- 実物検査（boss も別途行う）: `~/Projects/dir-framework` の `.claude/audit-scope.json` と tracked ファイル群を一時 dir に
  コピー（`git init` して add）し、config 不在で `--check --json --doc-glob '**/*.md'` → `rules=24`・`errors=[]`・
  `equivalenceChecked=46`・`state=not-imported` を assert するテスト（dir-framework が無い環境では skipTest）。

## 2. SKILL 配線
### 2.1 `skills/audit/SKILL.md` Phase 0
`--break-lock` 早期 exit 段落（`:19-24`）の**後**、lock 取得側 `open-run.py` 行（`:25`）の**前**に、次を追加:
- `AUDIT_SCOPE_PATH` を config の `auditScope.path` から bind（無ければ `.claude/audit-scope.json`）。
- `python3 "$SD/scripts/import-audit-scope.py" --repo-root "$CLAUDE_PROJECT_DIR" --config "$CFG" --scope "$AUDIT_SCOPE_PATH" --check --json`
  を実行し `AUDIT_SCOPE_STATE` を bind。
- `state ∈ {drift}` または `errors` 非空 → **open-run を呼ばず停止**。停止メッセージは `diff.missing`／`diff.extra`（または
  `errors[]`）と復旧コマンド `/docaudit:init --import-audit-scope` を含む。`not-imported` → 💡 1 行で継続。`absent`／`in-sync` → 無音。
- Phase 5 の status 行は追加しない。
### 2.2 `skills/init/SKILL.md`
- front matter `argument-hint` に `--import-audit-scope` を追加。
- `--import-audit-scope`: 既存 config があっても許可される例外（`--harness` と同様に明記）。手順: `--check --json` を実行し
  `diff.missing/extra`・`translated`・`skippedNoImpact`・`configSha`・`scopeSha` を提示 → AskUserQuestion で承認 → `CONFIG_SHA`・
  `SCOPE_SHA` を `--check` 出力から bind → `--write --expect-config-sha "$CONFIG_SHA" --expect-scope-sha "$SCOPE_SHA"`。承認なしに
  書かない。
- 初回 init（config なし）: Step 2 の impactMap 起草は scope があれば `--check --json --doc-glob <draft の docGlobs 各値>` の
  `translated` を STARTER にする（mentions 起草より優先）。Step 3 承認後、承認済み draft config（auto 項目なし）を Write tool で
  `$TMPDIR` 等 repo 外に書き、その sha256 を `DRAFT_SHA` に bind し `--write --base-config - --expect-base-config-sha "$DRAFT_SHA"
  --expect-scope-sha "$SCOPE_SHA" < <draft>` で完成 config を一度で作成する。
### 2.3 docs
- `skills/audit/references/config-schema.md`: 設定キー表に `auditScope`（`{path, sha256, importedAt, rules}`、importer が書く・
  手編集しない）の行、impactMap 項目の任意キー `source`（予約値 `audit-scope`）の説明。
- `docs/ADOPTION.md`・`.ja.md` §6 に「audit-scope.json がある場合」節: 正本は audit-scope、docaudit は生成物、drift で Phase 0 停止、
  復旧は `/docaudit:init --import-audit-scope`、run 間の import では `--accept-config` は不要（exit 6 は実行中 config 変更で REFUSED
  した場合のみ）、run 中は lock で拒否、`{"impact":"none"}` は heuristic が拾い得る。
### 2.4 契約テスト `tests/test_v013_contracts.py`
(a) init front matter を解析して `argument-hint` に `--import-audit-scope`；(c) Phase 0: `import-audit-scope.py --check` 行が
`--break-lock` 早期 exit 段落の後・**lock 取得側**（`--break-lock` を含まない）`open-run.py` 行の前にあること、check 行に
`--scope "$AUDIT_SCOPE_PATH"`、その bind 行が `auditScope.path` を参照、drift/errors 分岐が lock 取得側 open-run を呼ばず停止し
メッセージに `diff.missing`/`diff.extra` と `/docaudit:init --import-audit-scope` を含む、`not-imported` のみ継続；(d) init の
`--write` 行が `--expect-config-sha "$CONFIG_SHA" --expect-scope-sha "$SCOPE_SHA"`、初回行が `--base-config - --expect-base-config-sha
"$DRAFT_SHA"`、各変数の bind 行が `--check` 出力（`configSha`/`scopeSha`）参照；(h) の `auditScope` 行と `source`。
（S2 が有効化済みの項目は触らない。各検査は**行単位**で行い、説明文中の語の出現では通らないこと。）

## 3. 完了条件（PLAN §6 #44 全項目＋契約 (a)(c)(d)(h)）
- フルスイート全 green。件数を報告（前後）。
- 1.6 の各項目について、テスト名と検査内容の対応表を報告に含める。主要 3 件（lock 順序・expect SHA・multiset drift）について
  実装を revert すると赤になることを確認し方法を報告。

## 4. 変更範囲（PLAN §7 抜粋）
**許可**: `skills/audit/scripts/import-audit-scope.py`（新規）、`skills/audit/SKILL.md`（Phase 0 の該当箇所のみ）、`skills/init/SKILL.md`、
`skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`tests/test_import_audit_scope.py`（新規）、
`tests/test_v013_contracts.py`、`tests/data/audit-scope/`（新規 fixture）。
**禁止**: `open-run.py`・`start-run.py`・`decide-verdict.py`・`docaudit_paths.py`・`resolve-impact.py`・`compute-baseline.sh`・
`~/Projects/dir-framework`（読み取りのみ）・`tasks/`・`.gitignore`・`.claude/`。既存 assert の変更禁止。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 5. 検証コマンド一式
```bash
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_import_audit_scope tests.test_v013_contracts -v
```

## 6. コミットと報告
- Conventional Commits（例: `feat(audit-scope): import-audit-scope.py — deterministic impactMap from audit-scope.json (#44)`、
  `docs(audit-scope): init --import-audit-scope, Phase 0 drift stop, config-schema`）。push はしない。
- 報告は結論先行・完全な文で。各主張はツール結果と突合し、未検証は未検証と明言。テスト失敗は出力ごと報告。末尾に
  「変更ファイル一覧」「テスト件数（前後）」「許可外変更の必要有無」「テスト名⇔検査内容の対応表」。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認
