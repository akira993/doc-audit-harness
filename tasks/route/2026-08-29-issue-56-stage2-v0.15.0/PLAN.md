# PLAN — Issue #56 第2段: webExtract / codexReview の key-gate 化 → docaudit v0.15.0（rev.8, 2026-08-29 — Sol R1〜R5＋Opus O1（B1〜B5/C1/C2）＋O2（走査粒度・行番号訂正）反映）

## 0. rescope 裁定（rev.5 の設計原則 — R2-1 以降の発散への回答）

R2〜R4 で積み増した EVIDENCE SHA 照合層（planner `--evidence`・config-changed 終端・model/timeout の
検証済み出力・taint 連携）は**今版から全て撤回**する。理由:
(a) それらが防ぐ「run 途中の config 一時改竄（TOCTOU）」は **v0.13.2 の graph 系 key-gate・mdq の bin
    解決を含む全 seam に既存**の露出であり（graph probe も live config を無照合で読む）、#56 第2段が
    新設するものではない。
(b) 部分的な照合層は R3-1／R4-3／R4-4 が示したとおり別の迂回路と新 terminal path を生み、1 リリース分の
    外科的変更を超える。この機構は `docaudit-history`／anchor と同じ信頼クラス（封印・barrier・taint 一元化）
    を要し、#59 の設計制約と同族 — **独立 Issue として起票し（ユーザー承認待ち）、専用 route で設計する**。
(c) 本版の key-gate の正しさは決定論で完結できる: **運用判定は「key-gated probe の実行結果」単一経路**とし、
    fresh は Phase-0 probe、resume は probe 再実行（決定論・ローカル・秒未満）で束縛する。probe が読む
    live config の信頼は既存 v0.13.2/v0.14 と同一水準（変更なし）。

## 1. 目的

Issue #56 第2段のユーザー裁定（2026-08-29 実測、AskUserQuestion）を実装する:
**`webExtract`（ax）と `codexReview`（codex）の 2 seam を key-gated 化**（config にキーが無ければ
`reason:not-configured` で tool を一切起動しない — v0.13.2 の symbolGraph/docGraph/semanticSearch と同型）。
**`indexing`（mdq）と `contextMode` は既定有効を維持**し、原則「トークン節約装置は既定有効、
optional 統合は key-gated」として文書化する。これで #56 は close（PR に `Closes #56`）。
キーが**存在する**場合の意味論（`{}` は有効・`enabled:false`・invalid-config・bin 検査）は v0.14.0 のまま不変。
単体呼び出し時の防御は参照実装（graphify）と同一へ揃える（§5.1）。

## 2. 入力・参照資料

- ユーザー裁定と実測記録: `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/REVIEW.md`
- 事前調査（Luna read-only, 全 file:line 引用）: 同dir `investigate-report.md`
- Sol 計画批判 R1〜R4: 同dir `critique-r{1..4}-answer.md`（対応表は REVIEW.md）
- 参照実装: `skills/audit/scripts/graphify-probe.sh:31-51`（「a missing or invalid config never falls
  back to enabled」）／`codegraph-probe.sh:28-35`／`cocoindex-probe.sh:34-41`
- Issue: #56（close 対象）。#59 と新 Issue（§9）は対象外（据え置き）。

## 3. 担当

boss = Fable（計画・レビュー・承認。実装は書かない）

## 4. 実行者

worker = Terra `medium`（仕様確定済みの通常実装。1 ステージ、branch `fix/v0.15.0-issue-56-stage2`）

## 5. 成果物

### 5.1 エンジン実装（2 probe + record + planner キー判定）

1. `skills/audit/scripts/ax-probe.sh` — config 判定を graphify-probe.sh:31-51 と**次の 3 点に限り**同型へ
   （Sol R2-3: disabled 時の既定 bin 名返却など既存 v0.14 契約は不変）:
   (i) config 必須化 — `--config` 省略・**値欠落**（`--config` が末尾 — Sol R3-12）・空パス・不存在・
   壊れた JSON → `invalid-config`（enabled へのフォールバック廃止。「ALWAYS emit JSON + exit 0」契約を
   全ケースで維持）、(ii) top-level 非 object → `invalid-config`、(iii) 正常 object で
   `"webExtract" not in config` → `not-configured`（object/enabled/bin 検査・tool 起動より前に確定）。
   emit `{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"not-configured"}`・exit 0。
   ヘッダコメント（:2-9）の conditional-force 記述を key-gated へ更新。
