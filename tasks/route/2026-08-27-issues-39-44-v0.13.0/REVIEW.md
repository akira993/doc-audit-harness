# REVIEW — Issues #39〜#44 → docaudit v0.13.0（2026-08-27）

boss = Fable（本セッション）。worker = Sol/Terra/Luna（`direnv exec . codex exec`、CODEX_HOME=~/.codex-doc-audit-harness、auth.json 確認済み 2026-08-27）。

## セッション ID 記録

- 計画批判セッション（Sol `high`, read-only）: `01a041dc-f683-74f0-be66-57abce7c0e97`
- 実装セッション S1（Terra `medium`, workspace-write）: `01a0423c-7062-7281-9663-f70cc30da98a`
- 実装セッション S2（Terra `medium`, workspace-write）: `01a04253-1d72-7e92-9aea-11b1c3230f21`
- 実装セッション S3（Terra `medium`, workspace-write）: `01a04263-772f-7261-b901-f12dde4b2b46`
- 実装セッション S4a（Sol `high`, workspace-write）: `01a0427f-72ea-7660-a992-4129d5757a0b`
- 実装セッション S4b（Sol `high`, workspace-write）: `01a04293-f7e4-7493-be7c-1fd2204dd162`
- 実装セッション S5（Terra `medium`, workspace-write）: `01a042b4-b8a4-7950-a9cb-4b293ea9ec42`

## インタビュー決定（route 手順 1、2026-08-27）

1. #44 方向: **audit-scope.json を正本 → impactMap を生成**（SHA 記録・Phase 0 で drift WARN）
2. 範囲: **#39〜#44 全部を v0.13.0 で**（1 ブランチ・1 PR）
3. #39/#41 深度: **最小実装**。boss 裁定: 多数決（phase3Votes）は据え置き・別 Issue 起票案（要ユーザー追認）

## 事前調査（read-only）

- 調査担当（architecture-researcher, Opus）: Evidence Pack → PLAN §2 に反映。主要発見: scaffold.py に impactMap
  書き込み経路なし／impacted == dispatch ∪ cached の二重強制／SKILL.md:617-619 が codex 3 状態を 1 行に畳む／
  trend table は存在しない／check-docs エンジンの実体は generic-layers.py。
- baseline: `python3 -m unittest discover -s tests -t .` → Ran 368 tests, OK（109 s、2026-08-27）。
- dir-framework HEAD 5ff26a9（local clone）: `resolve-audit-scope.py --validate` → 「規則 24 件を検証」exit 0。
- **#44 構文限定変換の実物検査（boss、2026-08-27、read-only）**: PLAN §9 の規則（`*`連続→`**`、`**/`・`?`・`[`・
  先頭 `./`・末尾 `/`・catch-all を拒否）を dir-framework の 24 規則に適用 → **拒否 0 件**。tracked 46 件に対し
  全 24 規則で `fnmatch.fnmatchcase` 集合 == `docaudit_paths.glob_to_regex` 集合（例: `.claude/*.json` →
  `.claude/**.json` 2/2、`scripts/check-*.py` → `scripts/check-**.py` 6/6、`docs/runbooks/**` 5/5）。

## 計画批判ラウンド（route 手順 3）

### R1（Sol high, read-only）— `critique-r1.md` → `critique-r1-answer.md`
23 件（BLOCKER 7・MAJOR 15・MINOR 1）。boss 検分の結果**全件採用**（3 件は実機確認のうえ採用: #3 `start-run.py:190`
の `phase4Required` 条件、#9 manifest が impact.json を封印しないこと、#21 exit 6 が実行中 config 変更時のみで
あること）。PLAN rev.2 への反映:

