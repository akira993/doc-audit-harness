# REVIEW — Issues #28/#37 + 保留リリース一括実施（2026-08-25）

boss = Fable/Opus（本セッション）。worker = Sol/Terra/Luna（codex exec、CODEX_HOME=~/.codex-doc-audit-harness）。

## セッション ID 記録

- 計画批判セッション（Sol `high`, read-only）: `01a03763-4fad-7ad0-960a-c8a8c21885b4`
- 実装セッション（Stage 1〜, workspace-write, Terra `medium`）: `01a037ff-46a5-7923-822d-e6ad488c7ff7`
  （初回起動は既知の上書き承認待ちで停止 → 包括承認を resume で送付）

## インタビュー決定（route 手順 1、2026-08-25）

1. リリース戦略: **(a) 二段** — `docaudit--v0.11.0` を 01344ea に遡及タグ + 今回分を v0.12.0
2. 実施順: **#37 → #28**（PLAN は両方を見て確定）
3. #28 A/B: **student-pathway-ops**、部分集合（10〜15 docs）1 往復の小規模評価
4. #28 mdq 問題: **grep-degrade 設計**（upstream 変更なし）
5. #28 不成立時: **結果提示のうえユーザー確認**
6. #37 方向: **事前の好みなし — Sol 批判で選定**（全数表は PLAN §9）

## 実機検証記録

### ゲート (a)（Issue #28 コメント、2026-08-19 — 前セッション時点で確認済み）
mdq は `codex exec -s read-only` 下で BROKEN（`store.open_store()` が毎回 `PRAGMA user_version` を
実行し readonly DB への書き込みで OperationalError）。→ grep-degrade 設計で確定。

### ゲート (b)（本セッション、2026-08-25、`probes/results.md`）
codex-cli 0.149.0、`--output-schema` + `-o`、Luna low、7 起動:

| probe | 結果 |
|---|---|
| P1 正常系 | exit 0・`-o` は純粋 schema 準拠 JSON |
| P2 schema 不正 | exit 1・`-o` 不生成 |
| P3 SIGTERM | exit 143・`-o` 不生成（部分ファイルなし） |
| P4 親 dir 不在 | **exit 0 なのに `-o` 不生成**（stderr のみ）→ exit code はファイル存在を保証しない |
| P5 3 並行 | 全 exit 0・全正常 |

帰結: 「returns 照合を CLI exit code で置換」は不成立。ファイル存在＋schema＋runid の機械照合
（check-verdicts.py 相当）は維持必須。`verdicts/` の事前作成必須。

## 計画批判ラウンド（route 手順 3）

### Round 1（Sol `high`）— 承認不可（BLOCKER 5・MAJOR 8・INFO 2）
指摘全文: `critique-r1-answer.md`。boss 裁定:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | (a) は --break-lock に対する保証なし | 受理 — --break-lock を「直列化保証を破る非常操作」として契約明文化 |
| 2 | BLOCKER | post-gate lock 状態機械が未設計 | 受理 — PLAN §9 に状態表を追加、finalizer で機械化 |
| 3 | BLOCKER | (c) の SKILL prose 手順では原子性を保証できない | 受理 — 新ヘルパー write-report.py を唯一の writer とし O_EXCL〜fsync〜release を所有 |
| 4 | BLOCKER | #28「gate 不変」と「returns 置換」が矛盾 | 受理 — dispatcher が現行形式 returns.json を生成、gate 完全不変 |
| 5 | BLOCKER | -o 直書きは stale verdict 誤採用（P4） | 受理 — 試行ごと一時ファイル→検査→write-verdict.py 原子公開の 2 段階 |
| 6 | MAJOR | opt-in 仕様不足 | 受理 — fail-closed・黙示 fallback 禁止・backend を manifest/report/cache 条件に記録 |
| 7 | MAJOR | direnv exec を製品経路に使うのは不適切 | 受理 — 製品契約は ambient codex、A/B のみ明示 CODEX_HOME |
| 8 | MAJOR | 再現テストの具体設計 | 受理 — Sol 提示の逐次 interleaving＋pipe READY＋Barrier 方式を §8 に採用 |
| 9 | MAJOR | 意図的差分リストの対象漏れ | 受理 — test_start_run/test_wp12_contracts/cache 試験を §10 に追加 |
| 10 | MAJOR | docs/config-schema.md は存在しない（正本は skills/audit/references/） | 受理 — §7 修正 |
| 11 | MAJOR | handoff の冪等・再実行・rsync --delete・偽 git テスト | 部分受理 — 冪等ガード・HEAD/tag ガード・--delete 不使用は受理。偽 git/gh による handoff 自動テストは不採用（タスク記録物であり配布エンジンではない。冪等ガード＋対話実行の可視性で代替） |
| 12 | MAJOR | #28 据え置き時も一律 close・0.11.1 分岐の不整合 | 受理 — 0.12.0 固定（(a)+(c) が公開後条件を変更）。#28 close は実装時のみ、据え置き時はユーザー選択 |
| 13 | MAJOR | 0.10.1→最新の飛び越し更新テスト欠落 | 受理 — §10 に追加 |
| 14 | INFO | (b) 不採用は妥当 | 記録 — (b) 恒久不採用 |
| 15 | INFO | 遡及タグの監査性 | 受理（notes 側）— 軽量タグ慣行は維持、Release notes に遡及公開・SHA・既知 #37 を明記 |

→ PLAN rev.2 に反映。Round 2 で確認へ。

