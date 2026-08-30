メタ認知: 表の網羅性を状態遷移の完全性と取り違えないよう、失敗途中と再入場を重点的に確認した。R3-1の信頼境界の格下げは受理し、外部の改変不能ストアは再要求しない。

結論は、まだ収束していない。

[R4-1] Major last_run の書込み・読取り失敗時に、履歴隔離待ちを解除して開ける経路が残る  
→ 根拠: 隔離失敗 marker を「書けなければそのまま」と許容し、lock だけを残す（[PLAN.md:49](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:49)）。しかし `--break-lock` と既知RUNIDの `--release` は lock を削除するだけである（[open-run.py:87](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:87)、[open-run.py:108](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/open-run.py:108)）。SKILLの一般規約も terminal path で release を要求する（[SKILL.md:70](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/SKILL.md:70)）。marker 書込みが失敗した状態で解除すると、次回 open は再隔離を起動せず、live history を正規入力にする。さらに unreadable last_run を `--accept-config` だけで開ける仕様では（[PLAN.md:10](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:10)）、その中にあった可能性のある `historyQuarantineFailed` も config 承認で消える。  
→ 推奨する修正: marker 永続化失敗を lock holder にも記録し、`--release`／`--break-lock`／unreadable last_run の承認時はいずれも live history の隔離成功前に unlock/open できない単一の回復規則にする。

[R4-2] Major history parser の symlink 検査は実装不能かつ、正当な過去履歴を後日の通常変更で corrupt にする  
→ 根拠: `parse_history_document(data)` は repo root を受け取らないのに、file の symlink 成分検査を要求する（[PLAN.md:65](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:65)）。既存 validator の symlink 判定は現在の filesystem と repo root に依存する（[docaudit_paths.py:37](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:37)、[docaudit_paths.py:49](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_paths.py:49)）。前回は通常ファイルだった path が次 run で symlink になっただけで、保存 bytes が正しい history 全体を4 readerが corrupt と判定・隔離する。CT-5はこの誤動作を正解として固定している（[PLAN.md:83](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:83)）。  
→ 推奨する修正: history parser は型と字句的な repo-relative 正規形だけを検査し、現在の存在・通常ファイル・symlink はS11のcarry-forward選択時だけ検査する。

[R4-3] Major §9.6 が resolve-impact→plan-dispatch 間の既存 history SHA 防壁を脱落させている  
→ 根拠: 真理値表は plan-dispatch の SHA 不一致を `—` とする（[PLAN.md:187](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:187)）。現行では resolve-impact が読んだ history の SHA を出力し（[resolve-impact.py:243](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:243)、[resolve-impact.py:338](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/resolve-impact.py:338)）、plan-dispatch が再読値と照合している（[plan-dispatch.py:103](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/plan-dispatch.py:103)）。現行の不一致 exit 3 はv4のexit 7/token停止規約へ入らず、変更されたhistoryを隔離しない。一方、plan-dispatch はobserverに列挙済みである（[PLAN.md:180](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:180)）。  
→ 推奨する修正: `impact.historySha` がある場合の不一致を exit 7のhistory mismatchとして定義し、`--taint-observed history --observed-by plan-dispatch.py`へ流す行とテストを§9.6に追加する。

[R4-4] Major §9.7 は不可能な promptVariant×state を受理し、flip記録だけを回避できる  
→ 根拠: incrementalの`diff`/`null`でstateを「任意」とするため、`diff/not-active`や`null/completed`が通る（[PLAN.md:201](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:201)）。後者ではcompleted findingsをverdictへ入れながらrecordを残さず、flip計測を回避できる。現行state集合は `completed/execution-failed/ref-invalid/skipped-full-run/not-active` であり（[docaudit_cache.py:11](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:11)）、表の `not-installed` はstateではなくreasonである（[codex-review-plan.py:33](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:33)、[codex-review-plan.py:36](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/codex-review-plan.py:36)）。欠落した `promptVariant` の扱いもない。  
→ 推奨する修正: plannerが生成可能な `(mode, promptVariant, state)` を完全列挙し、キー欠落を含む未列挙組合せをすべてREFUSEDにする。

[R4-5] Major 512 KiB上限はJSON escapeを考慮せず、仕様上validな最大recordを拒否する  
→ 根拠: PLANは500件×512 bytesを約300 KiBと見積もる（[PLAN.md:64](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:64)）が、historyのfileには引用符を禁止していない。512-byteの引用符主体pathを500件生成した実測では、compact JSONが523,829 bytes、現行writerと同じindent=2では536,866 bytesとなり、512 KiB＝524,288 bytesを超えた。現行 `json_bytes` はindent=2である（[docaudit_cache.py:96](/Users/akiratakahashi/Projects/doc-audit-harness/skills/audit/scripts/docaudit_cache.py:96)）。CT-5の「500件×512 bytes」はescape最悪形を指定していない。  
→ 推奨する修正: recordサイズ判定用のcanonical serializationを固定し、その表現でescape最悪形を含む最大recordが通る上限と境界テストに改める。

再計数結果は次のとおりで、数値自体は一致する。

- N=22
- M=4
- G=13
- K=21
- O=19

ただしregistry #10の `stamp ≥ 0.16.0`（[PLAN.md:134](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:134)）は、S6の `== 0.16.0`（[PLAN.md:55](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md:55)）へ表記を合わせる必要がある。件数には影響しない。

計画自体の欠陥:

- R4-1〜R4-5すべて。実装前に状態遷移・真理値表・サイズ契約を修正すべきである。
- 足りない成果物は、marker永続化失敗を含む回復状態表、pre-seal history SHA行、完全なPhase-4 eligibility表、escape最悪形の境界テスト。
- 落とすべき成果物は、history parserでの現在filesystem依存のsymlink検査。carry-forward時の検査だけで足りる。

worker指示で吸収できる細部:

- registry #10の `≥`→`==` 修正。
- 上記契約確定後のatomic replaceやcanonical serializerの具体的な実装方法。

ファイル変更は行っていない。