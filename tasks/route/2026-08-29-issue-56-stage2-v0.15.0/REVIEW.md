# REVIEW — Issue #56 第2段（webExtract / codexReview key-gate 化）→ docaudit v0.15.0

## セッション記録
- 事前調査（Luna read-only, medium）: session `01a04cd8-a364-7cf3-a781-392b98c6cf31` → `investigate-report.md`
- 計画批判セッション（Sol read-only, high）: session `01a04cdf-e883-7ce0-a2fc-256beffbaf85`（R1 起動 2026-08-29）
- 実装セッション（Terra workspace-write, medium）: session `01a04d2a-9baa-79f1-bb2d-41f7fded38d9`
  （起動 2026-08-29、branch `fix/v0.15.0-issue-56-stage2`、prompt: `impl-prompt.md`）

## ユーザー裁定（2026-08-29、AskUserQuestion 実測）
- スコープ: #56 第2段のみ。#59 は据え置き（専用 route、Issue+設計ノートで追跡済み）。
- 裁定: **codexReview + webExtract を key-gated 化**（キー不在＝not-configured・tool 不起動）。
  indexing(mdq)/contextMode は既定有効を維持（トークン節約装置は既定有効、optional 統合は key-gated という原則）。
- 版: minor **v0.15.0**（verdict に影響し得る挙動変更＝codexReview の暗黙実行停止を含むため）。
- 運用要件（ユーザー指示・最重要）: docaudit 消費トークン抑制（機械的検査ゲート最大活用）、
  先回り修正（承認後）、1 回で CONSISTENT、据え置き課題は Issue 化（ユーザー承認）。

## 事前確認（boss 実測）
- #56 第1段（4 seam の boolean 必須化・invalid-config）は v0.14.0 出荷済み。
- #56 コメントの 2 指摘（SKILL.md enum の not-configured 欠落・graphify probe 判定順フラップ）は
  HEAD で解消済み（enum: SKILL.md:204/225/245・状態行 :775/:784、graphify-probe.sh はキー判定→update の順）。
- 「absent key remains enabled by default (intentional asymmetry)」の文書化は v0.14.0 出荷済み
  （config-schema.md:33-36、init SKILL.md の conditional-force 文言）→ 本タスクで webExtract/codexReview の
  2 行は key-gated 文言へ書き換え、indexing/contextMode の 2 行は維持。
- codex 認証: CODEX_HOME=~/.codex-doc-audit-harness に auth.json あり（AUTH_OK）。

## ベースライン（boss 実測、HEAD 4c9df5b）
- フルスイート: **Ran 609 tests OK, skip 0, 193s**（`python3 -m unittest discover -s tests`）

## 計画批判ラウンド（手順 3）
- R1（Sol high, read-only）: High 5・Medium 7 → **全 12 件受理**、PLAN rev.2 へ反映（`critique-r1-answer.md`）。
  boss 検分メモ: R1-2 は graphify-probe.sh の「a missing or invalid config never falls back to enabled」
  コメントと ax-probe.sh の CONFIG_SET=0 フォールバックを boss が実測して確定。R1-1 は
  codex-review-plan.py への config key hard gate ＋ SKILL resume 正規化文の 2 段で吸収。
  R1-10 は not-configured 分岐のみ caller 探索を短絡（disabled/invalid の既存分岐は外科的変更の原則で不変）。
- R2（resume・据え置き effort）: 新規 High 3・Medium 7 → **9 件受理＋1 件修正受理**、PLAN rev.3 へ反映
  （`critique-r2-answer.md`）。修正受理は R2-2（Phase-4 完了済み旧 run の再ゲート）: decide-verdict の
  変更はせず、ADOPTION 固定文③で再ゲート範囲を「codex review 実行前の resume」に限定・版跨ぎ resume
  非推奨を明記し、機械的禁止は #59 の設計制約（manifest への engine version）へ据え置き（59-design-note の
  反例 11 と同一機構のため独立実装しない — boss 裁定）。boss 実測: README.md:25 の ax/codex 記述が
  残骸に該当することを確認し README.md を変更範囲へ追加（R2-7 派生）。R2-1 は codex-review-plan への
  `--evidence` 封印整合検査として受理（decide-verdict は不変のまま）。