2. `skills/audit/scripts/codex-probe.sh` — 同様に 3 点同型（disabled 時の既定 bin 名維持）。キー不在 →
   `not-configured` を **caller（CODEX_HOME/auth.json）探索より前**に確定し、caller 3 フィールドは
   固定中立値 `callerCodexHome:null, callerCodexHomeSource:"unknown", callerAuthFile:"unknown"`、
   `probeCommands:[]` で 8 フィールド形を維持（Sol R1-10）。exit 0。ヘッダ更新。
3. `skills/audit/scripts/probe-record.py` — 許容 reason 集合に `not-configured` を追加: webExtract
   （:105-112）・codexReview（:113-128）。codexReview は `reason=="not-configured"` 専用の一括検証:
   `available=false`・既定 bin・`version:null`・`probeCommands:[]`・caller 中立 3 値を強制し、かつ
   **キー集合が正規 8 フィールドと完全一致**（未知フィールドの持ち込みも拒否 — Sol R2-8・R4-11）。
   **record の書込み機構（汎用 atomic upsert — probe-record.py:332）は変更しない**（Sol R5-1: 現行は
   全 seam upsert であり「他 seam 拒否」は回帰になる）。resume 再 probe の再記録はこの既存 upsert を
   そのまま使い、webExtract/codexReview の置換と他 seam の保持を正テストで固定するだけとする。
4. `skills/audit/scripts/codex-review-plan.py` — **キー判定のみ追加**（Sol R1-1。rev.4 の
   `--evidence`/SHA/model/timeout 出力は §0 により撤回）: 読み込んだ config で
   `"codexReview" not in config` なら `--available` の値に関わらず `action:"not-active"`,
   `reason:"not-configured"` を返し codex を起動させない。**既存 16 行判定表（availability×mode×
   required×baseline）の意味論・CLI・出力形式は不変**（Sol R4-7）。

### 5.2 SKILL・schema 文書（同一 PR 内で先回り整合）

5. `skills/audit/SKILL.md`
   - ax reason enum（:162）と codex reason enum（:178）へ `not-configured` を追加。
   - 両 probe 段落に key-gated の 1 文（codegraph 段落の表現に合わせる）。単体呼び出し防御の説明
     （:194 相当）を「unreadable/absent config は invalid-config（enabled へフォールバックしない）」へ更新。
   - **resume 規則（:68 相当の置き換え — Sol R1-1・R3-2・R4-1・R4-10 を単一機構で解決）**:
     resume 後、webExtract/codexReview の**運用値（available/reason/bin）は rebind から復元せず、
     `ax-probe.sh`／`codex-probe.sh` を再実行して束縛し直し、その結果を probe-record へ再記録（上書き）**
     する。これにより (a) v0.14 記録の `available:true` 持ち越しが機構的に消え（key-gate は probe 単一
     経路）、(b) planner・Phase-4 実行に必要な 3 値が checkpoint 位置によらず束縛され、(c) Phase-5 表示・
     caller 情報も現行 config と整合する。他 seam の rebind 意味論は不変。**失敗時規則**（Sol R5-2 修正
     受理）: 再 probe の起動不能・非 JSON・parse 失敗は、旧 rebind 値を運用に**使わず**、fresh Phase-0 と
     同一の degrade 規則で `available=false`（ax: `AX_AVAILABLE=false/AX_REASON=probe-error` 相当、codex:
     `CODEX_REVIEW_AVAILABLE=false`）に倒して続行する — false 方向は tool 不起動なので keyless 保証は
     破れず、`required:true` は planner not-active → 既存 decide-verdict 整合検査で fail-closed になる
     （「停止」は fresh の never-fatal 契約と非一貫のため不採用）。**表示規則の統一**（Sol R5-4＋Opus B1）:
     resume で webExtract/codexReview の運用値を probe から束縛し直せなかった**全ケース**（再 probe の
     起動不能・非 JSON・parse 失敗、および再 probe 成功後の再記録失敗）で、当該 2 行の Phase-5 表示を
     `state unknown` 系へ強制し、旧 record 値（v0.14 の `available:true/ok` と旧 caller path）を正常
     表示しない（non-blocking のまま。失敗経路でだけ「持ち越し表示」が復活する穴を塞ぐ）。
     この規則は SKILL.md:649「bind exclusively from rebind」・:653-654「failed record write merely
     emits ⚠ and continues」・:766「do not substitute conversation values」と矛盾するため、**この 3 文を
     編集対象に含め**、webExtract/codexReview の resume 特例（再 probe 由来の束縛と unknown 強制）を
     明記する形へ改訂する（Opus B2）。
   - Phase-5 状態行: **ax 表（:744-748）のみ** `AX_REASON=not-configured` の 💡 行（:775 の文型 —
     :747 の「install: curl …」案内がキー不在時に誤案内になるのを防ぐ）を ⚠ invalid-config の直後に追加。
     **codex-review 表への 💡 not-configured 行と :646 優先順位への rung 追加は行わない**（Opus C1 採用:
     R1-3 の順位では reviewState=null 条件が上位 bullet に食われて到達不能、not-active は既存 4-way が
     `not active (<reason>)` として `not-configured` を表示するため重複。:646 の優先順位文は**不変**）。
     4-way の `<rebind.codex-review.reason>` に `not-configured` が現れ得ることを仕様として 1 句明記。
