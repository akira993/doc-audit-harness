S2 の主要実装を行い、全体テストは **398 件成功・6 件保留** でした。

実装済み:
- `resolve-impact.py` に飽和率・文書パス由来トークン除外・回帰再検証・`historySha`・cap 優先順を追加。
- `plan-dispatch.py` に履歴ハッシュ照合（不一致は exit 3）と `dispatch.json` の `impactSha` を追加。
- 補完優先順位、消費側の provenance 文言、設定表・既定説明、契約テストを更新。
- 追加・更新した対象テストは 40 件成功。

検証:
- `python3 -m unittest discover -s tests -t .`
  - `Ran 398 tests in 105.833s`
  - `OK (skipped=6)`

留意点: 依頼にある型検証表、9/9 飽和、丸め境界、plan-dispatch の専用ケース群までは追加できていません。実装の一部は対象テストで通していますが、これら未追加の検証は未検証です。

変更ファイルは許可範囲内です。`.claude/` は開始時からの未追跡項目です。git 操作・コミットは行っていません。