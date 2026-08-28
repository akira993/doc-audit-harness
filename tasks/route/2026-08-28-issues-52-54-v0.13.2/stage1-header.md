# S1 実装依頼 — docaudit v0.13.2（Issues #52・#53・#54 ＋ 既往 red の fixture 化）

あなたは実装担当（worker）。boss（Claude）が確定した計画 `tasks/route/2026-08-28-issues-52-54-v0.13.2/PLAN.md`（rev.6）に従って **S1 のみ** を実装する。
S2（版バンプ・engine-shas・§7 段落・release-handoff）は別依頼なので触らない。PLAN.md を最初に全文読むこと（§0 決定事項が仕様の正）。
Issue 本文: 同ディレクトリ `issues-52-54.md`。レビュー経緯: `REVIEW.md`、`critique-r*-answer.md`（設計判断の根拠。再審議しない）。

## 作業の要点（PLAN §0 の要約。詳細・固定文言は PLAN が正）
- #52: `fix-scope.py` の `docGlobs` 既定を `["docs/**/*.md", "*.md"]` に。basename deny（casefold で `claude.md`/`agents.md`、任意の深さ、docGlobs より優先）を追加。
  fail-closed 注記の撤去（fix-scope.py コメント、config-schema.md:10、ADOPTION en/ja の docGlobs 行）。組込み deny の列挙 5 か所に CLAUDE.md/AGENTS.md（case-insensitive）を追加。
- #53: SKILL.md Phase 3 の seal 手順に 3 停止分岐（exit 5／`Any other non-zero exit`／read-manifest 失敗）を、各分岐に SKILL.md:52 の完全な解放コマンドを伴って記述。
  `read-manifest.py` は hash 一致後に `isinstance(manifest, dict) and manifest.get("sealed") is True` を検査、不成立は `ValueError("manifest is not sealed")` → exit 2。
- #54-1: 3 probe（graphify/cocoindex/codegraph）の config 解釈を PLAN §0-4 の判定表（10 行）＋評価順序どおりに。reason `not-configured`／`invalid-config` を追加。
  SKILL.md Phase 0 の 3 probe 段落で `*_REASON` を probe JSON `["reason"]` から完全な式で束縛。Phase-5 の 3 状態行を `*_REASON` による排他表に書き直し（6-state(7 msgs)/6-state/8-state）。
  config-schema.md（3 行＋3 節、:39 の「runtime reads only」文言更新）、ADOPTION en/ja の状態行要約、init SKILL.md の OMIT 文 3 か所を更新。
- #54-2: `cocoindex-probe.sh` の初期化判定を `-f .cocoindex_code/settings.yml` に。`ccc index` 前後の `.gitignore`（存在有無＋sha256）比較で変化を検出 → `gitignore-modified`
  （**書き戻さない**。exit code より優先）。文書 5 本を settings.yml マーカーに更新。状態行に `gitignore-modified` 枝（PLAN §0-5 の文言）。
- 既往 red: `tests/test_import_audit_scope.py` の外部 repo 依存テストを `tests/data/dir-framework-scope/` fixture（3 点、sha 固定）に置換。fixture は
  `git -C ~/Projects/dir-framework show 951570b:.claude/audit-scope.json`（そのまま）、`git -C ~/Projects/dir-framework ls-tree -r --name-only 951570b`（そのまま、LF 終端）、
  `show 951570b:.claude/doc-audit.json` から `auditScope` を除去して `json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"` で作る（dir-framework は読み取りのみ）。
- 新規 `tests/test_v0132_contracts.py`: PLAN DoD の固定テスト名どおり。各 test の docstring に対応する DoD 番号を書く。

## 実装上の注意
- 3 probe の config 解釈は現在 bash 内の python one-liner。判定表を満たす形に書き直してよいが、出力 JSON の既存キー（`docGraphAvailable`/`docGraphBin`/`reason`/`gitignoreOk`、
  `semanticSearchAvailable`/`semanticSearchBin`/`reason`、`symbolGraphAvailable`/`symbolGraphBin`/`reason`）と「常に exit 0・JSON 1 行」は維持する。
- `enabled` は JSON boolean のみ有効。Python 側で `isinstance(v, bool)` を先に判定（`bool` は `int` のサブクラスなので `minScore` の数値判定では `bool` を除外）。
- 状態行の書き直しは既存の記号・既存文言（`not active`、`install:` 等）を可能な限り保ち、新枝を足す。他の状態行（mdq/context-mode/ax/codex/harness/pre-flight）は変えない。
- 既存テストの改変は最小限（cocoindex の ok/index-failed fixture に `settings.yml` を置く、`test_import_audit_scope` の当該テスト置換）。他の既存テストを緩めない。
- Terra の sandbox では 30 秒超のフルスイートが完走しないことがある。その場合は対象ファイル単位の `python3 -m unittest -v tests.test_xxx` を全て実行して結果を報告し、
  フルは boss が実行する旨を報告に書く。`git` への書き込み（add/commit/checkout）は行わない。
- 対象外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。

## 報告（最後に `tasks/route/2026-08-28-issues-52-54-v0.13.2/stage1-report.md` へ書き出す）
1. 変更ファイル一覧と各ファイルの変更要旨。2. PLAN DoD (1)〜(15) と (20)〜(22) の各項目について、実行したコマンドと結果（実測値）。
3. 実行したテストコマンドと `Ran N tests` の実数・OK/FAIL。4. 未対応・判断に迷った点・対象外ファイルの変更が必要と判断した点。

以下は行動規範。全て命令。
- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 状態変更コマンド前に証拠がその操作を支持するか確認

---
# 以下、PLAN.md の完了条件・変更範囲・検証コマンド一式（原文）
