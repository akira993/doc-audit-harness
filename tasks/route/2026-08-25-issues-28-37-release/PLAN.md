# PLAN — Issue #28（Phase-3 検証器の codex exec 化）+ #37（レポート書き込み競合）+ 保留リリース一括実施

rev.12（実装仕様・最終）— 2026-08-25 / 第 2 巡 Sol 批判 R5（MAJOR 2・MINOR/INFO 7、
第 2 巡上限到達）を boss 最終裁定で反映。残 2 MAJOR はいずれも Sol 提示の救済策
（receipt 機構・A/B digest の分離）をそのまま採用して解決。実装忠実性は Stage ごとの
boss 全行 diff レビューと手順 5 の `codex exec review`（Sol `high`）で検証する。
ユーザー決定により #37 は**軽量案（gate-writes-report）**。旧 rev.6（finalizer 方式）は第 1 巡の
記録として REVIEW.md に保存。機構非依存の確定事項は継承。Sol は第 2 巡 R1 #15 で「finalizer
固有の問題群（gate-result/nonce/intent/done・重複 finalizer・manifest 差替え）は消滅、A/B の
baseline 矛盾も解消」を確認済み。

**脅威モデル境界**: 防御対象は「LLM orchestrator の事故的な誤順序・手順逸脱・並行 run の競合」。
同一権限の完全に敵対的なローカルプロセスへの暗号学的保証は原理的に不能で目標外
（Issue #22 の残余境界と同一線上）。

## 1. 目的

1. **#37**: gate の lock 解放後にレポートが書かれることで並行 run の sealed tree digest を壊す
   競合、および同日 2 run の suffix 上書き競合を、**report 書き込みを gate 自身（lock 保持中）に
   移す**ことで解消する。旧実装での原因実証と修正後の回帰テストを分離して立証する（§8）。
2. **#28**: Phase-3 doc 検証器を opt-in で doc ごとの `codex exec -s read-only --output-schema`
   起動に置き換える提案の実機検証・プロトタイプ・小規模 A/B を行い、「採用（実装完了）」または
   「ユーザー確認済みの据え置き」に決着させる。verdict は「試行ごと私有ディレクトリの一時出力 →
   機械検査 → write-verdict.py の原子公開」の 2 段階（§11）。
3. **リリース**: 二段戦略 — (i) `docaudit--v0.11.0` タグを `01344ea` に遡及＋Release、
   (ii) 今回分を新版として bump→PR→タグ→Release→skills-dir 同期 — を fail-closed な handoff
   スクリプト（ユーザー実行）として用意する（§12）。

## 2. 入力・参照資料

- `tasks/route/2026-08-25-issues-33-34-35/NEXT-SESSION-PROMPT.xml`（指示書）
- Issue #28 本文＋コメント（mdq read-only BROKEN 実機記録 2026-08-19）／Issue #37 本文
- `skills/audit/scripts/decide-verdict.py`（:281-288 pre-lock REFUSED / :293-316 owned 判定 /
  :394 指紋再照合 / :520 unlink / :523-525 sibling / :551-557 except path）
- `skills/audit/scripts/open-run.py`・`tree-digest.py`・`write-verdict.py`・`check-verdicts.py`・
  `start-run.py`・`docaudit_cache.py`・`docaudit_paths.py`
- `skills/audit/SKILL.md`（Phase-5 gate+report・:509 記述（要修正）・:516 suffix 契約・
  checkpoint/release 義務・returns 契約 :351-365）
- probe: `probes/results.md`／Sol 批判第 1 巡: `critique-r1..r5-answer.md`（機構非依存の指摘は
  本 rev にも適用済み）
- メモリ: docaudit-v0.11.0-release-state / verdict-persistence-v0.9.0 / codex-review-cli-seam-pivot /
  codex-background-kill-collab-wait / docaudit-release-procedure / docaudit-deploy-channels

## 3. 担当（boss）

Fable/Opus（本セッション）。計画・レビュー・裁定・route-close のみ。実装は書かない。

## 4. 実行者（worker）

Sol/Terra/Luna（`direnv exec . codex exec ...`、CODEX_HOME=~/.codex-doc-audit-harness）。

- 計画批判: Sol `high`（`-s read-only`、第 2 巡・上限 5 往復）。
- Stage 1（#37 実装）: **Terra `medium` 起点**（軽量案は既存 gate 内への処理追加が主で、
  トランザクション新設がないため。rev.6 時の Sol medium 格上げは撤回）。不足時は絶対順位表
  どおり Terra `high` → Sol `medium` → Sol `high`。
- Stage 2（#28 プロトタイプ＋A/B）: Terra `high` 起点。
- Stage 3（版 bump・docs・handoff）: Luna `medium`。handoff の SHA 検証と分岐テストは
  Stage 1 セッションの resume で Terra が書いてもよい。
- 実装は同一 codex セッションを resume で継続（session ID は REVIEW.md に記録）。
- 初回 workspace-write 起動は AGENTS.md 規約の上書き承認待ちで停止（前セッション実測）→
  「PLAN 許可パス内に限る包括承認・単独作業・collab 不使用」を resume で流す。

