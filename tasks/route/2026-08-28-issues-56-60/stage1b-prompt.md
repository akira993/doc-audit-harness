あなたは docaudit プラグイン（このリポジトリ、branch `fix/v0.14.0-issues-56-60`）の実装担当（worker）である。boss（Fable）が確定した計画
`tasks/route/2026-08-28-issues-56-60/PLAN.md`（rev.8）の **Stage S1b（#57）** を実装せよ。S1a は commit 済み（`git log` で確認）。PLAN.md 全文を最初に読み、§0-6 と §6 の (10)(11)、§7、§8 に従う。
不明点は推測で埋めず、PLAN の該当箇所を引用して報告せよ。**PLAN.md・REVIEW.md・allowlist.txt・baseline-hashes.txt・59-design-note.md・scope-check.py は読むだけで変更しない。** 既存ファイルの上書き・新規作成は本プロンプトで包括承認する（再確認不要）。単独で作業し、collab／サブエージェントは使わない。git commit は行わない。

## S1b の範囲（PLAN §0-6 を正とする。以下は要点）
1. 新規 `skills/audit/scripts/probe-record.py`:
   - 共通引数 `--repo-root --runid --evidence`。repo-root は最初に `os.path.realpath`。その fd から `.claude`→`state`→`docaudit-run`→`<RUNID>` を成分ごとに `os.open(name, O_RDONLY|O_DIRECTORY|O_NOFOLLOW, dir_fd=parent)` で辿る（`open-run.py:38-46` 参照）。RUNID は `start-run.py:17` の正規表現。`EVIDENCE.runDir` の realpath 一致（不一致 exit 2）。
   - `--seam <name> --stdin`: 10 seam 固定集合 `{indexing, mdqHealth, mdqDegrade, contextMode, webExtract, codexReview, codexReviewState, symbolGraph, docGraph, semanticSearch}`。seam 別 schema（availability/reason 判別の分岐別 union、必須キーと型を検査、余分キーは許容）は §0-6 の表のとおり。`mdqHealth` は `mdq-health.py` の実出力 5 キー `{files,chunks,searchSmoke,healthy,status}`。
     `codexReviewState.state ∈ {completed,execution-failed,ref-invalid,skipped-full-run,not-active,phase4-not-required}`。graph 3 seam は各 probe script（`codegraph-probe.sh`／`graphify-probe.sh`／`cocoindex-probe.sh`）の分岐から表を起こし、reason 集合は SKILL.md の列挙と一致させる。
     読み `O_RDONLY|O_NOFOLLOW`＋`S_ISREG`、一時ファイル `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` 0o600＋fsync、`os.replace(src_dir_fd=fd, dst_dir_fd=fd)`、失敗時 `os.unlink(dir_fd=fd)`。違反 exit 2・ファイル不変。stdout に保存後の全体 `{"schemaVersion":1,"seams":{...}}`。
   - `--read`: 同じ検査で読み `{"schemaVersion":1,"seams":{...},"rebind":{...}}`。`rebind` は 7 行（`mdq, context-mode, ax, codex-review, symbol-graph, doc-graph, semantic-search`）の正規化済み値（§0-6 の各キー）。完全性条件: mdq は `indexing`＋`mdqDegrade`、`indexing.mdqAvailable:true` なら `mdqHealth` も；他は各 seam 1 件；`codexReviewState` は完全性に算入せず `reviewState` のみ供給（未記録なら null）。
     `callerCodexHomeDisplay` は生文字列を 200 文字に切ってから `json.dumps(v)[1:-1]` でエスケープ（1 行保証）、`null` → `(null)`。不在ファイル → 7 行 `unknown`（値 null）exit 0。破損／schema 違反 → exit 2。