6. `skills/audit/references/config-schema.md`
   - :35（webExtract）・:36（codexReview）を key-gated 文言へ書き換え（:37/:38 の型。codexReview の
     `required:true … REFUSED` 文は維持し、required はキー内のためキー不在と競合しない旨を 1 句）。
     :33-34（indexing/contextMode）は**変更禁止**。
   - 定義文 :215-225（ax）・:233-240（codex）を「キーが存在する場合に限り」へ修正（Opus 非ブロッキング 3:
     「実例 walkthrough」ではなく `webExtract/codexReview is optional and conditional-force` の定義文）。
     **:223-224 の「When `ax` is absent, `webExtract.enabled` is `false`, …」は「key が存在し tool が
     absent」の場合と分離して書き直す**（Opus B5: 旧 PLAN が SKILL.md:224-225 としていたのは誤記で、
     実体はこの config-schema.md の行）。
7. `skills/init/SKILL.md` — ax OMIT 文言（:131-135）と codex OMIT 文言（:136-142）を symbolGraph 型へ:
   「OMIT the key; absent key ⇒ the audit reports `not-configured` and never runs the tool.」
8. `docs/ADOPTION.md`／`docs/ADOPTION.ja.md`
   - §7 に `**v0.15.0 behavior changes:**`／`**v0.15.0 の挙動変更:**` を v0.14.0 ブロック（en :271／
     ja :247）の直後へ追加。固定文（en 4 文＋ja 4 文、**双方とも契約テストの期待値** — Sol R2-10）:
     ① `webExtract and codexReview are now key-gated like symbolGraph/docGraph/semanticSearch: an absent key reports not-configured and never runs the tool — ax and codex no longer run implicitly on configs without those keys (previously an absent key defaulted to enabled); a directly invoked probe with an unreadable or absent config now reports invalid-config instead of falling back to enabled, and the codex probe collects no caller CODEX_HOME/auth.json information for a keyless config (neutral values are recorded)`
     ② `for a new run, or a run resumed before its codex review has run, a keyless config therefore loses the Phase-4 codex review and its verdict-affecting critical/high findings — an audit that was NEEDS FIX only because of implicit codex findings can become CONSISTENT after upgrading; add "codexReview": {} to keep the old best-effort behavior, or additionally "required": true for a separate, stronger fail-closed guarantee (a non-completed review becomes REFUSED — this is NOT the old implicit behavior)`
     ③ `on resume, the operational webExtract and codexReview state is re-derived by re-running their key-gated probes against the current config (probe records are overwritten accordingly); a run whose codex review already completed keeps those findings — cross-version in-flight resume is discouraged: start a fresh run (a mechanical prohibition is tracked in #59)`
     ④ `indexing and contextMode keep their enabled-by-default behavior (intentional: they reduce token consumption); enabled:false and invalid-config semantics are unchanged for all four seams, and bin validation is unchanged for the three bin-bearing seams (indexing/webExtract/codexReview; contextMode has no bin)`
     ja 固定文（同順・契約テスト期待値）:
     ① `webExtract と codexReview は symbolGraph/docGraph/semanticSearch と同じ key-gated になった: キーが無い場合は not-configured と報告し、tool を一切起動しない — キー無し config で ax / codex が暗黙に実行されることはなくなった（従来はキー不在＝既定有効）。probe を単体で直接呼んだ場合も、読めない・存在しない config は既定有効へフォールバックせず invalid-config になる。また codex probe はキー無し config では呼び出し元の CODEX_HOME / auth.json 情報を収集しない（中立値を記録する）`
     ② `したがって、新規 run および codex review 実行前に resume した run では、キー無し config は Phase-4 codex review と、その verdict に影響する critical/high 所見を失う — 暗黙の codex 所見だけが理由で NEEDS FIX だった audit は、更新後 CONSISTENT になり得る。旧来の best-effort 挙動を維持するには "codexReview": {} を追加する。さらに "required": true を付けると別種のより強い fail-closed 保証になる（未完走の review が REFUSED になる — これは旧来の暗黙挙動ではない）`
     ③ `resume 時、webExtract と codexReview の運用状態は key-gated な probe を現在の config に対して再実行して導出し直す（probe 記録も対応して上書きされる）。codex review が既に完走した run はその所見を保持する — 版をまたぐ resume は非推奨であり、新しい run を開始すること（機械的な禁止機構は #59 で追跡）`
     ④ `indexing と contextMode は従来どおり既定有効（トークン消費を減らす装置としての意図的設計）。enabled:false と invalid-config の意味論は 4 seam すべてで不変、bin 検査は bin を持つ 3 seam（indexing/webExtract/codexReview）で不変（contextMode に bin は無い）`
   - seam 一覧の両箇所（en :83-84・:115-127／ja :82-83・:100-112）を webExtract/codexReview のみ
     key-gated 記述へ更新（Sol R1-11）。**caller 表示段落（en :128-131／ja :113-116）**に「キー不在時は
     caller 情報を調べず中立値を返す」を追記（Sol R2-9）。版表示（en :231, :303-304／ja :211, :277-279）を
     0.15.0 へ。indexing/contextMode の記述は維持。
   - `README.md:25` の Optional 項目を **1 tool = 1 サブ bullet へ分離**した上で（Sol R3-11）、ax・codex の
     記述へ key-gated（doc-audit.json のキーで opt-in）の 1 句を追記。**codegraph/graphify/CocoIndex の
     3 bullet にも同じ key-gated 1 句を追記**（v0.13.2 から key-gated だが README は「degrades gracefully
     when absent」のままで、新 bullet と並置すると誤読を招く — Opus 非ブロッキング 1）。mdq/context-mode
     の記述内容は不変。
