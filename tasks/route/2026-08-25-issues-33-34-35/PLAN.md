# PLAN — Issues #33 / #34 / #35 対策 + v0.11.0 リリース（rev.6 — Sol 批判 R1〜R5 反映・最終）

日付: 2026-08-25 ／ boss: Fable（計画・レビュー専任） ／ worker: Sol/Terra/Luna（実装）

## 1. 目的

docaudit の決定論 3 層エンジンの 3 つの構造欠陥を修正し、v0.11.0 として一気通貫
（実装→テスト→PR→マージ→タグ→GitHub Release→Issue クローズ→skills-dir 同期）でリリースする。

- **#33**: bare path が不可視／リンク・backtick で severity が非対称 → bare 検出（WARN の検出網）追加＋
  構文明示パス（link/backtick）の FAIL 規則整備（§5.1。bare=WARN は R1〜R3 を経た明示的裁定 — R4-10）
- **#34**: `docGlobs` 共用による構造的永久 WARN → `layerGlobs` + `frontMatterOverrides`（additive）（§5.2）
- **#35**: 監査レポートの corpus 残留 → **単一のレポートマッチャ**を全経路（changed[] 除外・sibling-scan・
  corpus 列挙・impact pool・supplement・start-run）で統一し、corpus 側はデフォルト除外（§5.3）

バージョンは **v0.11.0（minor）**。ユーザー原文は「パッチ」だったがインタビューで minor に合意変更済み。

## 2. 入力・参照資料

- GitHub Issues #33/#34/#35、事前調査 `OUT-investigate.md`（Luna）
- 計画批判: `OUT-critique-r1.md`（4B/8M/2m）・`OUT-critique-r2.md`（4B/6M/5m）— 全件裁定済み（REVIEW.md）
- report-pattern 正本: `change-set-sha.py:43-57`（§5.3 で regex 化する）
- scaffold 同期契約: 版エントリは `check-docs`/`doc-lint`/`check-docs-engine` の 3 SHA 必須（scaffold.py:172-180）
- リリース手順（メモリ）: bump + `docaudit--vX.Y.Z` タグ + GitHub Release + skills-dir 再同期

## 3. 担当

boss = Fable（計画・裁定・全 diff レビュー・承認・リリース指揮）

## 4. 実行者

- 計画批判: Sol `high`（read-only, session 01a0369f-ed50-73b2-b407-2ec7ff938e34）
- 実装: **Terra `high`**（workspace-write。R2 で仕様の微妙さが判明したため既定の medium から 1 段引き上げ）
- 最終レビュー: `codex exec review` Sol `high`（承認直前に 1 回）

## 5. 成果物（仕様）

### 5.0 共通プリミティブ（existence 層・bare 収穫が共有）

- **コードマスク**: existence 層のトークン抽出（backtick・bare とも）は
  `_mask_fenced(text)` ＋ **indented code マスク**適用後のテキストに対して行う（R2-2 対応。
  fenced/indented code 内の backtick token が FAIL 化するのを防ぐ。従来そこから出ていた WARN も消えるが
  改善として許容し、テストで固定）。
  - **fence 判定の簡易拡張（R3-4, R4-4）**: fence の開始・終了判定は、行頭の blockquote マーカー
    （`>` ＋任意空白）とリストマーカー（`-`/`*`/`+`/`数字.`/`数字)` ＋空白）を**反復的に**（どちらの
    マーカーも残らなくなるまで。各反復は必ず文字を消費するので停止する — 固定上限は設けない R5-4）
    剥がした後のテキストに対して行う。これにより blockquote/リストの
    入れ子（`- > ` 等）内の fenced code もマスクされる。過剰マスク側（finding が減る方向）に倒れる
    簡易判定であることを config-schema.md に記載。
  - indented code の判定（簡易・文書化する）: 上記マーカー剥がし後、残りが 4 空白以上またはタブで
    始まる行をマスクする。リスト内継続行の誤マスク（検出漏れ側に倒れる）は既知の限界（R2-11）。
  - bare 収穫はさらに (a) markdown リンク `[...](...)` のマッチ範囲、(b) inline code span、
    (c) URL（`[a-zA-Z][a-zA-Z0-9+.-]*://` ＋ **URL 文字クラス** `[A-Za-z0-9_./+%@~?#=&:;,()-]` の連続。
    `\S+` ではなく文字クラスで止めることで日本語直結文を巻き込まず（R3-5）、query/fragment 内の
    パス様文字列も URL の一部としてマスクする（R4-9: `https://x.com/?next=docs/gone.md` を
    誤収穫しない））を空白化してから行う。