2. `skills/audit/SKILL.md`:
   - Phase 0: 各 probe 直後に記録行 9 本（`MDQ_PROBE_JSON`／`AX_PROBE_JSON` を新設して捕捉。mdqHealth は `mdq-health.py` の JSON verbatim、mdqDegrade は確認ゲート評価後に `{"degrade":"<MDQ_DEGRADE>"}`、contextMode は合成 `{"contextModeAvailable":…,"contextModeHealthy":…,"status":"…"}`、codex／3 graph は既存 `*_PROBE_JSON`）。
     形: `printf '%s' "$X_PROBE_JSON" | python3 "$SD/scripts/probe-record.py" --repo-root "$CLAUDE_PROJECT_DIR" --runid "$RUNID" --evidence "$EVIDENCE" --seam <name> --stdin >/dev/null || echo "⚠ probe-record: <name> not recorded [non-blocking]"`（fail-open）。
   - Phase 3（:405-412 付近）: mdq 再索引後に `indexing`／`mdqHealth` を再記録。
   - Phase 4: `write-evidence.py --name phase4` で `EVIDENCE` を置換した**直後**に `codexReviewState` を `{"state":"$CODEX_REVIEW_STATE"}` で記録。`SEALED_PHASE4_REQUIRED=false` の分岐では `{"state":"phase4-not-required"}` を記録。
   - SKILL.md:36-42 の EVIDENCE 置換規約段落に固定文 `probe-record.py also receives --evidence "$EVIDENCE" for run-dir validation only; it is not an evidence producer and its stdout MUST NOT replace EVIDENCE.`
   - 再開規約（:41-56）に固定段落（§0-6 の英文を verbatim）＋運用変数復元の 1 文（Opus N5）。
   - Phase 5: 状態行生成の前に `PROBE_REBIND="$(python3 "$SD/scripts/probe-record.py" --repo-root … --runid … --evidence … --read)"` を呼び（失敗時は 7 行 unknown）、7 行の入力を `rebind` から取る（唯一の例外: mdq 行の Phase-3 refresh 失敗 `<detail>` は会話変数、再開後は省く）。`CODEX_REVIEW_STATE` は `rebind.codex-review.reviewState` から再束縛し、既存の 4-way リテラル `CODEX_REVIEW_STATE=…` 分岐は**そのまま温存**。
     追加枝: `reviewState` null → `⚠ codex-review: state unknown after resume [non-blocking]`；`phase4-not-required` → `💡 codex-review: not run (phase 4 not required)`；probe 記録欠損かつ reviewState 非 null → 4-way 行＋接尾辞 ` (caller info unknown after resume)`。S1a が書いた caller 接尾辞の 3 値は `rebind.codex-review` の `callerCodexHomeDisplay`／`callerCodexHomeSource`／`callerAuthFile` を指すよう整合させる。
     6 行の unknown 文言: `⚠ mdq: state unknown after resume [non-blocking]`／`⚠ context-mode: …`／`⚠ ax: …`／`⚠ symbol-graph: …`／`⚠ doc-graph: …`／`⚠ semantic-search: …`（7 行の順序は既存どおり）。fail-open の固定文（write 失敗は警告続行、read 失敗は全行 unknown、verdict 不変）。
   - Guardrails に 1 句（`$RUN_DIR/phase0-probes.json` は probe の生出力の保存で表示専用。手書き evidence の禁止とは別。gate は読まない）。
   - **既存契約テスト（`test_v013_contracts.py`／`test_v0132_contracts.py`／`test_wp12_contracts.py`／`test_harness_contract.py`／S1a の `test_v014_contracts.py`）が固定する文言・順序・出現回数を壊さない。**
3. `skills/audit/references/config-schema.md` の run dir 節に `phase0-probes.json`（表示専用・schemaVersion 1・gate 不読）を追記。
4. テスト `tests/test_probe_record.py`（新規、固定 ID ≥ 24、`len(CASES)` と ID 集合を assert）: §0-6 の列挙（upsert／上書き／原子性／固定 seam 集合／分岐別 schema 違反 10 seam 各 1＋矛盾例／余分キー許容／`mdq-health.py` の実 stdout の write→read（probe-error 分岐は `--bin /nonexistent` で実行取得、ok 分岐は fixture）／非 object stdin／`--read` 不在→全 unknown／破損→exit 2／`rebind` 値の完全一致（完全・`mdqHealth` 欠損×available 真偽・部分欠損・`codexReviewState` 有無）／display の 1 行性と 199 文字＋改行の境界／中間 symlink 拒否／run dir symlink 拒否／ファイル symlink 拒否／runDir 不一致／RUNID 不正／symlink repo-root 受理）。
   `tests/test_v014_contracts.py` に DoD (11) の契約テストを追記。

