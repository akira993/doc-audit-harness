# REVIEW — 2026-08-31 Issue #66（方式 B: /code-review 自律実行）

## 事前検証
- 実機検証は `00-preflight-verification.md` に記録済み（headless 7 アーム＋interactive 1 実測＋上流 docs 調査）。
- ユーザー決定済み: 方式 B（`reviewCommands.code` 単一窓口）。ask 承認ゲートは実測不成立 → 推奨しない（deny/skillOverrides を opt-out として文書化）。

## セッション記録
| 役割 | モデル | session id | 備考 |
|---|---|---|---|
| 調査 (survey) | gpt-5.6-luna medium | 01a05576-fa51-7820-bf5b-7c98db1014f8 | 01-survey-luna.md |
| 批判 (critique) | gpt-5.6-sol high | 01a0557d-fdc3-70c1-b548-2b58fa32ad05 | resume で継続 |
| 実装 (impl) | gpt-5.6-terra high | 01a055bf-3d0b-77a1-9d74-0f1c25e22e6c | 07-impl-terra.md、workspace-write |

## 批判ラウンド記録

### Sol R1（02-critique-r1-out.md、判定: 差し戻し）
13 件（Critical 1・Major 10・Minor 2）。boss 全件検分の結果、全件妥当。
- #1 Critical: resume 後の「完了」自己申告で required を突破可能 → resume 後 ran 禁止で採用
- #2: severity 無し所見の WARN 既定は実測の eval() 注入を素通りさせる → UNSPECIFIED=blocking で採用
- #3: 空 diff では phase4 が走らず「REFUSED か黙殺か」の二択になる → start-run.py で phase4Required=true
- #4: gate 以外が REFUSED を出す契約違反 → planner refuse は起動抑止のみ、REFUSED は gate 単独
- #5〜#13: 決定表完全化(P1〜P8)・required×legacy 矛盾・phase4Runs 主張の撤回・テスト全数化・
  registry 正本化・getter 消費検査・test_release_handoff 変更禁止・旧意味句棚卸し・v0.16 run 非互換明記
→ PLAN v2 に全反映（#7 のみ縮小採用: 独立 record 新設は #66 要求外として見送り、意図的非対象を明文化）。

### Sol R2（03-critique-r2-out.md、判定: 差し戻し）
10 件（Major 8・Minor 2）。boss 全件検分の結果、全件妥当。
- #1: S3(start-run で phase4Required=true) は Phase 4 全体を強制起動する回帰 → boss は Sol 推奨(専用フラグ)
  ではなく「codexReview と対称に phase4 lifecycle に従う」代替案を採用（start-run.py 変更撤回）。R3 で裁定を求める
- #2: P5 charset が Unicode legacy command を REFUSED に巻き込む → 公式名前空間限定に縮小
- #3: §9.8 に phase4Required 軸が無い → false⇔none 双方向契約を追加
- #4: 偽 code-review 所見の混入 → source×state×config の整合検査を gate に追加
- #5: UNSPECIFIED の全 source 波及 → source=="code-review" 限定に修正
- #6: P1〜P8 の三重実装 → 共通分類 library docaudit_review.py に一本化
- #7〜#10: legacy 供給源一本化・e2e 本番順序・required:false 正規化・fresh run 記述の限定
→ PLAN v3 に全反映。

### Sol R3（04-critique-r3-out.md、判定: 差し戻し）
7 件（Major 5・Minor 2）。boss 検分: 全件妥当。決定的だったのは #1 — boss の v3 代替案の前提
「codexReview.required は空 diff で走らない」が実装事実（start-run.py:247・decide-verdict.py:1027）と
逆であることを実機根拠で反証。→ v4 で正しい対称形に再設計（required:true のみ phase4Required に参加、
planner を Phase 4 分岐前へ、phase4-not-required 状態新設、phase4Required 厳密 bool 検査、
テスト棚卸し追加）。false⇔none と taint/quarantine の両立、docaudit_review.py の
check-docs-engine sha 非対象は Sol が確認済み。

### Sol R4（05-critique-r4-out.md、判定: 差し戻し）
6 件（Major 4・Minor 2）。boss 検分: 全件妥当。
- #1: planner 前置により空 diff で legacy が実行される穴 → 分岐前は分類のみ、起動は true の内側限定
- #2: legacy 所見が新 evidence 契約で表現不能 → legacy-ran/legacy-not-run 分割＋source "review-command"
- #3: CODE_REVIEW_STATE が checkpoint (h) 後に復元不能 → gate 出力 codeReviewStatus に一本化
- #4: library の registry 外根拠が未証明 → AST＋隔離テスト
- #5: REFUSED 理由の優先順位 → 4 段の明示順
- #6: registry call-site 位置表記 → 訂正
→ PLAN v5 に全反映。R5（上限）で収束判定。

