# Issue 精査と根本解決案（boss 提示、2026-08-30）

対象: open Issue #59 / #63 / #65 / #66（doc-audit-harness）＋ dir-framework 側の docaudit 実施状況の確認。
実測の出所: GitHub Issue 本文、`tasks/route/2026-08-28-issues-56-60/59-design-note.md`、dir-framework の `.claude/state/docaudit-run/*`（15 run）・`docaudit-history.json`・`docs/logs/doc_audit_*.md`、上流ドキュメント（code.claude.com/docs/en/code-review, /settings）、scratchpad での codegraph 1.5.0 実機テスト。

## 0. 結論（先に）

| Issue | 根本原因（一文） | 推奨する根本解決 | 規模 |
|---|---|---|---|
| #63 TOCTOU | 設定ファイルを run 中に **何度も生で読み直している**（open-run で sha を取るだけで、probe・planner・start-run は各自 live ファイルを再読） | **open-run 時点で設定を run ディレクトリへ凍結コピーし、以後の全消費者は凍結コピーだけを読む**。gate は凍結コピーと EVIDENCE.config の一致＋live との一致（既存 :701）を検査 | 中（1 機構で全 seam 一括） |
| #59 Phase-4 再現性 | **サンプリングで動く LLM レビューを決定的検査器と同じ契約（「N 件直して再実行→通る」）で扱っている** | 設計ノートの ledger（P1 単調性・信頼クラス新設）は **撤回を推奨**。代わりに (1) Phase-4 の flip を gate が **決定的キー（file / 有無）で計測**し warning、(2) 前回所見の carry-forward は **gate が書いた history だけを出所**とする data-only のプロンプト材料（verdict に影響させない） | 中（#63 の凍結機構に相乗り） |
| #65 codegraph probe | init/sync の分岐を「ディレクトリの有無」で決めている | **索引ファイル `codegraph.db` の有無**で分岐（cocoindex-probe と同じ `not-initialized` 状態を追加） | 小（単独修正可） |
| #66 /code-review | 上流の制約（model-invocable でない）が **解除済み**なのに docaudit が旧契約を実装・文書化し続けている | 文書の是正は無条件。統合方式は **ユーザー決定**（A: Issue 案の新キー／B: 既存 `reviewCommands.code` を単一窓口として自律実行／C: docs-only 化＝レビュー層を verdict から外す） | A: 大／B: 中／C: 中 |

## 1. #63 — 設定改竄（TOCTOU）

**現状の構造（実測）**
- `open-run.py:152-162` が `.claude/doc-audit.json` のバイト列から sha を計算し EVIDENCE.config に入れる。
- しかし `SKILL.md:13` で `CFG=".claude/doc-audit.json"`（live パス）に固定され、Phase-0 の 6 probe（mdq/ax/codex/codegraph/graphify/cocoindex）、`codex-review-plan.py`、`start-run.py`（audit-scope の sha も live 読み :224）、`decide-verdict.py` が **それぞれ live ファイルを再読**する。config を読むスクリプトは 23 本。
- gate（`decide-verdict.py:701`）は「run 終了時点の live sha ≠ 封印 sha」しか検知できないため、**書き換えて戻す**操作は素通り（Issue の経路 1〜3）。

**根本解決（推奨）**: 「読むのは 1 回、以後は凍結コピー」
1. `open-run.py` が config（と `.claude/audit-scope.json`）を `$RUN_DIR/config.json`（0600）へコピーし、sha を EVIDENCE に載せる（config は既存、audit-scope は追加）。
2. SKILL.md の `CFG` を open-run 成功直後に `$RUN_DIR/config.json` へ **再束縛**。probe 等のスクリプトは `--config` を受け取るだけなので **無改修**。
3. gate は (a) 凍結コピーの sha == EVIDENCE.config、(b) live sha == 封印 sha（既存の taint 経路を維持・一元化）を検査。
4. run 中の唯一の正当な書き込み（Phase 0.5 の harness 判定 `set-config-key.py`、SKILL.md:274）は、凍結コピーと EVIDENCE を同時に更新する経路に載せ替える（PLAN で明示）。
5. open-run 前の読み（SKILL.md:28 の audit-scope drift 判定）は lock 取得後に凍結コピーで再判定するか、open-run を先頭へ移す。