## 5. 成果物

1. #37 修正一式: `decide-verdict.py`（report 書き込みの内蔵＋sibling 実行順の移動＋owned 判定
   AND 化＋EVIDENCE 必須キーの pre-lock 検証）、新ヘルパー `write-template.py`（receipt 機構
   込み）、`start-run.py`（report 候補生成規則＋reportDate の seal）、`open-run.py`
   （previousReportStatus 表面化）、`SKILL.md`（Phase-5 手順の書き換え・:509 記述修正・
   テンプレート事前生成手順・release 義務 2 経路）、原因実証記録＋回帰・故障注入テスト
2. #28 の決着物（採用時: dispatcher 実装＋A/B 記録／据え置き時: Issue コメント文面＋REVIEW 記録。
   Issue close は実装マージ時のみ）
3. 新版 bump（版文字列・engine-shas.json 新エントリ・docs 整合）
4. PR（ユーザー承認でマージ）
5. `release-handoff.sh`（§12 の fail-closed 要件）＋分岐テスト
6. REVIEW.md（セッション ID・各ラウンド裁定・A/B 記録・route-close marker）

## 6. 完了条件（DoD）

- [ ] #28: 実機検証の結果が REVIEW.md に記録され、「実装完了（A/B 根拠つき）」または
      「ユーザー確認済みの据え置き（Issue コメント反映）」に到達。
- [ ] #37: 旧実装での原因実証（記録）と修正後の回帰テスト（直列化・suffix 原子性・故障注入）が
      揃い、マージ可能な状態。
- [ ] テストスイート全 green（`python3 -m unittest discover -s tests -t .` — 着手前実測 298 件 OK）。
- [ ] リリース: handoff スクリプトが用意され、ユーザー実行後にタグ（v0.11.0@01344ea・新版@承認済み
      merge commit）・Release・skills-dir 同期一致（§12 の管理対象照合）まで完了。
- [ ] route-close: REVIEW.md に close marker。doc-audit.json 不在のため、変更した公開挙動に対応する
      文書（`skills/audit/references/config-schema.md` / ADOPTION 英日 / SKILL.md）の同時更新で代替。
- [ ] メモリ更新: `docaudit-v0.11.0-release-state.md` の未完了項解消と新版記録。
- [ ] 既存テスト期待値の変更は 1 件ごとに §10 との対応を worker が列挙。

## 7. 変更範囲

**許可パス**（この repo のみ）:
- `skills/audit/scripts/`（**plan-dispatch.py**（#28 採用配線: phase3Backend を解決し
  cache_qualification へ渡す最小変更 — Stage 2c で boss 承認済み）/ decide-verdict.py /
  start-run.py / **open-run.py**
  （previousReportStatus 表面化 — 2R4 #2 で boss 承認済みの必須変更）/ 新規 write-template.py /
  #28 採用時の codex dispatcher。generic-layers.py は self-contained 契約内のみ。
  **tree-digest.py・write-verdict.py は原則変更しない**（2R1 #12 — 変更が必要になった場合は
  boss 承認を経て本リストに追記する））
- `skills/audit/SKILL.md`・`agents/`・`skills/audit/references/`
- `tests/`・`docs/ADOPTION.md`・`docs/ADOPTION.ja.md`（公開挙動が変わる場合のみ）
- 版文字列ファイル＋`engine-shas.json`
- `tasks/route/2026-08-25-issues-28-37-release/`（記録。コミットは `git add -f`）

**禁止パス／禁止事項**:
- generic-layers.py の repo 内 import。report_pattern に触る場合は 5 複製＋契約テスト同時更新
- `.gitignore`／`~/.claude/skills/docaudit/` 直接書き込み（同期は handoff のみ）
- 実体の student-pathway-ops への書き込み（A/B は隔離コピーのみ）
- セルフマージ・`gh pr merge`・`gh release create` の直接実行
- durable 規約変更がなければ SSoT は 0 ファイル更新

## 8. 検証コマンド一式

