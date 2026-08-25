# boss レビュー結果（段階 A）と 段階 B の指示

## 段階 A の差し戻し 2 件（先に修正せよ）

1. **frontMatterOverrides のスキーマが PLAN §5.2 と不一致**。PLAN・Issue #34 は
   `{ "globs": ["glob1", "glob2"], "fields": [...] }`（globs は**配列**）。現実装は `glob`（単一文字列）。
   `globs` 配列（いずれかの glob に一致で採用・先勝ち）に修正し、テストも追随させること。
2. **コロンを含む実在ファイル名の回帰**。旧実装はフルトークンの存在確認を locator 分割より先に行って
   いた。現 `_token_base` は locator 基底を常に優先するため、`docs/foo:bar` という実在ファイルが
   backtick 参照されると偽 finding になる。フルトークン（suffix 除去後）が存在すればそれを解決済みと
   する順序に修正し、回帰テストを 1 件追加すること。

## 段階 B — レポートマッチャの全経路統一（PLAN §5.3）

対象ファイル（PLAN §7 の許可範囲内）:
- `skills/audit/scripts/change-set-sha.py` — 正本のレポート除外（glob 導出＋excluded()）を PLAN §5.3 の
  テンプレート由来 regex に置き換える（**マッチャ統一に必要な変更のみ**。妥当性条件は現行実装を
  一切変更しない。機構除外は opt-in の影響を受けない＝無条件）
- `skills/audit/scripts/decide-verdict.py` — sibling-scan へ渡すパターンを同 regex に統一
- `skills/audit/scripts/sibling-scan.py` — `--report-pattern` を regex 受けに変更
- `skills/audit/scripts/resolve-impact.py` — full corpus と heuristic pool から corpus 除外
  （mapped は無変更・opt-in 対象）
- `skills/audit/scripts/impact-supplement.py` — **任意引数** `--config <doc-audit.json>` を追加し
  reportPath/opt-in を読んで候補から除外。未指定時は現行挙動（no-op 契約）を完全維持
- `skills/audit/scripts/start-run.py` — corpus 数算出に corpus 除外を適用
- `skills/audit/SKILL.md` — impact-supplement 呼び出し箇所へ `--config` を追加（この変更のみ。
  suffix 生成契約・層説明は段階 C で行う）
- `tests/` — PLAN §5.6 の #35 節に対応するテスト全部:
  - **契約テスト**: §5.3 ケース表（正常形・`[_NN]` 有無×suffix 1/2/3 桁・日付後リテラル＋suffix 位置・
    `doc_audit_policy.md`・非 `.md`・placeholder 欠落・空 prefix・placeholder がディレクトリ側・
    docGlobs 不一致・全角数字）を**全実装**（change-set-sha 正本・generic-layers 複製・resolve-impact・
    impact-supplement・start-run）に同一入力で与え、同一判定であることを固定する。
    正本と generic-layers 複製の**妥当性判定の完全一致**も確認せよ（段階 A の複製に正本に無い条件
    — 例えば `.endswith(".md")` — を入れていた場合は正本に合わせて修正すること）
  - change-set-sha: 日付付きレポート除外・`doc_audit_policy.md` **非除外**（挙動変更の固定）・
    opt-in true でも機構除外維持・既存テスト期待値の更新（変更 1 件ごとに PLAN §5.6 後方互換節の
    意図的差分との対応を報告に列挙）
  - **compute-baseline.sh 経由の統合テスト**（`[_NN]` suffix・policy.md 残留・machineryExcludedCount）
  - resolve-impact / impact-supplement（--config 有無）／start-run: 除外・opt-in 復帰（corpus 4 経路）・
    opt-in 不正型（`"true"`・`1`・`[]`）で除外解除されない・レポートのみ repo で start-run 正常・
    mapGapCandidates 等付随出力整合

拘束は段階 A と同じ（generic-layers.py への import 追加禁止・他は repo 内複製または既存慣行・
compute-baseline.sh は**変更禁止**・既存テスト期待値変更は意図的差分リストと突合して報告）。
検証: `python3 -m unittest discover -s tests -t . -v` を実行し末尾サマリを報告（scaffold 系の
engine-shas stale 失敗が残るのは段階 C までは想定どおり — その失敗が「engine-shas stale のみ」で
あることを確認して報告せよ）。