- **repo パス判定** `looks_like_repo_path()` の強化（backtick・bare 共通）:
  - `..` セグメントを含むトークンを拒否（R1-8）
  - `//` で始まるトークンを拒否（scheme-relative URL の残骸 — R3-5）
  - 既存条件（`/` を含む・空白/シェル文字なし・先頭要素が実在トップディレクトリ）は維持
- **正規化パイプラインと解決判定（R4-3 で順序を確定）**: トークンごとに次の順で「判定基底パス」を得る:
  (1) `#`/`?` サフィックス除去 → (2) `:locator` があれば基底パス側を採用（基底が repo パスとして
  妥当な場合）→ (3) `%` を含む場合は percent-decode を試み、decode 結果が NUL・制御文字を含む、または
  `..` セグメントを含む場合は **decode 候補を破棄**（R4-2 の安全再検証。`%2e%2e` 対策）。
  解決は「基底パス」「decode 済み基底パス」の順に試み、どちらかが存在すれば finding なし。
  **file/dir 判定（下記）は、最後に解決を試みて失敗した判定基底パス**（decode 候補があれば decode 後）
  に適用する（→ `docs/gone.md?raw=1`・`docs/gone.md:12`・`docs/gone%2Emd` はいずれも基底
  `docs/gone.md` として FAIL クラス判定される）。
  ファイルシステム呼び出し（`os.path.exists`/`realpath`）は OSError/ValueError を捕捉し、例外時は
  そのトークンをスキップする（`docs/%00.md` のような入力で監査全体を停止させない — R4-2。回帰試験必須）。
  `os.path.realpath` が repo root（realpath）配下に無い場合は**トークンごとスキップ**
  （finding なし。symlink 越境を「解決済み」にも「stale」にもしない）（R2-9）。
- **file/dir 判定（FAIL クラス定義。backtick token にのみ使用）**: 判定基底パスに対し、末尾が `/` で
  ない ∧ basename が `.` 始まりでない ∧ basename の最後の `.` 以降が `[A-Za-z][A-Za-z0-9]{0,7}` に
  マッチ → 「具体的ファイルパス」。**非 ASCII を含む backtick パス（`docs/旧概要.md`）もこの定義に
  従い FAIL になりうる**（R4-1: 仕様とテストの統一 — backtick は著者明示なので ASCII 制限は課さない）。
  それ以外（末尾 `/`・拡張子なし `docs/LICENSE`・数字拡張子 `docs/v1.2`）は「ディレクトリ形状」。
  `docs/LICENSE` 型が WARN に留まるのは文書化する既知の限界（R1-3）。

### 5.1 #33 — bare path 検出（WARN の検出網）+ 構文明示パスの FAIL 昇格

**設計判断（R1-1・R2-1・R3-1/2/3 の最終裁定 — 3 ラウンドの結論）:**
散文からの bare 収穫は、コマンド例・日本語の直結文・Unicode 境界の曖昧さにより、blocking 権限
（FAIL）を与えられる精度に原理的に到達しない（R3-1: 降格則は回避可能、R3-2: 1 候補コマンドの偽陽性は
高頻度、R3-3: Unicode 融合）。したがって:
- **bare path finding は常に WARN**（「検出網」。Phase-4 決定論層の可視化と、監査レポート経由の
  修正誘導が目的）。コマンド行降格則・非 ASCII フォールバック解決は**採用しない**（削除）。
