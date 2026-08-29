# 読み取り専用の事前調査 — Issue #56 第2段（webExtract / codexReview の key-gate 化）の全変更点列挙

あなたは調査担当である。**ファイルの変更は一切行わないこと**。成果物は本回答のみ（markdown、全項目に `file:line` の実測引用を付ける）。

## 背景

docaudit engine（この repo）は v0.13.2 で `symbolGraph`/`docGraph`/`semanticSearch` の 3 seam を key-gated 化した（config にキーが無ければ `reason:not-configured` で tool を起動しない）。次版 v0.15.0 で、残り 4 seam のうち `webExtract`（ax）と `codexReview`（codex）の 2 seam を同じ key-gated に揃える（`indexing`/`contextMode` は既定有効のまま維持）。キー不在＝`not-configured`（tool 不起動・💡 状態行）、キー存在時の挙動（enabled/bin 検査、invalid-config、disabled-by-config）は現行 v0.14.0 のまま。

この変更に必要な**全変更点**を、実装前に漏れなく列挙するのが本調査の目的である。

## 調査項目（全て file:line 引用付きで）

1. **現行実装**: `skills/audit/scripts/ax-probe.sh` と `skills/audit/scripts/codex-probe.sh` の全文を読み、キー不在／`{}`／`enabled:false`／enabled 非 boolean／キー非 object／bin 不正 の各判定がどの行で行われ、どの JSON（全フィールド）を emit するかの判定表を作る。exit code も記す。
2. **参照パターン**: key-gated 側の実装例として `graphify-probe.sh`（docGraph）と codegraph／cocoindex 系 probe スクリプトの「キー不在→not-configured」分岐が、他の検査（enabled/bin/インストール確認/実行）に対してどの順序・どの行にあるか。emit される reason 文字列の正確な値。
3. **audit SKILL.md**（`skills/audit/SKILL.md`）: webExtract/ax と codexReview/codex-review に関する (a) reason enum の列挙行、(b) Phase-0 probe 手順の段落、(c) Phase-5 状態行の全分岐（⚠/💡/4-way、:646 付近の優先順位規則を含む）、(d) Phase 4 が codex review を実行するか否かを決める条件（`CODEX_REVIEW_AVAILABLE`/`CODEX_REVIEW_REASON` の下流利用箇所全て）、(e) resume/rebind（probe-record 経由の再束縛）で webExtract/codexReview の reason がどう扱われるか。それぞれ行番号を列挙。
4. **probe-record.py**（`skills/audit/scripts/probe-record.py`）: seam ごとの schema 検査で webExtract/codexReview の reason に許容値リストがあるか。あるなら行番号と現在の許容値。`not-configured` を足す必要がある箇所。
5. **下流の消費者**: `AX_REASON`/`AX_AVAILABLE`/`CODEX_REVIEW_REASON`/`CODEX_REVIEW_AVAILABLE`/reason 文字列を読む他のスクリプト・テンプレート（`workflow-template.js`、decide-verdict／gate 系、`import-audit-scope.py` 等）。新 reason 値 `not-configured` が来たときに壊れる箇所・分岐追加が要る箇所。
6. **init SKILL.md**（`skills/init/SKILL.md`）: webExtract/codexReview の提案・OMIT 文言の行。key-gated 側（symbolGraph/docGraph）の OMIT 文言（「absent key ⇒ not-configured」型）の行 — 揃える際の見本。
7. **config-schema.md**（`skills/audit/references/config-schema.md`）: webExtract/codexReview の行と、見本になる symbolGraph/docGraph 行。
8. **テスト**: `tests/` 配下で上記 2 seam のキー不在挙動（既定有効）を固定しているテストの一覧（ファイル・テスト名・行）。特に `test_ax_probe.py`・`test_codex_probe.py`・`test_v014_contracts.py`・`test_v0132_contracts.py`・`test_probe_record.py`・`test_codex_review_plan.py`。また、版文字列の列挙を持つテスト（`test_v013_contracts.py` の refresh 許可 regex :201/:210/:215 相当）で 0.15.0 追加が必要な箇所全て。`test_release_handoff.py` が版文字列に依存する箇所。
9. **版文字列と ADOPTION**: `.claude-plugin/plugin.json`・`docs/ADOPTION.md`・`docs/ADOPTION.ja.md` の版記載行。ADOPTION §7 の「vX.Y.Z behavior changes」ブロックの構造（v0.14.0 ブロックの行範囲、en/ja）。`skills/audit/references/engine-shas.json` の構造と、それを生成・検証する仕組み（スクリプト・テスト）の場所。
10. **その他の残骸**: 「absent key remains enabled by default (intentional asymmetry)」等、キー不在既定有効を明記した文が webExtract/codexReview について残る全ファイル（docs/・skills/・tests/ 横断 grep）。変更後に矛盾する文を全列挙。

## 出力形式

各項目を見出しにし、file:line と現物の短い引用（1〜2 行）で示す。推測・未確認は「未確認」と明記。最後に「変更が必要なファイルの一覧（ファイルごとに変更点の要約 1 行）」を付ける。