- R3（resume・据え置き effort）: 裁定 R2-2 への異議なし（#59 単一機構への集約を妥当と追認）。新規
  High 5・Medium 7・Low 1 → **11 件受理＋2 件修正受理**、PLAN rev.4 へ反映（`critique-r3-answer.md`）。
  修正受理: R3-2（ax の resume 正規化）は SKILL 一文では実装手段が無いという指摘を認め、「resume 時は
  rebind を信頼せず ax-probe.sh を再実行」へ変更（判定を probe 単一経路へ集約）。live config 一時改変で
  advisory の ax を起動させ得る残余リスクは boss 裁定で許容（ax は verdict 非影響・攻撃者は ax を直接
  実行可能なため封印照合の追加は不釣り合い）。R3-9（handoff 安全停止）は既存 v0.14 テスト不変のまま
  同等ケース群を新ファイルへ複製する形で受理。R3-1 は config-changed を終端エラー化（not-active 吸収を
  廃止）、R3-3 は planner が model/timeoutMs を検証済み出力として返し SKILL の生 config 再読を廃止。
- R4（resume・据え置き effort）: 新規 High 8・Medium 5。Sol は裁定 R3-2 に**正当な異議**（ax は
  workflow-template.js:122,153,156 経由で verifier prompt → verdict に影響し得る — boss の「advisory＝
  verdict 非影響」前提の誤りを実測で指摘）。→ **boss rescope 裁定（PLAN rev.5 §0）**: R2-1 以降積み増した
  EVIDENCE SHA 照合層を今版から全て撤回。理由: 防御対象の TOCTOU は v0.13.2 graph 系 key-gate を含む
  全 seam の既存露出であり、部分照合層は R3-1/R4-3/R4-4 のとおり新たな迂回路を生む。今版の key-gate は
  「key-gated probe 単一経路（fresh=Phase-0、resume=probe 再実行＋再記録）」の決定論で完結させ、
  TOCTOU 全体は**新 Issue（PLAN §9、ユーザー承認待ち）**へ切り出し。R4 個別の帰結:
  1（rebind 表示専用化で resume 不能）・10（旧 record の表示汚染）→ resume 再 probe＋再記録で解消／
  2・3・4・5・9・12 → SHA 層撤回により消滅、TOCTOU 証拠として新 Issue へ転記／
  6（test_v014 :222/:227 rebind 文言）・7（16 行表の削除禁止）・8（handoff 境界ケース全複製）・
  11（未知フィールド拒否）・13（Release notes directive 集合）→ 受理、rev.5 に反映。
- R5（resume・据え置き effort、上限ラウンド。初回投入は環境要因で killed → 同一セッション resume 再投入
  で回収）: **rescope と §9 切り出しを妥当と認定**。「fresh・単体呼び出し・正常 resume のキー無し
  不起動経路は閉じている」。残る計画欠陥 6 件＋worker 細部 1 件:
  1（probe-record は既に汎用 upsert — rev.5 の「他 seam 拒否」指定は回帰）→ 受理: upsert 不変・テストのみ／
  2（再 probe 失敗時の運用値）→ 修正受理: 「停止」ではなく fresh Phase-0 と同一の degrade（available=false
  で続行。false 方向は tool 不起動で keyless 保証を破らず、required は既存 fail-closed が拾う）／
  3（completed が not-configured 表示に隠れる）→ 受理: 💡 行を reviewState null/not-active に限定／
  4（再記録失敗で旧値正常表示）→ 受理: state unknown 強制／5（handoff 複製が :410 で切れる）→ 受理:
  :289-446 全 method・≥17 ケース／6（新 Issue 未起票でも出荷可能）→ 受理: 起票・OPEN・notes 参照を
  handoff 前提条件化／7（配線順）→ worker 細部として boss 検収項目に追加。全て PLAN rev.6 に反映。
  **Sol 批判は R5 で締め**（上限 5 往復到達・区分完了）。