- **FAIL 昇格は著者がパスと明示した構文のみ**: markdown link（format 層、従来から FAIL）と
  backtick token（§5.0 の「具体的ファイルパス」のみ FAIL、他は WARN）。
- ユーザー合意（Q3）は check_existence の backtick token に関するものであり、この裁定はそれを満たす。
  Issue #33 の bare 提案も「収穫の追加」であり severity 指定はない。整合を REVIEW.md に記録。

**(a) bare path ハーベスタ（新設・WARN 専用）**
- §5.0 のマスク済みテキストから、**ASCII パス文字クラス** `[A-Za-z0-9_./+%@~-]` の最長連続で `/` を
  含むものを候補として抽出。抽出後、末尾の `.` を 1 個トリム。
  - 非 ASCII ファイル名（`docs/旧概要.md`）の bare 参照は検出対象外（既知の限界として文書化。
    backtick/link で書かれていれば従来どおり検査される）。これにより R3-3（日本語融合）・R3-7
    （後置曖昧性）・R3-13（NFD）は構造的に発生しない。日本語文中の ASCII パス
    （`docs/gone.mdを参照` の `docs/gone.md`）は文字クラス境界で正しく切れる。
- glob/ellipsis/brace 除外・`path:line` 基底解決・§5.0 の解決判定を適用。backtick token とは対象
  テキストが排他（inline code マスク済み）なので二重報告なし（テストで固定）。
- message は bare 由来と分かる文言（例: `bare path reference does not resolve: ...`）。

**(b) backtick token の FAIL 昇格（ユーザー合意の適用先）**
- `check_existence` の backtick token（§5.0 マスク済みテキストから抽出）で、解決せず「具体的
  ファイルパス」なら **FAIL**。「ディレクトリ形状」は WARN 維持。
- link（format 層 FAIL）は無変更。
- docstring（generic-layers.py:8-19）と ADOPTION.md:350 / ADOPTION.ja.md:331（existence=WARN の説明）を
  新挙動へ更新（R2-15）。

**互換性注記**: 既存 repo で CONSISTENT→NEEDS FIX がありうる。#35 除外との同梱・layerGlobs が緩和策。
config-schema.md と Release notes に明記。

### 5.2 #34 — `layerGlobs` + `frontMatterOverrides`（additive・generic-layers.py のみ）

（rev.2 から変更なし。要点のみ）
- `layerGlobs.{format,existence,semantic}.exclude`: 各 check 関数内部で適用（`--paths` 経由にも効く）。
  semantic は「orphan 報告対象」からの除外のみで、**発リンクは referenced に残す**（scan は縮めない）。
- `frontMatterOverrides`: 配列先勝ち・`fields: []`=スキップ・一致なしは `frontMatterFields` fallback。
- 不正型仕様: 不正部分は無視し WARN finding 1 件（path は `"(config)"` とし、**text 出力の pass 集計は
  「findings のうち docs に属する path」だけで減算する**よう修正 — R2-13）。未知キーは黙って無視。

### 5.3 #35 — レポートマッチャの統一と corpus 除外（R2-3/4/5/6/10 裁定）