```bash
# フルスイート（毎 stage 完了時 + 最終。リリース時は §12 のとおり merge commit 上でも再実行）
python3 -m unittest discover -s tests -t .

# #37 の立証は 2 部構成:
#  [原因実証 — 旧実装に対して 1 回だけ実行し、出力を REVIEW.md に記録]
#   旧順序: A open→seal→gate（lock 解放）→ B open→seal → A が report を docs/logs/ へ書く →
#   B gate が digest mismatch REFUSED（tests には残さない）
#  [回帰テスト — 修正後の恒久テスト]
#   - 直列化: A の gate（report 書き込み含む）実行中に B open が exit 4／--break-lock が
#     gate-running 拒否（プロセス間 flock は子が取得後 pipe で READY を返す方式）
#   - 正常系: gate が report を書いて unlink → B open→seal→gate が CONSISTENT
#   - suffix 原子性（実装機構と同じ経路で — 2R1 #12: test_decide_verdict.py の実経路試験として。
#     test_report_matcher_contract.py は候補規則の純粋契約のみ）: 候補作成時 EEXIST 注入で
#     次候補へ正しく進む／既存 report 非破壊
#   - lock 延長の統合試験（2R1 #11）: sibling scan（最大 30 秒・timeout 含む）中も B open と
#     --break-lock が拒否され、scan 完了後に gate が lock を解放することを実プロセスで固定
#   - 順序の固定: sibling scan → 最終再照合 barrier（:482-496 一括 — lock/HEAD/digest/history/
#     anchor/config）→ 状態更新 → report link の順。barrier の各対象（digest 対象ファイル・
#     history・anchor・config・lock）を scan 中に変更する注入試験を個別に持つ（2R3 #1）／
#     reportStatus の not-requested / pending→written / written-durability-unknown / failed 遷移
#   - receipt ライフサイクル（2R5 #1）: helper 失敗（EEXIST 含む）→ receipt {failed:true} →
#     gate が reportless 縮退 / helper クラッシュ（invalidate-first の各時点）→ 最悪 reportless /
#     正常 receipt → 採用
#   - previousReportStatus（2R4 #2、2R5 #3/#4）: 新 lock 取得後の再読（先行 gate の
#     pending→written→unlink と重ねる決定論的試験）/ pending・failed・
#     written-durability-unknown の表面化 / REFUSED reportless が not-requested 直行で
#     pending を残さないこと
#   - 追加故障注入（2R2 #9）: sibling scan の決定論的フック中に digest 対象ファイルを変更 →
#     最終再照合が REFUSED / link 成功後の dir fsync・last_run 更新・unlink の各失敗が verdict を
#     反転させない / write-template.py の既存ファイル拒否・--replace・重複起動 / 重複 token・
#     不正 UTF-8・サイズ上限超過
#   - 故障注入: report 書き込み失敗（親 dir 不可・EXDEV 等）→ reportWriteError 警告つきで
#     run は完走 / テンプレート欠落 → 警告つき reportless / reportPath 省略 → reportless /
#     owned REFUSED でも report 生成 / pre-lock REFUSED の orchestrator release /
#     report 書き込み中 kill → stale lock → --break-lock 回収
python3 -m unittest tests.test_decide_verdict tests.test_start_run tests.test_wp12_contracts -v

# #28 dispatcher 失敗系・正常系（採用時）: §11 のとおり
# handoff 分岐テスト（PATH shim の偽 git/gh/rsync、専用一時宛先 — 分岐一覧は §12-5 が正）
```

quality gate: unittest 全 green が唯一の機械的ゲート。加えて boss が全行 diff レビュー。

## 9. #37 確定設計 — gate-writes-report（軽量案）

方向 (b)（digest 除外）は恒久不採用（第 1 巡 R1 #14）。(a) 直列化 + (c) suffix 原子化を、
**lock をプロセス境界を跨がせずに gate 内で完結**させることで実現する。

### 9.1 機構

1. **orchestrator は gate 起動前に report 本文を事前生成**する。gate 出力に依存する値
   （verdict・reason・counts・historyStatus・warnings・siblingScan・anchor 前進の有無）は
   `{{GATE_*}}` プレースホルダで書く。それ以外（change set・per-doc verdicts・各 status line・
   レビュー要約等）は gate 前に確定しているため実体を書く。
   **テンプレートの受渡しは機械化する**（2R1 #4、2R2 #3、2R4 #1）: 新ヘルパー
   `write-template.py` は `--repo-root` と `--runid` を必須引数に取り、書込み先を
   **共有 path validator（docaudit_paths.py）で
   `<repo>/.claude/state/docaudit-run/<runid>/report-template.md` に自己束縛**する
   （親 symlink 不在検証込み — LLM が誤った `$RUN_DIR` を渡しても任意ディレクトリへ
   書けない）。書込みは `O_NOFOLLOW|O_CREAT|O_EXCL`。
   **鮮度は receipt で機械化する**（2R5 #1 — `--template-sha` の LLM 経由受渡しは廃止）:
   helper は**毎回の起動**で `$RUN_DIR/report-template.receipt.json` を原子更新する — 成功時は
   `{sha256, bytes, failed:false}`、**失敗時（EEXIST 含む）も `{failed:true}` で必ず無効化**する。
   gate は receipt を自分で読み（template と同じ規律 — O_NOFOLLOW・単一 fd・通常ファイル検査）、
   `failed:false` かつ sha が template 実体と一致する場合のみ採用（receipt なし・failed・不一致は
   `reportTemplateMissing`/`reportTemplateInvalid` 警告つき reportless）。**receipt の更新順序は
   invalidate-first**: 起動直後にまず `{failed:true}` を書く → create/replace を試みる → 成功時に
   成功 receipt を書く（どの時点でクラッシュしても旧 `{sha, failed:false}` が残らず、最悪でも
   reportless に縮退する）。sha は orchestrator の手を経由しないため、「helper 失敗を見落として
   旧 template を続用」する手順逸脱は機械的に採用不能になる。**既存 path は既定で
   拒否**（unlink→再作成はしない — 重複・遅延起動が先行テンプレートを黙って置換できてしまう）。
   正当な再生成は明示 `--replace` のみ: 既存が RUN_DIR 内の通常ファイルであることを O_NOFOLLOW
   検査のうえ、temp+atomic rename で差し替える（2R3 #2 の `--template-sha` 引数方式は 2R5 #1 の
   receipt 機構に置き換え — 上記）。
   gate は `O_NOFOLLOW` で一度だけ open した同一 fd 上で fstat（通常ファイル）・サイズ上限・
   UTF-8 検査を行って読む。**サイズ上限は全経路で固定**（2R3 #7）: helper の書込み上限 2MB・
   gate の bounded read（上限+1 byte で超過検知）・置換後出力の上限 4MB。
