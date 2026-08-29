メタ認知: 計画書・事前調査の権威に引っ張られず、実行経路と現行試験を優先しました。逆に、単なる表現差を回帰として膨らませないよう実害のある項目だけに絞りました。

結論: この PLAN は現状のまま承認できません。Critical はありませんが、High 5件、Medium 7件です。修正は行っていません。

## 1. バグ・回帰

1. High — 旧 run の resume で key-gate を迂回する

   根拠:

   - `PLAN.md:43-44` は「rebind は無変更」。
   - `probe-record.py:147-154` は記録形式を `schemaVersion=1` のまま受理し、`:276-290` は保存済みの `available/reason` をそのまま復元する。
   - `SKILL.md:68` は resume 後の Phase 4 で availability を rebind から復元可能としている。
   - `codex-review-plan.py:25-29` はキー不在を `{}` にし、`:32-43` は `available=true` なら incremental で `action:"run"` を返す。
   - 実測でも、`codexReview` を持たない `engine-shas.json` と `available=true` の組合せが `{"action":"run",...}` になった。

   v0.14で開始したキー無し run の記録が `available:true/reason:"ok"` なら、v0.15で再開後も Codex が起動し得ます。

   推奨修正: resume 時に封印済み config と旧記録を照合し、対象キーが無ければ ax/codex とも必ず `available:false/reason:not-configured` に正規化する。

2. High — `--config` 省略時の単体 probe は依然として tool を探索・起動する

   根拠:

   - `ax-probe.sh:25-31` は `state="enabled"` で始まり、設定指定時だけ config を読む。
   - `codex-probe.sh:26-32` も同じ。
   - `test_ax_probe.py:161-187` と `test_codex_probe.py:180-206` は `cfg_omitted` を `ok` 側に分類している。
   - 対して PLAN `:39` は「読めない設定の `invalid-config` 防御は不変」と誤認している。

   推奨修正: `--config` 省略・空パス・不存在・壊れたJSONをすべて `invalid-config` とし、tool 未起動を固定する。

3. Medium — Phase-5 の優先順位が review-state 記録失敗を隠す

   根拠:

   - PLAN `:54-55` は `invalid-config → not-configured → review-state-not-recorded` を指定。
   - `SKILL.md:754-758` は現在、`reviewState=null` を明示的な記録欠落警告にしている。
   - `probe-record.py:279-290` は probe reason と review state を独立して復元する。

   probe の `not-configured` は保存できたが `codexReviewState` の保存だけ失敗した場合、⚠警告が正常な💡表示に隠れます。

   推奨修正: `invalid-config → review-state-not-recorded → probe-record-unavailable → not-configured → 4-way` にする。

## 2. 互換性

4. Medium — `required:true` の probe→Phase-4 一体契約がない

   根拠:

   - PLAN `:108-110` の判定表に `required:true` がない。
   - `test_codex_probe.py:166-178` の入力にも `required` がない。
   - `test_codex_review_plan.py:33-45` は probe 出力ではなく availability を手入力している。

   `{"codexReview":{"required":true}}` を probe が誤って無効扱いしても、下流試験は通り得ます。

   推奨修正: `required:true` と `enabled:false,required:true` を含め、probe の stdout を Phase-4 planner に直接渡す一体試験を追加する。

5. Medium — ADOPTION の「旧挙動維持」案が実際には挙動を強化する

   根拠:

   - PLAN `:68` は旧挙動維持として `codexReview` と「必要なら `required:true`」の追加を案内。
   - `config-schema.md:36` は `required:true makes a non-completed review REFUSED` と規定する。

   旧暗黙挙動は best-effort であり、`required:true` は同じ挙動ではありません。

   推奨修正: 旧 best-effort 維持は `codexReview:{}`、`required:true` は別の fail-closed 強化策として明確に分離する。

## 3. テスト不足

6. High — 判定表が「tool を一切起動しない」を検証しない

   根拠:

   - `test_ax_probe.py:175-187`、`test_codex_probe.py:194-206` は呼出し印を用意しているが、未起動を確認するのは invalid 分岐だけ。
   - PLAN `:108-111` は stdout JSON 比較しか要求していない。

   tool を実行した後で正しい `not-configured` JSON を出す誤実装でも通ります。

   推奨修正: `absent` は呼出し0回、空 `{}` は ax 1回・codex 2回と、偽toolの呼出し回数を厳密に固定する。