**単一マッチャ仕様（テンプレート由来 regex — 全経路共通の唯一の定義）:**
- `reportPath` テンプレート全体から導出する（**placeholder 変換規則を明示 — R5-3**）:
  1. `<YYYY-MM-DD>` → `[0-9]{4}-[0-9]{2}-[0-9]{2}`（**`\d` は使わない** — 全角数字対策 R3-12）
  2. `[_NN]` がテンプレートに**ある**場合: **その記述位置で** `(_[0-9]{2,})?` に置換（R5-1: 現行の
     `_01` 置換と同じ位置意味論を維持。`audit_<日付>_final[_NN].md` の既存レポート
     `audit_2026-08-24_final_02.md` は引き続きマッチする）
  3. `[_NN]` が**ない**場合: basename 内の日付 placeholder の直後に `(_[0-9]{2,})?` を挿入（R4-6 の
     互換性回帰対応 — R2-6 の絞り込みの明示的上書き。日付 placeholder が複数ある場合は
     **basename 内のもの**に適用。妥当性条件により basename には必ず 1 個ある）
  4. 残りのリテラル部分を `re.escape` した全体一致 regex とする（`[_NN]`・`<YYYY-MM-DD>` を
     リテラル扱いしないことをテストで固定）。
- **妥当性条件は正本 `change-set-sha.py:43-57` の現行実装を一切変更しない**（placeholder が basename 内・
  日付前 prefix 非空・サンプル instantiation が docGlobs に一致。R3-10）。regex 化は「マッチ判定」のみの
  置換であり、`docs/<YYYY-MM-DD>.md`（空 prefix）が除外されない既存挙動
  （tests/test_wp12_contracts.py:144-151）は維持する。導出不能時はマッチャなし＝除外なし。
- **生成側の suffix 契約を明文化（R3-11, R4-6/7）**: `skills/audit/SKILL.md` のレポート作成手順に
  「衝突時の suffix はゼロ埋め 2 桁の `_02` から開始（`_99` の次は `_100`）。挿入位置は `[_NN]` が
  テンプレートにあればその位置、無ければ日付の直後（マッチャの suffix 位置と一致 — R5-1）。既存
  レポートの上書き禁止」を明記し、
  生成物が必ずマッチャに一致することを保証する。この SKILL.md 変更は変更範囲・完了条件に含める。

**正本の置き換え（二本立ての解消 — R2-5）:**
- `change-set-sha.py` の report 除外（:46-57 の glob 導出と excluded() での使用）を上記 regex に
  置き換える。→ `doc_audit_policy.md` のような非レポート文書が changed[] からも除外されなくなる
  （過剰除外の根治。#31 の意図＝「機構自身の出力の除外」は日付付き実レポートで維持される）。
- `decide-verdict.py` → `sibling-scan.py` へ渡すパターンも同 regex に統一（sibling-scan の
  `--report-pattern` は regex を受ける形に変更。プラグイン内部 CLI であり配布物ではないことを確認済み）。
- 実装形態: 配布物である `generic-layers.py` には self-contained 複製（正本の場所をコメント明記）。
  それ以外（change-set-sha / resolve-impact / impact-supplement / start-run / decide-verdict）は
  repo 内複製または既存の再利用慣行に従う。**全実装を同一ケース表に通す契約テストを必須とする**
  （R2-10。ケース表: 正常形・`[_NN]` 有無×suffix 1/2/3 桁・日付後リテラル・`doc_audit_policy.md`・
  非 `.md`・placeholder 欠落・docGlobs 不一致・opt-in true/false）。

**マッチャの一致規則と除外の有効条件の分離（R3-8 の裁定）:**
- **マッチャ（regex）は全経路で同一**（契約テストで全実装の一致判定を固定）。
- **除外を有効にする条件は経路のクラスで異なる**:
  - **機構除外（無条件・opt-in の影響を受けない）**: `change-set-sha.py excluded()`（changed[] 除外）と
    sibling-scan への除外パターン供給。監査レポートは機構出力であり、sealed change-set / cache 資格の
    安定性のため常に除外（現行契約 SKILL.md:283-288 を維持）。
  - **corpus 除外（デフォルト有効・`auditReportsInCorpus: true` で無効化）**: generic-layers 列挙・
    resolve-impact full/heuristic・impact-supplement 候補・start-run corpus 数の 4 経路のみ。
- opt-in が機構除外に**影響しない**ことをテストで明示的に固定する。