### Round 2（Sol `high`, resume）— 承認不可（BLOCKER 7・MAJOR 9）
指摘全文: `critique-r2-answer.md`。boss 裁定（全件受理、#12 は R1 裁定を転換、#13 は方式選択）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | finalizer が書き込み中 flock を保持しない | 受理 — 開始時に flock 取得・path inode/lockIno/runid 全照合・unlink 完了まで保持（§9.2-1） |
| 2 | BLOCKER | 「gate 完了後」を機械的に証明できない | 受理 — gate が gate-result.json（runid/verdict/lockIno）を原子発行、finalizer が検証（§9.1/9.2-2） |
| 3 | BLOCKER | pre-lock REFUSED が lock 恒久残留 | 受理 — matching runid の reportless release を義務化（§9.3） |
| 4 | MAJOR | owned 判定 OR は同 runid 置換 lock を owned 扱い | 受理 — runid・fd inode・path inode・lockIno の AND に強化（§9.1） |
| 5 | MAJOR | report 確定後 release 前の部分完了が再開不能 | 受理 — intent/done 記録・inode 限定回収・release-only 再開（§9.2-3〜5）＋故障注入テスト |
| 6 | MAJOR | reportPath の信頼元未定義・親 symlink 競合 | 受理 — seal 時に manifest へ固定、config 不一致 REFUSED は reportless 限定、dir_fd 方式（§9.1/9.2） |
| 7 | BLOCKER | 「全 impacted」は returns 契約と矛盾 | 受理 — 「全 dispatched 集合」に訂正（§11） |
| 8 | BLOCKER | attempt-<n> 一時名は再開時に stale 誤採用 | 受理 — 毎実行 fresh O_EXCL 名＋事前不存在検証＋codex-out/ 事前作成（§11） |
| 9 | BLOCKER | A/B が禁止事項・状態変異・union 契約と矛盾 | 受理 — 隔離コピー 2 つの paired 比較・corpus 絞り込みで部分集合化（§11） |
| 10 | MAJOR | backend cache 方針が二択のまま | 受理 — key に optional-with-default（旧履歴=workflow）で一本化＋移行テスト（§11） |
| 11 | MAJOR | dispatcher 採用条件・timeout の未具体化 | 受理 — exit==0 AND fresh 検査合格・process group kill・失敗系テスト列挙（§11） |
| 12 | BLOCKER | handoff の skip 判定が SHA を検証しない／偽 git テスト全面不採用への異議 | 受理 — 完全 SHA 照合の fail-closed 化。異議も受理し PATH shim の最小 3 分岐テストを採用（R1 #11 裁定を転換、§12-3/5） |
| 13 | MAJOR | --delete 不使用と diff 一致の矛盾 | 受理 — 「--delete＋同期/検証で同一 exclude リスト（保護セット明記）」に一本化（rev.2 の --delete 禁止を撤回、§12-6） |
| 14 | MAJOR | release commit 上での最終テスト欠落 | 受理 — タグ前に commit 一致ガードつきフルスイート再実行（§12-4） |
| 15 | MAJOR | 旧順序テスト (5) は修正後実行不能 | 受理 — 原因実証（旧実装・1 回・記録）と回帰テストを分離（§8） |
| 16 | MAJOR | rev.2 内の旧記述 4 箇所 | 受理 — rev.3 で全面書き直し・一掃 |

Stage 1 の実装モデルを Terra `medium` → **Sol `medium`** に格上げ（トランザクション設計の失敗コスト）。
→ PLAN rev.3。Round 3 で収束確認へ。

### Round 3（Sol `high`, resume）— 承認不可（BLOCKER 8・MAJOR 7）
指摘全文: `critique-r3-answer.md`。boss 裁定（#1 のみ限定受理、他は全件受理）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | gate-result は同一権限プロセスに偽造可能 | 限定受理 — nonce を lock と gate-result の両方へ書き finalizer が一致検証（事故経路を閉じる）。暗号学的偽造不能性は原理的に達成不能で目標にしない（#22 と同じ残余境界）— 脅威モデルを PLAN 冒頭に明文化 |
| 2 | BLOCKER | gate-result 発行失敗で三重不整合 | 受理 — 発行順序（永続状態更新後・return 前）と回復（reportless release・report 欠落の明示）を状態表に追加 |
| 3 | BLOCKER | base reportPath では suffix 候補列を再現できない | 受理 — 候補生成規則（挿入位置含む構造）を seal・gate-result に固定 |
| 4 | BLOCKER | manifest 差し替えで reportPath 誘導 | 受理 — gate-result に manifest SHA を固定し finalizer が再照合 |
| 5 | BLOCKER | 作成→intent の間のクラッシュ窓 | 受理 — intent を作成前に記録する順序へ変更（path 所有は lock 直列化で担保） |
| 6 | MAJOR | done が完全性を証明しない・unlink 後死亡で再開不能 | 受理 — done に長さ＋SHA-256、lock 消失＋done 検証合格は冪等成功 |
| 7 | MAJOR | --release が期待 inode を検査しない | 受理 — `--expect-ino` 任意引数を追加、SKILL は EVIDENCE.lockIno を渡す |
| 8 | MAJOR | gate-result に counts 等がなく report が可変ファイル再計算になる | 受理 — gate stdout 完全オブジェクトを格納 |
| 9 | BLOCKER | fresh O_EXCL 名は codex -o と両立不能 | 受理 — 試行ごとの排他的私有ディレクトリ＋未存在 child 方式へ変更 |
| 10 | MAJOR | returns の null 行・試行番号・3 回上限の再現計画欠落 | 受理 — 現行 retry 契約の完全再現を明記 |
| 11 | BLOCKER | A/B の交絡（config 変更が changedSet/digest に混入・エンジン版未固定） | 受理 — config 変更は事前 commit で baseline に含め、エンジン SHA・prompt/schema digest を記録し両アーム一致 |
| 12 | MAJOR | cache テスト行列不足 | 受理 — 6 ケース行列に拡張 |
| 13 | BLOCKER | 承認済み merge SHA の権威ある取得元がない | 受理 — handoff の必須引数化＋fresh fetch＋local/remote タグ個別照合 |
| 14 | BLOCKER | rsync 保護セット未固定・分岐テストが実環境を削除しうる | 受理 — 保護セット 11 項目を PLAN に固定列挙、realpath/symlink 検査、テストは偽 rsync＋専用一時宛先 |
| 15 | MAJOR | tag 済み再開経路がフルスイートを迂回 | 受理 — 再開分岐でも tag SHA 上で再実行 |