| # | 要旨 | 反映（PLAN 節） |
|---|---|---|
| 1 | flip 集計が正当なソース変更を数える | changeSetSha/contractVersion/backend 一致も条件に（§10 #39） |
| 2 | required を evidence から読むと回避可能 | config のみから導出、evidence は state のみ（§10 #42） |
| 3 | impacted 0 件で strict 判定が走らない | start-run の phase4Required に required を追加（§7/§10） |
| 4 | drift 非ブロッキングは対象漏れ | drift は Phase 0 で監査停止（§9 配線） |
| 5 | --check が source SHA しか見ない | 再生成集合と config の照合、4 経路の drift（§9 --check） |
| 6 | tracked 集合の等価検査は将来を証明しない | 構文限定変換（`*`→`**`、`/` 前の `*` 拒否ほか）を主根拠に、tracked 検査は二次（§9） |
| 7 | --write の安全境界・承認手順 | validate_repo_path・lock 拒否・init は承認後に書く。フラグは維持し承認ゲート必須（§9） |
| 8 | history の二重読み | impact.json に historySha、plan-dispatch が照合（§10 #39） |
| 9 | provenance 未封印 | manifest impactSha、codex-dispatch が照合（§10 #39） |
| 10 | 統合試験が判別不能 | 全 provenance で cap 満杯の実プロセス統合試験（§6） |
| 11 | required の full 免除は名前と矛盾 | full も REFUSED、baseline 後に有効化と明記（§10 #42） |
| 12 | REFUSED 到達経路 | history/anchor/last-run 非更新を実ファイルで固定（§6） |
| 13 | exec --help は同形状でない | 保証範囲を「CLI 存在＋exec 到達」に縮小し明記（§10 #42） |
| 14 | 修飾 verdict の内部混入 | 表示文字列を分離、stdout/last-run/anchor を同一試験で固定（§6/§10） |
| 15 | 新 config 値の型契約 | 各キー型検証＋表形式否定試験、required 不正は REFUSED（§6/§10） |
| 16 | docCorpus ≥ 10 が飽和を隠す | 下限撤廃、heuristicOnly>0 かつ比率で WARN（§10 #40） |
| 17 | regressionRecheck 既定 true は互換追加でない | 既定 false、init draft で opt-in 提案、history 不在は無音（§10 #39） |
| 18 | list 継続規則が未定義 | content indent 追跡規則＋対テスト（§10 #43） |
| 19 | 「唯一の横断層」は誤り | 文言縮小、固定 report 行は不採用（§10 #41） |
| 20 | impacts と docGlobs の非対称 | docGlobs 外の影響先は拒否（§9 検証） |
| 21 | exit 6 の説明が逆 | run 中 import 拒否、run 間は accept-config 不要と明記（§9） |
| 22 | handoff 試験の安全条件 | 既存試験を拡張、13 分岐で破壊操作 0 回を固定（§12） |
| 23 | 版・成果物の契約検査 | `tests/test_v013_contracts.py`（5 キー・7 消費側・argument-hint・履歴行許容リスト）（§6） |

worker 吸収細部（Sol 区分）: impact-supplement.py の優先順位説明と許可パス追加（反映済み）、#43 の link 試験の
assert 内容（§6 に反映済み）。

### R2（resume 同一セッション）— `critique-r2.md` → `critique-r2-answer.md`
21 件（BLOCKER 6・MAJOR 13・MINOR 2）。Sol 側でも dir-framework 24 規則の通過と tracked 46 件・1,104 組の差異 0 を
独立に確認。boss 検分の結果**全件採用**。PLAN rev.3 への反映:

| # | 要旨 | 反映 |
|---|---|---|
| 1 | config 不在で --check が走らない | パス安全と存在を分離、config 不在許容＋`--doc-globs`（§9） |
| 2 | drift 停止が --break-lock 復帰を閉じる | Phase 0 順序: break-lock → scope 検査 → open-run（§9 配線、契約テスト (c)） |
| 3 | 承認→書込の内容未封印 | `--expect-config-sha/--expect-scope-sha` 必須、lock を O_EXCL 取得（§9） |
| 4 | required×full が anchor 喪失後に永久ループ | required:true の full は codex review を実行（プロンプト変種）、実行不能時のみ REFUSED（§10 #42） |
| 5 | REFUSED で last-run 非更新は既存契約を壊す | 非更新は history・anchor のみ、last-run は理由つき更新（§6/§10） |
| 6 | impactSha は codex 経路のみ | manifest `provenance` map を封印し両経路＋check-verdicts で照合。impactSha 不採用（§10 #39） |
| 7 | 統合試験工程が実コードと不一致 | resolve→supplement→plan-dispatch→start-run→seal-run→evidence→gate（§6） |
| 8 | S1 engine 変更と S4 版更新で S1 が赤 | #43・版 bump・engine-shas・test_scaffold を同一 Stage（S1）に（§4） |
| 9 | required:false で壊れた evidence を黙認 | codexReview 存在時は required 無関係に厳格検証、不在のみ互換（§10 #42） |
| 10 | Phase 5 の 3 状態 vs 4 状態 | 4 状態契約に統一（§6/§10） |
| 11 | list 規則の過小マスク・tab 展開 | 段落は中断不可・空行後のみコード・tab は 4 列境界（§10 #43、対テスト 3 面） |
| 12 | saturationWarnRatio 型契約の自己矛盾 | bool 除く数値・0 で無効・丸め前比較（§10 #40） |
| 13 | handoff「全分岐 0 回」が処理順と矛盾 | 分岐別期待回数表（§12） |
| 14 | 複合故障で判別不能 | 1 ケース 1 故障、PR 番号欠落/非数値を追加（§12） |
| 15 | 契約テストが単純 grep | front matter 解析・コマンド行・順序・列挙箇所の意味単位検査（§6） |
| 16 | custom --scope が引き継がれない | Phase 0 は `auditScope.path` を唯一の入力に（§9） |
| 17 | note 接頭辞の所有判定 | 構造化 `source:"audit-scope"` フィールド（§9） |
| 18 | 改行を含む名前で等価が破れる | `glob_to_regex` を `re.DOTALL` 化＋改行パス試験（§2/§7/§6） |
| 19 | 版残存検査の誤検出 | `git ls-files` 限定＋ADOPTION:139/124 を許容リストへ（§12） |
| 20 | 0.12.0 engine fixture が無い | S1 先頭で `tests/data/engine-0.12.0.py` 保存＋hash 固定（§10 #43） |
| 21 | report 除外の否定試験 | `auditReportsInCorpus` false/true の対試験（§6 (iii)） |

