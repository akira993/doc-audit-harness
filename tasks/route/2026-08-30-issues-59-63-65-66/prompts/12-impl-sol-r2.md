boss レビュー（差し戻し R2）。boss はフルスイート（697 OK）と CT-1/CT-2 の実数を自分で再実行して追認した。diff 全行精読と別レビュアーによるテスト/docs 検分の結果、以下を修正せよ。番号順に対応し、各項目に「対応内容／該当 file:line／検証方法」を報告に付けよ。作業ツリーは boss が `git add -A` でステージ済み（`git diff --cached` が現状）。git 操作はしない。

## A. 実装の欠陥
- **A-1 [Major]** `codex-review-plan.py:139` carry-forward の repo root に `os.getcwd()` を使っている。`--repo-root` を必須引数に追加し、`carry_forward(args.repo_root, ...)` に。SKILL.md :595 の call site に `--repo-root "$CLAUDE_PROJECT_DIR"` を付与。CT-6 に「cwd が repo 外でも実在判定が正しい」ケースを 1 本。
- **A-2 [Minor]** SKILL.md :389 の impact-supplement 行の `<config maxImpactedDocs, default 200>` `<config docGlobs, comma-joined>` `<config semanticSearch.minScore, default 0.4>` を、直前で束縛した `"$MAX_IMPACTED_DOCS"`、`DOC_GLOBS_JSON` の comma-join 結果、`"$SEMANTIC_MIN_SCORE"` に置換（プレースホルダを残さない）。
- **A-3 [Minor]** SKILL.md seal-run 分岐（:428-434 付近）「Any other non-zero exit → release」に、exit 7／`sealed-config-mismatch` は停止規約（`--taint-observed config --observed-by seal-run.py`）へ流し release しない旨を分岐内に明記。CT-3 に SKILL テキスト順序契約（停止規約の段落が seal-run の release 分岐より前に現れる、かつ seal-run 分岐内に exit 7 の除外がある）を assert する検査を追加。
- **A-4 [Minor]** `HARNESS_CONFIG_JSON` の getter（SKILL.md Phase 0.5）の `--default '{}'` を `--default null` に変え、`null` のとき `HARNESS_STATE=unset` と明記（キー欠落と空 object を区別する）。

## B. PLAN 外の契約変更（boss 承認済み・文書を実装に合わせる）
- **B-1 [Major]** 直接起動した probe（mdq-index.sh・ax/codex/codegraph/graphify/cocoindex-probe.sh）で config が不正 JSON／欠落／`--config` 省略のとき、旧契約は exit 0＋`invalid-config` JSON だったが、現実装は `sealed_config.py` 経由で exit 2（不一致は 7）。boss はこの fail-closed を**承認**する（run 内では open-run が config を object として検証済みで、到達し得るのは改竄＝7 のみ）。ただし文書が旧挙動のまま: SKILL.md :221／:239／:263 の "Always exits 0; any failure degrades to ..." を「`--expect-config-sha` の入力エラー（exit 2）と封印不一致（exit 7）を除き exit 0」に是正し、`docs/ADOPTION.md:278` と `docs/ADOPTION.ja.md` の対応文（"a directly invoked probe with an unreadable or absent config now reports invalid-config"）を v0.16.0 の挙動（exit 2、JSON 無し）に改訂。書き換えた既存テスト（`test_*_probe.py`・`test_mdq_index.py` の `..._stops`）はそのまま。
- **B-2 [Major]** `docs/ADOPTION.md:254-257` と `docs/ADOPTION.ja.md:230-234` の「`*.py` だけをコピー」する部分コピー手順を削除し、全 tree 同期のみを残す（同文書の新段落 "partial copies are unsupported" と矛盾している。PLAN S7 の明示要求）。

## C. テストの欠落（PLAN S14 が列挙した検査で未実装のもの）
- **C-1 [Major] CT-5**: (a) 保持 5／上限 6＋source guard: 同一 digest の full run を 7 回連続で流し、各 run 後に `phase4Runs` が ≤6 件・source record（digest の異なる最新）が残り続け・7 回目の `carryForwardSha` が 2 回目以降と同一であることを assert。(b) 501 件の codex-review findings → record `truncated:true`、flip 比較スキップ、warning。(c) gate reader の `phase4Runs` 退化: `entries` は valid・`phase4Runs` 不正の history で gate が隔離せず、warning を出し、新 record から `phase4Runs` を再構築する。(d) round-trip 失敗時に record を追加せず warning（parser の上限を monkeypatch 等で人工的に破る）。(e) writer→parser 最大境界: 500 件 × 直列化 512 bytes（非 ASCII 6 倍膨張形）の record が往復で valid、513 KiB／全体 1 MiB 超で退化。(f) `unresolvedFileCount` が record と warning に反映される。(g) flip 4 キーのうち `contractVersion` 相違・`configSha` 相違でそれぞれ 0。
- **C-2 [Major] CT-4c**: 以下の行を追加（table-driven 化は任意だが、各行を独立に assert）: 二重障害（state dir と lock を read-only 化して last_run も holder も書けない）→ exit 3・stderr `quarantine-marker-unpersisted`・release なし／last_run が非 object（`[]`）・marker 非 bool（`"yes"`）→ いずれも `last-run-unreadable`／`--release` での holder marker マージ／flock を他プロセスが保持している状態での `--release`・通常 open（何も変えず exit）／通常 open（lock 存在・flock 非保持）で history も不変。
- **C-3 [Major] CT-3b**: 非所有 4 ケース目「flock を他プロセス（別プロセスまたは別 fd）が保持」で `--taint-observed` が無書き込み exit 3。
- **C-4 [Major] CT-3**: gate 実行中に子 `change-set-sha.py` が読む config を差し替える（CT-2b の sitecustomize 機構を decide-verdict に向ける）→ `config-changed` taint＋`configAcceptanceRequired:true`。
- **C-5 [Minor] CT-6**: codex-review-plan 経路の連鎖「sha 不一致 exit 7 → `--taint-observed history --observed-by codex-review-plan.py` → 隔離 → 次 run が cold start（`carryForward:null`）」を 1 本。
- **C-6 [Minor] CT-7**: 5 文書連結ではなく **ファイルごと**に必須 token を assert（en/ja/README/config-schema/SKILL のどれに何が要るかを表で固定）。`test_v014_contracts.py:133-142` の日英非対称（ja 側に data-only carry-forward の条件が無い）を揃える。
- **C-7 [Minor] CT-2**: mismatch exit の 7 ハードコードを registry の列から取る。

## 報告
完了条件・検証コマンド一式は 08-impl-sol.md のまま。最後にフルスイートを 1 回実行し `Ran N tests` と `OK` を verbatim で。A〜C の各項目について対応内容と検証を列挙。PLAN に無い判断が新たに必要なら停止して報告。