**corpus 側の適用詳細:**
- `generic-layers.py`: `list_doc_files()` の列挙から除外。**明示 `--paths` は除外しない**。ただし
  semantic の scan 集合（all_docs）は「除外済み列挙 ∪ 明示 `--paths`」とし、明示指定されたレポートの
  発リンクが referenced に入るようにする（R2-7 の偽 orphan 防止）。
- `resolve-impact.py`: full corpus と heuristic pool から除外。mapped は無変更。
- `impact-supplement.py`: **CLI に任意引数 `--config <doc-audit.json>` を追加**（R3-9: 必須にしない。
  未指定時は除外なし＝現行挙動・no-op 契約を完全維持し、既存テスト・直接呼び出しを壊さない。
  後方互換テストを追加）。`skills/audit/SKILL.md` の呼び出し箇所（:298-306 付近）は `--config` を
  渡す形へ更新（R2-4）。
- `start-run.py`: corpus 数算出に同じ除外を適用（R1-7）。
- opt-in は **bool `true` のみ**有効。他の型は false 扱い（generic-layers は WARN finding、他は黙って false）。
- opt-in 復帰テストは **corpus 4 経路すべて**で行う（R2-10）。

### 5.4 ドキュメント・テンプレート同期

- `config-schema.md`: 新キー 3 種（`layerGlobs`/`frontMatterOverrides`/`auditReportsInCorpus`）、
  severity 変更と互換性影響、file/dir 判定・bare=非 ASCII 検出対象外・fence/indented 簡易判定の
  既知の限界、レポートマッチャのテンプレート由来 regex 仕様（suffix 常時許容と生成契約を含む）。
- `ADOPTION.md:350` / `ADOPTION.ja.md:331`: existence 層の説明を新 severity へ更新（R2-15）。
- `SKILL.md`/`init SKILL.md`/`scaffold.py` テンプレート: existence=WARN 前提・リンク限定の記述を grep で
  再確認し、あれば更新（無ければ「該当なし」報告。無理に変更を作らない）。
  ※ `SKILL.md` は impact-supplement 呼び出し契約の更新（§5.3）が必須で入る。
- `engine-shas.json`: 0.11.0 エントリを **3 SHA すべて**（scaffold.py の計算関数で算出。既存エントリ保持）。

### 5.5 バージョン bump（v0.11.0）

- `.claude-plugin/plugin.json:3`／`docs/ADOPTION.md:201`／`docs/ADOPTION.ja.md:186`／
  `docs/ADOPTION.ja.md:237-238`（refresh 到達版）／`tests/test_decide_verdict.py:422`／`engine-shas.json`
- `docs/ADOPTION.md:254`（英語版 refresh 説明）も 0.10.1→0.11.0 移行の記述に更新（R4-11）。
- 残置確認（R3-15, R4-11）: ゲートは配布物パス（.claude-plugin/ skills/ docs/）のみを対象とし、
  **許容残置のホワイトリスト**＝ (a) engine-shas.json の 0.10.1 履歴エントリ、(b) ADOPTION 両言語の
  「0.10.1 から 0.11.0 へ」という移行説明行。これ以外に `0.10.1` が無いこと。`tests/` は §5.6 の
  意図的参照（fixture・SHA assert）を許容。

### 5.6 テスト（強化版 — R2-12/13/14 反映。**期待値は件数・path・line まで固定**）

**#33:**
- reproducer 4 形式: link→format FAIL／backtick 具体ファイル→existence **FAIL**／bare（全角ダッシュ付き）
  →existence **WARN**（bare 由来 message）／backtick ディレクトリ→WARN — **件数・path・行番号を厳密に**
- bare 抽出の正例（動作の直接検証 — R2-12）: `「docs/gone.md」`・`docs/gone.mdを参照`・
  `- docs/logs/gone.md — 説明`・`cp docs/source.md docs/new.md`（new 不在→WARN 1 件）それぞれ
  **WARN 1 件・正しい行番号**