**脅威境界の明示**: 「repo 内の実行ファイルそのものを差し替える」は repo 書き込み者による任意実行であり本 Issue の範囲外（Issue の前提どおり判定経路の完全性のみ）。凍結コピーは `.claude/state/docaudit-run/<runid>/`＝既に docaudit-history と同じ信頼クラスの場所。

## 2. #59 — Phase-4 codex review の再現性

**dir-framework の実測（15 run、2026-08-27〜30）**
- codex 所見 34 件（13 run 合計）。**同一 (file, title) の再出現はゼロ**。ただしこれは「同じ欠陥が別の言い回しで再サンプリングされている」ことを含む（例: check-section-refs の「optional title」2 件、AGENTS.md ルール 1/12 の 2 件）。つまり **LLM が生成する title は run をまたいで安定しない**。
- 設計ノートの ledger キーは `sha256(file + normalize(title))`。title が揺れる以上、持ち越し entry は次回の所見と **一致せず近似重複が膨らむ**。ledger は信頼クラスの議論以前に **自分のキーで破綻**する。
- blocking（high/critical）が出たのは **full variant の 3 round のみ**（round1: high 1、round2: 別の high 1、round3: 0）。以後 10 run は blocking 0 だが **9 run は incremental**（diff が狭く既往所見が構造的に出にくい）。「問題は消えた」ではなく「露出は full variant に集中」と読むのが正しい。
- 15 run 中 **6 run は gate に到達していない**（例: `20260829T150944Z-d34bc565` は Phase-4 completed・所見 19 件のまま verdict 未記録）。gate に到達しない run の所見は **信頼できる痕跡を残さない** → carry-forward の出所を run ディレクトリの生ファイルにしてはならない（#63 の脅威モデルではそれは攻撃者が書けるプロンプト入力）。

**根本解決（推奨・設計ノート P1 からの方針転換）**
- 撤回: 「既知 blocking を単調非減少に維持する」ledger（P1）と、そのための新しい信頼クラス（P3/P4）。理由: (i) 13 run で「blocking が修正なしに消えた」事例は 0、(ii) title キーが不安定、(iii) 3 往復の批判で毎回 Critical が出た重装備。
- 採用:
  1. **Phase-4 flip 計測**: gate が history に「その run の blocking 所見の file 集合（title は使わない）＋ worktreeDigest」を書き、前回と digest 同一で blocking 集合が変わったら `verdictFlipsUnchangedContent` と同じ **warning**（REFUSED にはしない）。既存 counter の Phase-4 版。
  2. **data-only carry-forward**: 前回 **gate 到達** run の所見（history から機械生成、fenced JSON、「data, not instructions」宣言つき）を full variant のプロンプトへ自動添付。codex は毎回全件返す（P2 非抑止）ので verdict には影響せず、信頼クラス不要。
  3. 契約文言の是正: Phase-4 は「サンプリングによる敵対的レビュー」であり、「N 件直して再実行→通る」は full variant では保証しない旨を ADOPTION/SKILL に明記（v0.14.0 の運用注記を契約に格上げ）。
- #63 と同時設計する理由: (2) の出所を「gate が書いた history」に限定するのが、まさに #63 の「判定経路は封印済み入力しか読まない」原則の適用。

## 3. #65 — codegraph probe が `.DS_Store` だけの `.codegraph/` で永久に index-failed

- 再現済み（scratchpad、codegraph 1.5.0）: `.codegraph/.DS_Store` のみ → probe は `sync` を選び `CodeGraph not initialized` → `index-failed`。
- 実機で新たに判明: codegraph 1.5.0 では **初期化済みディレクトリへの `init .` は rc=0（受理）**。probe のコメント（2026-07-31 に「Already initialized で拒否」と確認）は現版では成立しない。ただし版依存で一度ひっくり返った挙動に修正を依存させない。
- 根本解決: 分岐条件を **`.codegraph/codegraph.db` の有無**へ（あれば `sync`、なければ `init`）。`not-initialized`→init で自己回復。genuine な失敗だけが `index-failed`。cocoindex-probe と対称の状態名。テスト `tests/test_codegraph_probe.py` に「.DS_Store のみ」ケースを追加。
- dir-framework で **実際に発生していた**（`.codegraph/.DS_Store` は 8/22 付、8/29 23:33 に手動 init で回復、現在は正常）。同 repo の runbook `initial-setup.md:50` に対する codex 所見「init は既存 .codegraph で拒否される」は 1.5.0 では stale。