### Sol R5（06-critique-r5-out.md、上限ラウンド、判定: 未収束 → 区分で終結）
途中 collab 待機で停止 → kill して「単独・collab 不使用」を明示し resume（既知の罠、メモリ記載どおり）。
新規 3 件（Major 3）: #1 報告書テンプレートに状態行 placeholder が無く gate stdout では公開報告書に
反映不能 → `{{GATE_CODE_REVIEW_STATUS}}` 新設で採用／#2 v5 編集起因の legacy enum 不整合 → 統一／
#3 review-command 偽所見の対照テスト欠落 → §9.8・S7 に追加。
区分: #1・#2 = PLAN 欠陥（v6 で修正済み）、#3 = worker 吸収可（v6 で PLAN にも明記）。
→ PLAN v6 で批判ラウンド終了。次は手順 3.5 Opus 全体敵対レビュー。

### Opus ラウンド 1（手順 3.5、判定: 差し戻し → v7 で反映）
ブロッキング 8＋小 2＋縮小提案 1。Sol 5 往復後になお: O-1 refuse 時の evidence 未定義（write-evidence
例外で gate 不達＝R1-4 意図の破壊）／O-3 新 placeholder の出現数契約欠落（not-active adopter の報告書
が消える）／O-4 UNSPECIFIED 正規化の主体未定義（同一実態で REFUSED/NEEDS_FIX に分岐）／O-5 CM 節の
生死未指定（波及 5 行）／O-6 版数棚卸しの漏れと stale 行番号／O-7 完了条件が全て静的（新機能を一度も
実行しない）→ 受入 run 追加／O-8 運用コスト（毎回レビュー・二重レビュー・code 欠陥で doc audit が
止まる意味変化）の ADOPTION 明記／O-9 test_v014 の見出しリテラル依存／O-10 warnings[] 警告コード。

#### ユーザー/advisor 裁定 2 件（2026-08-31）
1. **不正 config の拒否強度**: ユーザー「2（Issue どおり全 run REFUSED）で行きたいが advisor に意見を」
   → advisor 裁定: **option 2 支持**。理由: (i) required 既定 false の世界で「⚠＋CONSISTENT 継続」は
   #66 の発端症状（15 run 誰も気づかず）の再演。(ii) codexReview 対称論は誤類推 — static 設定ミス
   （一度直せば恒久解消）と runtime not-run（環境起因・一過性）は制御可能性が違う。(iii) v0.16.0 で
   probe invalid-config を exit 2 に強めた軌跡と一致。実測: adopter 9 件に `ultra` 0 件・P7 該当は
   sunrise-web の `/code-review xhigh` 1 件のみ（潜在誤設定、1 行移行）。緩和策: remediation 込み
   REFUSED 理由・ADOPTION breaking change 明記・PLAN §1 に裁定根拠を恒久記録（再審議防止）。
2. **P8 legacy の evidence 契約化**: ユーザー「縮小（Opus 推奨）」→ legacy は現行挙動を一切変更しない。
   v6 の legacy-ran/not-run・source "review-command"・偽所見マトリクスを全て撤去（部分撤去による
   enum 残骸＝R5-2 の再発を防ぐため一括巻き戻し）。P8 の状態行は gate が config から固定文言を描画。
→ PLAN v7。Opus reviewer へ resume で再検分を依頼（「指摘なし・実装承認」まで手順 4 に進まない）。

### Opus ラウンド 2（判定: 要修正 3＋小 2 → v8 で反映）
O-3 採用の波及を検出: V7-1 テンプレート fixture（wp12_helpers 9 ファイル依存）と SKILL 契約表の棚卸し
漏れ（表を検査するテスト自体が不存在）／V7-2 refuse の Refused を codexReview の検査位置（:955-963）に
置くと report_trusted（:968）未確定で REFUSED 報告書が公開されない／V7-3 分類前 REFUSED 経路で
placeholder 値未定義 → render_report が KeyError/TypeError で gate クラッシュ／V7-4 §6 の機械判定に
人手受入が混在 → §6b 分離／V7-5 legacy-pending の束縛先未定義。legacy 縮小の巻き戻し完全性・O-2
不採用の裁定記録は Opus が確認済み。→ PLAN v8。Opus へ最終承認判定を依頼中。

### Opus ラウンド 3（判定: 参照ずれ 2 行の修正を条件に実装承認・再レビュー不要）
V7-1〜V7-5 の反映は 5 件とも完全と確認。A: §9.8 の優先順位採番が S4 と食い違い V7-2 の配置規則を
誤読させる → S4 と同一の (1)〜(4) に統一。B: S2-10 参照の陳腐化 → S2-11 に訂正。両方 v8 に適用済み。
**PLAN v8（修正込み）で実装承認。手順 4 へ。**

## 実装ラウンド記録
- 実装（Terra high、session 01a055bf-3d0b-77a1-9d74-0f1c25e22e6c）: 上書き承認 1 回を挟み完走。
  worker 報告 `Ran 739 tests / OK`・CT `23/3/13/22/20`・対象 23/10 件。