### R3（resume 同一セッション）— `critique-r3.md` → `critique-r3-answer.md`
18 件（BLOCKER 5・MAJOR 12・MINOR 1）。boss 検分の結果**全件採用**（2 件は縮小採用: #5 は orchestrator が非スクリプトの
ため SKILL 文言契約に、#9 は DOTALL を撤回し CR/LF path を fail-closed 拒否に）。boss 補足発見: `glob_to_regex` は
`docaudit_paths.py` のほか `resolve-impact.py:45` と `generic-layers.py:29`・`impact-supplement.py:45` に複製（Sol も指摘）。
PLAN rev.4 への反映:

| # | 要旨 | 反映 |
|---|---|---|
| 1 | plan-dispatch 後〜start-run 前で impact が未束縛 | plan-dispatch が `impactSha` を dispatch/EVIDENCE に記録、start-run が照合（§10） |
| 2 | provenance 不一致が verdict に接続されない | decide-verdict に REFUSED 条件 (a)(b)(c)、check-verdicts は非 0 exit（§6/§10） |
| 3 | manifest.provenance の型契約 | keys==impacted・値 enum 7 値・違反 error/REFUSED（§6） |
| 4 | full 用プロンプト「HEAD tree」が封印対象と矛盾 | 「manifest.head＋worktreeDigest で封印された現在 worktree（未 commit 含む）」（§10 #42） |
| 5 | required/full の実行順試験がない | SKILL 文言契約（別行の分岐・順序）に縮小（§6 #42） |
| 6 | importer lock が --break-lock で消える | fd 排他 flock 保持＋inode 一致確認、break-lock 拒否を実プロセス試験（§9/§6） |
| 7 | lock path の symlink 保護 | run-base 包含・全 symlink 構成要素検証（§9） |
| 8 | 初回 init が SHA/lock を迂回 | 初回も draft を書いた直後に同一 `--write` 経路（§9 配線） |
| 9 | DOTALL が後続工程で貫通しない | DOTALL 撤回、importer と compute-baseline.sh で CR/LF path を fail-closed 拒否（§9/§10） |
| 10 | --doc-globs のカンマ分割 | 反復可能 `--doc-glob`（§9、対試験） |
| 11 | 契約試験が S5 で初出 | S1 で骨格、各 Stage が自担当 assert を追加（§4/§6） |
| 12 | 契約試験が値の導出元を見ない | (c)(d)(f) で bind 行と参照元まで検査（§6） |
| 13 | 統合試験 1 本で判別不能 | (A) regression 残存・(B) cap 落ちの 2 本（§6） |
| 14 | 版残存検査が tasks/ で失敗 | 出荷物 path 集合に限定（§6 (j)/§12） |
| 15 | Issue close 回数のみ | 集合 `{39..44}` 各 1 回（§12） |
| 16 | 途中失敗からの再開 | 再開表（3 境界）（§12） |
| 17 | 同期先 symlink を公開後に検査 | 同期先 preflight を tag 前へ、期待回数 0/0/0/0（§12） |
| 18 | 集合比較が重複 drift を見逃す | multiset 比較＋試験（§9/§6） |

### R4（resume 同一セッション）— `critique-r4.md` → `critique-r4-answer.md`
18 件（BLOCKER 7・MAJOR 10・MINOR 1）＋費用対効果で「落とせる 3 点」。boss 検分: **17 件採用、1 件は代替案で採用**
（#7: compute-baseline を全利用者向けに変えず、importer と Phase 0 `--check` が CR/LF 名を fail-closed 拒否 — §0「非導入
プロジェクト無影響」を維持するため。boss 実機確認: open-run は取得時に flock 保持・break は `LOCK_NB` で試みる（#6 の
窓は inode 再確認で閉じる）、`validate_evidence()` は追加キーを検証しない（#2 のとおり EVIDENCE には足さない））。
PLAN rev.5 への反映:

