boss の検収作業ミスにより、作業ツリーの次の 6 ファイルが **HEAD（e1c0b19）の内容に巻き戻されました**（あなたの実装が作業ツリーから消えています。責任は boss にあります）:

- `README.md`
- `.claude-plugin/plugin.json`
- `skills/audit/SKILL.md`
- `skills/audit/scripts/codegraph-probe.sh`
- `tests/test_codegraph_probe.py`
- `tests/test_release_handoff.py`

それ以外（`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`・`skills/audit/references/config-schema.md`・`skills/audit/references/engine-shas.json`・`tests/test_scaffold.py`・`tests/test_v0131_docs_contracts.py`・`tests/test_v013_contracts.py`・`tests/test_v015_contracts.py`・route dir の `gate.py`（`--only` 付き）・`release-handoff.sh`）は無事です。`git diff` で現状を確認できます。

依頼: 上記 6 ファイルを、あなたが実装 R1〜R2 で完成させた**最終内容と同一**に再作成せよ（PLAN.md rev.7a §5 の仕様どおり。あなたの前回のパッチ内容をそのまま再適用する）。再作成後、次を実行して出力を報告に貼れ:

```
python3 -m unittest tests.test_codegraph_probe tests.test_release_handoff tests.test_v015_contracts -v 2>&1 | tail -4
python3 tasks/route/2026-08-30-issue-65-v0.15.1/gate.py --base e1c0b19 --only G2,G3,G4,G5,G9,G11,G12
```

G2〜G5・G9・G11・G12 が全て PASS になるまで直せ。git の書き込み操作は引き続き禁止（コミット・add は boss が行う）。
