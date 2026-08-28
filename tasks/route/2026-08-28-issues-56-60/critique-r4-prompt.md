あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## boss 決定（再審議不要）
#59 の ledger は本版から**見送り**（Issue 最小案の運用注記のみ出荷）。理由: R1〜R3 で示されたとおり、blocking を決定論的に維持する機構は history/anchor と同じ信頼クラス（open-run 封印・barrier・transaction・taint 復元・版跨ぎ拒否）を要し、
5 Issue 同時の route に収まらない。反例 13 件と P1〜P4 は `tasks/route/2026-08-28-issues-56-60/59-design-note.md` に固定し、専用 route の起点とする（ユーザーに諮る）。
これに伴い `decide-verdict.py`／`start-run.py`／`codex-review-output.schema.json` は**禁止ファイル**に戻った。#56(c) の gate REFUSED は既存コード（`decide-verdict.py:797`）で成立するためテスト追加のみ。

## 前回指摘との対応（自己申告）— PLAN.md は rev.4（同じパスを再読）
- R1-11: 反映。run dir は引数で受けず、repo fd から `.claude`→`state`→`docaudit-run`→`<RUNID>` を成分ごとに `O_DIRECTORY|O_NOFOLLOW` で辿る。RUNID は `start-run.py:17` の正規表現。中間 symlink 拒否テストを追加。
- R1-15: 反映。allowlist は boss の先頭 commit（SCOPE_COMMIT）に固定し `git show` で読む。`--ignored=matching` で ignored も検査、除外は tool 所有 prefix（`.mdq/`、`.claude/worktrees/`、`tasks/`、`__pycache__/`）のみ。`.claude/settings.local.json` は禁止（allowlist の baseline 節に列挙し hit で越境扱い）。
- R2-5: 反映。CM 式は try/except と `isinstance(c,dict)` で読込例外・top-level 非 dict を `invalid` に。契約テストは 18 ID 全部で式を実行。
- R3-6: 反映。3 probe とも 18 variant の固定 ID 集合（`absent, empty, disabled, en_str, en_int, en_null, key_null, key_true, key_str, key_list, cfg_omitted, cfg_missing, cfg_broken, top_list, top_null, bin_int, bin_empty, compound`）。
- R3-7: 反映。明示 symlink fixture で apparent-root 分岐を実行（A〜D の 4 組合せを固定、D は拒否を文書化）。
- R3-8: 反映。件数検査は `test -ge`／`test -eq` で非 0 終了。
- #59 関連（R1-2/R1-3/R1-4/R2-2/R2-4/R2-7/R2-8/R3-1〜R3-5/R3-8 の ledger 部分）: 見送りにより本版では対象外。design note に転記済み。

## 依頼
rev.4 の**残スコープ（#58・#56 第 1 段・#57・#59 最小案・#60・S2）**だけを再批判せよ。#59 ledger の再審議はしない（design note への追記提案は歓迎、R4-note-N で別掲）。
前回指摘の再指摘は不要（対応不十分なら「Rx-N 対応不十分」と理由）。新規は R4-N、根拠（file:line／実測）と推奨 1 つ。
特に: (1) #57 の probe-record が禁止ファイルに触れずに成立するか（`open-run.py` の成分 walk と同等の実装を独自に持つことの是非）、(2) #56 の 18 ID が 3 probe と CM 式で同じ意味を持つか（`cfg_omitted` の CM 側の意味）、(3) #60 の `json.dumps` 化で既存テスト `test_codex_probe.py`／`test_v013_contracts.py` の固定文字列が壊れないか、
(4) S2 の 6 文と handoff の再標的、(5) DoD の判別力。
最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、PLAN を直すべき点を優先順で 5 件以内。無ければ「rev.4 で実装承認」と明言せよ。
