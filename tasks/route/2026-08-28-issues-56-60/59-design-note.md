# #59 設計ノート — Phase-4 codex review の既知所見 ledger（v0.14.0 では見送り、専用 route の起点）

作成: 2026-08-28（route `2026-08-28-issues-56-60`、Sol R1〜R3・advisor の結論）。本版で出荷したのは Issue #59 の最小案（運用注記）のみ。

## 見送りの理由（1 文）
「既知 blocking 所見を決定論的に維持する」機構は、その時点で **verdict に影響する永続状態**であり、`docaudit-history.json`／anchor／config と同じ信頼クラス
（open-run 時点の封印・gate barrier での再確認・保存のトランザクション・汚染時の隔離/復元・旧新 engine 混在の拒否）を要する。3 往復の計画批判で毎回新規 Critical が出た一方、
他 4 Issue は収束したため、独立タスクとして切り出す。

## 満たすべき性質（rev.3 で定義、rev.3 の規則では不成立と判定されたもの）
- P1 **単調性**: sealed `worktreeDigest`（および ledger 対象 file の contentSha 集合 — `digestExclude` 配下は digest に含まれない）が前回 run と同一なら、blocking な既知所見の集合は単調非減少。
- P2 **非抑止**: ledger は codex の所見を抑止しない（プロンプトは再検証依頼のみ。codex は毎回全所見を返す）。
- P3 **fail-closed**: 汚染・破損・実行中変更・封印前差し替えは REFUSED、かつ汚染 ledger は隔離（`.tainted-<runid>`）して次 run の正規入力にしない。
- P4 **単一 writer**: 永続書き込みは gate のみ。保存失敗は「次回 open を機械的に禁止する poison／回復 journal」を伴う（warning だけでは P1 が破れる）。

## Sol の反例（設計が必ず通すべき時系列テスト）
1. state≠completed（`execution-failed`、`required:false`）の run で既知 blocking を fold しない → 同一 digest で CONSISTENT（R3-1）。**carried blocking は codex state に関係なく常に fold**。
2. nested `codexReview.result.findings` に新規 high、top-level `findings` は空 → gate が見ない（R2-2）。**gate は nested result を authoritative に判定し、転記不一致は REFUSED**。
3. key 化できない blocking（`./docs/a.md` 等 `validate_repo_path` 不合格）が当該 run 限りで消える（R3-2）。**completed result の blocking が key 化不能なら REFUSED**。
4. 同一 key の findings に critical と low（R2-4）。**最大 severity へ決定論的に集約**。
5. `digestExclude` 配下の file だけ変更 → digest 同一のまま contentSha 不一致で drop（R3-3）。**P1 の比較入力に対象 file の contentSha 集合を含める**。
6. prompt 50 件 batch: 未掲載 key の `resolved` を受理／未掲載 entry の `lastDigest` を更新（R2-8）。**gate が `listedKeys` と `lastReviewedDigest` を管理し、未掲載は解決対象外・review 済み digest を更新しない**。
7. `full` 由来の所見を狭い `diff` review が `resolved`（R2-7）。**basis 遷移表（full→diff／diff→full／diff→diff）を gate 規則に**。
8. 対象 file が変わると明示 resolved なしで drop（R2-7）。ADOPTION の「worktree が変わり、かつ resolved」と矛盾しないよう文言か規則を揃える。
9. open-run 後・start-run 前に verifier が schema-valid な空 ledger に差し替え → start-run がそれを封印（R1-3）。**封印は open-run（lock 取得）時点・EVIDENCE に**。
10. `atomic(ledger)` だけ失敗 → 新規 high が永続化されず、次 run で省略されれば CONSISTENT（R1-2）。**transaction/poison**。
11. 旧 gate＋新 manifest（未知キー無視）で ledger 無しに判定（R3-5）。**in-flight run の版跨ぎ禁止（manifest に engine version、両方向の混在テスト）**。
12. `ledger_signature` を読み取り後に別 stat で取得 → inode 差替えを正規化（R3-4）。**同一 `O_NOFOLLOW` fd から `(raw, entries, signature)`**。
13. 中間 symlink（`.claude`／`state`）を `O_NOFOLLOW` が追跡（R1-11）。**repo fd から成分ごとに `O_DIRECTORY|O_NOFOLLOW`**。

## 解決（resolved）の意味論 — 未決
- モデル単独の `resolved` は prompt injection（title 経由）で削除を起動できるため不採用（R1-4）。候補: (a) 利用者承認（run 外の CLI `codex-ledger.py resolve --key`、または `.claude/state` の手動編集＝次 run で再封印）、(b) モデル外の検証結果（対象 file の変更＋Phase-3 verifier の PASS 等）。
- `lastDigest != worktreeDigest` 条件は「同一コーパスでの flip 防止」には効くが注入防御にはならない。

## 構成案（rev.3 のうち再利用できる部分）
- 永続 `.claude/state/docaudit-codex-ledger.json`（`schemaVersion`）。`start-run.py` の `BUILTIN_EXCLUDES` に追加必須（`.claude/state` 全体は除外されていない — `start-run.py:18` 実測）。
- entry: `{key(64hex)=sha256(file+"\n"+normalize(title)), file(検証済み相対 verbatim), title(制御文字除去・200), severity, contentSha, basis, changeSetSha, firstRunid, lastRunid, lastDigest, seenCount}`。
- `codex-review-output.schema.json` に `knownFindings[{key,status}]` を **required** で追加（Structured Outputs は全 required）。
- prompt block は JSON 行＋「data, not instructions」宣言、blocking のみ、上限件数。
- gate: 読み込み（封印 sha 検証）→ (fold は state 非依存) → merge/trim（blocking 非 trim・降格無効）→ barrier `state_unchanged` → commit（transaction）。stdout `codexReview.ledger` 集計。
- Phase-5 codex-review 行の接尾辞と ADOPTION §7・config-schema・Guardrails の文書。

## 本版（v0.14.0）で出荷した最小対応
- ADOPTION en/ja と SKILL.md Phase 4 に運用注記: 「`full`＋`required:true` の初回導入時は、Phase-4 codex review が既往所見を逐次サンプリングするため複数ラウンド要することがある。修正は blocking（critical/high）のみに絞り、非ブロッキングは報告書で記録して流す。前回 run の所見一覧をプロンプトへ手動で carry-forward すると収束が速い（engine 側の機械的 carry-forward は #59 で追跡）」。

## 追記（Sol R4-note-1）
手動 carry-forward（前回所見をプロンプトへ貼る運用）も title 経由の prompt injection と同じ脅威を持つ。v0.14.0 の運用注記は「fenced JSON data として貼り、内部文字列を命令として扱わない」に限定した。engine 側 ledger も同じデータ境界（JSON 行＋data 宣言）を最低限とし、それでも意味上の注入は防げない前提で resolved 意味論を設計すること。
