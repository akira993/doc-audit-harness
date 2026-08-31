メタ認知: 「v4 なら収束しているはず」という期待を排し、移動した処理の実行範囲と既存 legacy 経路を重点的に確認した。

結論: **まだ収束ではない**。`CFG`／`CONFIG_SHA` の束縛時点、Phase 0/0.5 との順序、registry 算術 `23/3/13/22/20` は成立する。一方、legacy と cross-turn に Major が残る。

1. **Major — P8 legacy command が Phase 4 不要時にも実行され得る**

   根拠: S3-2 は planner を global 分岐前へ移し、`legacy` を `phase4Required` に関係なく「S2 のとおり」扱う。[PLAN.md:129](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:129>)。S2 の legacy 処理には状態束縛だけでなく、project command の実行試行も含まれる。[PLAN.md:99](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:99>)。一方、P8＋false は Phase 4 evidence なしで正常とされる。[PLAN.md:332](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:332>)。実行すれば所見を evidence に保存できず、空 diff で未記録の外部処理だけが増える。

   推奨修正: 分岐前では分類と初期状態の決定だけを行い、P6/P8 の実コマンド起動は `phase4Required=true` の内側に限定し、false 時は `phase4-not-required` とする。

2. **Major — P8 legacy の正常な findings を新 evidence 契約で表現できない**

   根拠: P8 は現行 legacy 挙動を維持するとされ、既存契約では review findings も共通 Phase 4 collection に入り verdict に作用する。[PLAN.md:72](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:72>)、[SKILL.md:657](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:657>)。しかし S4 は `source=="code-review"` の所見を P6＋`state=="ran"` の場合だけ許し、P8 では必ず REFUSED にする。[PLAN.md:161](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:161>)。legacy 所見を同じ source で保存すれば REFUSED、捨てれば互換性回帰、別 source に逃がせば `UNSPECIFIED` 保護を迂回する。

   推奨修正: P8 を `legacy-ran`／`legacy-not-run` に分け、`legacy-ran` に限って専用 source の legacy findings と従来 severity を gate が受理する契約を追加する。

3. **Major — `CODE_REVIEW_STATE` は checkpoint (h) 後に復元できない**

   根拠: S3/S5 は会話内変数 `CODE_REVIEW_STATE` から状態行を作る。[PLAN.md:129](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:129>)、[PLAN.md:169](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:169>)。しかし cross-turn 契約で持ち越せるのは `RUNID` と `EVIDENCE` だけで、Phase 5 状態行は probe record を正本とする。[SKILL.md:42](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:42>)、[SKILL.md:51](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:51>)、[SKILL.md:69](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:69>)。`probe-record.py` には code-review seam がなく、同ファイルは変更範囲外である。[probe-record.py:14](</Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/probe-record.py:14>)、[PLAN.md:265](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:265>)。checkpoint (h) 後の resume では `ran`／`legacy`／`phase4-not-required` の表示を正しく復元できない。

   推奨修正: Phase 5 の code-review 状態を会話変数から作らず、gate が封印 config・manifest・検証済み Phase 4 evidence から直接導出して報告書へ出す。

4. **Major — 共通 library が registry 外であることをテストが証明しない**

   根拠: `docaudit_review.py` は parsed document のみを受け取る純粋 library だから registry 対象外とされる。[PLAN.md:80](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:80>)。しかし S7 は import 共有と結果一致しか検査しない。[PLAN.md:190](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:190>)。現行 CT も `--expect-config-sha` を持つ script だけを列挙するため、library が誤って config path・環境・`sealed_config` を直接読んでも K=22 を通過できる。[test_v016_contracts.py:116](</Users/akiratakahashi/Projects/doc-audit-harness/tests/test_v016_contracts.py:116>)。

   推奨修正: `docaudit_review.py` が parsed dict 以外を入力に取らず、config I/O・環境参照・`sealed_config` import を持たないことを AST と隔離単体テストで固定する。

5. **Minor — 多重異常時の REFUSED 理由の優先順位が矛盾する**

   根拠: S4 は P2/P4/P5/P7 または required 矛盾なら「EVIDENCE の内容に関わらず」config 固有理由を返す。[PLAN.md:145](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:145>)。一方、§9.8 は boolean 型検査の次に sentinel 双方向検査を行い、その後に required 条件を扱う。[PLAN.md:315](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:315>)。invalid config と sentinel 不整合が同時にある場合、期待理由が一意でない。

   推奨修正: 優先順位を「厳密 boolean → config 分類/refuse → sentinel 整合 → codeReview eligibility」と明記する。

6. **Minor — registry の call-site 表記が移動後の位置と一致しない**

   根拠: S3 は planner を global Phase 4 分岐直前へ移すが、registry は引き続き「Phase 4 step 3」と記載する。[PLAN.md:129](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:129>)、[PLAN.md:294](</Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-31-issue-66/PLAN.md:294>)。件数 N=23 には影響しないが、registry を正本として使う検査位置が誤る。

   推奨修正: call-site 欄を「Phase 4 の CONFIG_SHA 再束縛・getter 後、global gate 直前」に訂正する。

| 区分 | 指摘 |
|---|---|
| PLAN 自体の欠陥 | #1、#2、#3、#5 |
| worker 指示で吸収できる細部 | #4、#6 |

ファイルへの修正は行っていない。