→ PLAN rev.4。Round 4 で収束確認へ。

### Round 4（Sol `high`, resume）— 承認不可（BLOCKER 7・MAJOR 3・MINOR 5）
指摘全文: `critique-r4-answer.md`。boss 裁定:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | 通常 --release で finalizer 必須状態を迂回できる | 受理 — gate-result が report 必須＋done 不在なら release 拒否（--abandon-report 明示フラグのみ突破可） |
| 2 | BLOCKER | stdout 喪失後の gate 再実行が非冪等 | 受理 — 状態変更前に既存 gate-result を検出し同一結果を再送する one-shot 契約 |
| 3 | BLOCKER | reportPath 省略時の互換未決定 | 受理・boss 決定 — 省略時は reportless run（既存挙動維持）、無効テンプレートは seal 拒否 |
| 4 | MAJOR | lock への nonce 後書きが crash-safe でない | 受理 — 厳密に長くなる JSON の単一 pwrite（truncate 不要）＋parse 不能は --break-lock 帰着＋故障注入テスト |
| 5 | MAJOR | pre-lock REFUSED で expect-ino の入力源がない場合がある | 受理 — EVIDENCE 不正時に限る runid-only fallback を明示縮退経路化 |
| 6 | MAJOR | flock 待機後 path-missing の回復漏れ | 受理 — done 検証へ遷移し冪等成功 |
| 7 | MINOR | Barrier テスト期待が状態機械と矛盾 | 受理 — EEXIST 注入＋重複 finalizer 同一 path 収束テストへ差し替え |
| 8 | BLOCKER | A/B の「config 別 commit」と「HEAD 一致」が両立不能 | 受理 — 同一性基準を「impacted 集合・changedSet paths・doc 内容の機械的一致検証」に変更（HEAD 一致は要求しない） |
| 9 | MINOR | dispatcher 同時起動上限なし | 受理 — 上限つき worker pool（既定 4）・attempt 間は全子回収後 |
| 10 | MINOR | #28 正常系・既定互換テスト不足 | 受理 — 5 項目を追加 |
| 11 | BLOCKER | rsync 保護セットが実際の local 専用物より狭い | 受理 — #12 と併せ archive 方式へ。配布除外/宛先保護の 2 リストに分離し固定 |
| 12 | BLOCKER | 同期内容が tag の tracked 集合に結びつかない | 受理 — 同期元を git archive の一時展開物に変更（「tag=配布物」を構造的に証明） |
| 13 | BLOCKER | 版跨ぎ in-flight run の互換境界なし | 部分受理 — 同期前の「進行中 run なし」確認＋Release notes に in-flight 破棄（--break-lock）を明記。全 consuming repo の機械的検出は不採用（列挙不能・既往慣行・失敗モードは既存手段で回収可能） |
| 14 | MINOR | handoff 分岐テストの網羅不足・偽ツールリスト不一致 | 受理 — 8 分岐に拡張し §8/§12 のリストを統一 |
| 15 | MINOR | Release 再開検証が「存在」のみ | 受理 — 非 draft/prerelease＋必須 notes 要素の検証 |

→ PLAN rev.5。Round 5（上限）で最終確認へ。

### Round 5（Sol `high`, resume・上限到達）— 承認不可（BLOCKER 4・MINOR 8）
指摘全文: `critique-r5-answer.md`。**批判ループは規定上限 5 往復に到達**。boss 最終裁定:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | 状態更新後・gate-result 発行前死亡を one-shot で回復不能 | 受理 — gate-result を WAL 化（状態更新前に発行・計画変更を含む・replay は残り更新を冪等適用、(runid,path) 重複はスキップ） |
| 2 | BLOCKER | EEXIST 後死亡で既存 report を truncate | 受理 — intent/truncate 方式を廃止し temp-then-link(2) 方式へ（最終名には常に完全内容のみ。R3 #5 も同時解消） |
| 3 | BLOCKER | --release が done の存在だけで解除 | 受理 — release 側にも finalizer と同一の done 完全性検証 |
| 4 | BLOCKER | A/B の baseline 構築と payload 同一性 | 受理 — 両アーム --full モード固定・run class 記録一致・クローン間機械 diff で payload 同一性担保 |
| 5-12 | MINOR | reportless 成功経路の状態表行 / pwrite 検証条件 / 故障注入網羅 / dispatcher 単一 fd 読込 / timeout 公開契約 / rsync hide vs protect / tag 別 notes 検査 / archive 構造保証テスト・偽ツールリスト統一 | 全件受理 — rev.6 に worker 実装要件として固定 |

**ループ終了の裁定**: R5 の 4 BLOCKER はいずれも Sol 自身の提示した救済策をほぼそのまま採用して
解決した（新規の boss 独自設計は「link 後 done 前死亡の digest 一致採用」のみ）。上限到達に
つき本 rev.6 を実装仕様として確定し、rev.6 への実装忠実性は Stage ごとの boss 全行 diff
レビューと手順 5 の `codex exec review`（Sol `high`）で検証する。

### 設計転換（ユーザー決定、2026-08-25）

