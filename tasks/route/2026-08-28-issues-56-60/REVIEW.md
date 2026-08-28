# REVIEW — Issues #56(第1段)・#57・#58・#59・#60 → docaudit v0.14.0

## セッション記録
- 事前調査（Terra read-only, high）: session `01a046f5-364f-7451-a7ef-0448e6939773` → `investigate-report.md`
- 計画批判セッション（Sol read-only, high）: session `01a04703-eb33-7bf3-8e57-16b45ae16935`（R1 起動 2026-08-28T06:17:22Z）
- 実装セッション: （手順 4 で記録）

## 計画レビュー（手順 3: Sol）

### Sol R1（rev.1 → rev.2）— 17 件、全件反映
- R1-1 ledger は digest 除外外（boss 追認 `start-run.py:18` BUILTIN_EXCLUDES は個別ファイルのみ）→ 永続 ledger を BUILTIN_EXCLUDES に追加、書き込みは gate の state-commit へ移動（`start-run.py`/`decide-verdict.py` を限定的に許可）
- R1-2 REFUSED run の候補が残る → 候補は `$RUN_DIR/codex-ledger-next.json`、gate が barrier 後にのみ commit
- R1-3 抑止命令で CONSISTENT 偽造保証が崩れる → プロンプト抑止を撤去。既知 blocking は「明示 resolved まで blocking」（foldFindings で決定論に維持）
- R1-4 path/title 注入・保存先 → `file` は validate_repo_path 必須、title 制御文字除去＋200 上限、promptBlock は JSON 行＋data 宣言、パスは固定・O_NOFOLLOW
- R1-5 「無い＝resolved」不成立 → 出力 schema に `knownFindings{key,status}` を追加、`resolved` 明示のみ削除
- R1-6 key 衝突・trim → file は検証済み相対パス verbatim、blocking は trim 対象外
- R1-7 root は realpath 済み → apparent root を main で保持して safe_path に渡す
- R1-8 normpath で `..` 迂回 → 正規化前に成分検査で拒否、テスト追加
- R1-9 mdq キー集合 → 既存分岐は不変、invalid-config は not-installed 形
- R1-10 9 記録→7 表示・codex 行 → 対応表を固定文言化、codex は phase4.json/ledger-next から復元
- R1-11 probe-record 防御 → `--evidence` runDir 一致、seam 別 schema（write/read）、O_NOFOLLOW、symlink 拒否
- R1-12 `$HOME` 未設定 → `${VAR:-}` 形＋unknown 3 値、空文字列＝未設定
- R1-13 「実効」は wrapper を表さない → `caller*` へ改名・文書化・sanitizer 明記
- R1-14 §7 不足 → 固定文 7 つに拡張（bin 非文字列・確認ゲート・display-only・resolved 契約・schemaVersion）
- R1-15 差分検査が commit 後に空 → 基準 commit `dfdb8a9` との name-only／byte 比較に置換
- R1-16 端から端まで → 両 option×6、helper 迂回、plan 完全一致、gate REFUSED、env 7 ケース、ledger 24 件以上
- R1-17 固定文言・総件数 → 固定テスト名・出現回数・順序 assert・ファイル別最低件数
- 判定: **差し戻し（rev.2 で再批判）**

