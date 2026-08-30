メタ認知: rev.2 の対応表を追認し、前回指摘の言い換えに流れる危険がある。今回は「誤実装が通る入力」と「失敗しても成功終了する検査」に限定して判定した。

1／HIGH／`CODEGRAPH_DIR` の同値性を保証できない  
根拠: [PLAN.md:41](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:41) は codegraph と同じ trim を要求するが、実物は JavaScript の `String.trim()` を使用している（[directory.js:85](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/directory.js:85)）。N12 は `../x` が `..` と `/` を同時に含むため、片方しか検査しない誤実装でも通る。`\` 単独、`foo..bar`、前後空白付き有効名、NBSP/BOM、大文字、`.codegraph` 自体、Unicode 名も未検査である。probe と codegraph が別ディレクトリを参照し得る。  
推奨: N12を独立した無効入力と有効入力の表にし、`foo..bar`、`a\b`、`" .codegraph-win "`、NBSP/BOM、`.codegraph`、大文字、Unicode 名を追加する。

2／HIGH（前回 #4 対応不十分）／非通常ファイル契約を一般化した誤実装検査がない  
根拠: 分岐表は安定したファイル状態については網羅的だが、N5はDBのディレクトリ、N9は親ディレクトリ位置の通常ファイルしか検査しない（[PLAN.md:66](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:66)、[PLAN.md:70](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:70)）。「DBではディレクトリだけ」「親では通常ファイルだけ」を拒否する誤実装でも全Nケースを通る。表が明記するFIFOを検査していない。  
推奨: `DIR` がFIFO、`DB` がFIFOの2ケースを追加し、いずれも不実行・`index-failed`・対応stderrを厳密検査する。

3／HIGH（前回 #4・#9・#11 対応不十分）／テスト件数の基準が内部矛盾している  
根拠: 実測はprobe 20件、handoff 24件である。コマンド出力は `tests/test_codegraph_probe.py:20`、`tests/test_release_handoff.py:24`。N1〜N13はすべて「新規」なのでprobeは最低33件であり、[PLAN.md:58](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:58) の32件では1件欠落しても通る。またN14は既存methodの拡張なのに、[PLAN.md:76](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:76) は改修1以外の本体変更を禁止している。handoffの「既存26件」も実測24件と不一致。A1も最低追加数は13+1+1+2=17件なので、646ではなく少なくとも647件である。  
推奨: N→method対応表から件数を再計算し、probe≥33、handoff基準24、全体≥647へ統一したうえで、N14を既存本体変更の例外に明記する。

4／HIGH（前回 #11 対応不十分）／A1〜A8の多くが機械的な合否判定になっていない  
根拠: 実測では失敗したunittestをA1形式で流しても `Ran 1 test`、`FAILED` を表示しつつ終了状態は0だった。A3/A5形式の`tail`も0。さらに、0件の`grep -c`は終了状態1、差分を出した`comm -23`は終了状態0だった。したがってA1/A3/A5は失敗を成功扱いし、A2/A6は閾値を比較せず、A7は正しい0件で失敗終了し、A8は違反を出しても成功終了する（[PLAN.md:109](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:109)）。A4の`! grep`も読取エラーの終了状態2を成功へ反転する。  
推奨: 表示用パイプをゲートにせず、各期待値を明示比較して不一致時に終了状態1を返す単一の検査スクリプトにする。

5／HIGH（前回 #8・#11 対応不十分）／A8は変更ファイル集合を正しく作れない  
根拠: [PLAN.md:116](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:116) の`awk '{print $2}'`は空白を含むパスを切断し、rename/copyの新旧パスも処理できない。通常のporcelain出力は未追跡ディレクトリをまとめ、無視対象を出さない。[.gitignore:8](/Users/akiratakahashi/Projects/doc-audit-harness/.gitignore:8) により`tasks/`は無視され、現時点でもroute内ファイルは`git status`に出ない。さらに相対パス`allowed.txt`は§7の許可外で、固定 `/tmp/changed` は既存ファイルやsymlinkを上書きし得る。  
推奨: NUL区切りのGit出力、未追跡全件、無視対象との差分、rename両端を扱い、一時ファイルは安全に作成し、禁止パスが1件でもあれば失敗終了する専用検査に置き換える。

6／HIGH／fakeの記録内容では実行場所と環境変数の契約を検査できない  
根拠: 現行fakeは引数だけを記録する（[test_codegraph_probe.py:18](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:18)）。そのため、`cd "$REPO_ROOT"`を削除した実装や、実行直前に`CODEGRAPH_DIR`を上書きした実装でも同じログになる。また[test_codegraph_probe.py:31](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_codegraph_probe.py:31) は呼出元環境をそのまま継承するため、外部の`CODEGRAPH_DIR`でN1〜N9が変動する。これは[PLAN.md:53-55](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:53) の契約を検査していない。  
推奨: fakeに引数・現在位置・`CODEGRAPH_DIR`を構造化記録させ、呼出し回数を含む完全一致を要求し、通常ケースでは継承した`CODEGRAPH_DIR`を明示除去する。

7／HIGH／#66の「挙動不変」に自動契約がない  
根拠: [PLAN.md:86](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:86) は`not-model-invocable`と560〜563行の分岐を不変とするが、実測 `rg -n 'not-model-invocable|disable-model-invocation|CODE_REVIEW_STATE' tests` は0件だった。A4は空白入り旧文言だけを探し、ハイフン入り状態トークンを検査しない。文言修正時に状態名や分岐を変えても全ゲートを通る。  
推奨: `test_v015_contracts.py`に状態トークン、上流エラー文字列、560〜563行の各分岐を固定する回帰テストを追加する。

8／MEDIUM／A4は日本語の旧意味を残しても通る  
根拠: [ADOPTION.ja.md:79](/Users/akiratakahashi/Projects/doc-audit-harness/docs/ADOPTION.ja.md:79) には「ユーザー実行のみ」と「モデルからは起動不可」が併存する。後者だけ置換すればA4は成功するが、前者の誤った制約は残る。[PLAN.md:112](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:112) の正規表現には「ユーザー実行のみ」がない。  
推奨: 単語検索ではなく、対象13行を特定し各行の旧表現が消えたことを検査する。

9／MEDIUM／新handoffの実行可能属性が未検査  
根拠: 複製元はGit上も実体も実行可能（実測 `100755`、`755`）。一方、既存テストは`/bin/bash HANDOFF`で起動する（[test_release_handoff.py:253](/Users/akiratakahashi/Projects/doc-audit-harness/tests/test_release_handoff.py:253)）ため、0644でも通る。A6も追跡件数しか見ない。直接`./release-handoff.sh`で実行する運用は回帰する。  
推奨: ファイル実体の実行可能属性とGit index mode `100755`を両方検査する。

10／MEDIUM／`CODEGRAPH_DIR`をstderrへ生で埋め込むとログ注入が可能  
根拠: codegraphは前後だけをtrimし、内部の改行や端末制御文字を拒否しない（[directory.js:85-92](/Users/akiratakahashi/.codegraph/versions/v1.5.0/lib/dist/directory.js:85)）。分岐1・2のstderrは`<DIRNAME>`を含める仕様だが、エスケープ規則がない（[PLAN.md:45](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:45)）。複数行ログの偽装や端末制御が可能になる。  
推奨: パス操作には元の値を使い、stderr表示だけは制御文字を可視化して1行へエスケープする。

11／MEDIUM／A10は「codegraph不実行」を判定できない  
根拠: [PLAN.md:118](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:118) は機械ゲート欄にあるがコマンドがなく、`codegraph.db`がディレクトリの場合、実物の`sync`失敗もprobeの事前拒否も同じ`index-failed`になり得る。出力だけでは不実行を証明できない。  
推奨: 呼出しを記録してから実物へ転送するラッパーを使う再現スクリプトを定義し、ディレクトリケースの呼出し回数0を比較する。

12／MEDIUM／§7のroute許可とforce-addが広すぎる  
根拠: [PLAN.md:136](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:136) はroute配下すべてを許可し、[PLAN.md:100](/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-30-issue-65-v0.15.1/PLAN.md:100) はroute dirのforce-addを指示する。実測では同ディレクトリに`sol-r1-log.txt`、`sol-r1-out.md`、`sol-r2-log.txt`等が既にあり、ディレクトリ単位の追加では計画外ログも公開対象になる。A8もroute glob内なので検出しない。  
推奨: force-add対象と§7の許可を、公開する計画・レビュー文書・`release-handoff.sh`の具体的なファイル名に限定する。

計画自体を直すべき HIGH の一覧: **1、2、3、4、5、6、7**  
このまま実装に進めてよいか: **進めるべきではない。特に検査が失敗を成功扱いするため、現状では完了判定を信用できない。**