advisor 相談の結果、(1) Sol が承認不可のまま上限到達し R5 の 3 機構（WAL・temp-then-link・
release 側 done 検証）が敵対レビュー未通過であること、(2) スコープがインタビュー時の想定から
lock 生涯の再設計へ大幅成長していたことから、実装着手前にユーザーへ確認。
**ユーザーは「軽量案（gate-writes-report）を先に評価」を選択** — orchestrator がプレースホルダ
つき report 本文を事前生成し、lock を保持したままの gate 自身が置換・suffix 選択・書き込み・
unlink まで行う設計。lock がプロセス境界を跨がなくなり、WAL・nonce・finalizer・--release 変更が
全て不要になる。

→ **PLAN rev.7**（gate-writes-report。機構非依存の確定事項は rev.6 から継承）。
rev.6 は本記録に第 1 巡の成果として保存。批判ループ**第 2 巡**（上限 5 往復）を開始。

## 計画批判ラウンド — 第 2 巡（rev.7: gate-writes-report）

### 第 2 巡 Round 1（Sol `high`, resume）— 承認不可（BLOCKER 4・MAJOR 4・MINOR 5・INFO 2）
指摘全文: `critique2-r1-answer.md`。#15 で「finalizer 固有の問題群は消滅・A/B baseline 矛盾も
解消」を確認。boss 裁定（全件受理）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | report link が gate 自身の digest 再照合を壊す | 受理 — 公開順序を「digest 再照合 → 状態更新 → link」に確定（§9.1-3） |
| 2 | BLOCKER | 状態確定前に成功様の report が公開されうる | 受理 — 同上（link は状態更新後のみ。pending 状態は last_run で機械判定可能） |
| 3 | BLOCKER | owned REFUSED の report 可能条件が広すぎる | 受理 — 「manifest SHA・seal・候補規則の検証成立後の REFUSED」に限定 |
| 4 | BLOCKER | テンプレート受渡しが symlink/FIFO/巨大ファイルに無防備 | 受理 — write-template.py（O_NOFOLLOW\|O_EXCL）＋gate 側 O_NOFOLLOW 単一 fd・fstat・サイズ上限・UTF-8 検査 |
| 5 | MAJOR | プレースホルダ言語未定義 | 受理 — 原文 1 回走査 allowlist・verdict 別必須/禁止 token・再置換なし |
| 6 | MAJOR | report 障害の例外境界がない | 受理 — 局所捕捉で warning 縮退、外側 except へ漏らさない |
| 7 | MAJOR | reportWriteError が永続しない | 受理 — last_run に reportStatus（pending→written/failed）を永続化 |
| 8 | MAJOR | AND 化後の non-owned stale lock | 受理 — EVIDENCE 必須キー検証を lock open 前に固定（pre-lock REFUSED 化）＋真の不一致は --break-lock 帰着を明文化 |
| 9 | MINOR | 失敗時 stdout schema | 受理 — reportPath は成功時のみ＋固定 warning code |
| 10 | MINOR | 公開 mode・dir fsync・temp 後始末 | 受理 — 0644・宛先 dir fsync・成功後 temp unlink |
| 11 | MINOR | sibling 移動の lock 延長統合試験 | 受理 — §8 に追加 |
| 12 | MINOR | 原子性テスト配置・変更範囲過大 | 受理 — test_decide_verdict 実経路試験へ、open-run.py/tree-digest.py/write-verdict.py は原則変更しない |
| 13 | MINOR | rsync protect の 3 分離試験 | 受理 — §12-6 に追加 |
| 14 | INFO | 版番号 | 受理 — 0.12.0 確定（0.11.1 分岐削除） |
| 15 | INFO | 第 1 巡論点の仕分け | 記録 — finalizer 固有問題は消滅、順序/解放漏れ/report 完全性は #1-8 で対処 |

→ PLAN rev.8。第 2 巡 Round 2 で収束確認へ。

### 第 2 巡 Round 2（Sol `high`, resume）— 承認不可（BLOCKER 2・MAJOR 4・MINOR 5・INFO 1）
指摘全文: `critique2-r2-answer.md`。boss 裁定（全件受理）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | digest 再照合が sibling scan（最大 30 秒）より前で回帰 | 受理 — 最終再照合を scan 後・状態更新直前へ（現行の安全条件を維持） |
| 2 | BLOCKER | report 公開後の失敗が確定済み verdict を REFUSED に反転しうる | 受理 — 「状態確定後は判定を反転させない」境界を明文化。post-link 失敗は warning 縮退・link 済みなら reportPath を返し reportDurabilityUnknown |
| 3 | MAJOR | write-template.py の unlink→再作成が O_EXCL を自壊 | 受理 — 既存 path は既定拒否、正当な再生成は --replace（O_NOFOLLOW 検査＋temp+atomic rename）のみ |
| 4 | MAJOR | 置換値の形式・安全化未定義 | 受理 — 型つき固定形式描画・自由文字列は制御文字エスケープの単一行・token 出現数検査 |
| 5 | MAJOR | owned REFUSED の commit 順序未定義 | 受理 — reason+pending 永続化 → report → status 更新 → unlink、各段局所捕捉・unlink 必行 |
| 6 | MAJOR | SKILL の OR 所有判定契約が未更新 | 受理 — §9.3 に追加 |
| 7 | MINOR | reportless run の reportStatus | 受理 — not-requested 終端値を追加 |
| 8 | MINOR | 原子性テスト配置矛盾（O_EXCL 表記） | 受理 — §8 を正に統一・§10 修正 |
| 9 | MINOR | 新境界の故障注入不足 | 受理 — §8 に追加 |
| 10 | MINOR | handoff 初回成功経路の試験欠落 | 受理 — 分岐 (ix) 追加 |
| 11 | MINOR | 行単位 diff は構造的比較でない | 受理 — JSON 正規化比較＋payload 直接検査 |
| 12 | INFO | rsync --delete の契約明記 | 受理 — §12-6 に明記 |

→ PLAN rev.9。第 2 巡 Round 3 で収束確認へ。