| # | 要旨 | 反映 |
|---|---|---|
| 1 | 封印後 manifest を消費側が未照合 | codex-dispatch が起動前に `EVIDENCE.manifest` と照合し子 0 回で停止、workflow 経路は seal 直後に読み直し（§6/§10） |
| 2 | impactSha が二重の正 | dispatch.json 内のみ、EVIDENCE のキー集合は不変（§10） |
| 3 | full+required 分岐が到達不能でも通る | 排他的 3 分岐の順序契約（full+required が skip より前、baseline 検査不要、共有処理）（§6/§10） |
| 4 | expect SHA 照合が lock 前 | lock 内で読み直して照合（§9 順序） |
| 5 | 初回 init が中間 config を公開 | `--base-config` で完成形を一度で原子作成（§9） |
| 6 | O_EXCL〜flock の窓 | flock 直後に fd/path inode 一致確認、不一致は無変更停止（§9） |
| 7 | CR/LF 拒否が非 NUL 出力で不能・全利用者影響 | 代替: importer/`--check` で拒否、compute-baseline は不変（§9 不採用欄） |
| 8 | check-verdicts 非 0 の終了未定義 | exit 0 の診断契約に戻し REFUSED は gate に集約（§6/§10） |
| 9 | auditScope metadata の型異常 | 型契約＋違反は error 停止（§9 検証、§6 (vi)） |
| 10 | source 互換試験が脱落 | (viii) として復活（§6） |
| 11 | 同期先 repo 外拒否が正規経路を拒否 | 承認済み skills root の期待パス一致に変更（§12） |
| 12 | handoff の版・Release 内容検査 | tag→SHA、Release tagName/title/body を全成功・再開ケースで固定（§12） |
| 13 | enum 否定試験が SHA 違反で通る | 全 SHA 整合の sealed fixture で provenance のみ不正（§6） |
| 14 | --doc-glob が last-wins でも通る | 2 glob にだけ属する影響先各 1 件（§6 (vi)） |
| 15 | 再開表が二回実行を判別しない | 失敗コマンド明示の二回実行表（§12） |
| 16 | docCorpus 0 の除算 | 0.0・warning なし・正常終了（§6/§10） |
| 17 | Phase 5 audit-scope 行は費用に見合わない | 削除（§9） |
| 18 | 書込失敗時の lock 解放 | finally で inode 照合つき解放＋置換失敗注入試験（§9/§6） |

### R5（resume 同一セッション、上限）— `critique-r5.md` → `critique-r5-answer.md`
16 件（BLOCKER 5・MAJOR 10・MINOR 1）。Sol 区分: (A) 計画欠陥 1〜11／(B) worker 吸収 12〜16。boss 検分: **全件採用**。
上限到達のため Sol ラウンドはここで終了し、手順 3.5（Opus 全体敵対レビュー）へ。PLAN rev.6 への反映:

| # | 要旨 | 反映 |
|---|---|---|
| 1 | Phase 0 の scope 整合が封印されない | start-run が scope 実 bytes の sha を metadata と照合し manifest `auditScopeSha` に封印、gate が状態確定直前に再照合（§6） |
| 2 | manifest SHA 照合が codex 経路のみ | 新規 `read-manifest.py`（一度だけ bytes 読取→sha 照合→同 bytes を解析）を Phase 3 workflow・Phase 4・codex-dispatch の共通読取に（§6/§10） |
| 3 | 3 分岐が利用可能性を含まず到達可能性を証明できない | 新規 `codex-review-plan.py`（enabled×available×mode×required×baseline の真理値表 32 行）に判定を分離（§6 #42） |
| 4 | CR/LF が tracked 限定 | scope の規則キー・影響先文字列＋tracked/untracked を NUL 列挙して拒否（§9 検査順序） |
| 5 | 非導入無影響の順序 | `scope absent && metadata absent` は git 列挙前に exit 0、shim で git 0 回を固定（§6 (ii)） |
| 6 | --base-config PATH の矛盾 | `--base-config -`＋`--expect-base-config-sha`、stdin を lock 内で一度だけ読む（§9） |
| 7 | fresh init で run-base 不在 | symlink 検査後 0o700 で作成、`.claude/state` 不在試験（§6 (v)） |
| 8 | `git push --tags` | 単一 refspec push＋無関係 tag 非送信の否定試験（§12） |
| 9 | 再開表の「3 件目失敗＝残り 3 件」矛盾 | (a) 副作用前失敗→残り 4、(b) 3 件後の読取失敗→残り 3 に分離（§12） |
| 10 | 同期先固定が override を破壊 | `DOCAUDIT_SKILLS_DIR` 維持＋`DOCAUDIT_SKILLS_ROOT` 配下照合（§12） |
| 11 | Release title 未定義 | 完全一致文字列を定義（§12） |
| 12 | Phase 0 契約が check 無視を検出しない | drift/errors → open-run 0 回、not-imported → 継続を意味単位で検査（§6 (c)） |
| 13 | codex-dispatch `--evidence` の呼出し配線 | Phase 3 コマンド行を契約テストで固定（§6 (f)） |
| 14 | 故障試験が config 最終状態を見ない | replace 前／後 dir fsync に分離（§6 (v)） |
| 15 | hash と解析の bytes 同一性 | read-manifest の仕様に明記（§6） |
| 16 | `rules` が bool を受理 | bool 明示拒否＋否定試験（§6 (vi)） |

Sol 5 往復の総計: 96 件（採用 95、代替案採用 1）。

## Opus 全体敵対レビュー（route 手順 3.5）

### Opus R1（change-reviewer, read-only, Opus）— 対象 PLAN rev.6 → 判定 **差し戻し**
BLOCKER 2・MAJOR 5・非ブロッキング 8。boss 検分: **全件採用**（うち 2 件は boss 再裁定 — 下記 B-2 と 非 1）。PLAN rev.7 への反映:

| # | 要旨 | 反映 |
|---|---|---|
| B-1 | §10 の「rev.N のとおり」は復元不能（PLAN は上書き運用・tasks/ は gitignore） | §10 を全文インライン化、「rev.N のとおり」参照を禁止（rev.7 冒頭） |
| B-2 | flip 集計の `changeSetSha` 全一致条件は Issue #39 の実測（remediation commit を挟む 2 run）で 0 を返し、cache 適格タプルと同一で観測不能 | **boss 再裁定**: `changeSetSha` を数え上げ条件から外し `contentSha`・`contractVersion`・`backend` で数える。同一 change set の件数を `…SameChangeSet` として併記。Issue #39 型を DoD ケース (ii) に（§0-4a、§6、§10） |
| M-1 | `probeCommands[]` が未定義 | probe JSON の出力キー（実行コマンド列の記録）として定義（§6 #42） |
| M-2 | codex review 設計 spec が 3 状態・非ブロッキングの SSoT で v0.13.0 と矛盾 | 許可パスに spec を追加、S4b で改訂節を追記（§5/§6/§7） |
| M-3 | `regression` の cap 優先順位が PLAN 本文に無い | §10 #39 に明記＋3 複写先＋統合試験 (B) の期待値固定（§6） |
| M-4 | 契約テスト (c) の `open-run.py` 行が 2 箇所（break-lock 早期 exit と lock 取得）で判別不能 | lock 取得側の行に束縛、配線文言を修正（§6 (c)、§9） |
| M-5 | Phase 2 の封印前 manifest 生 parse と Phase 3/4 の read-manifest 束縛が二重 | Phase 2 内のみ有効と明記、Phase 3/4 は再束縛、契約テスト (f)（§6） |
| 非 1 | handoff の全面再設計は Issue が要求していない | **boss 裁定**: v0.12.0 handoff の単段縮約＋追加試験 4 点に縮小、再開表・期待回数表は不採用（§0-4b、§12） |
| 非 2 | 真理値表 32 行のうち 8 行は probe が生成できない | 到達可能 16 行に縮小、`--available` の束縛元を契約テストで検査（§6 #42） |
| 非 3 | 版一致が 3 面 vs 5 面 | 5 面に統一（§6 (i)） |
| 非 4 | #40 suggestion 4（コスト主因）が無い | ADOPTION 段落を DoD に追加（§6/§10） |
| 非 5 | drift 停止の復旧手順が未規定 | 停止メッセージに diff と復旧コマンド（§6 (c)、§9） |
| 非 6 | `test_workflow_template.py:361-366` が意図的差分に無い | §11 に追加 |
| 非 7 | check-verdicts が read-manifest 経由でない | 診断専用の意図的除外と明記（§6） |
| 非 8 | S4 が 1 セッションに収まらない | S4a（封印連鎖）／S4b（#42）に分割（§0-4c、§4） |

Opus が「矛盾なし」と確認した組み合わせ: importer lock × open-run × break-lock／`auditScopeSha` 三重照合／required × full の到達
可能性／S2 末フルスイート／read-manifest × codex-dispatch × check-verdicts／provenance 消費側 7 面の anchor。

### Opus R2（同一エージェント resume）— 対象 PLAN rev.7 → 判定 **軽微差し戻し（文面 5 点で承認可）**
R1 の 15 点は全反映と確認。rev.7 のインライン化で生じた新規 5 点を boss が全件採用し PLAN（rev.7 改）へ適用:

| # | 要旨 | 反映 |
|---|---|---|
| N-1 [BLOCKER] | codex state 語彙が `not-active`／`not-available` に分裂し、既定設定の全 run が evidence enum 違反で REFUSED | enum を `not-active` に統一、判定表と gate が同一定数を参照（§10 #42、§6 #42） |
| N-2 | 真理値表「16 行」の算術が説明と不整合、probe reason の受け渡し手段なし | 4 軸 16 行（`enabled` は軸外）＋`--available-reason` 引数（§6 #42） |
| N-3 | Phase 2 生 parse「Phase 2 内のみ」で `phase3CodexTimeoutSeconds`（`:373`）・`digestExclude[]`（`:421`）が束縛元を失う | 封印後に使う全値を read-manifest から再束縛、`preflightRequired` は対象外（§6 封印連鎖） |
| N-4 | flip 第 2 カウントのキー名不一致 | `counts.verdictFlipsUnchangedContentSameChangeSet` に統一（§6） |
| N-5 | 契約テスト (h) が probe 出力キーを設定キー表に要求 | 設定キー表と `## Codex review` 節に分割（§6 (h)） |

### Opus R3（同一エージェント resume）— 対象 rev.7 改 → 判定 **条件付き合格 → 条件反映済み → 実装承認**
R2 の 5 点は全反映と確認。条件 2 句（契約テスト (e) に `--available-reason "$CODEX_REVIEW_REASON"` の束縛検査、(f) に `:373`
`--timeout-seconds` と `:421` `--exclude` の read-manifest 由来検査）を PLAN に追記し rev.8 として確定。Opus は「追加の検分依頼は
不要」と明言 → **route 手順 4（実装）へ進む**。