- 偽陽性の否定: `docs/api.md（旧版）`（実在）・`docs/api.md?raw=1`（実在）・`docs/foo+bar.md`（実在）・
  `docs/foo%20bar.md`（`docs/foo bar.md` 実在 — percent-decode 解決）・
  `https://example.comを参照。docs/api.md`（api.md 実在・URL マスクが後続を巻き込まない）・
  `https://docs/gone.md`／`//docs/gone.md`（URL・scheme-relative → finding 0 件）
- 非 ASCII の限界の固定: `docs/旧概要.md`（不在・bare）→ finding 0 件（検出対象外の仕様固定）／
  **同パスが backtick なら FAIL**（R4-1: 著者明示構文には ASCII 制限を課さない）
- 安全性（R4-2, R5-5）: `` `docs/%00.md` ``・`` `docs/%2e%2e/x.md` `` を含む文書で監査が停止せず decode
  候補が破棄されること、**および例外捕捉経路そのものの試験**（NUL 検査を通過してファイルシステム
  呼び出しで例外になる入力 — 生 NUL を含むトークンを直接関数に与える、または `os.path.exists` への
  例外注入（unittest.mock）— で「スキップして継続」を検証）
- 正規化順序（R4-3）: `` `docs/gone.md?raw=1` ``・`` `docs/gone.md#x` ``・`` `docs/gone.md:12` ``・
  `` `docs/gone%2Emd` ``（いずれも不在）→ すべて基底 `docs/gone.md` として **FAIL**
- コードマスク: fenced 内 backtick token（R2-2 再現例）・4 空白 indented 内・blockquote 内 fence・
  リスト内 fence・**入れ子 `- > ``` ` 内 fence・`1)` ordered list 内 fence（R4-4）** → finding 0 件
- URL 境界（R4-9）: `https://example.com/?next=docs/gone.md` → finding 0 件
- file/dir 境界（backtick）: `docs/LICENSE`→WARN・`docs/v1.2`→WARN・`docs/schema.d`→FAIL・末尾 `/`→WARN
- `..` 拒否・symlink 越境スキップ（repo 外 symlink fixture）・bare×backtick 二重報告なし・
  ellipsis/glob スキップとトリムの適用順
**#34:** rev.2 と同じ＋config WARN 時の text `pass` 件数整合（R2-13）
**#35:**
- マッチャ契約テスト: §5.3 ケース表 × 全実装（同一入力→同一判定）
- generic-layers: 列挙除外・明示 `--paths` 非除外・**明示レポートの発リンクが referenced に入る**
  （R2-7 の再現: レポート＋そこからのみリンクされる doc を --paths で渡し、偽 orphan が出ない）・
  `doc_audit_policy.md` 残留・opt-in 復帰・counts/pass 整合
- change-set-sha: 日付付きレポートは changed[] から除外・`doc_audit_policy.md` は**除外されない**
  （挙動変更の固定）・**opt-in true でも機構除外が維持される**（R3-8）・既存テストの期待値更新・
  **compute-baseline.sh 経由の統合テスト**（`[_NN]` suffix・policy.md 残留・`machineryExcludedCount`
  の固定 — R3-14）
- resolve-impact / impact-supplement（--config 経由）／start-run: 除外・opt-in 復帰（corpus 4 経路）・
  **impact-supplement の `--config` 未指定時の no-op 後方互換（R3-9）**・レポートのみ repo で
  start-run 正常・`mapGapCandidates` 等付随出力整合
- マッチャケース表の追加項目: 空 prefix（`docs/<YYYY-MM-DD>.md` — 非除外維持）・placeholder が
  ディレクトリ側・全角数字日付（非マッチ — R3-12）・**`[_NN]` 無しテンプレートでの `_02` 生成物
  （マッチ — R4-6）**・日付後リテラルと suffix の併存（`audit_<日付>_final.md` 型テンプレートでの
  suffix 位置）