### 第 2 巡 Round 3（Sol `high`, resume）— 承認不可（BLOCKER 1・MAJOR 2・MINOR 6・INFO 1）
指摘全文: `critique2-r3-answer.md`。boss 裁定（全件受理）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | BLOCKER | 最終確認が digest 単独に縮退（現行 :482-496 は一括） | 受理 — 一括再照合を不可分 barrier として scan 後へ・対象別注入試験 |
| 2 | MAJOR | helper 成功と gate 入力が未結合（stale template 採用可能） | 受理 — helper が sha256 を返し gate は --template-sha 一致時のみ採用 |
| 3 | MAJOR | unlink 失敗の回収契約なし | 受理 — lockReleaseFailed 固定 code＋所有確認つき --release → 失敗時停止・--break-lock 案内 |
| 4 | MINOR | warning code 一覧・耐久性の永続化が未完 | 受理 — 6 code 列挙・written-durability-unknown を last_run に永続化 |
| 5 | MINOR | REFUSED reportless が pending を残す | 受理 — REFUSED にも not-requested/failed 分岐 |
| 6 | MINOR | report 日付が seal されていない | 受理 — reportDate を runid から導出し manifest に固定・--date 不使用 |
| 7 | MINOR | サイズ上限が全経路未固定 | 受理 — helper 2MB・bounded read・置換後 4MB |
| 8 | MINOR | A/B payload 比較の射影未固定 | 受理 — 比較/除外フィールド列挙・追加除外は boss 承認制 |
| 9 | MINOR | handoff 初回試験が二段を通すか不明 | 受理 — 二段全体の初回成功経路に明記 |
| 10 | INFO | 不正 Release 拒否の分岐試験 | 受理 — (x) として追加 |

→ PLAN rev.10。第 2 巡 Round 4 で収束確認へ。

### 第 2 巡 Round 4（Sol `high`, resume）— 承認不可（BLOCKER 0・MAJOR 3・MINOR 6・INFO 1）
指摘全文: `critique2-r4-answer.md`。「前回指摘（barrier・warning code・reportDate・A/B・handoff）は
概ね解消」と確認。boss 裁定（全件受理）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | MAJOR | write-template.py の書込み先が run ledger に未束縛 | 受理 — --repo-root/--runid 必須＋共有 path validator で自己束縛 |
| 2 | MAJOR | 「pending を残さない」と status 更新失敗許容が矛盾 | 受理 — pending を回復対象の終端として公認し、open-run が previousReportStatus を表面化（open-run.py を変更対象に戻す） |
| 3 | MAJOR | lockReleaseFailed 回収と SKILL release 義務が矛盾 | 受理 — release 義務を 2 経路（pre-lock REFUSED＋post-gate 回収）に整理 |
| 4 | MINOR | 回収経路の試験・§10 の表現 | 受理 — 試験 2 経路追加・「通常時または回収完了時」に修正 |
| 5 | MINOR | front matter 日付と sealed reportDate の一致 | 受理 — {{GATE_REPORT_DATE}} を必須 token 化 |
| 6 | MINOR | helper 失敗後の旧 SHA 続行で stale 採用 | 受理 — 「最後の起動の sha のみ・非 0 なら破棄」を契約化＋試験 |
| 7 | MINOR | 表示偽装（LS/PS・bidi） | 受理 — JSON 文字列化エスケープ＋Unicode 表示制御の拒否に一意化 |
| 8 | MINOR | A/B プロンプト共通部の境界 | 受理 — シーム利用可否差は treatment 差として記録、changeSummary/provenance は一致必須 |
| 9 | MINOR | UTC 日付の可視変更 | 受理 — §10 に追加＋日跨ぎ・不正暦日試験 |
| 10 | INFO | サイズ/SHA 境界値 | 受理 — 実装時に一意化（worker 詳細） |

→ PLAN rev.11。第 2 巡 Round 5（上限）で最終確認へ。

### 第 2 巡 Round 5（Sol `high`, resume・上限到達）— 承認不可（MAJOR 2・MINOR 6・INFO 1）
指摘全文: `critique2-r5-answer.md`。「barrier・helper 束縛・pending 回復・release 二経路・
UTC 日付・handoff は解消」と確認。boss 最終裁定（全件受理、#1/#2 は Sol 提示の救済策を採用）:

| # | 重要度 | 要旨 | 裁定 |
|---|---|---|---|
| 1 | MAJOR | 最後の helper 起動の成否を gate が識別できない（旧 sha 続用可能） | 受理 — --template-sha を廃止し receipt 機構へ（毎起動で receipt を原子更新、失敗時も {failed:true} で無効化。gate は receipt を自読）。sha が LLM の手を経由しない |
| 2 | MAJOR | seam 差と prompt digest 全文一致が同時不成立 | 受理 — 「共通 core digest 一致必須」＋「adapter/seam 個別 digest＋差分記録」に分離 |
| 3 | MINOR | written-durability-unknown が通知対象外 | 受理 — previousReportStatus の対象に追加 |
| 4 | MINOR | previousReportStatus 読取りの競合 | 受理 — 新 lock 取得後に再読・決定論的試験 |
| 5 | MINOR | REFUSED reportless が pending を書く | 受理 — not-requested 直行に修正 |
| 6 | MINOR | GATE_REPORT_DATE の出現数矛盾 | 受理 — per-token 出現数契約（当該 token は 2 回） |
| 7 | MINOR | JSON escape では HTML 表示偽装が残る | 受理 — HTML 有効文字も Unicode escape |
| 8 | MINOR | open-run.py の変更が §7/§5 未反映 | 受理 — 反映済み |
| 9 | INFO | サイズ/mode 境界値 | 受理 — worker 固定（公開 mode は fd へ明示 fchmod） |