## Opus ラウンド（手順 3.5）
- O1（change-reviewer, read-only, Opus）: **条件付き承認**（B1〜B5 反映が条件、C1/C2 縮小推奨）。
  boss 全件検分の結果、全て受理し PLAN rev.7 へ反映:
  B1（再 probe 失敗経路で旧 record が正常表示＝keyless で ✓ ax: active）→ unknown 強制を再 probe 失敗
  にも統一適用／B2（SKILL :649/:653-654/:766・test_v014:225 の編集漏れ）→ 編集対象に明記／
  B3（残骸ゲートの行単位判定が ADOPTION:115/:124・init:135 を素通り）→ 段落単位走査へ／
  B4（allowlist 未列挙）→ §7 歴史ブロック 2 段落の literal 指定・ファイル単位禁止／
  B5（SKILL:224-225 は誤記、実体は config-schema.md:223-224）→ 記載場所訂正。
  C1（codex 側 💡 not-configured 行は到達不能＋4-way と重複）→ 採用: codex 側の行・優先順位変更・
  関連 assert を全て削除（ax 側のみ実装。test_v014:253-264 は不変に戻る）／
  C2（handoff テストは 5 世代 in-place 再ターゲットが確立運用 — boss の「歴史保存・新ファイル複製」裁定を
  git 履歴実測で覆した）→ 採用: test_release_handoff.py を v0.15 へ in-place 再ターゲット、新ファイル廃止。
  非ブロッキング 1（README graph 3 seam の key-gated 句）・3（ラベル訂正）・4（集合一致→代表 path 検査へ
  縮小）も採用。2（codex-review-plan.py の ensure_ascii=False）は Opus 推奨どおりスコープ規律で放置。
  Opus 実測: フルスイート 609 OK 再確認・波及先 22 ファイル走査で start-run/decide-verdict/
  workflow-template/example config は変更不要と確認。
- O2（同一エージェント resume）: rev.7 の反映 10 件を全件確認 OK。残 2 件 → 受理し rev.8 へ反映:
  O2-1（ブロッキング — 空行段落走査は保持必須テキスト 5 箇所で false positive、Opus が仕様どおりの
  スキャナを実装・実行して実測）→ 走査単位を「表行／リスト項目／散文段落の最小」へ変更、保持 5 箇所の
  負テストを完了条件に追加／O2-2（test_v014 の行番号ずれ — :225 は今版と無関係の EVIDENCE 所有権契約で
  変更禁止、正しくは :226/:227/:228）→ 行番号訂正・:225 変更禁止を明記。
- O3（同一エージェント resume）: **指摘なし・実装承認**。Opus が rev.8 仕様どおりの最小単位走査器を
  実装・実行し、保持テキストの false positive 0・真陽性全捕捉を実測確認。行番号訂正も実ファイルと一致
  確認。参考指摘（「真陽性 9 箇所」の数値）は定性表現へ修正済み。**手順 3.5 完了 — worker（Terra
  medium）投入は Opus 承認済み。次はユーザーの計画承認（手順 2 のユーザー提示）。**

## ユーザー承認（2026-08-29、AskUserQuestion 実測）
- ① PLAN rev.8 での実装開始: **承認**。② TOCTOU 新 Issue 起票: **承認**。
- 新 Issue 起票済み: **#63**（https://github.com/akira993/doc-audit-harness/issues/63 — release-handoff の
  前提条件検証の対象番号）。PLAN §9 の「番号記録」はこれで充足。
- 実装 branch `fix/v0.15.0-issue-56-stage2` 作成済み（base: main 4c9df5b）。

## worker 実装チェックリスト
- [x] 1〜4: ax/codex probe、probe record、codex review plan
- [x] 5〜8: audit/init skill、schema、ADOPTION、README
- [x] 9〜10: 版番号、engine SHA
- [x] 11〜16: probe/planner/契約/scaffold テスト
- [x] 17〜18: v0.15 release handoff と安全停止テスト
- [x] §8 の検証コマンド一式、実数集計、許可範囲確認