2. **プレースホルダ契約**（2R1 #5、2R2 #4）: 置換は**原文を一度だけ走査する allowlist 方式**
   （置換値に token が含まれても再置換しない）。token は固定 allowlist のみ・verdict 別に
   必須/禁止 token を契約化（例: REFUSED では counts/historyStatus/siblingScan token は
   禁止または `n/a` 固定）し、**各 token の正確な出現数**（既定 1 回）も検査する。
   **置換値は gate が型つき固定形式で描画**する（verdict は enum 文字列・counts は JSON・
   reason 等の自由文字列は **JSON 文字列化方式のエスケープ**で単一行化し、Unicode 行区切り
   （LS/PS）・双方向表示制御文字は拒否またはエスケープ — 2R4 #7 で方式を一意化）— 置換値
   経由で偽の verdict/status 行や表示偽装を report に挿入できないようにする。
   **report の front matter 日付（created/updated）は必須 token `{{GATE_REPORT_DATE}}`**とし、
   gate が sealed reportDate で置換する（2R4 #5 — orchestrator の実体書きでは sealed 日付との
   一致を保証できない）。
   **helper 失敗時の無効化は receipt が担う**（2R4 #6 → 2R5 #1 で機械化）: 失敗起動も receipt を
   `{failed:true}` に更新するため、旧 sha 続行の経路は存在しない（テストで固定）。
   **token 出現数は per-token 契約表で指定**（2R5 #6 — 既定 1 回、`{{GATE_REPORT_DATE}}` は
   created/updated の 2 回。worker が契約表を確定）。エスケープは JSON 文字列化に加えて
   **HTML 有効文字（`<` `>` `&`）も Unicode escape** する（2R5 #7 — `<br>` 等による表示偽装を防ぐ）。必須 token 欠落・未知 token・
   出現数不正は `reportTemplateInvalid` 警告つき reportless に縮退（黙殺しない）。
3. **decide-verdict.py の実行順序**（2R1 #1/#2/#7、2R2 #1/#2 で最終確定）:
   全検証（manifest SHA・changeSetSha・verdicts・returns …）→ verdict 確定 →
   sibling scan（現行 :523-525 の unlink 後実行を手前へ移動。最大 30 秒）→
   **最終再照合 barrier（永続状態更新の直前 — 2R2 #1、2R3 #1: digest 単独ではなく、現行
   :482-496 の一括再照合＝lock identity・HEAD/digest・history・anchor・config を不可分の
   barrier として scan 後に置く。scan 中の worktree・state・config・lock の変更をすべて検知
   してから状態を確定する。各対象の変更を注入する試験を §8 に含める）**→
   **永続状態更新**（history/anchor/last_run。last_run に `reportStatus:"pending"`。
   reportPath 未構成の run は `"not-requested"` — 2R2 #7）→ テンプレート読込・置換 →
   **suffix 候補ループで公開**（RUN_DIR 内 temp に全量書き込み・fsync → `link(2)` で候補名へ
   原子リンク、EEXIST は次候補。公開 mode 0644 相当・宛先 dir fsync・成功後 temp unlink）→
   last_run の `reportStatus` を `written`+path / `failed`+code に更新 → unlink(lock) → stdout。
   **状態確定後は判定を反転させない**（2R2 #2）: 永続状態更新の commit 後に起きる失敗
   （report 公開・dir fsync・reportStatus 更新・unlink）はすべて局所捕捉して warning に縮退し、
   verdict・stdout は確定済みの値を返す。link 成功後の dir fsync 失敗は「report は可視」という
   実在状態に合わせ `reportPath` を返しつつ `reportDurabilityUnknown` 警告を付す。
   reportStatus 更新失敗・unlink 失敗も warning（unlink は必ず試行する）。
   digest 再照合は link より前に完了しているため gate 自身の report が再照合を壊すことはなく、
   report 公開は状態確定後のみ（pending は機械判定可能）。親 dir 不在時は検証済み repo path 内に
   限り作成。EXDEV は失敗を表面化。
4. **report I/O の局所例外境界**（2R1 #6）: テンプレート読込・decode・mkdir・write・fsync・
   link・temp 後始末の失敗は**局所で捕捉**して `reportWriteError` 等の warning に縮退させ、
   外側 except（REFUSED 化・reason 記録・unlink）へ漏らさない。owned REFUSED 中の report
   失敗も元の reason 記録と unlink を必ず実行する。