**第 2 巡ループ終了の裁定**: 上限 5 往復に到達。残 2 MAJOR は Sol 自身の救済策をそのまま採用して
解決し、新規の boss 独自設計はない。**PLAN rev.12 を実装仕様として確定**。実装忠実性は Stage
ごとの boss 全行 diff レビューと手順 5 の `codex exec review`（Sol `high`）で検証する。

## 確定 PLAN: rev.12（実装仕様）
`tasks/route/2026-08-25-issues-28-37-release/PLAN.md` rev.12。批判経緯: 第 1 巡 5 往復
（finalizer 方式 → ユーザー決定で転換）＋第 2 巡 5 往復（gate-writes-report）。

## 実装レビューラウンド（route 手順 5-6）

### Stage 1 第 1 段（engine scripts＋テスト、Terra `medium`）Round 1 — 差し戻し
worker 報告: 原因実証記録済み（`stage1-cause-demo.txt` — B gate の digest mismatch REFUSED を
実証）・328 件全 green（+30）・§10 対応 3 件列挙（boss 検証済み・全件正当。特に history 隔離の
期待変更は AND 所有判定の状態表どおり）。boss 全行 diff レビュー済み
（decide-verdict.py 408 行・open-run.py・start-run.py・write-template.py 新規・テスト 4 ファイル）。

指摘（差し戻し 2・確認 1・nit 1）:
1. [要修正] REFUSED token 契約: 現実装は「成功用 token を REFUSED で禁止」のため、gate 前に
   書く 1 枚のテンプレートでは REFUSED 時に必ず reportTemplateInvalid → reportless になり、
   v0.11.0 の「REFUSED でも report が残る」挙動を失う。PLAN 2R1 #5 が許容する n/a 固定方式へ:
   契約を verdict 非依存の単一契約（counts/historyStatus/siblingScan=1 回・DATE=2 回・
   VERDICT/WARNINGS/ANCHOR=1 回・REASON=0..1 回）にし、REFUSED では counts 系を "n/a"、
   成功では REASON を "n/a" で置換する。
2. [要修正] publish_report の親 dir 競合窓: validate→os.link の間に親を symlink へ差し替える
   競合が残る（PLAN §9.1-3 は dir_fd 経由を要求）。親を O_DIRECTORY|O_NOFOLLOW で open した
   fd を保持し `os.link(..., dst_dir_fd=fd)`＋同 fd で fsync に変更。
3. [確認] start-run が date マーカー無し reportPath を seal 拒否する互換影響:
   `skills/audit/references/config-schema.md` の reportPath 定義と突合し、date-less を許す
   記述なら差分を報告（SKILL/docs 段で明文化する）。
4. [nit] validate_report_rule の suffixStart 型検査（float 2.0 が通る — isinstance int に）。

### Stage 1 第 1 段 Round 2 — 承認
worker が 4 点全て修正（単一 token 契約＋n/a 置換・publish_report の dst_dir_fd＋同 fd fsync・
suffixStart の int/bool 検査・config-schema.md 突合で date マーカー必須を確認 → 互換問題なし）。
boss が修正 diff を再検証し一致を確認。331 件全 green（+3: n/a・reason 省略・型拒否試験）。
§10 対応は 3 件から増減なし。**第 1 段承認、第 2 段（SKILL.md）へ**。

### Stage 1 中間 — worker の仕様矛盾検出（正当な停止）
第 2 段着手前に worker が「PLAN §9.1-5 の stdout schema は reportStatus を要求するが実装に無い」
矛盾を検出して停止（推測回避せず報告 — 規律どおり）。boss 裁定: PLAN が正 → 第 1 段を再開して
全終了経路の stdout に reportStatus を追加（last_run と常に一致・未作成経路では省略）。

### Stage 1 第 2 段（SKILL.md）＋ stdout 補完 Round 1 — 承認（Stage 1 完了）
worker 報告: 332 件全 green。§10 対応は累計 6 件（stdout/last_run 一致・EVIDENCE 不正時省略・
非 owned 時省略の 3 件追加 — boss 検証済み・全件正当）。boss 全行 diff レビュー:
- SKILL.md: placeholder 契約表（8 token・出現数・n/a 規則）・write-template 手順（--replace 含む）・
  gate stdout 報告（reportPath/warnings/reportStatus）・release 義務 2 経路＋非 owned は
  --break-lock 案内・--break-lock の非常操作契約と gate-running 全区間拒否・AND 所有判定
  （4 事実全一致）・previousReportStatus のユーザー報告・siblingScan 行の placeholder 化 —
  すべて §9.3 どおり、外科的変更。
- decide-verdict.py: finalize_report が「実際に永続化できた status」のみを返し stdout に載せる
  実装（更新失敗時は disk 上の pending を返す）— 一致保証が正しい。
**Stage 1（#37）完了・承認。** 既知の軽微な挙動変更として、report 内の siblingScan 行が
人間可読の整形行から JSON オブジェクト置換になる（非 blocking・機械には未参照）。
Stage 1 コミット: `4cc53bf`（branch `feat/v0.12.0-issues-28-37`）。

### Stage 2 の段階分割（boss 決定）
2a = dispatcher スクリプト＋テストのみ（A/B に必要な最小。Terra `high` に昇格 — 探索的・
複数システム）／2b = A/B（隔離クローン・--full・boss orchestrate）／2c = ユーザー採用決定時のみ
SKILL 配線・config schema `phase3Backend`・cache backend key。据え置き時の捨て作業を最小化する
ための順序最適化（PLAN §11 の全項目は 2a+2c で網羅）。

## A/B 記録（#28）— 2026-08-25 実施