- opt-in の不正型（`"true"`・`1`・`[]`）を **corpus 4 経路すべて**に与え、除外が解除されないこと（R4-8）
**scaffold:**
- 0.10.1 stamp の `scripts/check-docs.py` refresh → 0.11.0 更新／改変済み旧 engine は skipped。
  歴史的 fixture は `git show docaudit--v0.10.1:...` から取得して `tests/data/` に置き、テスト冒頭で
  **fixture の stamp 除外 SHA が engine-shas.json の 0.10.1 エントリと一致することを assert**（R2-14）
- 新規生成物 3 種の SHA が 0.11.0 エントリと一致
**後方互換:** 新キー未設定 config での既存テスト全 green（意図的差分は #33 severity・#35 除外・
change-set-sha の過剰除外解消のみ）

## 6. 完了条件

1. `python3 -m unittest discover -s tests -t . -v` 全 green
2. §5.6 の全観点が期待値（件数・path・line）どおり
3. 新キー未設定 repo の挙動差が §5.6「後方互換」記載の意図的差分のみ
4. engine-shas.json 0.11.0 エントリ（3 SHA）が scaffold 計算と一致し `/docaudit:init --harness` が動作
5. 版文字列 §5.5 全箇所 bump・配布物パスの残置は §5.5 のホワイトリスト（engine-shas 履歴＋ADOPTION
   両言語の移行説明行）のみ（R5-2 で完了条件と検証コマンドを §5.5 に整合）
6. config-schema.md / ADOPTION（層説明 2 箇所＋refresh 説明の英日 2 箇所）/ SKILL.md
   （impact-supplement 契約＋suffix 生成契約）更新
6b. R4-5（レポート書き込みと並行監査の sealed 指紋の競合・同日 suffix 上書き競合）は**本リリースの
   スコープ外**（既存挙動で本変更と独立）とし、Sol の再現手順を引用した follow-up Issue を GitHub に
   起票する（リリースフェーズで実施）
7. boss の全行 diff レビュー承認 + `codex exec review`（Sol high）指摘ゼロまたは解消済み
8. リリース: feature ブランチ → PR → main マージ → `docaudit--v0.11.0` タグ → GitHub Release →
   Issue #33/#34/#35 クローズ → `~/.claude/skills/docaudit/` 再同期（同期一致確認）
9. route-close: /docaudit:audit 実行（走った版を REVIEW.md に記録）、REVIEW.md に close marker

## 7. 変更範囲

**許可:**
- `skills/audit/scripts/generic-layers.py` / `resolve-impact.py` / `impact-supplement.py`（--config 追加＋
  除外）/ `start-run.py`（corpus 数除外のみ）
- `skills/audit/scripts/change-set-sha.py` / `decide-verdict.py` / `sibling-scan.py`
  （**レポートマッチャの regex 統一に必要な変更のみ**。他のロジックは不可）
- `skills/audit/references/config-schema.md` / `engine-shas.json`
- `skills/audit/scripts/scaffold.py`（テンプレート文言更新が必要な場合のみ）
- `skills/audit/SKILL.md`（impact-supplement 呼び出し契約＋層説明＋**レポート作成手順の suffix 生成
  契約（R4-7）**）/ `skills/init/SKILL.md`（層説明のみ）
- `.claude-plugin/plugin.json`, `docs/ADOPTION.md`, `docs/ADOPTION.ja.md`
- `tests/`（`tests/data/` の歴史的 fixture 追加を含む）
- `tasks/route/2026-08-25-issues-33-34-35/`

**禁止:**
- `compute-baseline.sh`（change-set-sha.py の excluded() を呼ぶ側 — 呼び出し契約を変えない）、
  上記以外のスクリプト・`.gitignore`・`agents/`・`data/`・過去 `tasks/`
- リファクタ・共通モジュール抽出。generic-layers.py の self-contained 契約（import なし）維持

