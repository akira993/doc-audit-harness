結論: rev.2も現状では承認できません。前回12件の再掲は除外し、新規に High 3件、Medium 7件を確認しました。修正は行っていません。

## バグ・回帰・互換性

1. High — 「最終防衛線」が封印済み設定ではなく変更可能な生ファイルを読む

   根拠:

   - `PLAN.md:52-55` は planner が sealed config を読むと規定。
   - 実際は `SKILL.md:577` が `--config "$CFG"` を渡し、`codex-review-plan.py:23-25` はその時点のファイルを直接開く。
   - config SHA は `open-run.py:157-163,221-223` に保存されるが、Phase 4直前には検証されない。次の検証はCodex実行後の `decide-verdict.py:699-701`。

   Phase 4直前にキーを追加し、Codex実行後に元へ戻せば、最終SHA検査まで通してkey-gateを迂回できます。

   推奨修正: plannerへ `EVIDENCE` を渡し、読み取ったconfig bytesが `EVIDENCE.config` のSHAと一致した場合だけキー判定し、不一致ではCodex未起動のまま停止する。

2. High — Phase 4完了済みの旧runは再ゲートされない

   根拠:

   - PLAN `:83` はv0.14開始runをv0.15 resume時に再ゲートすると無条件に説明。
   - `SKILL.md:50-66` はPhase-4 evidence完成後のcheckpoint `(h)` からのresumeを認める。
   - この段階ではplannerは再実行されない。
   - `decide-verdict.py:787-798` はキー不在を確認せず旧Codex状態を受理し、`:894-899` は旧 `phase4.findings` をverdictへ折り込む。
   - PLAN `:164-166` は同ファイルを変更禁止にしている。

   v0.14で暗黙実行済みのCodex High所見は、キー無しでもv0.15のverdictに残ります。

   推奨修正: `decide-verdict.py` を許可範囲へ加え、キー無しの旧runでは `source:"codex-review"` 所見を除外し、状態を `not-active/not-configured` に正規化するcheckpoint `(h)` 回帰試験を追加する。

3. Medium — 「graphify完全同型」が既存のdisabled契約を壊す

   根拠:

   - PLAN `:38-44` は両probeを `graphify-probe.sh:31-51` の完全同型にすると指定。
   - graphifyは `:44-49` でcustom binを先に読み、`enabled:false` でも有効なcustom名を返す。
   - 現行axは `ax-probe.sh:35-41,54-56` でdisabled時にbinを読まず既定名を返す。
   - `test_ax_probe.py:223-228` は `axBin=="ax"`、`test_codex_probe.py:309-315` は `codexReviewBin=="codex"` を固定。
   - PLAN自身も `:10,84` でenabled:false意味論は不変としている。

   推奨修正: 「完全同型」を、config必須化・top-level検証・キー不在判定の順序だけに限定し、disabled時は既定bin名を維持すると明記する。

## テスト不足

4. Medium — probe→planner一体試験の4構成が重複している

   根拠:

   - PLAN `:108-110` の `{"enabled":false,"required":true}` には外側の `codexReview` がない。
   - 同じく `{}` は直後の「キー不在」と同一。
   - plannerは `codex-review-plan.py:23-30` でtop-levelの `config.get("codexReview", {})` を読む。

   記載どおりなら4構成中3構成が実質キー不在になり、disabled+requiredとキー存在の空objectを検査しません。

   推奨修正: 完全configを次の4つとして固定する: `{"codexReview":{"required":true}}`、`{"codexReview":{"enabled":false,"required":true}}`、`{"codexReview":{}}`、`{}`。

5. Medium — Phase-5優先順位は説明文だけ正しくても試験を通せる

   根拠:

   - PLAN `:111-118` は新優先順位「文」の存在を契約化。
   - 更新対象の `test_v014_contracts.py:253-264` も現状は `invalid-config < reviewState=null < 4-way` までしか比較せず、`probe-record-unavailable` と `not-configured` の実bullet順を検査しない。

   推奨修正: codex status block内の5条件を抽出し、`invalid → review-state-missing → probe-unavailable → not-configured → 4-way` の実index順を直接assertする。

6. High — handoff試験に「#59を閉じない」負契約がない

   根拠:

   - PLAN `:24` は#59据え置きを確定。
   - 新試験仕様 `:132-134` は#56 closeだけを検証し、close集合が#56だけとは要求しない。
   - 既存fake ghは `test_release_handoff.py:156-162` で任意Issueのcloseを受理する。
   - したがって#56と#59の両方を閉じる誤scriptも、#56確認だけなら通り得る。

   推奨修正: fake stateで#59をOPENにし、初回・再実行後ともclose call集合が厳密に `{"56"}`、#59がOPENのままとassertする。

7. Medium — 手動grepは機械ゲートと同じ集合ではなく、正しい実装でも残骸を報告する

   根拠:

   - PLAN `:180-181` は「test_v015と同一集合」とするが、実際のコマンドはtasks以外を無条件検索する。
   - 機械ゲート `:114-118` は歴史allowlistとseam文脈を適用する別仕様。
   - 実測で手動コマンドは10ファイルを返した。
   - `ADOPTION.md:81-82`／日本語版`:80-81` のindexing/contextModeの `auto-used` はv0.15でも正しい。
   - `README.md:25` は同一行にcontext-modeの `auto-used` とax/codexを併記するため、単純な行単位文脈判定でも誤検出する。

   推奨修正: 手動grepを廃止し、`test_v015_contracts` の同じ検査関数を直接実行する。

## セキュリティ

8. Medium — 保存境界がnot-configuredとcaller中立値の相関を強制しない

   根拠:

   - PLAN `:45-47` はnot-configured時のcaller値を `null/unknown/unknown` と規定。
   - PLAN `:49-51` はその組を「許容」するだけ。
   - `probe-record.py:113-127` はreason、home、source、auth、commandsを個別に検証する。
   - `:283-289` は受理したcaller値をresume表示へ戻す。

   `reason:not-configured` と秘密パス・`auth:"present"`・非空commandsを組み合わせた矛盾記録を受理できます。

   推奨修正: `reason=="not-configured"` 専用検証でavailable=false、既定bin、version=null、commands=[]、caller中立3値を一括強制する。

## 文書整合

9. Medium — ADOPTION本文がキー無し時の認証情報非収集と矛盾する

   根拠:

   - PLAN `:45-47` はキー無し時に `CODEX_HOME/auth.json` を探索しない。
   - しかしPLANの本文更新範囲は英語`:115-127`、日本語`:100-112`まで（`:85-87`）。
   - その直後の `ADOPTION.md:128-131` は「probe displays caller's CODEX_HOME … and whether auth.json exists」と無条件に記載。
   - 日本語版`:113-116`も同様。
   - v0.15固定文 `PLAN.md:81-84` に打消し説明がない。

   推奨修正: 本文とv0.15固定文の双方に「キー不在時はcaller情報を調べず、中立値を返す」と英日で明記する。

10. Medium — 「英日各4文の固定文」なのに日本語固定文字列が存在しない

   根拠:

   - PLAN `:79-80` は「固定文（en/ja各4文）」と宣言。
   - `:81-84` に列挙されるのは英語4文だけ。
   - `:111-114` は英日双方の固定文を契約試験で検査する。

   実装者が日本語本文と期待値を同時に作れば、誤訳や意味欠落でも自己整合して通ります。

   推奨修正: 日本語4文を実装前にPLANへ完全な固定文字列として追加し、その事前定義値を試験の期待値にする。