- 対象: student-pathway-ops の隔離クローン 2 つ（完全一致検証 ok・1,251 エントリ差分 0）。
  clone 元 HEAD `41b5128`・corpus commit `554c81d`・監査エンジン `abcb7a9`（full-mode prompt
  修正 `cd98ccc` 適用後に実行）。--full モード・12 docs・standard class・両アーム grep ベース
  （mdq index 両方不在 — 意図した純化）・cache なし・空 run 状態。
- アーム: workflow = 本番 `docaudit:doc-impact-verifier`（Sonnet）12 体並列、Workflow テンプレート
  と同一プロンプト（full-mode 適応）／codex = `codex-dispatch.py` + 実 codex
  （CODEX_HOME=~/.codex-student-pathway-ops、gpt-5.6-terra medium、並行 3、timeout 600s）。
  行動規範ブロックは workflow アームに付さず本番プロンプト忠実を優先（boss 裁定・treatment 統制）。

### 結果

| 指標 | workflow (Sonnet) | codex (Terra medium) |
|---|---|---|
| 収集 | 12/12（初回） | **12/12・1 試行・失敗 0** |
| wall-clock | 330s（12 並列） | **214s（並行 3）** |
| verdict 分布 | FAIL5 / WARN4 / PASS3 | FAIL9 / WARN2 / PASS0 |
| トークン | 約 491k（subagent 合計） | 未計測（ChatGPT アカウント側） |

- verdict 一致: **6/12**。不一致 6 件はすべて codex がより厳しい判定で、**別種の具体的矛盾を
  引用**（HSTS 設定・font preload 方式・testing.md の適用 glob・VisaApplication status enum・
  admin 制限・scope クエリ喪失）。
- **boss 裏取り（2/2 確定）**: DES-019 の HSTS（doc「HSTS ON」vs settings.py default 0・
  fly.toml 上書きなし）と DESIGN.md の font preload（doc `as="font"` vs 実 `as="style"`）は
  いずれも codex の指摘どおり実在する矛盾 — 幻覚ではない。workflow アームの指摘（coverage 80↔92・
  reka-ui 改名・ARCHIVED 非実在等）も実在。**両アームとも実在の問題を発見しており、不一致は
  誤りではなく着眼点の相違**（同一 doc に複数の実矛盾がある）。
- 収集信頼性: #28 の動機だった「Workflow 経路の verdict 書き込み欠落（歴代 38/60〜59/60）」は
  CLI 書き込みで構造的に消滅（12/12・1 試行）。
- 比較の限界: 12 docs・1 往復・1 repo。rationale 引用品質は同等（両者 file:line 引用）。
  codex のコストは直接計測不能。

### ユーザー採否決定（2026-08-25）
**採用（opt-in で実装完了へ）** — Stage 2c を実施し v0.12.0 に含めて #28 を close する。

### Stage 2c（採用配線）Round 1 — 承認
中間で worker が正当な停止（cache 分離に plan-dispatch.py の最小変更が必須と根拠つきで報告）→
boss 承認・PLAN §7 追記。完了報告: 356 件全 green（+13）・既存期待値変更 0。boss 全行 diff
レビュー: start-run の phase3_settings 検証と seal・docaudit_cache の optional-with-default と
6 ケース行列・plan-dispatch 最小変更・gate の sealed/config 一致検証と履歴 backend 記録・
config-schema 2 キー・SKILL の sealed backend 分岐（codex 経路の evidence 合流・fail-closed
無言 fallback 禁止・Phase-0 mdq ゲート免除・Phase-5 backend 行）— すべて仕様どおり。
Stage 2c コミット: `d7c3d3f`（Closes #28 を含む）。中間コミット: `abcb7a9`（2a）・
`cd98ccc`（full-mode prompt 修正 — boss が A/B 実行前レビューで発見したバイアス欠陥）。

## Stage 3 作業記録（worker、2026-08-25）

- [x] 前版 bump と同じ面を 0.12.0 に更新し、scaffold の正規化方式で 3 SHA を算出・登録した。
- [x] 0.10.1 stamp から 0.12.0 への飛び越し refresh と変更済み生成物の保持を回帰試験で固定した。
- [x] ADOPTION 英日へ #37・#28・UTC reportDate・0.12.0 refresh の公開差分だけを追記した。
- [x] PLAN §12 の二段 release・検証つき再開・archive 同期を release-handoff.sh に実装した。
- [x] PATH shim の偽 git/gh/rsync で指定 10 分岐と archive 境界を試験した。
- [x] 絞り込み 28 件と全スイート 366 件を完走した（いずれも OK）。全スイートでは既存の
  `tests/test_generic_layers.py` 由来の ResourceWarning が出るが失敗はない。

### Stage 3 engine SHA 算出結果

`scaffold.py` の `_harness_sources()` と `_normalized_sha()` を直接使って算出した。

- `check-docs`: `a5c1efbcbe1bdbece74cb188228fd676d4c6c0446a42f27d6514afe40c5f1ab8`
- `doc-lint`: `ebc5944f8739b4b0ff9740f442fe05225c6df300f6fcb471ba20120f30366727`
- `check-docs-engine`: `d0e64dd5c436a04ec1b28e75a73964b324da9de47ff81e7541f7ec223dba5a82`

3 生成本文は v0.11.0 から変更されていないため SHA は同一。版 stamp は正規化 SHA の対象外。

### Stage 3 §10 対応

`tests/test_scaffold.py` の既存期待値変更は全て、PLAN §10 の「scaffold 版上げ・過去 stamp の
段階飛び越し（0.10.1 から最新への直接更新）」に対応する。

1. refresh stdout の `stampVersion`: `0.11.0` → `0.12.0`
2. 最新 SHA の参照キー: `0.11.0` → `0.12.0`
3. 更新後 stamp 行: `check-docs-engine@0.11.0` → `@0.12.0`
4. plugin の現行版期待: `0.11.0` → `0.12.0`

これ以外の既存テスト期待値変更はない。