9. `.claude-plugin/plugin.json` — version `0.15.0`。
10. `skills/audit/references/engine-shas.json` — `0.15.0` エントリ追加（scaffold 生成元から再計算、
    `tests/test_scaffold.py:307-317` で機械検証）。

### 5.3 テスト（機械的検査ゲート）

11. `tests/test_ax_probe.py` — キー不在既定（:121-130）→ not-configured へ。判定表（:132-187）を v0.15 表へ:
    absent → not-configured／`{}` → 有効／config 省略・値欠落・不存在・壊れ → invalid-config（全ケース
    ASCII JSON 1 行・exit 0）。**偽 tool 呼出し回数の厳密固定**: absent・invalid=0 回、`{}`＋tool あり=1 回
    （Sol R1-6・R3-12）。出力フィールド集合（:189-205）に not-configured を追加。
12. `tests/test_codex_probe.py` — 同様（:140-149, :151-206。呼出し回数: absent・invalid=0、`{}`＋tool
    あり=2）。not-configured の 8 フィールド＋caller 中立値固定（:208-251, :277-291 の型）。
    **非 ASCII CODEX_HOME で absent-key 分岐 → 純 ASCII・JSON 1 行・終端 LF 1 本**（Sol R1-8）。
13. `tests/test_probe_record.py` — ax/codex の not-configured record 受理＋read 後 rebind 復元。codex は
    **mutation 表**: 連動 7 フィールドを 1 つずつ矛盾させた fixture 全 7 件の個別拒否（Sol R3-7）＋
    **未知フィールド追加（例 `leakedHome`）の拒否 1 件**（Sol R4-11）。**同一 runid の上書き再記録**
    （webExtract/codexReview のみ許可・他 seam は拒否のまま）の正負テスト。
