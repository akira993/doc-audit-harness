あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN.md は rev.2 に更新済み（同じパスを再読すること）
- R1-1: 反映。永続 ledger `.claude/state/docaudit-codex-ledger.json` を `start-run.py` の BUILTIN_EXCLUDES に追加し、書き込みは gate（`decide-verdict.py`）の state-commit 節（`atomic(last_run_path,…)` 直後、barrier 内）で `docaudit_ledger.commit_candidate` が行う。両ファイルを限定範囲で許可（§0-6, §7）。
- R1-2: 反映。Phase 4 は候補 `$RUN_DIR/codex-ledger-next.json` を書くだけ。REFUSED は barrier 前 raise なので commit に到達しない。
- R1-3: 反映。プロンプトの抑止命令を撤去。codex は毎回全所見を返す。ledger は blocking を「明示 resolved まで維持」する方向にしか働かず、CONSISTENT を偽造できない（§0-6 設計原則）。
- R1-4: 反映。`file` は `validate_repo_path(must_exist=True)` 必須（不合格は記録しない）、title は制御文字除去・空白正規化・200 上限、promptBlock は JSON 1 行ずつ＋「data, not instructions」宣言、保存先は固定パス・O_NOFOLLOW・通常ファイルのみ。
- R1-5: 反映。`codex-review-output.schema.json` に任意 `knownFindings[{key,status∈{still-present,resolved,out-of-scope}}]`。削除は `resolved` 明示のみ。それ以外（still-present／out-of-scope／未言及）は維持し、今回 findings に無ければ `foldFindings` として phase4 に畳む。
- R1-6: 反映。key は検証済み相対パス verbatim＋title 正規化。blocking は trim 対象外、non-blocking のみ 500 件・`(lastRunid,key)` 昇順。
- R1-7: 反映。`main()` で `repo_apparent=os.path.abspath(args.repo_root)` を realpath 前に保持し `safe_path(repo, repo_apparent, …)`。
- R1-8: 反映。正規化せず成分検査（`""`/`.`/`..` 拒否）→ 接頭辞照合 → `validate_repo_path`。repo 内へ戻る `..`・中間 symlink 絶対パスをテストに追加。
- R1-9: 反映。既存分岐のキー集合不変、`invalid-config` は not-installed 形。
- R1-10: 反映。9 記録→7 表示の対応表を固定文言化。codex-review 行は probe 記録＋`phase4.json`（存在時）＋`codex-ledger-next.json` の summary（存在時）から復元。Phase-3 refresh 接尾辞は再開後は付けないと文書化。
- R1-11: 反映。`--evidence` の runDir 一致、seam 別必須キー・型を write/read 双方で検査、O_NOFOLLOW、run dir/ファイルの symlink 拒否。lock identity 検査は採用しない（表示専用で verdict 不変、write-evidence.py と同水準に揃える — 反論があれば根拠を）。
- R1-12: 反映。`${CODEX_HOME:-}`／`${HOME:-}`、空文字列＝未設定、両方無しは `unknown`/`null`。
- R1-13: 反映。キー名を `callerCodexHome`/`callerCodexHomeSource`/`callerAuthFile` に改め「呼び出しシェルで観測、wrapper 内は観測外」と文書化。値は既存 BIN_J と同じ sanitizer。
- R1-14: 反映。§7 固定文を 7 つに拡張、ledger に `schemaVersion:1`（不一致は fail-open＋警告）。
- R1-15: 反映。DoD (19)(20) を `dfdb8a9` との name-only／byte 比較に置換。
- R1-16: 反映。DoD (1)(3)(4)(7)(11) を端から端まで（両 option×6、helper 迂回、plan 完全一致、gate REFUSED、env 7 ケース、ledger carry 8・stage 16・gate 4・start-run 1）。
- R1-17: 反映。固定テスト名・出現回数（各 1 回だけ）・順序 assert・新規ファイル別最低件数。

## 依頼
rev.2 を再批判せよ。前回指摘の再指摘は不要（対応が不十分なら「R1-N 対応不十分」として理由を）。新規の指摘は R2-N で番号を振り、根拠（file:line／実測）と推奨 1 つを付けよ。
特に検分してほしい点:
1. gate 変更（§0-6 の `commit_candidate`）が既存の barrier・lock 規約・`--accept-config`・taint 経路と衝突しないか。`decide-verdict.py:895-960` を読んで、挿入位置の妥当性と「失敗しても REFUSE しない」の是非。
2. `foldFindings` を orchestrator が phase4 findings に加える契約: モデル媒介である点の弱さと、それを決定論にする代替（例: `stage` が `phase4` 補助ファイルを書き gate が読む）との費用対効果。
3. `knownFindings` 追加後の schema と `codex exec --output-schema` の互換（任意プロパティ＋`additionalProperties:false`）。
4. #57 の対応表の完全性（Phase 5 の 7 行が全て決定論的に再束縛できるか。`mdqHealth` が available:false のとき不要という条件の妥当性）。
5. #58 の成分検査＋接頭辞照合＋`validate_repo_path` の三段で、まだ迂回できる入力があるか（Windows 区切り・末尾スラッシュ・`//` 重複・`~`・URL 形）。
6. 「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、最後に PLAN を直すべき点を優先順で 5 件以内。指摘が無ければ「rev.2 で実装承認」と明言せよ。