## 実装ラウンド（route 手順 4〜6）

### S1（#43＋版 bump＋契約テスト骨格）— Terra `medium`, workspace-write — `stage1-prompt.md`
- 初回起動（`stage1-report.md`）: 読み取り・テスト実行の許可を求めて停止（既知パターン、memory `codex-background-kill-collab-wait`）。
  → `stage1-approve.md` で包括承認を resume（`stage1-report2.md` / `stage1-session2.log`）。
- R1（`stage1-report2.md`）: 実装完了報告。boss 全行 diff レビューで**差し戻し 1**: (1) 共有ヘルパ `_strip_container_markers` の引用符
  正規表現 `[ \t]*`→`[ \t]?` は範囲外の挙動変更（`_mask_fenced :243` が使用）→ 復元指示、(2) 契約テスト (j) が S5 対象
  `test_release_handoff.py` の 0.12.0 参照で失敗 → S5 まで skipTest。worker 報告「1 failure」に対し boss 再実行は 2 failures
  （並行実行の混入の可能性、再現せず）。codex sandbox が `.git` に書けずブランチ・コミット未達 → boss が git 操作を担当。
- R2（`stage1-report3.md`）: 2 点修正、engine hash 再計算（`fbef5b46…`）。**boss 再実行: `Ran 396 tests … OK (skipped=9)`**
  （着手前 368）。diff 検分: #43 3 修正・対テスト 14 件＋link 1＋dead code 1・fixture hash 固定・版 5 面・0.12.0→0.13.0 更新
  テスト・契約テスト (i) 有効。**承認**。
- boss コミット（branch `feat/v0.13.0-issues-39-44`）: `3e2b404` fix(engine) #43、`dd6ba4a` chore(release) 0.13.0。
  `tests/data/engine-0.12.0.py` はローカル `.gitignore` の `data/` に該当するため `git add -f`。

### S2（#40／#39 resolve-impact・plan-dispatch・impact-supplement・消費側）— Terra `medium` — `stage2-prompt.md`
- R1（`stage2-report.md`）: 実装完了報告（テスト一部未追加を自己申告）。boss 再実行 `Ran 398 tests … OK (skipped=6)`（worker
  報告と一致）。boss 全行 diff レビューで**差し戻し 1**（`stage2-feedback1.md`）: (A-1) `saturationWarnRatio:false` が bool 検査前の
  `== 0` で「無効化」扱い、(A-2) history 破損時に `historySha` が null になり plan-dispatch が `corrupt` 経路でなく exit 3 に落ちる、
  (A-3) heuristic∧regression の provenance が `regression`（PLAN は既存優先）、(B) 型検証表・9/9 飽和・丸め境界・cap 順序・
  plan-dispatch 専用ケース・`source` 互換の各テスト未追加。
- R2（`stage2-report2.md`）: A-1〜A-3 修正（revert で赤になることを worker が確認）、`tests/test_plan_dispatch.py` 新設（5 件）、
  test_resolve_impact 30 件、docs/init SKILL 追記。boss 検分: `history_sha` は raw bytes 読取直後に計算（`:249`）、provenance は
  mapped→heuristic→regression の順（`:292-295`）、bool 先行判定（`:176`）。**boss 再実行 `Ran 414 tests … OK (skipped=6)`。承認**。
- boss コミット: `c6efd28` feat(impact) #40/#39、`5f4ab37` docs(impact) 消費側・契約 (b)(g)(h)。

### S3（#44 `import-audit-scope.py`＋配線）— Terra `medium` → 差し戻しは `high` — `stage3-prompt.md`
- R1（`stage3-report.md`）: 本体 287 行＋配線は完了、テストは 3 件のみ・フルスイート未完走で途中終了。boss 再実行
  `Ran 417 tests … OK (skipped=3)`。boss 全行レビューで**差し戻し 1**（`stage3-feedback1.md`）: (A-1) `acquire()` の except で
  inode 不一致でも lock を unlink（他者 lock 破壊）、(A-2) config 不在で `--base-config` なしでも空 config から作成、(A-3)
  `report_pattern` の 6 複製目が契約テスト外、(A-4) `datetime.UTC`、(A-5) 1 行多文の可読性と error 重複、(B) 故障注入フック
  `DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT` の定義（hold-lock／before-replace／after-replace／unlink-before-flock）、(C) (i)〜(viii) の
  網羅完遂。effort を `high` に上げて resume（推論の浅さ＝途中終了への対処）。