14. `tests/test_codex_review_plan.py` — **既存 16 行判定表は削除・縮小禁止**（キー存在時の意味論不変の
    判定装置 — Sol R4-7）。追加: (a) `available:false/reason:not-configured` → not-active、
    (b) キー不在＋`--available true --available-reason ok`（旧 record 相当）→ not-active/not-configured
    （Sol R1-1）、(c) probe 実 stdout → planner 一体テストを **full mode・baseline 無効に固定**し
    完全 config 4 構成（`{"codexReview":{"required":true}}`／`{"codexReview":{"enabled":false,
    "required":true}}`／`{"codexReview":{}}`／`{}`）の `action/state/reason/promptVariant` を完全一致で
    検査（Sol R2-4・R3-5）。
15. **新規 `tests/test_v015_contracts.py`** — (a) config-schema :35-36 の key-gated 文言、(b) init OMIT
    文言 2 箇所、(c) audit SKILL の enum 2 箇所・ax の Phase-5 not-configured 行 1 本・4-way reason 明記句
    （codex 側の 💡 行と優先順位 assert は Opus C1 採用により**作らない**）、**resume 再 probe 規則の配線**
    （resume 節に ax-probe.sh／codex-probe.sh の再実行・再記録・unknown 強制の指示が存在し、旧
    「restore … from rebind」文言が当該 2 seam に残っていないこと — Sol R4-6・Opus B1/B2）、
    (d) ADOPTION §7 v0.15.0 固定文 en 4＋ja 4（§5.2-8 の事前定義文字列が期待値）、
    (e) **残骸 grep ゲート**（Opus B3/B4・O2-1 反映）: 走査単位は**「表の 1 行／リストの 1 項目
    （bullet 行＋その継続行）／それ以外は空行段落」のうち最小のもの**とし、単位内に seam トークン
    （webExtract/ax/codexReview/codex）を含む単位の旧文言（`absent key … enabled by default`・
    `auto-used`・`conditional-force`・`自動使用` 等）を検出する。空行段落一律は不可（Opus O2-1 実測:
    config-schema の表 34 行・ADOPTION の表・init の bullet 群・README のサブ bullet 群が 1 段落に
    融合し、保持必須の indexing/contextMode/mdq 記述 5 箇所が false positive になる）。この粒度で
    ADOPTION.md:115/:124（散文段落の継続行）・init SKILL.md:135（webExtract bullet の継続行）は捕捉
    され、真陽性の検出力は落ちない（Opus O3 実測: 最小単位走査で保持テキストの誤検出 0・真陽性は全て
    捕捉）。allowlist は**段落 literal 指定の 2 件のみ**:
    「`**v0.14.0 behavior changes:**` で始まる段落」「`**v0.14.0 の挙動変更:**` で始まる段落」
    （**ファイル単位 allowlist は禁止**）。対象は tasks/ と歴史契約テスト（test_v014_contracts.py の
    固定文配列）を除く全 tracked ファイル。test_v014_contracts.py:135 のヒットは item 16 の seam
    ループ縮小（4→indexing/contextMode の 2）で自然解消するため追加 allowlist 不要。完全性検査は
    「走査件数 > 0 かつ既知の代表 path（docs/ADOPTION.md・skills/init/SKILL.md・README.md）を含む」。
