# 段階 A 実装記録

## 計画

- [x] PLAN rev.6 と既存実装・テスト・作業ツリーを確認する
- [x] 共通のパス判定と Issue #33 の挙動を実装する
- [x] Issue #34 の設定拡張と Issue #35 のレポート除外を実装する
- [x] PLAN §5.6 の段階 A テストを追加・調整する
- [x] 全テスト、差分、変更範囲を検証する

## レビュー

- `python3 -W ignore::ResourceWarning -m unittest tests.test_generic_layers`: 58 件成功。
- §8 の単体実行: docs=1 / findings=4 / fail=2 / warn=2。path と line は 1〜4 行の仕様どおり。
- `python3 -m unittest discover -s tests -t . -v`: 281 件中、5 failures / 5 errors。
  原因はすべて `generic-layers.py` の変更により `check-docs-engine` の照合値が古くなったこと。
  照合値と版の更新は段階 C の範囲なので、段階 A では変更していない。
- 既存テストの期待値変更: なし。新仕様は新規テストで固定した。
- 変更範囲外の未追跡 `.claude/` は変更していない。

## 修正から得た学び

- 計画が設定キーの入れ子まで定めている場合、名称だけでなく単数・複数と値の型まで原文どおり照合する。
- 既存処理に正規化を加える場合、正規化前の値で成立していた解決順序を回帰テストで固定する。

## boss 差し戻し対応

- `frontMatterOverrides` を `globs: string[]` に修正し、配列内のいずれかに一致する先勝ち契約を固定した。
- suffix 除去後のフルトークンを locator 分割前に解決し、コロンを含む実在ファイル名の回帰を固定した。
- 差し戻し対象を含む 16 件: 成功。