## 完了条件（PLAN §6 (10)(11)＋共通）
- (10) `tests/test_probe_record.py`（固定 ID ≥ 24）。
- (11) `test_v014_contracts.py`: Phase 0 に 9 seam 記録行＋Phase 4 に `codexReviewState` 記録行（not-required 分岐含む）、Phase 3 再記録 2 行、Phase 5 の `--read` 行、再開段落固定文（`"rebind" map is authoritative` を含む）、6 unknown 文言、`CODEX_REVIEW_STATE=` 既存リテラル 4 つの温存（`test_v013_contracts.py::test_e` green）、`phase4-not-required` 枝の固定文、EVIDENCE 規約段落の O8 固定文、再開段落の運用変数復元 1 文、fail-open 固定文、Guardrails 1 句、SKILL に表示用 python -c 式が無い（`grep -c 'callerCodexHome"\]' skills/audit/SKILL.md` = 0）、`grep -c phase0-probes skills/audit/scripts/decide-verdict.py` = 0。
- (15) フルスイート green・skip 0（`-v` 出力に ` ... skipped` 0 行）。`Ran N` 実数報告。
- (16) `py_compile skills/audit/scripts/probe-record.py`。
- (18) 禁止ファイルに差分無し。

## 変更範囲（PLAN §7 の S1b 分）
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/probe-record.py(新)`、`skills/audit/references/config-schema.md`、`tests/test_probe_record.py(新)`、`tests/test_v014_contracts.py`。
**禁止**: 上記以外すべて（特に `decide-verdict.py`、`start-run.py`、`write-evidence.py`、`open-run.py`、`mdq-health.py`、3 graph probe、S1a の変更ファイル `import-audit-scope.py`／`mdq-index.sh`／`ax-probe.sh`／`codex-probe.sh`、ADOPTION、`.claude/**`、`tasks/**`）。
**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。**

## 検証コマンド一式（すべて実行し、要点と exit code を報告）
```
python3 -m unittest discover -s tests -t . -v > /tmp/s1b-full.log 2>&1; tail -3 /tmp/s1b-full.log; test "$(grep -c ' \.\.\. skipped' /tmp/s1b-full.log)" -eq 0 || echo SKIP-FOUND
python3 -m unittest -v tests.test_probe_record tests.test_v014_contracts tests.test_v013_contracts tests.test_v0132_contracts tests.test_wp12_contracts tests.test_harness_contract
python3 -m py_compile skills/audit/scripts/probe-record.py
test "$(grep -c phase0-probes skills/audit/scripts/decide-verdict.py)" -eq 0 || echo GATE-READS-PROBES
test "$(grep -c 'callerCodexHome"\]' skills/audit/SKILL.md)" -eq 0 || echo DISPLAY-EXPR-FOUND
git diff --quiet HEAD -- skills/audit/scripts/decide-verdict.py skills/audit/scripts/start-run.py skills/audit/scripts/write-evidence.py skills/audit/scripts/open-run.py skills/audit/scripts/mdq-health.py skills/audit/scripts/import-audit-scope.py skills/audit/scripts/mdq-index.sh skills/audit/scripts/ax-probe.sh skills/audit/scripts/codex-probe.sh docs && echo forbidden-clean
git status --short
```

## 報告形式
Markdown で: (1) 変更ファイルと要点、(2) DoD ごとの固定テスト名と `Ran N`、(3) 検証コマンドの結果（失敗は出力ごと）、(4) PLAN との乖離・許可外変更が必要だった点・未実施（無ければ「無し」）。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
