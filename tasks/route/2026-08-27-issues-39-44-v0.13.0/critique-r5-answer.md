メタ認知: 「最終ラウンドだから収束しているはず」という正常性バイアスと、自己申告された対応を実装可能性の証明と見なすバイアスに注意した。個別文言ではなく、入力から封印・判定・リリースまでの接続で検証した。

新規指摘あり。BLOCKER が残っているため、rev.5 のまま実装開始すべきではない。

1. [BLOCKER] Phase 0 の scope 整合結果が封印されない  
   根拠: [PLAN.md:187](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:187)、[PLAN.md:191](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:191)、[PLAN.md:215](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:215)。`--check` 後、seal 前に scope だけ変更すると、旧 scope 由来の config/impactMap と変更後 worktree が正常に封印され、CONSISTENT に到達できる。worktree digest は「どの scope で impact を計算したか」を証明しない。  
   推奨: `scopeSha` を manifest に封印し、start-run・seal-run・gate の状態確定直前で実 scope bytes と照合する。

2. [BLOCKER] manifest SHA 照合が Codex 経路だけで、Workflow と Phase 4 は改変済み manifest を使用できる  
   根拠: [PLAN.md:111](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:111)、[PLAN.md:215](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:215)。Workflow は「読み直す」だけで SHA を検証せず、Phase 4 も `phase4Required` を直接使用する（現行 [SKILL.md:389](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:389)、[SKILL.md:428](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:428)）。後段 gate の REFUSED では、不正な子処理の起動を取り消せない。  
   推奨: EVIDENCE SHA を照合して同じ bytes を解析する共通 manifest 読取処理を設け、Codex・Workflow・Phase 4 の全経路でのみ使用する。

3. [BLOCKER] #42 の「排他的3分岐」は利用可能性を含まず、順序検査でも到達可能性を証明できない  
   根拠: [PLAN.md:119](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:119)、[PLAN.md:123](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:123)、[PLAN.md:224](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:224)。`enabled/available=false` が3分岐に入っておらず、required full で実行不能時に子を起動するか、既存 availability 分岐に吸われるかが未定義。また、model/retry を「skip を含む3分岐で共有」は矛盾する。文面の出現順だけでは、別位置の先行分岐や到達不能コードを検出できない。  
   推奨: `enabled × available × mode × required × baseline` の決定をテスト可能な小さな判定処理へ分離し、真理値表で子プロセス数と state を検査する。

4. [BLOCKER] CR/LF 拒否が tracked path に限定され、実際に後段を壊す入力を通す  
   根拠: [PLAN.md:87](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:87)、[PLAN.md:174](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:174)。scope の規則キー・impact 文字列自体の改行と、untracked な改行名の影響文書が対象外である。存在検査に通った後、改行区切りの path 受け渡しで分割・欠落し得る。  
   推奨: scope 内の全 path/pattern 文字列と、tracked＋untracked の変更対象を NUL 区切りで列挙して CR/LF を拒否する。

5. [MAJOR] 「audit-scope 未導入は無影響」を判別する検査順序がない  
   根拠: [PLAN.md:8](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:8)、[PLAN.md:174](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:174)、[PLAN.md:200](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:200)。scope と metadata がともにない場合でも tracked CR/LF 検査を先に行う誤実装が可能で、非導入利用者の挙動を変える。  
   推奨: `scope absent && metadata absent` は Git 列挙前に `absent/exit 0` とする順序を仕様化し、CR/LF 名を含む非導入 fixture で固定する。

6. [MAJOR] `--base-config PATH` がパス安全契約と矛盾し、承認済み draft に束縛されない  
   根拠: [PLAN.md:169](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:169)、[PLAN.md:195](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:195)。repo 内包含を適用すれば repo 外 `mktemp` は拒否され、適用しなければ一時 path の差し替えが可能になる。`expect-config-sha none` は draft の内容を束縛しない。  
   推奨: `--base-config - --expect-base-config-sha <sha>` とし、承認済み stdin bytes を lock 内で一度だけ読み取る。

7. [MAJOR] fresh init で run-base が存在しない場合の契約がない  
   根拠: [PLAN.md:180](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:180)。初回 import は open-run より前なので、通常 `.claude/state/docaudit-run` は未作成である。事前作成済み fixture だけなら欠陥を見逃す。  
   推奨: symlink 検査後に run-base を安全な権限で作成する契約と、`.claude/state` 不在の fresh repo 試験を追加する。