16. 既存契約テストの現行系のみ更新（歴史固定は保存 — Sol R1-7）:
    - `tests/test_v014_contracts.py` — §7 v0.14.0 歴史ブロック（:23-48）不変。現行断言を v0.15 実態へ
      更新または test_v015 へ移設（行番号は Opus O2-2 の実測で確定）: :50-70 enum・:135-142 schema 文言
      （seam ループを indexing/contextMode の 2 seam へ縮小）・**:226**（`"rebind" map is authoritative`）・
      **:227**（`Phase 4 may restore any missing operational availability, reason, or binary variables
      from rebind`）・**:228**（`a failed read makes all seven status lines unknown; neither case changes
      the verdict`）。**:225 の `probe-record.py also receives --evidence "$EVIDENCE" …` は今版と無関係の
      EVIDENCE 所有権契約であり変更禁止**。:253-264 の Phase-5 優先順位文断言は**優先順位を変えないため
      不変**（Opus C1）。
    - `tests/test_v0132_contracts.py` — :239-244 reason 集合へ `not-configured` 追加、:300-306 の件数
      3→5 ＋**段落 seam 名一致断言を 5 seam 集合へ**（Sol R3-8）。
    - `tests/test_v013_contracts.py` — release surface `{"0.15.0"}`（:182-201）、refresh 許可 regex へ
      v0.15.0 追加（:203-225）。
    - `tests/test_scaffold.py` — 版・stamp・engine-shas 期待を 0.15.0 へ。
17. `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/release-handoff.sh` — 前版を雛形に v0.15.0 版
    （tag `docaudit--v0.15.0`・Release title/notes・`Closes #56`・skills-dir 同期）。
    **handoff 前提条件**（Sol R5-6）: §9 の新 Issue が起票済みで OPEN であり、その番号が Release notes
    から参照されることを script が検証（未起票なら停止）。
18. `tests/test_release_handoff.py` — **従来どおり in-place で v0.15 へ再ターゲット**（Opus C2 採用:
    git 履歴実測で 5 世代連続の in-place 再ターゲットが確立運用。rev.6 までの「歴史保存＋新ファイル複製」
    方針は撤回 — 450 行規模のテストをリリースごとに増殖させない）。docstring・`HANDOFF` path・tag・
    title・notes・close 対象を v0.15 値へ更新し、**既存の安全停止/境界 method（:289-446）を全数維持**
    （Sol R5-5 は再ターゲットで自動的に満たされる）。追加ケース: **#59 非 close 負契約**（close call
    集合厳密 `{"56"}`・#59 OPEN 維持 — Sol R2-6）・**Release notes 内 close directive 集合も厳密
    `{"56"}`＋#59 継続文の固定**（Sol R4-13）・**新 Issue 前提条件の正負**（Sol R5-6）。

## 6. 完了条件（機械判定）

1. フルスイート green: `python3 -m unittest discover -s tests` が OK・skip 0。ベースライン **609 tests**
   以上、増分内訳を REVIEW.md へ実数記録。
2. 判定表の実数: ax probe **≥ 23 ID**・codex probe **≥ 23 ID**（absent/empty/省略・値欠落・不存在・壊れ/
   disabled/invalid×2/bin 系/not-installed/ok）、呼出し回数固定 **≥ 6**、probe-record **≥ 12**
   （受理 2・mutation 拒否 7・未知フィールド拒否 1・上書き正負 2）、codex-review-plan **既存 16 行維持＋
   追加 ≥ 7**（not-configured 2・旧 record 迂回 1・full-mode 一体 4）、ASCII/1 行 **≥ 2**、
   resume 再 probe 配線 **≥ 2 本**（boss 検収で「同一 probe stdout から運用 3 値を束縛・記録し consumer
   より前に置く」配線順を直接確認 — Sol R5-7）、probe-record 上書きは**既存 upsert 不変＋置換/保持の
   正テスト ≥ 2**、handoff は **test_release_handoff.py の既存 method 全数維持（v0.15 再ターゲット）＋
   追加 ≥ 5**（#59 負契約 2・notes directive 1・新 Issue 前提条件 正負 2）。各テストは対象スクリプトを
   実起動して stdout/exit code を比較（常時 PASS の偽陽性検査は差し戻し）。boss は検収時に §6-2 の下限値が
   既存テスト表の実件数を下回っていないかも確認する（Opus 未検証項目）。