5. **stdout schema と warning code の全列挙**（2R1 #9、2R3 #4）: `reportPath` は公開成功時
   （link 成功）のみ返す。固定 warning code は次で完結させる: `reportWriteError` /
   `reportTemplateMissing` / `reportTemplateInvalid` / `reportDurabilityUnknown` /
   `reportStatusUpdateFailed` / `lockReleaseFailed`。**耐久性不明は永続化する**: dir fsync 失敗時の
   last_run は `written-durability-unknown` とし、stdout 消失後も機械判定できる。
   `reportStatus` の終端値は `not-requested` / `pending` / `written` /
   `written-durability-unknown` / `failed`（REFUSED でも reportless 要求時は `not-requested`、
   公開失敗時は `failed` — 2R3 #5）。**`pending` は「確定不能を示す回復対象の終端」として
   正式に認める**（2R4 #2 — I/O 障害下で別 status への更新成功は保証できない。status 更新失敗
   時は pending が残る）: `open-run.py` は次回 open 時に前回 last_run の
   `reportStatus ∈ {pending, failed}` を検出したら自身の stdout JSON に
   `previousReportStatus` として表面化し、SKILL は orchestrator にそれをユーザーへ報告させる
   （黙って上書きして異常記録を消さない）。表面化の対象は `pending` / `failed` /
   `written-durability-unknown`（2R5 #3）。**読取りは新 lock 取得成功の後に行う**（2R5 #4 —
   先行 gate の pending→written→unlink と重なって解消済み異常を報告しないため。pipe/barrier に
   よる決定論的試験を含める）。※この検出追加のため open-run.py は変更対象（§7 に反映済み）。
6. **lock unlink 失敗の回収契約**（2R3 #3）: unlink 失敗は `lockReleaseFailed` 警告（verdict は
   反転しない）。SKILL に「この警告を受けた orchestrator は gate 終了後に所有確認つき
   `open-run.py --release --runid` で回収し、それも失敗したら停止して `--break-lock` を
   ユーザーに案内する」を契約化する。
7. **reportDate は seal 時に固定**（2R3 #6）: `<YYYY-MM-DD>` の値は start-run.py が runid の
   UTC タイムスタンプから導出して manifest に `reportDate` として固定し、gate は sealed 値のみ
   使う（front matter の日付とも一致させる）。現行の未検証 `--date` 系入力は使わない/除去する。
8. **lock は常に単一プロセス内で保持**: `--break-lock` は gate+report 全区間で flock により
   `gate-running` 拒否（第 1 巡 R1 #1 の穴が消滅）。gate-result.json・nonce・WAL・one-shot・
   finalizer・`--expect-ino`・`--abandon-report`・done/intent は**導入しない**。
9. **report 候補生成規則と reportDate は seal 時に manifest へ固定**（start-run.py —
   `[_NN]` 挿入位置を含む構造＋§9.1-7 の日付）。
10. **owned 判定の AND 化は維持**（第 1 巡 R2 #4）。**EVIDENCE 必須キー（lockIno 含む）の
   型・存在検証は lock open より前に行う**（2R1 #8 — 欠落・不正は pre-lock REFUSED となり
   orchestrator の release 義務で回収される）。検証を通った後の真の inode 不一致（non-owned）は
   release せず、回収は `--break-lock` に帰着することを明文化。

### 9.2 失敗時の意味論（fail-loud・ただし report は非 evidence）

- **report 書き込み失敗**（親 dir 作成不可・EXDEV・容量等）: run を REFUSED にはしない。
  永続状態更新と unlink は行い、stdout の `warnings` に `reportWriteError` を載せて表面化する
  （report は人間向け出力であり evidence ではない。書けない事実は隠さないが、監査結果は有効）。
- **テンプレート欠落**（orchestrator の手順逸脱）: `reportTemplateMissing` 警告つきで reportless
  完走（黙殺しない）。
- **reportPath 構成なし**: reportless run（既存 fixture 挙動の維持 — 第 1 巡 R4 #3 の boss 決定）。
  無効テンプレート（候補生成規則として解釈不能）は seal 時に拒否（fail closed）。
- **owned REFUSED**: report を書けるのは「manifest SHA・seal・候補生成規則の検証が成立した
  **後**に発生した REFUSED」に限定（2R1 #3 — それ以前の REFUSED は sealed 候補規則自体を信頼
  できないため reportless。config SHA 不一致も reportless）。**commit 順序を固定**（2R2 #5、
  2R5 #5）: report を書く REFUSED のみ REFUSED reason と `reportStatus:"pending"` を last_run に
  永続化 → REFUSED 用 token 契約で report 公開（局所例外境界）→ `reportStatus` 更新 → unlink。
  **reportless の REFUSED（reportPath 未構成・config SHA 不一致等）は `not-requested` を書き、
  pending を経由しない**（不要な回復警告を次 run に残さない）。各段の失敗は局所捕捉し、
  reason 記録の失敗でも unlink を必ず試行する（現行 except の「last_run 書込みと unlink が
  同一 try 内」という構造は分離する）。