- R2（`stage3-report2.md`、Terra `high`）: 5 欠陥修正・故障注入 4 種・(i)〜(viii) 27 テスト・実物検査テスト・revert 確認（A-1/A-2/
  hold-lock）。boss 検分: `acquire()` は LockBusy 例外＋`remove_owned_lock`（inode 一致時のみ unlink）、write は lock 内で config/scope
  再読・expect 照合・`before-replace`/`after-replace` フック・dir fsync、main は absent を git 列挙前に早期 return。
  **boss 再実行 `Ran 441 tests … OK (skipped=3)`**（414 → 441）。**boss 実物検査**（dir-framework HEAD の archive を一時 dir に展開・
  `git init`・config 不在・`--doc-glob '**/*.md'`）: `state=not-imported`・`rules=24`・`equivalenceChecked=46`・`errors=[]`・
  `skippedNoImpact=['bak/**']`・translated 23。**承認**。
- boss コミット: `5ebe03d` feat(audit-scope) #44、`dd81010` docs(audit-scope) 配線・契約 (a)(c)(d)(h)。

### S4a（封印連鎖: read-manifest／provenance／auditScopeSha／flip 集計）— Sol `high` — `stage4a-prompt.md`
- R1（`stage4a-report.md`）: 一発完了。新規 `read-manifest.py`（47 行）＋`test_read_manifest.py`、start-run（impactSha 照合・provenance
  enum 7 値・auditScopeSha）、gate（REFUSED 条件 4 種・flip 2 集計・warning）、codex-dispatch（`--evidence` 必須・manifest 由来
  provenance のみ）、check-verdicts（診断・exit 0）、SKILL（seal → read-manifest → `SEALED_*` 再束縛。backend 選択を封印後に
  するため mdq refresh を seal の後へ移動 — `.mdq` は `BUILTIN_EXCLUDES` のため digest に影響なしと boss 確認）。統合試験 (A)(B)・
  否定試験 4 種・flip 3 ケースを実プロセスで固定、revert 確認 3 件。boss 全行 diff レビューで指摘なし。
  **boss 再実行 `Ran 465 tests … OK (skipped=2)`**（441 → 465）。**承認**。
- boss コミット: `85e415c` feat(gate) 封印連鎖・flip、`f07aea2` docs(skill) 再束縛・契約 (f)。

### S4b（#42: codex-review-plan／gate required／probe／SKILL Phase 4-5／設計 spec）— Sol `high` — `stage4b-prompt.md`
- R1（`stage4b-report.md`）: 新規 `codex-review-plan.py`（4 軸 16 行、共有定数 `CODEX_REVIEW_STATES` を `docaudit_cache.py` に）、
  gate（config 由来 required・evidence 厳格検証・REFUSED 4 種・degrade warning・表示分離 `report_verdict`・stdout `codexReview`）、
  start-run `phase4Required`、probe `exec --help`＋`probeCommands[]`、SKILL Phase 0/4/5（判定表経由の排他分岐・full 変種・#41 の
  3 観点・4 状態行）、config-schema、設計 spec 改訂節。revert 確認 3 件。**boss 再実行 `Ran 476 tests … OK (skipped=1)`**
  （465 → 476）。boss 全行 diff レビューで**軽微差し戻し 1**（`stage4b-feedback1.md`）: start-run の `codexReview` 非 object で
  `.get` 例外落ち → gate と同じく `{}` に畳む＋テスト。
- 設計 spec `docs/superpowers/specs/2026-07-31-codex-review-docaudit-integration-design.md` は**ローカル .gitignore（`docs/superpowers/`）
  で追跡外**（`git ls-files docs/superpowers` 空）。改訂追記はローカルに反映済みだがコミット対象外 — PLAN §7 の「durable 規約変更は
  spec 1 本」はローカル SSoT の更新として充足（配布物・PR には含まれない）。
- R2（`stage4b-report2.md`）: start-run の非 object 畳み込み＋回帰 4 組。**boss 再実行 `Ran 477 tests … OK (skipped=1)`。承認**。
- boss コミット: `2fce025` feat(codex-review) #42、`cbc3165` docs(skill) Phase 4/5・schema・契約 (e)(h)。

### S5（#41 docs／docs 最終整合／handoff 単段縮約＋試験／契約 (j) 有効化／pr-body）— Terra `medium` — `stage5-prompt.md`
- R1（`stage5-report.md`）: docs（盲点節・互換性影響節）、`release-handoff.sh`（223 行、単段・単一 refspec・title 完全一致・Issue 6 件・
  同期先 root 照合）、`test_release_handoff.py`（10 件 435 行 → 6 件 61 行、偽 git/gh/rsync/python3 の状態機械）、契約 (j) 有効化、
  pr-body。worker はフルスイート完走を取得できず。boss 再実行 `Ran 473 tests … FAILED (errors=1)`（worker の並行編集中の実行
  のため要再確認）。boss レビューで**差し戻し 1**（`stage5-feedback1.md`）: (A) 試験ファイルが `;` 詰めの 1 行多文（160 文字超 8 行）
  で保守不能 → 通常様式に展開、(B) 分岐不足 10 件（root 外・非 main・dirty・HEAD/origin 不一致・suite 失敗・PR 引数・再開 2 種・
  同期確認 n）、(C) pr-body の実数、(D) フルスイート完走の報告。