### 最終 codex review 追修正（Sol high）

- P1: incremental Codex prompt に sealed `changedSet` を最大100件、総件数・表示件数つきで列挙。
  未コミット・未追跡を含みうるため sealed worktree の現在内容を照合する契約を明記した。
- P2a: 子 Codex の未使用 stdout/stderr を `DEVNULL` へ送り、timeout と process-group kill は維持。
- P2b: report 公開後に判明する4警告は report token に入らず、gate stdout と
  `last_run.reportStatus` が正本である旨を SKILL Phase 5 に追記した。
- P3: 暗黙 suffix の位置を描画前の `<YYYY-MM-DD>` マーカー位置から算出するよう修正した。
- 回帰試験: 絞り込み38件＋SKILL参照31件＋全368件が OK。既存期待値変更は0件で、§10の増減なし。
  timeout試験の期待値は維持し、成功側の固定処理時間を吸収するため入力timeoutだけ
  `0.15` 秒から `0.5` 秒へ安定化した。
- skill-creator の `quick_validate.py` は環境に `yaml` module が無く起動不能。追加installはせず、
  front matter と差分を直接確認した。製品試験への影響はない。

自己改善メモ: 複数ファイルを1つの `apply_patch` で触る場合も、各 Update File 内の照合文脈を
そのファイル自身から採る。timeout故障注入は失敗側の十分な遅延と成功側の固定起動費を分離し、
成功側に極端に短い境界を置かない。

### Stage 3（版 bump・docs・handoff）Round 1 — 承認
366 件全 green・shellcheck 通過。boss レビュー: handoff スクリプトは §12 全要件充足（SHA 必須
引数・fetch＋branch/HEAD/origin/clean 検証・両 tag preflight 照合・遡及 notes・detached checkout
でのフルスイート再実行・ensure_tag/ensure_release の冪等 SHA 検証と Release 修復・Issue close
冪等・進行中 run 確認プロンプト・archive 同期の hide/protect filter 二意味論＋dry-run 検証＋
スモーク）。ADOPTION 英日・config 表・版 bump・engine-shas（_normalized_sha により SHA 同一は
妥当）・scaffold 飛び越しテストも確認。§10 対応 4 件（scaffold 期待）正当。
コミット: `fa173af`（handoff スクリプトは suite が参照するため `git add -f` で同梱）。

## 最終レビュー（route 手順 5 — `codex exec review --base main`, Sol `high`）

指摘 4 件（P1×1・P2×2・P3×1）。裁定: P1（incremental プロンプトが未コミット変更を確認範囲から
落とす）受理・P2a（子プロセス出力の無制限蓄積）受理・P2b（公開時警告が report 本文に載らない）
**限定却下** — 公開済みファイルの書き換えは不変性契約違反で原理的に不可能、正本は gate stdout と
last_run に永続済み（SKILL に注記を追加して閉じる）・P3（suffix 挿入位置の日付誤選択）受理。
worker が 3 件修正＋SKILL 注記（368 件全 green・§10 増減なし・timeout 試験の起動猶予 0.15→0.5s は
テスト安定化のみ）。boss が修正 diff を検証（marker 位置の長さ差処理含め正確）。
コミット: `fa4973c`。**boss 最終承認 — PLAN §6 の DoD 充足（リリース実行分を除く）を確認。**

## route-close

（手順 7 実施後に記入: 対象タスク / HEAD / 変更ファイル / audit verdict 代替 / SSoT 更新有無）

（記入: 2026-08-25）
- **対象タスク**: NEXT-SESSION-PROMPT.xml — Issue #28（codex Phase-3 backend）・#37（レポート
  書き込み競合）の対応と保留リリース（v0.11.0 遡及＋v0.12.0）の一括準備
- **記録時点の HEAD**: `6709d1693c782b4c97bde9d1a0a495ee55063e2b`（branch
  `feat/v0.12.0-issues-28-37`、PR #38）
- **確定した変更ファイル**（コミット 4cc53bf/abcb7a9/cd98ccc/d7c3d3f/fa173af/fa4973c/6709d16）:
  engine: decide-verdict.py・start-run.py・open-run.py・plan-dispatch.py・docaudit_cache.py・
  新規 write-template.py・新規 codex-dispatch.py／SKILL.md／references: config-schema.md・
  新規 codex-phase3-verdict.schema.json・engine-shas.json／plugin.json（0.12.0）／
  docs: ADOPTION.md・ADOPTION.ja.md／tests: 8 ファイル（新規 3 含む・368 件全 green）／
  task 記録（git add -f）: PLAN・REVIEW・pr-body・原因実証・probe 結果・A/B 比較・
  release-handoff.sh。未コミットは着手前から存在する未追跡 `.claude/` のみ（本タスク未接触）。
- **audit verdict 代替**: この repo に doc-audit.json は無いため、変更した公開挙動に対応する文書
  （skills/audit/references/config-schema.md・docs/ADOPTION.md・docs/ADOPTION.ja.md・
  skills/audit/SKILL.md）を同一 branch 内で同時更新し、Stage 2c/3 の boss 全行 diff レビューで
  整合を確認（前例踏襲）。
- **SSoT 更新の有無**: **あり** — durable な公開仕様の変更（phase3Backend/
  phase3CodexTimeoutSeconds キー・gate-writes-report の report 意味論・UTC 日付・
  previousReportStatus）に対応して上記 4 文書を更新。それ以外の SSoT は 0 ファイル更新。
- **残作業（ユーザー実行）**: PR #38 の承認・マージ → `bash tasks/route/2026-08-25-issues-28-37-release/release-handoff.sh <merge-sha> 38`
  （v0.11.0 遡及タグ＋Release → v0.12.0 タグ＋Release → #37/#28 close → skills-dir 同期・検証）。
