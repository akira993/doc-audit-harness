# 実装タスク 段階 A — generic-layers.py 本体（Issues #33/#34/#35 の engine 側）+ テスト

あなたは実装担当。拘束仕様は `tasks/route/2026-08-25-issues-33-34-35/PLAN.md`（rev.6・レビュー承認済み）。
**まず PLAN.md 全文を読んでから着手せよ。** 本タスクは 3 段階分割の A（この後 B: マッチャ統一を他
スクリプトへ、C: scaffold/版bump/docs が続く。同一セッションで継続する）。

## 段階 A の範囲

`skills/audit/scripts/generic-layers.py` と、その挙動を検証する `tests/`（既存 `tests/test_generic_layers.py`
の拡張または新規テストファイル）のみ。**他のスクリプト・docs・版数には触れない**（B/C で行う）。

実装する仕様（PLAN の該当節番号）:
1. **§5.0 共通プリミティブ**: existence 層のコードマスク化（fenced＋indented、blockquote/リストマーカーの
   反復剥がし・固定上限なし）／`looks_like_repo_path()` の `..` 拒否・`//` 拒否／正規化パイプライン
   （`#`/`?` 除去 → `:locator` 基底 → percent-decode with NUL・制御文字・`..` 再検証で破棄）／
   ファイルシステム呼び出しの OSError/ValueError 捕捉＝トークンスキップ／realpath による repo 封じ込め／
   file/dir 判定（FAIL クラス定義、判定基底パスに適用、非 ASCII backtick も対象）
2. **§5.1**: bare path ハーベスタ（ASCII パス文字クラス・URL マスクは URL 文字クラスで停止・
   markdown リンク範囲マスク・常に WARN・bare 由来 message）／backtick token の FAIL 昇格
   （具体的ファイルパスのみ）／docstring 更新
3. **§5.2**: `layerGlobs`（各 check 内部適用・semantic は orphan 報告対象からの除外のみで発リンクは
   referenced に残す）／`frontMatterOverrides`（先勝ち・`fields: []`・fallback）／不正型 WARN
   （path=`"(config)"`）と text 出力 pass 集計の修正
4. **§5.3 の generic-layers 部分**: レポートマッチャの self-contained 導出（placeholder 4 段変換規則
   R5-3・suffix 位置規則 R5-1 を厳密に）／`list_doc_files()` 列挙からの除外・明示 `--paths` 非除外・
   semantic scan = 除外済み列挙 ∪ 明示 paths／`auditReportsInCorpus` bool true のみ有効・不正型 WARN
5. **§5.6 のうち上記に対応するテスト全部**（#33 ブロック・#34 ブロック・#35 の generic-layers 行・
   後方互換）。期待値は件数・path・line まで厳密に assert すること。

## 絶対拘束（PLAN 外の追加指示）

- **generic-layers.py への import 追加は禁止**（標準ライブラリの既存 import への追加は可。ただし
  リポジトリ内他モジュールの import は絶対禁止 — このファイルは consuming repo へ byte 複製される）。
  レポートマッチャ導出は self-contained で書き、正本 `change-set-sha.py:43-57` を参照するコメントを付す。
- **既存テストの期待値を変更した場合、変更 1 件ごとに「PLAN §5.6 後方互換節のどの意図的差分に
  対応するか」を最終報告に列挙せよ。**対応しない既存テスト変更は回帰であり、実装を修正すること。
- 挙動変更は PLAN が明示するもののみ。スコープ外のリファクタ・整形・コメント追加は禁止。
- 検証: `python3 -m unittest discover -s tests -t . -v` を実行し、全 green の出力（末尾サマリ）を
  報告に含める。失敗があれば失敗のまま報告する（隠すことは最悪の失敗）。

## PLAN の 3 点セット（原文転記）

### 完了条件（PLAN §6 — 段階 A に関わるもの）
1. `python3 -m unittest discover -s tests -t . -v` 全 green（新規テスト含む）
2. §5.6 の全観点が期待値（件数・path・line）どおり
3. 新キー未設定 repo の挙動差が §5.6「後方互換」記載の意図的差分のみ

### 変更範囲（PLAN §7 — 段階 A ではさらに狭い）
許可: `skills/audit/scripts/generic-layers.py`・`tests/`・`tasks/route/2026-08-25-issues-33-34-35/`
禁止: それ以外すべて（resolve-impact.py 等は段階 B。scaffold・docs・版数は段階 C）

### 検証コマンド（PLAN §8 抜粋）
```bash
python3 -m unittest discover -s tests -t . -v
python3 skills/audit/scripts/generic-layers.py --config <fixture>/doc-audit.json \
  --repo-root <fixture> --layer all --format json
```

## 行動規範（全て命令）

- **結論先行**: 報告の最初の一文で「何が起きたか/見つかったか」に答える。断片・矢印チェーン・自作ラベルで圧縮しない。完全な文で書く
- **即行動**: 行動に足る情報が揃ったら行動。確定済み事実の再導出・決定済み事項の再審議・採らない選択肢の陳列をしない。迷ったら推奨を1つ
- **進捗の実証**: 報告前に各主張をツール結果と突合。未検証は未検証と明言。テスト失敗は出力ごと報告。捏造進捗は最悪の失敗
- **スコープ規律**: 要求以上の機能追加・リファクタ・抽象化禁止。動く最小をやる。起こり得ないシナリオへの防御コード禁止
- **ターン終了規律**: 「これから X します」で終わらない。実行してから終える。停止してよいのは完了時かユーザーにしか出せない入力待ちのみ
- **境界**: 問題の説明を受けた時の成果物は評価であって修正ではない。状態変更コマンド前に証拠がその操作を支持するか確認