- **pre-lock REFUSED**（EVIDENCE/identity 不正、:281-288）: gate は lock を検証できないまま
  終了する。orchestrator は既存の `open-run.py --release --runid` で閉じる（SKILL の
  terminal-path release 義務に明記 — 第 1 巡 R2 #3）。
- **report 書き込み中の process kill**: stale lock（flock 保持中に死亡）→ 既存の `--break-lock`
  回収に帰着。final 名は link(2) 原子性により常に完全内容。
- **状態更新後・stdout 出力前の死亡**: 現行実装と同一の既存挙動（anchor は前進済み・再実行は
  lock 消失で REFUSED）。本タスクの回帰ではないため機構追加はしない（第 2 巡でスコープ外と明記）。

### 9.3 SKILL.md の変更

- **lock 所有判定の公開契約を AND 化に合わせて更新**（2R2 #6 — SKILL:617 付近の現行 OR 記述を
  runid・fd inode・path inode・期待 lockIno の全一致に修正。実装と公開手順の矛盾を残さない）。

- Phase-5: 「gate 起動前にテンプレートを生成して RUN_DIR に置く → gate を起動 → stdout の
  reportPath / warnings を報告する」に書き換え（orchestrator が report を書く手順は削除）。
- :509 付近の「report は sealed digest を無効化できない」→「report は gate が lock 保持中に
  書くため、並行 run の sealed digest と競合しない」に修正。
- suffix 契約 :516 は文言維持（実装が gate 内へ移る旨を追記）。
- `--break-lock` が gate+report 区間で拒否されることを明記。checkpoint/terminal-path release
  義務は **2 経路**に整理（2R4 #3 — 矛盾解消）: (i) pre-lock REFUSED、(ii) gate が
  `lockReleaseFailed` 警告を返した場合の post-gate 回収（所有確認つき `--release --runid` →
  失敗時は停止して `--break-lock` 案内）。
- 前回 run の `previousReportStatus`（pending/failed）が open-run から報告された場合の
  ユーザー通知手順を追記（§9.1-5）。

### 9.4 #28×#37 干渉

codex 検証器の書き込み先は RUN_DIR（digest 除外済み）で直交。両者とも SKILL.md Phase-3/5 を
書き換えるため実施順は #37 → #28 の直列とし、#28 は #37 修正後の SKILL を前提に書く。
テンプレート事前生成は Phase-3 の backend に依存しない。

## 10. 意図的差分リスト（既存テスト期待値の変更を許す範囲）

軽量案では gate の公開後条件（**通常時または回収完了時**に lock は解放済み — 2R4 #4:
unlink 失敗時は lockReleaseFailed 警告と回収契約による）が維持されるため、第 1 巡で
列挙した lock 生存期待の変更（test_start_run:167-179・test_decide_verdict の cache 試験・
test_wp12_contracts の release 契約）は**原則不要**。許す変更は:

- `tests/test_decide_verdict.py`: gate stdout への `reportPath`／新 warnings の追加・sibling
  実行順の移動・report 生成の副作用に伴う期待追加
- owned 判定 AND 化で OR を前提とする既存期待があれば、その変更（worker が特定して列挙）
- `tests/test_start_run.py`: 候補生成規則の seal 追加に伴う manifest 期待
- `tests/test_scaffold.py:200-219,278-287` の 0.10.1→0.11.0 固定期待 → 新版更新＋0.10.1→最新の
  飛び越し更新回帰テスト追加
- **report 日付の UTC 化に伴う可視変更**（2R4 #9 — ローカル日付と異なる時間帯ではファイル名・
  front matter 日付が従来と変わりうる）: 関連する既存期待の変更を許す。UTC 日跨ぎ・不正暦日の
  試験を追加
- lock 回収経路のテスト（2R4 #4）: lockReleaseFailed 検出 → gate 終了後 `--release --runid`
  成功経路／release も失敗 → 停止・--break-lock 案内経路
- 前回 pending/failed の `previousReportStatus` 表面化（open-run.py — 2R4 #2）
- `tests/test_report_matcher_contract.py` は期待値を変えない（候補規則の純粋契約のみ）。
  link(2)/EEXIST の原子性・非破壊は `tests/test_decide_verdict.py` の実経路試験として追加
  （2R2 #8 — §8 が正）
- （#28 採用時）`tests/test_workflow_template.py` 等の dispatch 契約期待

これ以外は worker が 1 件ごとに本リストへの追加を申請し boss が承認する。

## 11. #28 確定設計・実機検証・A/B

**前提（実機確認済み）**:
- mdq は `codex exec -s read-only` 下で BROKEN（2026-08-19）→ codex 検証器は **grep-degrade
  設計で固定**（インタビュー決定。upstream 変更なし）。
- codex-cli 0.149.0 に `--output-schema` / `-o` / `-s read-only` 実在。
- ゲート (b) probe（2026-08-25、`probes/results.md`）: P1 正常 exit 0・純 JSON ／ P2 schema 不正
  exit 1・不生成 ／ P3 SIGTERM exit 143・不生成 ／ **P4 親 dir 不在は exit 0 で `-o` 不生成**
  （exit code はファイル存在を保証しない）／ P5 3 並行正常。