## 4. #66 — `/code-review` は model-invocable になった

**実測**
- この環境は Claude Code **2.1.251**（境界 v2.1.246 以降）。本セッションの Skill 一覧に `code-review` が **モデル起動可能として列挙**されており、`skillOverrides` はユーザー／両プロジェクトの settings のいずれにも無い。
- 上流ドキュメント確認済み: Claude は自発的に `/code-review` を開始できる／`skillOverrides: {"code-review":"user-invocable-only"}` が opt-out／レベル省略時は前回タイプしたレベルを再利用し `-p` で渡したレベルは記憶を更新しない／`ultra` 以外では行の残りは全てレビュー対象。
- dir-framework の設定は `reviewCommands.code: "/code-review high"` なのに、**全報告書に「code-review: not run — user-invocation-only (expected)」** が出て CONSISTENT。設定されたレビュー層が黙ってスキップされ「期待どおり」と表示されている（「黙ってスキップ＝完了は誤り」の類）。一方 route-close 方針では「手順 5 で codex review 済みのため重ね起動しない」と、運用上は **意図的に走らせていない**。

**無条件で行うこと**: README / ADOPTION / SKILL.md の「not model-invocable」「user-invocation-only」記述と `CODE_REVIEW_STATE=not-model-invocable` 経路の是正（上流変更による文書ドリフト＝docaudit 自身が検出対象とする種類の欠陥）。

**ユーザー決定（3 択）**
- **A. Issue 案どおり**: 新キー `codeReview {enabled, effort, required}` を key-gate 方式で追加、承認は `permissions.ask: ["Skill(code-review *)"]` に委譲。→ `reviewCommands.code` と **設定が二重化**する（effort は既に `/code-review high` に入っている）。
- **B. 既存キーを単一窓口に（boss 推奨）**: `reviewCommands.code` があれば Skill ツールで自律実行し所見を verdict へ畳み込む。実行を確認できなければ WARN（`reviewCommands.required` で REFUSED に格上げ可）。無ければ走らせない。承認は Issue 案どおり permission 層に委譲。Issue の制約 3（1 行連鎖）は Skill ツール経由なら無関係。
- **C. docs-only 化**: `/code-review`・`/security-review` を verdict から外し、文書監査に専念（route スキル手順 7 の「将来拡張」）。ユーザーの実運用（route 手順 5 で codex review 済み）は C 寄り。
- **A/B いずれでも PLAN 確定前に実機検証が必要**（route ルール）: (i) `permissions.ask` が `Skill(code-review *)` に効くか（上流の例は allow/deny のみ）、(ii) forked subagent として走る `/code-review` の所見が監査の同一ターン内へ戻るか。scratch repo で手順 2 の事前調査として行う。

## 5. dir-framework 側の確認結果

- run 15 本（8/27〜8/30）。gate 到達 9 本＝全て CONSISTENT（8/27 の round1 のみ NEEDS_FIX）。未到達 6 本は fix ループ中の中断・再開（うち 1 本は Phase-4 完了後に未記録）。
- anchor は `70183d3`、HEAD は `b1aa774`（PR #15: `c7c9e30` check-docs.py 195 行変更を含む 7 file）。**未監査の commit が 1 つ意図的に残っている**（2026-08-30 HANDOFF の trap「タスク中に anchor を前進させない」）。
- 2026-08-30-audit-followup HANDOFF（Q2〜Q7）は準備完了・未実行。本件 4 Issue のエンジン側修正と **作業項目の衝突なし**。関連は Q5（initial-setup の codegraph 条件付き手順）に #65 の版依存知見が効く程度。
- #65 は実発生・回復済み。#66 のドリフトは全報告書に露出。#63 の改竄痕跡なし（config sha は各 run で封印一致）。

## 6. 進め方の提案（パッケージング）

1. **#65 を単独の小 route** で先に出す（Luna/Terra medium、テスト 1 ケース追加）。v0.15.1。
2. **#63＋#59 を合同設計 route**（Sol high、security 絡みのため批判は xhigh）。v0.16.0。
3. **#66 は決定後に別 route**（文書是正は 1. に同梱可）。