7. High — 歴史契約と現行契約の分割漏れでフルスイートが失敗する

   根拠:

   - PLAN `:95` は v0.13.2試験の件数を3→5にする指定だけ。
   - `test_v0132_contracts.py:239-244` は ax/codex reason 集合を `not-configured` なしで完全一致固定。
   - 同 `:300-306` は段落名も3 seamだけに限定。
   - PLAN `:55` は優先順位文を変えるが、`test_v014_contracts.py:253-264` は旧文と旧順序を完全一致固定している。
   - PLAN `:92-95` の更新対象にこの優先順位試験がない。

   推奨修正: 現在の SKILL/schema/init を読む断言をすべて `test_v015_contracts.py` に移し、旧版試験は旧ADOPTIONブロックや固定fixtureだけに限定する。

8. Medium — `not-configured` 分岐の純ASCII・単一行契約が未検証

   根拠:

   - 既存試験 `test_ax_probe.py:82-103`、`test_codex_probe.py:84-107` は必ず seam key を書くため新分岐を通らない。
   - PLAN `:80-82,108-111` は項目集合とJSON値だけを要求する。

   特にCodexは caller path を含むため、`ensure_ascii=False` 回帰を見逃せます。

   推奨修正: 非ASCII・不正byteを含む `CODEX_HOME` で absent-key 分岐を実行し、stdoutが純ASCII、終端LF 1本、JSON 1行であることを固定する。

9. High — 新しい v0.15 release-handoff が一切自動試験されない

   根拠:

   - PLAN `:100-102` は新scriptを作る。
   - PLAN `:99,130` は既存 handoff 試験を変更禁止。
   - `test_release_handoff.py:14-24` は旧route、`docaudit--v0.14.0`、旧titleのみを対象にする。

   フルスイート green でも、誤tag、誤Issue close、再実行失敗、同期失敗を検出しません。

   推奨修正: 既存の偽GitHub環境を再利用し、v0.15 script専用の handoff 契約試験を追加する。

## 4. セキュリティ

10. Medium — キー不在でも `CODEX_HOME/auth.json` を探索・記録する

   根拠:

   - PLAN `:40-42` は `not-configured` でも caller 3項目を通常どおり算出する指定。
   - `codex-probe.sh:51-59` は `CODEX_HOME/HOME` を読み、`auth.json` の存在を確認。
   - `:61-67` は利用者パスと認証ファイル有無を出力し、`probe-record.py:283-289` が再表示する。

   opt-inしていないrepoでも、利用者パスと認証状態の収集が残ります。

   推奨修正: `not-configured` は caller 探索より前に確定し、8項目形を `home:null/source:"unknown"/auth:"unknown"` で維持する。

通常監査経路の config path containment には指摘なしです。今回の変更は `SKILL.md:13,25-28` から既存の path 検証へ進む順序を変えません。ただし、前述の単体 `--config` 省略防御は別問題です。

## 5. 文書整合

11. Medium — 残骸列挙と grep gate が既知の矛盾を見逃す

   根拠:

   - PLAN `:71-72` はADOPTION本文だけを更新対象にする。
   - `ADOPTION.md:83-84` は ax を `auto-used when installed`、Phase-4 Codexを `conditional-force` と記載。
   - `ADOPTION.ja.md:82-83` にも同義の記載がある。
   - `ax-probe.sh:4-6`、`codex-probe.sh:4-7` のヘッダも「toolがあれば有効」と読める。
   - これらは `investigate-report.md:354-429` の残骸一覧にない。
   - PLAN `:88-91,144-145` の検索語は `absent key ... enabled by default` / `enabled by default` だけで、上記表現を捕捉しない。
   - PLAN `:112` の走査数 `N ≥ 1` も全対象を走査した証明にならない。

   推奨修正: tracked fileの固定対象集合を全走査し、`auto-used`、`conditional-force`、日本語同義表現も検出対象に加え、上記6箇所を修正範囲へ入れる。

12. Medium — ADOPTION固定文③の「4 seamすべてでbin検証」は事実誤認

   根拠:

   - PLAN `:69` は `bin validation are unchanged for all four seams` と固定。
   - `config-schema.md:34` の `contextMode` は `{enabled}` だけ。
   - 同 `:201-208` も context-modeには `bin` が不要と明記する。

   推奨修正: 「`enabled:false` / `invalid-config` は4 seamで不変、bin検証は indexing/webExtract/codexReview の3 seamで不変」と分離する。

補足: probeの単体実行確認は、この読み取り専用環境がシェルの一時ファイル作成を拒否したため完走できませんでした。この環境制約に依存する指摘は採用しておらず、上記は現物の分岐・既存試験・下流判定器の実測に基づきます。