- R2（`stage5-report2.md`）: 試験を通常様式に展開（462 行・160 文字超 0）、18 テスト（PLAN §12 の 13 分岐＋再開 2 種＋同期 n＋
  冪等＋単一 refspec）、pr-body 実数（368 → 485、skip 0）。boss 検分: 再開テストは偽 python3 の `suite_runs==1`・tag 0・Release 1・
  close 6 を assert、ADOPTION 盲点節は「唯一」を使わず。**boss 再実行 `Ran 485 tests … OK`（skip 0）。承認**。
- boss コミット: `5f1a0dc` docs(adoption) #41・互換性影響・handoff 試験・契約 (j)。

## 最終レビュー（route 手順 5 — `codex exec review --base main`, Sol `high`）
`final-review-answer.md`（対象: main..5f1a0dc の差分）— 指摘 2 件。
- **P1** `tests/test_release_handoff.py:18-19` が参照する `tasks/…/release-handoff.sh` は tasks/ の除外設定で未追跡 → クリーン
  checkout で exit 127。boss 判定: **route-close の記録コミット（`git add -f tasks/route/2026-08-27-…/`）で解消**（前版 v0.12.0 も同方式。
  PLAN §7「記録。コミットは `git add -f`」）。route-close 後に `git ls-files` で追跡を確認して記録する。
- **P2** `resolve-impact.py:254-256` regression 候補が history の `contentSha` と現在内容を比較しておらず、修正済み文書も regression
  tier の枠を消費する（PLAN §10 #39・ADOPTION の「内容不変」契約違反）。boss 判定: **実欠陥、差し戻し**（`final-review-fixes.md` →
  S2 セッション `01a04253…` へ resume、medium）。
- P2 修正（`final-fixes-report.md`）: `content_sha(repo, path) == entry["contentSha"]` を条件に追加、テスト (a)(b)(c)（cap 境界で
  heuristic 2 件保持）、wp12 統合試験の history を実ハッシュに、ADOPTION 追記。revert で (b)(c) が赤になることを worker が確認。
  **boss 再実行 `Ran 487 tests … OK`（skip 0）。承認**。boss コミット `b0987fd`。
- 最終判定: **承認**（差し戻し 1 → 修正済み。P1 は route-close 記録コミットで解消）。

## route-close（route 手順 7、2026-08-27）

- **対象タスク**: Issues #39〜#44 → docaudit v0.13.0（PLAN rev.8）。
- **記録時点の HEAD**: `b0987fd11e863baea6432f60eef1b44c9169609b`（branch `feat/v0.13.0-issues-39-44`、main からの commit 12 件。
  この後に本 REVIEW/PLAN/prompts/`release-handoff.sh`/`pr-body.md` を `git add -f tasks/route/2026-08-27-issues-39-44-v0.13.0/` で
  記録コミットする — その commit が close marker を兼ねる）。
- **確定した変更ファイル**（`git diff --name-status main..HEAD`、45 ファイル、+4486/−513）: 新規 8（`codex-review-plan.py`、
  `import-audit-scope.py`、`read-manifest.py`、`tests/data/engine-0.12.0.py`、`test_codex_review_plan.py`、`test_import_audit_scope.py`、
  `test_plan_dispatch.py`、`test_read_manifest.py`、`test_v013_contracts.py`）、変更 37（`plugin.json`、agents 2、docs 4、SKILL 2、
  references 4、scripts 10、tests 14）。ローカル限定（追跡外・PR 非含有）: `docs/superpowers/specs/2026-07-31-codex-review-docaudit-
  integration-design.md` の改訂追記。
- **audit verdict**: **N/A — 本リポジトリは docaudit 未導入**（`.claude/doc-audit.json` なし）。代替として、変更した公開挙動・設定・
  手順と既存文書の整合を S5（ADOPTION en/ja・PROMPTS・config-schema・default-heuristics の更新）＋`tests/test_v013_contracts.py`
  （(a)〜(j) 全 10 項目有効・skip 0）で確認。
- **SSoT 更新の有無**: AGENTS.md / PROJECT.md は本リポジトリに存在せず **0 ファイル更新**。durable 規約変更は設計 spec 1 本
  （ローカル追跡外）のみ。
- **検査系成果物の実数**: importer 実物検査 = dir-framework 24 規則・tracked 46 件・拒否 0・`skippedNoImpact=['bak/**']`・translated 23／
  glob 等価検査 = 24 規則 × 46 パス／真理値表 = 16 行／contract tests = 10 項目／unittest = **368 → 487（skip 0）**。
- **未実施（ユーザー実行）**: PR 作成（`pr-body.md`）、マージ、`release-handoff.sh <merge-sha> <pr>`（tag `docaudit--v0.13.0`・Release・
  Issue #39〜#44 close・skills-dir 同期）。
- **要ユーザー追認の boss 裁定**: (1) #39 多数決（`phase3Votes`）は据え置き・別 Issue 起票案、(2) flip 集計から `changeSetSha` を
  条件除外、(3) handoff 試験の縮約、(4) dir-framework 側（シード自身への docaudit 導入・phase-template 条件分岐）は本タスク外。
