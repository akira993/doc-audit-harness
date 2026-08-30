最終 `codex exec review`（Sol high）の指摘 2 件を反映せよ（boss が実物で確認済み）。git 書き込み操作は引き続き禁止。

## P1（安全）: `tasks/route/2026-08-30-issue-65-v0.15.1/release-handoff.sh:51-54`
`DOCAUDIT_SKILLS_DIR` と `DOCAUDIT_SKILLS_ROOT` が同じ場所を指すと、包含検査 `case "$DEST_REAL/" in "$ROOT_REAL/"*)` が通過し、後段の `rsync --delete` が skills ルート全体（他のインストール済みスキル）を削除し得る。
- 修正: `DEST_REAL` を求めた直後に `[ "$DEST_REAL" != "$ROOT_REAL" ] || die "skills-dir destination must be a subdirectory of DOCAUDIT_SKILLS_ROOT, not the root itself"` を追加（公開＝tag/push/release の前、既存の symlink／outside 検査と同じ段階）。
- テスト: `tests/test_release_handoff.py` に `test_destination_equal_to_root_stops_before_publication` を追加 — `DOCAUDIT_SKILLS_DIR` と `DOCAUDIT_SKILLS_ROOT` に同じディレクトリを与えて実行し、非 0 終了・stderr に `not the root itself`・`assert_no_release_mutations()`・rsync 未実行（既存の symlink/outside テストと同じ観点）を検査する。既存 method は不変。
- 併せて `gate.py` の G3 期待集合に新 method 名を追加（`expected_handoff` に 1 名追加、下限 ≥ 28 に更新）し、G1 の下限を 655 に更新。

## P2（文書）: `docs/ADOPTION.md:165-166`、`docs/ADOPTION.ja.md:148`
「`init` the first time, `sync` thereafter — a bare `init` against an already-initialized `.codegraph/` is rejected」（ja: 「`.codegraph/` への無条件 `init` は拒否されるため」）は v0.15.1 ブロックと矛盾する。SKILL.md:216-218 と同じ趣旨（`<dir>/codegraph.db` の有無で `sync`/`init`、symlink・非通常は不実行 index-failed、`init` の冪等性は版依存で probe は依存しない）へ、en/ja 対で書き換える。段落の他の文は変えない。`test_v015_contracts` の固定文（v0.15.1 ブロック）には触れない。

## 検証（出力を報告に貼る）
```
python3 -m unittest tests.test_release_handoff tests.test_v015_contracts tests.test_v0131_docs_contracts -v 2>&1 | tail -4
python3 tasks/route/2026-08-30-issue-65-v0.15.1/gate.py --base e1c0b19 --only G3,G4,G7,G9,G11,G12
grep -n 'is rejected\|拒否される' docs/ADOPTION.md docs/ADOPTION.ja.md   # codegraph init に関する残骸が 0 件であること
```