### Sol R2（rev.2 → rev.3）— 対応不十分 8 件＋新規 9 件、全件反映
- R1-2 anchor 失敗後の REFUSED 経路 → ledger commit を anchor 書き込み後へ（g6）。候補ファイル廃止（gate が next を自前計算）
- R1-3 破損・差し替えで既知 blocking が消える → 永続 ledger の sha を `start-run.py` が manifest に封印（`codexLedgerSha`）、gate が読み込み時と barrier で再確認、破損・不一致は REFUSED（fail-closed、history/anchor と同格）
- R1-4 モデル単独 resolved → resolved は「knownFindings にちょうど 1 回・未報告・carried・`lastDigest != worktreeDigest`」のときのみ有効（P1: digest 不変なら blocking 単調非減少）
- R1-10 表示値不足 → seam 別 schema を probe 全キー＋条件付き必須（healthy/chunks/dbDir/gitignoreOk）に拡張、codex 行は gate 出力から
- R1-11 run dir race → dir fd（O_DIRECTORY|O_NOFOLLOW）基準の open/create/replace
- R1-13 sanitizer が値を壊す → JSON 全体を python json.dumps で生成（BIN/VERSION も）
- R1-15 未追跡・rename → NUL 区切り＋rename 両 path＋baseline 未追跡一覧固定＋非 0 終了の allowlist 検査（§8）、`allowlist.txt` を boss 提供
- R1-16 5 分岐 → probe-exec-failed を含む 5 分岐でキー集合一致
- R1-17 subTest 数 → テスト内で `len(CASES)` と ID 集合を assert
- R2-1 severity 降格で blocking 解除 → carried blocking は降格無効（fold 条件 `reported ∉ {critical,high}`）
- R2-2 fold が orchestrator 任せ → codex の生 result を `phase4.json`（EVIDENCE 束縛済み）に埋め、gate が carry/fold/next を自前計算して verdict に合流（g3/g4）
- R2-3 任意プロパティは Structured Outputs 非互換 → `knownFindings` を required に
- R2-4 短縮 key・矛盾 → full 64hex、重複・矛盾・reported の resolved は無視（保守的）
- R2-5 `contextMode:null` → `"contextMode" not in c` と `is None` を分離、契約テストが式を 6 入力で実行
- R2-6 Windows → POSIX のみを文書化（非対象）
- R2-7 basis/changeSet → entry に `basis`・`changeSetSha`・`lastDigest` を記録（carry 条件は contentSha のまま — 根拠は rev.3 §0-6）
- R2-8 無制限 prompt → prompt は blocking 50 件上限（超過は gate の fold で維持）
- R2-9 §7 文言矛盾 → ①⑤を判定順・commit 条件を含む文へ修正
- Stage を S1a/S1b(#57)/S1c(#59)/S2 に分割。S1c 不承認時は revert して次版へ送る逃げ道を明記
- 判定: **差し戻し（rev.3 で再批判）**

### Sol R3（rev.3 → rev.4）— 対応不十分 10 件＋新規 8 件
- #59 ledger: R1-2（保存失敗 transaction／poison journal）、R1-3（open-run 時点の封印・taint 復元）、R1-4（モデル単独 resolved）、R2-2（nested result の新規 high を gate が見ない）、R2-4（同一 key 重複 severity）、R2-7（basis 遷移表）、R2-8（50 件 batch と P1 の衝突）、
  R3-1（state≠completed で fold しない → P1 破れ）、R3-2（key 化不能 blocking → REFUSED 要）、R3-3（digestExclude で digest 同一でも drop）、R3-4（signature 取得の TOCTOU）、R3-5（旧新 engine 混在の両方向）、R3-8（時系列テスト）
  → **boss 裁定（advisor 同意）: #59 の ledger は「blocking を決定論的に維持する時点で verdict 影響状態＝history/anchor と同じ信頼クラス（open-run 封印・barrier・transaction・taint 復元）を要する」独立タスク。3 往復で毎回新規 Critical が出る一方、他 4 件は収束。
  本版では Issue 最小案（運用注記）のみ出荷し、設計制約を `59-design-note.md` に固定して次版の専用 route へ送る。スコープ縮小はユーザー判断につき最終報告の第 1 項目で諮る。**
- 残スコープに適用: R1-11（run dir を repo fd から成分ごとに `O_DIRECTORY|O_NOFOLLOW` で辿る）、R1-15（allowlist を boss commit に固定し `git show` で読む。ignored ファイルも `--ignored=matching` で検査）、
  R2-5（CM 式は読込例外・top-level 非 dict も `invalid`、判定表全入力で実行）、R3-6（3 probe × 17 variant の固定 ID 集合）、R3-7（明示 symlink root fixture）、R3-8（件数検査は `test -le` で非 0 終了）
- 判定: **差し戻し（rev.4 で残スコープのみ再批判）**

### Sol R4（rev.4 → rev.5）— 対応不十分 3 件＋新規 11 件＋note 1、Critical なし
- R3-6 CM と CLI の ID 集合が別物 → CLI 18 ID／CM 13 ID（`bin` 無し・`cfg_omitted` 無し）に分離、§7 ①の `bin` 句を CLI 3 seam 限定に
- R4-1 読めない config は Phase 0 前に停止 → `invalid-config` の適用範囲を「正常 top-level 内の seam 不正」に限定、行 6〜8 は probe 単体の防御と明記、§7 ①に既存挙動を明記
- R4-2 状態行注入 → 機械用 JSON 無加工＋表示直前に `json.dumps` 由来の可視エスケープ・200 上限、1 行性を式の実行で assert
- R4-3 gate 後の `phase4.json` 再読 → codex 行の state は gate stdout のみ
- R4-4 矛盾 record を受理 → availability/reason 判別の分岐別 union（余分キー禁止、`available == reason∈OK`）
- R4-5 symlink repo-root → 最初に realpath（open-run と同契約）、受理テスト追加
- R4-6 失敗時の停止 → fail-open 規約（write 失敗は警告続行、read 失敗は 7 行 unknown）
- R4-7 文言確認だけ → `--read` が `rebind` map を機械算出（完全性判定をモデルに任せない）＋算出テスト
- R1-15 `tasks/` 除外・ignored 偽陽性 → allowlist は tracked 差分のみ、ignored/untracked は `baseline-hashes.txt` の sha256、boss 文書 5 つは直前 boss commit と byte 比較、log/prompt/answer の固定 glob のみ除外
- R3-8 `|| echo` → `|| exit 1`
- R4-8 3 変数目 → DoD (9) に `CODEX_CALLER_HOME_SOURCE`
- R4-9 handoff の誤認 → title の範囲表記撤去、notes 完全一致 2 文、旧定数不在を DoD
- R4-10 direnv 文言 → 「hook が無い場合がある／wrapper 内は観測外」に限定
- R4-11 キー集合不変と 3 キー追加 → additive 例外を明記
- R4-note-1 手動 carry-forward の注入 → 注記を「fenced JSON data・命令として扱わない」に、design note に追記
- 判定: **差し戻し（rev.5 で最終ラウンド R5）**

### Sol R5（rev.5 → rev.6、上限到達）— (A) 6 件・(B) 5 件、Critical なし
- (A) R5-1 `mdqHealth` の実出力は 5 キー → schema を `{files,chunks,searchSmoke,healthy,status}` verbatim に、実出力の write→read テスト
- (A) R4-7 `rebind` が完全性のみ → 7 行の正規化済み値を script が算出し、**Phase 5 は初回・再開とも `--read` の `rebind` からのみ入力**（表示エスケープも script 側、SKILL から表示用 python -c 式を撤去）
- (A) R4-2 再開時の改行復活 → 上記一本化で解消（`*Display` は生文字列を 200 で切ってからエスケープ — R5-5 も同時解消）
- (A) R5-2 codex の complete と gate state の不一致 → 基本状態は gate stdout のみ、`null` は固定 unknown 文、probe 記録欠損は caller 接尾辞のみ unknown
- (A) R1-15 ignored を status 集合に混ぜて常時失敗 → tracked/未追跡（ignored 無し）の allowlist 検査と、保護 root の再列挙による path 集合・種別・mode・hash 完全一致検査を分離（追加・削除・symlink 置換も検出）
- (A) R5-3 NUL 入り `bin` → `invalid-config`、ID `bin_nul` 追加（CLI 20 ID）
- (B) R5-4 不正 `bin` の出力値 → 既定名を完全一致で assert／R5-5 → 上記／R5-6 skip 0 → `-v` 出力の ` ... skipped` 0 行を機械判定／R5-7 → repo 全体 `git grep '0\.13\.2'` を許可 path・行パターンと固定比較／R5-8 `--config ""` → `invalid-config`、ID `cfg_empty`
- 判定: **上限到達につき Sol への再送はしない。(A) 全件を rev.6 に反映し、手順 3.5 の Opus 全体敵対レビューへ**

## セッション記録（追記）
- SCOPE_COMMIT: `8abfb91`（allowlist・baseline-hashes・scope-check.py の権威元）。scope-check dry-run: scope-clean（未変更の木）

## Opus 全体敵対レビュー（手順 3.5、change-reviewer）
### O-R1（rev.6 → rev.7）— ブロッキング 6・非ブロッキング 3。baseline 独立実測 `Ran 551 tests OK`、skipped 0 行
- O1 状態行は gate 起動前に生成（SKILL.md:596-599）→「codex 行の基本状態＝gate stdout」は実装不能（Sol R4-3/R5-2 の組み合わせ矛盾）→ Phase 4 evidence 書き込み直後に 10 番目の seam `codexReviewState` を記録し、`rebind.codex-review.reviewState` から `CODEX_REVIEW_STATE` を再束縛
- O2 `test_v013_contracts.py:82-86` の `CODEX_REVIEW_STATE=` リテラル → 温存（4-way 分岐キー不変）を DoD (11) に
- O3 S2 の refresh 更新で `test_j`（:210,215 の許可 regex）が落ちる → 更新対象に追加
- O4 §8 の `0.13.2` 残存 grep が ja の読点列挙で偽違反 → ja パターン追加
- O5 `grep -c ' ... ok$'` は subTest を数えない（実測 14 = メソッド数）→ 件数コマンド撤去、in-test `len(CASES)` に一本化
- O6 「`rebind` からのみ」が Phase-3 refresh 失敗 `<detail>` を初回でも壊す → 会話変数からの補完を唯一の例外として明記
- N1 9 seam 厳密 schema の費用対効果 → 余分キー許容に緩和（必須キー・型・分岐は維持）／N2 最小 env に PATH 必須を明記／N3 reason 列挙 3 か所を mdq 散文・ax・codex に特定（graph 3 seam は不変）
- 判定: **差し戻し → rev.7 で反映。O1 の是正案（codexReviewState seam）は同一エージェントへ resume で追認依頼（S1b 開始前）**