3. 残骸 grep ゲート: 最小単位（表行／リスト項目／散文段落）走査で allowlist（§7 歴史ブロック 2 段落
   literal）外 0 件、走査件数 > 0 かつ代表 path 3 件を含むこと、実数出力。indexing/contextMode/mdq の
   保持テキスト 5 箇所（Opus O2-1 の表）が発火しないことを負テストで固定。
4. 版整合: release surface `{"0.15.0"}`、test_scaffold green（engine-shas 0.15.0 実測 SHA）。
5. スコープ検査: `git diff --name-only <base>..HEAD` が §7 許可一覧の部分集合（boss 照合）。
6. 手順 5 の最終 `codex exec review`（Sol high）で blocking 指摘 0（P2 以下は boss 裁定）。

## 7. 変更範囲

**許可（この一覧のみ）**:
- `skills/audit/scripts/ax-probe.sh`, `skills/audit/scripts/codex-probe.sh`,
  `skills/audit/scripts/probe-record.py`, `skills/audit/scripts/codex-review-plan.py`
- `skills/audit/SKILL.md`, `skills/audit/references/config-schema.md`, `skills/init/SKILL.md`
- `docs/ADOPTION.md`, `docs/ADOPTION.ja.md`, `README.md`, `.claude-plugin/plugin.json`,
  `skills/audit/references/engine-shas.json`
- `tests/test_ax_probe.py`, `tests/test_codex_probe.py`, `tests/test_probe_record.py`,
  `tests/test_codex_review_plan.py`, `tests/test_v015_contracts.py`（新規）,
  `tests/test_release_handoff.py`（in-place 再ターゲット — Opus C2）, `tests/test_v014_contracts.py`,
  `tests/test_v0132_contracts.py`, `tests/test_v013_contracts.py`, `tests/test_scaffold.py`
- `tasks/route/2026-08-29-issue-56-stage2-v0.15.0/**`

**禁止**: 上記以外の全ファイル。特に `decide-verdict.py`・`start-run.py`・`open-run.py`・
`workflow-template.js`・graph 系 3 probe・`mdq-index.sh`・config-schema.md :33-34。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 8. 検証コマンド一式

```
python3 -m unittest discover -s tests

python3 -m unittest tests.test_ax_probe tests.test_codex_probe tests.test_probe_record \
  tests.test_codex_review_plan tests.test_v015_contracts tests.test_release_handoff \
  tests.test_v014_contracts tests.test_v0132_contracts tests.test_v013_contracts tests.test_scaffold -v

# 残骸スイープ＝機械ゲートの直接実行（手動 grep は使わない — Sol R2-7）
python3 -m unittest tests.test_v015_contracts -v

git diff --name-only main...HEAD   # boss 照合
```

route-close: 本 repo は `.claude/doc-audit.json` 未導入のため `/docaudit:audit` は不実行。代替＝機械ゲート
（フルスイート・契約テスト・残骸 grep）で「1 回で CONSISTENT 相当」を判定（LLM 消費ゼロ）。
出荷手順: PR（`Closes #56`）→ ユーザー merge → `release-handoff.sh`（tag・Release・#56 close・skills-dir 同期）。

## 9. 新 Issue 起票（ユーザー承認待ち — 本版では実装しない）

**題**: mid-run config tampering (TOCTOU) can steer seam probes/planner across ALL seams — pre-existing
since v0.13.2 key-gating; needs a sealed-config verification design of the docaudit-history trust class.
**内容**: R2-1（planner 直前のキー追加→復元）・R4-2（ax 経由の verifier prompt 影響 — ax は厳密には
verdict 非影響ではない: workflow-template.js:122,153,156）・R4-3（Phase-0 probe が改竄 bin を実行）・
R4-4（taint 記録の一元化）を証拠として記載。graph 系 3 seam・mdq も同じ露出を持つこと、部分対策は
新たな迂回路を生むため EVIDENCE 封印・gate barrier・taint 一元化を含む全 seam 一括設計が必要なこと、
#59（版跨ぎ禁止・封印クラス）と密接に関連することを明記。
**起票タイミング**: ユーザーが本 PLAN と併せて承認したら、worker 実装と並行して boss が起票し、番号を
REVIEW.md へ記録する。release-handoff は当該 Issue の存在・OPEN・Release notes 参照を前提条件として
検証する（未起票なら停止 — Sol R5-6）。