- boss 検分: 変更集合 = PLAN §7 許可リストと一致（22 modified + 5 new、test_release_handoff diff 0）。
  中核 diff 全読（docaudit_review.py／code-review-plan.py／decide-verdict.py／start-run.py／
  write-evidence.py／SKILL.md／docs）— PLAN v8・V7-1〜V7-3 に忠実。boss 実測 `Ran 739 tests / OK`
  （319.994s）・CT 実数一致・grep 0 件・版数 0.17.0 一致。
- 差し戻し R1（boss、Minor）: CT-2 の `対象 21 本を検査` が stale リテラル → `len(checked)` 導出に修正。
  boss 追認: `対象 22 本を検査`・OK。
- 最終 codex review（`codex exec review --uncommitted` Sol high、別セッション）: P1 1 件 —
  「resumed run 一律 not-run」がレビュー開始前の中断まで巻き込む → 差し戻し R2。
- 差し戻し R2: SKILL.md:595 を「起動後の中断（行 (g)）のみ not-run、起動前の再開は通常起動」に限定、
  v015 契約タプルも更新。worker `Ran 739 tests / OK`、boss 追認（v015＋gate テスト再実行 OK）。

## §6b 受入 run（boss 実施、2026-08-31、headless opus、scratchpad i66-accept2）
scratch repo（calc.py＋docs/calc.md、未コミットの eval() 植込み、reviewCommands.code="/code-review low"）
で 0.17.0 の audit skill（project skill 複製）を全フェーズ完走（45 turns / 803s）。
- (i) 報告書 `docs/logs/doc_audit_2026-08-31.md` :119 に gate 描画の
  `✓ code-review: ran (findings folded into phase4)` を確認。
- (ii) phase4.json: `codeReview: {"state": "ran"}`、fold 所見
  `{source: "code-review", severity: "UNSPECIFIED", title: "calc.py:3 - float(s) replaced with eval(s) ..."}`
  （植込み欠陥を自律検出・契約どおりの source/severity で fold）。
- (iii) verdict = REFUSED。理由は `verdict set does not equal impacted set` — headless -p で Workflow
  ツールが承認不能で Phase 3 検証者が起動できなかったことによる**既存機構の正しい fail-closed**
  （#66 変更とは独立。報告書は publish・lock は自己解放）。
- 副次観測（本 route のスコープ外・記録のみ）: 1 回目 run は監査自身の `__pycache__` 書換えで
  seal exit 5（規定どおり解放→再実行で解消）／`/security-review` は origin リモート無しの scratch
  では preamble 失敗で WARN／`diffGlobs: ["**/*.py"]` が repo 直下ファイルに不一致（`*.py` 併記が必要）。

## 承認判定
PLAN §6 完了条件 1〜9 = boss 実測で全充足（739 tests OK・CT 23/3/13/22/20・対象 22/23/10 件・
grep 0・版数一致・release_handoff 無変更）。§6b 充足。R1・R2 差し戻しは解消・追認済み。**承認**。

## route-close 記録（pre-merge）
- 対象タスク: Issue #66 方式 B → docaudit v0.17.0（branch fix/v0.17.0-issue-66）
- 記録時点の HEAD: ccbbe813b740a5e56dd85c352efb49e65d31b73f
- 確定した変更ファイル: 22 modified ＋ 5 new（git diff --stat main...HEAD。PLAN §7 許可リストと一致、
  tests/test_release_handoff.py 無変更）
- audit verdict: **n/a** — 本 repo は doc-audit 未導入（.claude/doc-audit.json 無し。
  import-audit-scope --check 実測 state=absent/configSha=none）。route skill の規定どおり
  「変更した公開挙動に対応する既存ドキュメントとの整合確認」で代替: README／ADOPTION en+ja／
  config-schema／example json／init SKILL は本 route の成果物として更新済みで、
  test_v016_docs_contracts ほか docs contract テスト（フルスイート 739 件 OK に包含）が新契約
  トークンの存在と旧意味句の不在を機械的に固定している。
- SSoT 更新: 0 ファイル（AGENTS.md／PROJECT.md は本 repo に存在しない）
- 検査系成果物の実数: CT `call sites 23／exempt 3／getters 13／scripts 22／observers 20`・
  CT-2 対象 22 本・test_docaudit_review 対象 23 件・test_code_review_plan 対象 10 件・
  フルスイート Ran 739 tests / OK（boss 実測 319.994s）
- PR: https://github.com/akira993/doc-audit-harness/pull/69（セルフマージは classifier 拒否のため
  マージはユーザー実施 → 以後 tag `docaudit--v0.17.0`・Release・#66 close・skills-dir 同期の handoff）
- handoff 派生時の注意: PR #69 本文に `Closes #66` があるためマージ時に #66 は **GitHub が自動 close**
  する。v0.16.0 の release-handoff.sh を派生させる際は `gh issue close` ステップを削除するか
  「既 close 許容」にすること（盲目コピー禁止）。