**確定設計**:
- dispatch: opt-in 時、dispatched doc ごとの background `codex exec`。light=Luna `medium` /
  standard=Terra（classify-run.py の routing 踏襲）。`$RUN_DIR/codex-out/` を事前作成。
- **gate・EVIDENCE 契約は完全不変**: dispatcher が現行形式の `returns.json` を機械生成。対象は
  **全 dispatched 集合**（cached は現行どおり別照合）。**現行 retry 契約を完全再現**（失敗割当ての
  null 行・試行番号の累積・最大 3 試行後の不完全は gate が REFUSED）。SHA を EVIDENCE に載せる。
- **verdict 2 段階書き込み**: 試行ごとに排他的新規作成した**私有ディレクトリ**の未存在 child を
  `-o` 先にする（stale 誤採用と O_EXCL 予約衝突を同時排除）。採用条件は **exit == 0 かつ当該
  child が存在・通常ファイル・schema 合格・期待 runid/path/verdict 一致**（fail closed）。
  **検査と読込は `O_NOFOLLOW` で一度だけ open した同一 fd 上で fstat・サイズ上限・全読込**
  （差し替え窓の排除）とし、採用判定は子プロセス群の完全回収後。合格後のみ write-verdict.py の
  原子公開で `verdicts/<slug>.json` へ最終化。
- **timeout は process group kill**・**同時起動は上限つき worker pool（既定 4）**・attempt 間は
  全子回収後に遷移。**per-doc timeout は config schema に公開契約として固定**（キー名・既定値・
  許容範囲・queue 待機を含まない・retry ごとにリセット。worker が具体値を提案し boss が確定）。
- **opt-in 仕様**: config `phase3Backend: "workflow" | "codex"`（既定 `workflow`）。明示 opt-in 時に
  codex 不在・未認証・不正設定なら fail closed（黙示 fallback 禁止）。使用 backend を sealed
  manifest と report に記録。
- **cache**: key に backend を optional-with-default（旧履歴=workflow）で追加。テスト行列 6 ケース:
  旧形式非 corrupt／明示 workflow と旧キー互換 hit／codex→codex hit／codex→workflow miss／
  workflow→codex miss／無効値拒否。
- **正常系テスト**: backend 欠落→workflow／codex 正常結果からの verdict+returns 一致生成／
  light 初回と standard retry の切替／dispatch 空なら codex 未起動／対象 repo への cwd/-C 束縛。
- **CODEX_HOME**: 製品経路は ambient な `codex`（direnv exec 不使用）。

**A/B プロトコル（隔離コピー・--full 固定）**:
- student-pathway-ops を一時ディレクトリへ clone した隔離コピー 2 つ（arm ごと）。実 repo には
  一切書かない。隔離コピー内では config 編集・commit・状態生成を許可。
- **両アーム `--full` モード**（baseline/changedSet 構築問題を排除）。対象は corpus 設定の絞り込みで
  10〜15 docs に固定。run class を記録・一致確認。**同一性検証は構造的比較で行う**（2R2 #11 —
  config は JSON として読み `phase3Backend` キーだけを除去して正規化比較。行単位 diff は不可）。
  加えて dispatch 対象集合と per-doc dispatch payload の一致を直接検査 — **比較射影を固定する**
  （2R3 #8）: 比較するのは doc path・doc 内容 sha・layer/run class・プロンプト本文（backend 非依存
  部分）。正規化・除外するのは repoRoot・runId・runDir・backend/model 指定・config commit SHA
  （2 つの隔離コピー間で必然的に異なる値。worker が除外範囲を恣意的に広げることは禁止 —
  追加除外は boss 承認制）。**mdq/context-mode/ax/symbol graph の利用可否差は treatment 差**
  （codex arm は grep-degrade 設計、workflow arm は利用可能なシームを使う）として記録し、
  比較射影には含めない（2R4 #8 — changeSummary・provenance は --full・同一内容のため一致必須）。
  config 変更は監査開始前に各コピー内で commit。
- 両アーム空の run 状態・cache なしから開始。監査エンジンの commit SHA は両アームで一致。
  **prompt/schema digest は 2 層に分離**（2R5 #2 — seam 差により全文一致は原理的に不成立）:
  「共通 prompt core（backend 非依存部分）の digest は一致必須」＋「backend adapter /
  tool-seam 部分は個別 digest を取り差分を記録」。いずれも REVIEW.md に記録。
- codex arm は boss が明示 `CODEX_HOME=$HOME/.codex-student-pathway-ops` で起動。
- 比較項目: verdict 一致率／rationale 引用品質／wall-clock／概算コスト → REVIEW.md に記録 →
  **ユーザーに採否確認**。据え置き時は Issue #28 コメント文面を用意し確認後投稿（close は
  ユーザー選択）。

## 12. リリース手順（二段・fail-closed）

