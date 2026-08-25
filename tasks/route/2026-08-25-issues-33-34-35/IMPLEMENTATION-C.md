# 段階 C 実装記録

## 計画

- [x] v0.11.0 への版更新と文書・SKILL の契約更新を行う
- [x] scaffold.py の計算関数で 3 種の SHA を算出し engine-shas.json に追加する
- [x] 0.10.1 engine fixture と refresh 回帰テストを追加する
- [x] scaffold / skill 形式 / 全体テストを検証する
- [x] 版残置、差分、変更範囲を確認し、レビュー結果と学びを記録する

## レビュー

- `.claude-plugin/plugin.json` と指定文書・テストの版を 0.11.0 へ更新した。
- `scaffold.py` の `_normalized_sha()` と `_harness_sources()` で算出した 0.11.0 SHA:
  - `check-docs`: `a5c1efbcbe1bdbece74cb188228fd676d4c6c0446a42f27d6514afe40c5f1ab8`
  - `doc-lint`: `ebc5944f8739b4b0ff9740f442fe05225c6df300f6fcb471ba20120f30366727`
  - `check-docs-engine`: `d0e64dd5c436a04ec1b28e75a73964b324da9de47ff81e7541f7ec223dba5a82`
- 歴史的 fixture は `docaudit--v0.10.1` の本文と同一で、SHA は 0.10.1
  `check-docs-engine` の `4dc97df6e2d31ced9ec267039c5a75f2c4c989ec8bbdee57ac55203cbe76c5eb`
  に一致した。
- scaffold / decide-verdict 対象 52 件: `Ran 52 tests in 28.515s` / `OK`。
- 全体 298 件: `Ran 298 tests in 58.421s` / `OK`。
- `git diff --check`: 成功。
- 古い「リンクのみ」「existence は WARN のみ」の前提は、指定された `skills/audit/SKILL.md`、
  `skills/init/SKILL.md`、`scaffold.py` に該当なし。
- 配布物内の 0.10.1 残置は、`engine-shas.json` の履歴 1 行と ADOPTION 英日移行説明 2 行のみ。
- `skill-creator` の `quick_validate.py` は実行環境に PyYAML がなく起動できなかった。標準機能で
  同等条件を確認し、既存の `argument-hint` を許容した本文・先頭情報検査は成功した。
- `tests/data/` は既存 `data/` 無視規則の対象。fixture は存在して全テストで使用済みだが、この環境は
  `.git` が読み取り専用のため `git add -N -f` が `index.lock: Operation not permitted` で失敗した。
  コミット時は `git add -f tests/data/generic-layers-v0.10.1.py` が必要。
- 既存テストの期待結果変更はなし。`tests/test_decide_verdict.py` の契約版入力だけを、PLAN §5.5 の
  明示指示どおり 0.10.1 から 0.11.0 へ更新した（期待 return code 0 は不変）。
- 最終レビュー P2 を修正し、5 実装の `report_pattern()` が `docGlobs` 省略時にも既定値
  `["docs/**/*.md", "*.md"]` を使うよう統一した。契約テストと generic-layers 列挙テストを各1件追加。
- P2 修正後の 0.11.0 `check-docs-engine` SHA は
  `d0e64dd5c436a04ec1b28e75a73964b324da9de47ff81e7541f7ec223dba5a82`。

## 学び

- 版依存の scaffold SHA は、manifest の版更新後に必ず同じ `scaffold.py` 計算関数から得る。
- 明示追加が必要な fixture でも、親名に対する広い無視規則が適用されることがある。禁止された
  `.gitignore` を変えず、コミット時に対象ファイルだけを強制追加する。
- 設定キーの妥当性確認では、キー欠落を空値に置き換えず、実際の実行経路と同じ既定値を使う。
