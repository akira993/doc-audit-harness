===== #52 =====
# fix-scope.py: docGlobs default is [] (deny-all) while 12 other call sites default to ["docs/**/*.md","*.md"]

## 概要
`skills/audit/scripts/fix-scope.py:88` は `docGlobs` 省略時の既定値を `[]` としており、pre-flight fix path の分類で**全パスを拒否**する。他の 12 か所（`resolve-impact.py:95,196`、`start-run.py:43,254`、`generic-layers.py:65,598`、`change-set-sha.py:46`、`impact-supplement.py:71`、`import-audit-scope.py:148,422,588`）は `["docs/**/*.md","*.md"]` を既定にしている。

検出: v0.13.0 出荷後の文書整合レビュー（Issue #50 所見 5）。v0.13.1 では **runtime を変えず**、意図的な fail-closed としてコメント 1 行（`fix-scope.py:87`）と文書注記（`config-schema.md` の `docGlobs` 行、`docs/ADOPTION.md` / `.ja.md` §5 の `docGlobs` 行）で明文化するに留めた（PR #51）。

## 論点
- `docGlobs` を省略した設定では、Phase 0.5 の「fix and audit」パスが常に「path does not match docGlobs」で拒否され、利用者は `docGlobs` を明示しないと pre-flight 修正を使えない。安全側ではあるが、他スクリプトの既定と挙動が食い違う。
- 揃える場合は `fix-scope.py` の既定を `["docs/**/*.md","*.md"]` にし、`tests/test_fix_scope*`（該当テストが無ければ追加）で「`docGlobs` 省略時に `docs/**/*.md` が allowed になる」ことを固定する。runtime 挙動変更なので minor 版（v0.14.0）で扱う。
- 据え置く場合は本 Issue を close し、v0.13.1 の文書化を最終とする。

## 提案
既定を揃える（他 12 か所と同値）。安全側の性質は `protectedGlobs` と組込み deny（`.claude`／ADR／decisions／logs）で維持される。

関連: #50（v0.13.1 で文書化済み）、`tasks/route/2026-08-27-issues-46-50-v0.13.1/REVIEW.md` route-close「別 Issue 候補 (1)」。


===== #53 =====
# audit SKILL.md: seal-run.py non-zero exits other than 5 have no explicit stop branch; post-failure behavior differs by Phase-3 backend

## 概要
`skills/audit/scripts/seal-run.py` が exit 5（HEAD／change-set drift）以外の非 0 で失敗した場合（例: `digestExclude` に glob を含む値 → `tree-digest.py` が拒否 → `ValueError` → exit 2、`seal-run.py:63-70`）、`skills/audit/SKILL.md` の Phase 3 seal 手順（:358-364 付近）には**明示的な停止分岐が無い**。exit 5 のみ「run を解放して停止」と書かれており、それ以外の非 0 では manifest が未 seal（`digest` も付与されない）のまま手順が続き得る。

検出: v0.13.1 の計画レビュー（Sol R2-1／R4-1、Opus）で実機確認。v0.13.1 では文書契約を「seal 失敗 → run は seal されない」までに限定して記述し、runtime／手順は変更していない（PR #51）。

## 現状の後続挙動（backend で非対称）
- `read-manifest.py` は hash のみ検証し `sealed:true` を確認しない（`read-manifest.py:15-`）→ 未 seal manifest でも読める。
- workflow backend: SKILL.md:418 付近の手順で未 seal のまま verifier（Workflow）を起動し得る。
- codex backend: dispatch が非空なら `codex-dispatch.py:60` が未 seal を拒否。dispatch が空なら dispatcher を呼ばず先へ進む（SKILL.md:394）。
- gate: 到達すれば `EVIDENCE required keys are missing`（`decide-verdict.py:316,653`）で `REFUSED` を出力（`manifest is not sealed` 検査 :693 より前に落ちる）。

## 提案
1. SKILL.md の seal 手順に「`seal-run.py` の非 0 exit は exit 5 以外でも run を解放して即停止し、`read-manifest.py` を呼ばず stderr を利用者へ報告する」分岐を追加する（fail-closed の明文化。run 解放は lock 削除を伴うため runtime 手順の変更として minor 版で扱う）。
2. 併せて `read-manifest.py` で `sealed is not True` を拒否する（defense in depth）か、少なくとも `tests/test_read_manifest.py` に未 seal manifest の扱いを固定するテストを足す。
3. `tests/test_v013_contracts.py` 系の契約テストで「Phase 3 節に非 0 停止分岐の文がある」ことを固定する。

関連: #47（v0.13.1 で文書側を修正済み）、`tasks/route/2026-08-27-issues-46-50-v0.13.1/PLAN.md` §0-6、REVIEW.md route-close「別 Issue 候補 (2)」。


===== #54 =====
# report-only 監査の Phase-0 probe が対象 repo の worktree に書き込む（graphify-out 生成・.gitignore 追記）

dir-framework への 0.13 導入時（dir-framework PR #4・2026-08-27 実測）に、report-only であるはずの /docaudit:audit Phase 0 probe が対象 repo の worktree を 2 経路で変更した。

1. **graphify probe が config 省略時も既定有効**: doc-audit.json に docGraph キーが無い場合（init が「graphify 未採用なら OMIT」と指示する構成）でも graphify-probe.sh が \`graphify update .\` を実行し、未追跡の \`graphify-out/\`（実測 884K・44 パス）を生成した。init 側の「OMIT = 不採用」と audit 側の「キー不在 = 既定有効」で意味が食い違っている。キー不在は disabled 扱いにするか、init が明示の enabled:false を書くべき。
2. **cocoindex 系が .gitignore へ追記**: probe 実行の過程で対象 repo の .gitignore に \`/.cocoindex_code/\` が追記された（既存の \`.cocoindex_code/\` 行と重複する冗長行）。SKILL.md は「ccc init は audit phase から決して呼ばない（.gitignore write のため）」と定めるが、実測では ccc init を経ずに追記が発生しており、report-only 契約に反する。

いずれも digest 除外対象のため verdict には影響しないが、(1) は Phase 1 の machinery 除外 44〜45 件・状態行 WARN の恒常化、(2) は changed set 汚染（boss が git checkout -- で復元して回避）を起こす。

🤖 Generated with Claude Code