8. [BLOCKER] `git push --tags` が無関係なローカル tag まで公開する  
   根拠: [PLAN.md:267](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:267)。現行は対象 tag だけを push している（[release-handoff.sh:106](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh:106)）。  
   推奨: `git push origin refs/tags/docaudit--v0.13.0:refs/tags/docaudit--v0.13.0` に限定し、無関係 tag が送信されない否定試験を置く。

9. [MAJOR] 「Issue close 3件目失敗」と「残り3件」が両立しない  
   根拠: [PLAN.md:268](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:268)。3件目の close が副作用前に失敗すれば、完了は2件で残り4件である。残り3件になるのは、成功後に応答だけ失われた場合に限られる。  
   推奨: 失敗点を「3件正常 close 後の次の読取失敗」に変更するか、3件目 close 失敗なら残り4件と定義する。

10. [MAJOR] 同期先の固定化が既存 override を破壊する  
    根拠: [PLAN.md:255](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:255)。現行は `DOCAUDIT_SKILLS_DIR` を提供し（[release-handoff.sh:198](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh:198)）、既存試験も使用している（[test_release_handoff.py:268](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:268)）。互換性変更として記載されていない。  
    推奨: 明示 override を維持した上で、その正規化先を承認済み root と照合する。

11. [MAJOR] Release title の正解が未定義で、検査が判別不能  
    根拠: [PLAN.md:136](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:136) は title 検査を要求するが、[PLAN.md:257](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:257) は tagName と body 要素しか定義していない。任意の title を検査する誤実装でも通る。  
    推奨: Release title の完全一致文字列を PLAN で一つ定義する。

12. [MAJOR] Phase 0 契約試験が check 結果の無視を検出しない  
    根拠: [PLAN.md:129](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:129)。break-lock → check → open-run の出現順だけなので、`drift/errors` でも open-run する誤 SKILL が通る。  
    推奨: `drift/errors → open-run 0回で停止` と `not-imported → open-run 継続`を意味単位で検査する。

13. [BLOCKER] `codex-dispatch.py --evidence` の実呼出し配線が契約試験にない  
    根拠: [PLAN.md:113](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:113) で必須化しているが、契約項目 [PLAN.md:129](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:129) に呼出し行の検査がない。現行呼出しにも引数がない（[SKILL.md:373](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:373)）。  
    推奨: Phase 3 の実コマンド行に `--evidence "$EVIDENCE"` があることを契約試験で固定する。

14. [MAJOR] fsync/replace 失敗試験が config の最終状態を検査しない  
    根拠: [PLAN.md:91](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:91) は lock 消滅しか要求しない。replace 前失敗では旧 config 維持、directory fsync 失敗では完成 config が既に公開済みという差を判定できない。  
    推奨: replace 前後の故障を分離し、前者は旧 config 不変、後者は完成 JSON のみ存在することを検査する。

15. [MAJOR] manifest の SHA 照合と JSON 解析が同一 bytes である保証がない  
    根拠: [PLAN.md:113](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:113)。hash 後に再度ファイルを開いて解析する実装なら、その間の置換で照合を迂回できる。静的な改変試験では検出できない。  
    推奨: manifest を一度だけ bytes として読み、その bytes の hash 検証後に直接 `json.loads` する。

16. [MINOR] `auditScope.rules` が bool を受理し得る  
    根拠: [PLAN.md:175](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md:175)。Python では bool は int の部分型なので、`isinstance(True, int)` による誤検証を通る。  
    推奨: bool を明示的に拒否し、`true`/`false` の否定試験を追加する。

## (A) 計画自体の欠陥

PLAN を直してから実装すべきもの: **1〜11**。  
特に **1、2、3、4、8** は封印・到達制御・外部公開境界の BLOCKER であり、実装開始を承認できない。

## (B) worker 指示で吸収できる細部

- **#12:** 「Phase 0 契約試験に、drift/errors では open-run を呼ばず停止し、not-imported のみ継続する動作検査を追加する。」
- **#13:** 「Phase 3 の codex-dispatch 実呼出しへ `--evidence "$EVIDENCE"` を必須追加し、コマンド行を契約試験で固定する。」
- **#14:** 「原子書込みの故障試験を replace 前後に分け、旧 config または完成 JSON のどちらかだけが残ることを検査する。」
- **#15:** 「manifest は一回だけ bytes 読取し、同じ bytes で SHA 検証と JSON 解析を行う。」
- **#16:** 「`auditScope.rules` は bool を除外した整数のみ受理し、true/false を否定試験へ追加する。」

読み取りのみで確認し、ファイルは変更していない。