## boss 検収（手順 5 — 実装ラウンド 1）
- worker は codex sandbox の `.git` 制限で commit 不能 → boss が diff 全 1352 行を読了の上、計画どおり
  6 commit に分割して commit（fad5cef〜d346edc、handoff script は `git add -f`）。
- boss 追認（worker 報告と独立に再実行）: フルスイート **Ran 629 tests OK, skip 0**（609→+20）、
  残骸ゲート実数 **files=101 units=2789 hits=0**（worker 報告と一致）。
- スコープ検査: `git diff --name-only main...HEAD` = 23 ファイル、全て PLAN §7 許可一覧内。
  禁止対象（test_v014:225 の EVIDENCE 所有権 assert・config-schema :33-34）は diff で不変を確認。
- §6-2 下限照合（Opus 保留分）: ax 27≥23・codex 27≥23・probe-record 12≥12・planner 16 行維持+7・
  handoff 既存 18 method 維持+5・ASCII 2・resume 配線 2 — 全て充足。
- Sol R5-7 配線順: SKILL.md resume 節「Re-run … before either consumer … bind … from that same probe
  stdout … re-record that same stdout」を diff で確認、test_v015 の配線契約（script 名が "before either
  consumer" より前に出現・同一 stdout 束縛/再記録文言）で機械固定済み。
- 新規 2 ファイル（test_v015_contracts.py 261 行・release-handoff.sh 160 行）は全文/雛形 diff で検分:
  最小単位スキャナの fixture 自己検証・保持 5 path 負テスト・#63 OPEN 前提条件・安全停止継承を確認。

## 実装レビューラウンド（手順 5/6）
- ラウンド 1（最終 `codex exec review` -m gpt-5.6-sol high, `--base main`）: **P2 × 1・blocking 0**
  （`final-review.md`）。指摘: handoff が #63 の OPEN しか検証せず、#59 CLOSED でも「#59 remains open」
  notes を公開可能。判定: **差し戻し**（boss 裁定 — 正当な整合性欠陥）。
- 差し戻し 1（実装セッション resume, effort medium）: #59 OPEN 前提条件＋負テスト追加。
  boss 追認: `tests.test_release_handoff` **Ran 24 OK**・`bash -n` OK・diff 2 ファイルのみ（許可内）。
  commit `20706eb`。判定: **承認**（完了条件 §6-6 blocking 0 充足）。

## route-close（手順 7 — merge 前時点。tag/Release/同期は PR merge 後の handoff で実施し追補を書く）
- 対象タスク: Issue #56 第 2 段（webExtract/codexReview key-gate 化）→ docaudit v0.15.0（minor）。
  PR **#64**（branch `fix/v0.15.0-issue-56-stage2`、`Closes #56`。merge はユーザー）。
- 記録時点の HEAD: `d507647c90cfced203506024b7de511a1cfb4c9c`（route 記録 commit 込み）。
  `git status --short` は既存の未追跡 `?? .claude/` のみ。
- 確定した変更ファイル（`git diff --name-only main...HEAD`、route 記録除く 23 件）: engine 4
  （ax-probe/codex-probe/probe-record/codex-review-plan）・文書 8（SKILL.md, config-schema, init SKILL,
  ADOPTION en/ja, README, plugin.json, engine-shas）・テスト 10（新規 test_v015_contracts 含む）・
  handoff script 1。全て PLAN §7 許可一覧内。
- audit verdict: `.claude/doc-audit.json` 未導入のため `/docaudit:audit` は不実行。代替の機械ゲート =
  フルスイート **Ran 629 tests OK, skip 0**（boss 追認）＋契約テスト（v013/v0132/v014/v015）＋
  残骸 grep ゲート **files=101 / units=2789 / hits=0** → **CONSISTENT 相当を 1 回で達成**（LLM 消費ゼロ）。