1. **v0.11.0 遡及**: `git tag docaudit--v0.11.0 01344ea` + push + Release。軽量タグ（慣行維持）、
   Release notes に遡及公開の明示・公開日・完全 SHA・既知 #37・後続新版を明記。
2. **新版番号は 0.12.0 で確定**（2R1 #14）: #28 採用時は明確な新機能、据え置きでも gate の
   入力物・report 書き込み責任・stdout・SKILL 手順が変わるため minor が互換性上安全。
   0.11.1 分岐は削除。
3. **handoff の fail-closed 要件**: 新版の承認済み merge commit full SHA を**必須引数**とする。
   冒頭で `git fetch`、branch==main・`HEAD == origin/main == 引数 SHA`・tracked clean を検証。
   既存 tag/Release は local/remote を個別に完全 SHA 照合（不一致は即 abort）。部分失敗からは
   検証つき再開。
4. **タグ前後の再検証**: タグ作成前に対象 commit checkout でフルスイート再実行。tag 済み・
   Release 未作成からの再開でも tag SHA 上で再実行してから Release 作成。
5. **handoff 分岐テスト**（PATH shim の偽 git/gh/rsync・専用一時宛先）: (i) 誤 SHA 既存 tag →
   停止、(ii) 正 tag＋Release 欠落 → 再実行のうえ再開、(iii) Release 済み＋Issue/sync 未完 →
   再開、(iv) SHA 引数欠落・不正 → 停止、(v) fetch 失敗 → 停止、(vi) local/remote tag 不一致 →
   停止、(vii) 同期先 symlink → 停止、(viii) rsync 失敗後の再開、(ix) **両 tag・両 Release とも
   未作成の初期状態から、v0.11.0 遡及と v0.12.0 の二段全体を作成・push・同期まで通す完全な
   初回成功経路**（2R2 #10、2R3 #9）、(x) **不正な既存 Release（draft/prerelease/必須 notes
   欠落）からの再開拒否を v0.11.0・v0.12.0 それぞれで**（2R3 #10）。
   **archive 構造保証も直接試験**:
   archive 対象が新版 tag・一時展開物が唯一の rsync 元・live worktree 未追跡物の非混入・
   同期と diff の管理境界一致。
6. **skills-dir 同期は tag の archive 展開物を同期元にする**（tag=配布物の構造的証明）:
   - **削除動作は実装契約**（2R2 #12）: `rsync --delete` を明記して使う（hide 対象の旧残骸を
     確実に消すため。3 分離試験だけに委ねない）
   - 配布除外リスト（hide — 宛先の過去配布残骸は削除する）: `tasks/` `data/` `tests/`
     `docs/superpowers/` `.gitignore`
   - 宛先保護リスト（protect — 削除からも上書きからも守る）: `.git` `__pycache__/` `*.pyc`
     `.venv/` `.brv/` `.DS_Store` `AGENTS.md` `.claude/` `.mdq/` `.serena/` `.envrc`
   - rsync filter で hide/protect の 2 意味論を書き分け、diff 検証（archive 展開物 vs skills-dir）
     も同じ境界で行う。**protect は削除防止と上書き防止を別々に試験する**（2R1 #13 — 代表
     ファイルで「宛先だけにあれば保持」「送信元に同名があっても非上書き」「hide 対象の旧残骸は
     削除」の 3 挙動を固定）。送受信先は realpath 解決＋symlink 検査。同期後
     `generic-layers.py --help` スモーク。0.10.1 → 新版へ一気に同期。
   - 版跨ぎの進行中 run: 同期前に「docaudit run 進行中でないこと」をユーザーに確認し、in-flight
     run の破棄（`--break-lock`）を Release notes に明記（機械的検出は不採用 — boss 裁定）。
7. **Release 再開時の内容検証**（tag 別）: 非 draft・非 prerelease かつ — v0.11.0: 遡及公開明示・
   公開日・完全 SHA・既知 #37・後続新版の記載／新版: 完全 SHA・#37 修正（と #28 決着形）の記載。
8. **Issue クローズ**: #37 は close。#28 は実装マージ時のみ close（据え置き時はユーザー選択）。

## 13. 進行順序

1. ~~probe・第 1 巡批判（5 往復）・ユーザー設計選択~~（済）→ **第 2 巡 Sol 批判**（rev.7、
   上限 5 往復）→ 設計確定
2. Stage 1: #37 実装（原因実証記録 → gate-writes-report 実装 → 回帰・故障注入テスト →
   フルスイート）→ boss 全行 diff レビュー
3. Stage 2: #28 プロトタイプ → A/B（隔離コピー・--full）→ **ユーザー採否確認** → 採用なら本実装・
   据え置きなら Issue コメント文面準備
4. Stage 3: 版 bump・docs 整合・handoff スクリプト＋分岐テスト
5. `codex exec review`（Sol `high`、最終承認直前に 1 回）→ boss 最終承認
6. PR 作成 → ユーザー承認・マージ → ユーザーが handoff 実行 → 同期検証
7. route-close（REVIEW.md close marker・メモリ更新）