## 8. 検証コマンド一式

```bash
python3 -m unittest discover -s tests -t . -v            # 品質ゲート（README 記載）
python3 -m unittest tests.test_scaffold -v               # scaffold / engine-shas 整合
# #33 reproducer 手動確認（boss 目視）
python3 skills/audit/scripts/generic-layers.py --config <fixture>/doc-audit.json \
  --repo-root <fixture> --layer all --format json
# 版残置確認（配布物パスのみ。ホワイトリスト＝engine-shas 履歴＋ADOPTION 両言語の移行説明行 — R5-2）
grep -rn "0\.10\.1" .claude-plugin/ skills/ docs/ | grep -v __pycache__ | grep -v engine-shas.json \
  | grep -v 'ADOPTION.*\.md'   # ADOPTION の残置は移行説明行のみであることを目視確認
grep -c '0\.10\.1' skills/audit/references/engine-shas.json
# リリース後
git tag -l 'docaudit--v0.11.0' && gh release view docaudit--v0.11.0
```

## 改訂履歴

- rev.6（最終）: Sol R5（2B/3M/1I）全件反映。suffix は `[_NN]` の記述位置を維持（無い場合のみ日付直後
  挿入 — R5-1）／placeholder→regex 変換規則を 4 段で明示（R5-3）／マーカー剥がしの固定上限撤廃
  （R5-4）／例外捕捉経路の直接試験（R5-5）／版残置の完了条件・検証コマンドをホワイトリストに整合
  （R5-2）。R4-5 スコープ外裁定は Sol 受容（INFO）。批判ループは上限 5 往復に到達し、残指摘は全て
  機械的仕様修正だったため rev.6 を実装フェーズの拘束仕様として確定。
- rev.1: 初版
- rev.2: Sol R1（4B/8M/2m）全件反映
- rev.3: Sol R2（4B/6M/5m）全件反映。bare=FAIL＋コマンド行降格則／existence 層コードマスク／
  マッチャ全経路統一（change-set-sha 等 scope 入り）／--config／semantic union／Unicode 抽出／
  realpath／テスト強化／実装者 Terra high
- rev.5: Sol R4（2B/5M/4m）反映。backtick 非 ASCII は FAIL（仕様とテスト統一 R4-1）／percent-decode の
  NUL・`..` 安全再検証と例外時トークンスキップ（R4-2）／FAIL 判定の正規化パイプライン確定（R4-3）／
  fence マーカー剥がしを反復化＋`数字)` 対応（R4-4）／R4-5 はスコープ外＝follow-up Issue 起票／
  suffix 常時許容へ（R2-6 の明示的上書き）＋生成契約を scope・完了条件へ（R4-6,7）／opt-in 不正型
  ×4 経路テスト（R4-8）／URL 文字クラス拡張（R4-9）／文言整合（R4-10）／残置ゲートのホワイトリスト化＋
  ADOPTION.md:254（R4-11）
- rev.4: Sol R3（4B[1,2,3,8]/6M/5m）全件反映。**設計単純化**: bare は常に WARN（検出網）とし、降格則・
  Unicode 抽出・フォールバック解決を削除（R3-1,2,3,7,13 を構造的に解消。FAIL 昇格は link/backtick のみ）／
  fence 判定に blockquote/リストマーカー剥がし（R3-4）／URL マスクをパス文字クラスで停止＋`//` 拒否
  （R3-5）／percent-decode 解決（R3-6）／**opt-in は corpus 4 経路のみ・機構除外（changed[]/sibling-scan）
  は無条件**（R3-8）／impact-supplement --config は任意＋no-op 互換（R3-9）／正本の妥当性条件を無変更と
  明記（R3-10）／生成側 suffix 契約を SKILL.md に明文化（R3-11）／`[0-9]` 使用（R3-12）／
  compute-baseline.sh 経由統合テスト（R3-14）／版残置ゲートを配布物パス限定（R3-15）