- SSoT 更新: **0 ファイル**（AGENTS.md/PROJECT.md は本 repo に存在しない。規約・仕様の変更は
  config-schema.md／ADOPTION §7／SKILL.md に記録済み）。
- 検査系成果物の実数: ax probe **27 ID**／codex probe **27 ID**／呼出し回数固定 **6 分岐**／
  probe-record **12 ID**（mutation 7・未知フィールド 1・上書き正負 2 含む）／codex-review-plan
  **既存 16 行維持＋追加 7**／ASCII・1 行 **2 probe**／resume 再 probe 配線 **2 本**／
  release-handoff **既存 18 method 維持＋追加 6**（#59/#63 前提条件・#59 負テスト含む、Ran 24 OK）／
  残骸ゲート走査 **101 files・2789 units・0 hits**（保持 5 path 負テスト成功）。
- 計画レビューの実数: Sol **5 往復**（R1 12・R2 10・R3 13・R4 13・R5 7 件 — 全件受理/修正受理/rescope
  転記）、Opus **3 ラウンド**（O1 条件付き→O2 残 2→O3 指摘なし・承認）、最終 codex exec review
  **P2 ×1 → 修正済み（20706eb）**。
- 据え置き（Issue 追跡）: **#59**（ledger・版跨ぎ禁止）・**#63**（TOCTOU 全 seam 封印設計 — 本 route で
  起票、ユーザー承認済み）。handoff は両者の OPEN を公開前提条件として検証する。
- 出荷後手順: PR #64 merge（ユーザー）→ `release-handoff.sh <merge-sha> 64`（tag `docaudit--v0.15.0`・
  Release・#56 close・`~/.claude/skills/docaudit/` 同期）→ 本 REVIEW に追補。

## worker review（完了時に実測値を記入）
- PLAN §5 の項目 1〜18 は全て実装。未実装項目なし。
- フルスイート: `Ran 629 tests in 194.007s`, `OK`, skip 0。ベースライン 609 から +20。
  増分は probe-record +5、codex-review-plan +3、v0.15 contracts +7、release-handoff +5。
- 指定 10 module: `Ran 127 tests in 36.629s`, `OK`。
- v0.15 contracts 単独: `Ran 7 tests in 0.051s`, `OK`。
- 判定表: ax 27 ID、codex 27 ID、tool 呼出し回数固定 6 分岐、probe-record 12 ID、
  codex-review-plan は既存 16 行維持 + 追加 7 ID、ASCII/1行 2 probe、resume 再 probe 2 本、
  probe-record 置換/保持 2 seam、release-handoff は既存 18 method + 追加 5 = 23 method。
- 残骸 gate: 101 files / 2,789 units / 0 hits。代表 path 3 件と test_v014 を走査し、保持 5 path の
  負検査も成功。
- release surface は `{\"0.15.0\"}`。engine SHA は check-docs
  `a5c1efbcbe1bdbece74cb188228fd676d4c6c0446a42f27d6514afe40c5f1ab8`、doc-lint
  `ebc5944f8739b4b0ff9740f442fe05225c6df300f6fcb471ba20120f30366727`、check-docs-engine
  `fbef5b46ff06271e740424eb6fc1c73171c6e461e057c8d4d70690dabb8c23a3`。
- `git diff --check` と `bash -n release-handoff.sh` は成功。禁止された
  `tests/test_v014_contracts.py:225`、`config-schema.md` の indexing/contextMode 2 行、許可外ファイルは不変。
- コミット作成は実行環境の `.git` 読み取り専用制限により失敗:
  `fatal: Unable to create '.git/index.lock': Operation not permitted`。したがって項目→commit 対応は
  1〜18 全て「未 commit（環境制限）」で、`git diff --name-only main...HEAD` は空。実差分は
  `git diff --name-only` と新規/ignore 対象の明示一覧で §7 許可範囲内であることを確認した。
- フルスイートでは既存 `tests/test_generic_layers.py` 由来の ResourceWarning が出たが、失敗ではなく、
  同ファイルは許可外のため変更していない。
