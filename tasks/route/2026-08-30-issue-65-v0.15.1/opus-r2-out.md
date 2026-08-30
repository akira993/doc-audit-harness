# Opus R2 — rev.7 再レビュー（docaudit v0.15.1）

**判定: 実装承認可。** R1 のブロッキング 4 件はすべて意図どおりに反映され、反映によって新たな組み合わせ矛盾は生じていない（下記 §2 で 7 点を実測照合）。残る指摘は 5 件すべて非ブロッキングで、うち 2 件は 1 行修正なので rev.7 に折り込むことを推奨する（折り込まなくても実装は開始できる）。

検証は read-only。rev.6 との差分は 70 行で、全行を読んだ。repo は変更していない（本ファイルの Write のみ）。

---

## 1. 反映の確認（R1 指摘 → rev.7）

| R1 | 反映 | 判定 |
|---|---|---|
| B-1 許可範囲 216-217 | §5.3 が `SKILL.md:216-218`（「218 行頭の `fast);` は 217 の sync 節の続き — 3 行を同じ 3 行数のまま書き換える」）、§7 が `:216-218`、G11(2) の許可行が `{3, 216-218, 560-563, 778}`。config-schema は「283 行頭が `self-generates ...` で始まるため 282 の置換文は主語 `codegraph` で終える」を明記 | **意図どおり**。実体（216-218 の折り返し、283 行頭）と一致 |
| B-2 注記 × insert=0 | §5.4 が「**注記の追加は禁止** — G11 は総行数不変を要求する」に変更。G11 は difflib を廃し「(1) 総行数同一／(2) 許可行以外の全行完全一致／(3) 行 3 は `old_line3.replace(...)` で gate 内生成・行 778 はリテラル」へ | **意図どおり**。行番号固定の前提（挿入ゼロ）が (1) により構成的に保証される |
| B-3 ascii 生成主体 | §5.1 が 4 フィールド `STATE\0BIN\0DIRNAME\0DIRNAME_ESC\0`、`DIRNAME_ESC = ascii(DIRNAME)` を python 側で生成、read イディオムを 1 行提示、python の 4 出口（:35 裸 `print`・:45・:47・:49）すべてを同形式にすることを明記 | **意図どおり**。イディオムを実機検証した（§2-5） |
| B-4 test_j の 0.12.0 罠 | §5.5 が「`set(json.loads(read(SHAS))) | {plugin_version}` から**導出**。版リテラルを増やさない」＋理由（test_j が allowlist 外の `0.12.0` リテラル行を検出）を明記 | **意図どおり**。推奨した導出方式そのもの |
| S-1 G13 削除 | G13 と `--ignored-manifest` を削除（G1〜G12）、A1・A2・§8 の該当記述も同時に除去、G8 に「追跡済み route dir は `git diff` に出るので本検査がカバー」の理由を追記 | **完全に反映**。`grep 'G13|manifest'` の残存は G8 の説明文 1 箇所のみで、これは経緯の記録として妥当 |
| S-2 trim 表 | U+0085 を「剥がれない」側に追加（5 文字）、「U+FEFF が最重要: JS が剥がして Python が剥がさない唯一の方向で、export が保険にならない」を明記 | **意図どおり**（表維持を選択したうえで欠落を補った） |
| (d)3 fake の stdin | §5.2 に「fake は argv 記録の**前**に必ず `sys.stdin.read()` を実行して読み切る」 | 反映済み |
| (d)4 G11 期待行の生成 | G11(3) が `old_line3.replace(...)`（ハードコード不要） | 反映済み |
| 軽微 1（auto-close） | §5.6 が「commit message 全体と PR body に closing keyword（`Closes`/`Fixes`/`Resolves` 等）＋ `#N` を書かない。裸の `#65` 単独は発火しない」へ精密化 | 反映済み |
| 軽微 2（symlink regression） | ADOPTION v0.15.1 ブロック (1) に「従来は有効な symlink 構成でも sync が通っていたが、本版から意図的に非対応」を追加 | 反映済み |
| 軽微 3（config-schema は元から 0） | G4 の期待欄に注記 | 反映済み |

R1 の全指摘が反映されている。取りこぼしは無い。

---

## 2. 新たな組み合わせ矛盾の探索（すべて実測。結果は 7 点とも「無し」）

1. **G11(2)「許可行以外の全行が完全一致」× 版 bump（0.15.1）** — `grep -n '0\.1[0-9]\.[0-9]' skills/audit/SKILL.md skills/audit/references/config-schema.md` = **0 件**。この 2 ファイルに版文字列は存在しないので、版 bump が G11(2) と衝突する経路は無い。
2. **G11(1) 総行数不変 × §5.3「3 行で分岐説明を書き切る」— 実現可能**。制約は「216-218 の 3 行に収める」だけで行長の制限は無い（SKILL.md:3 は約 470 字の 1 行なので前例あり）。例: 216「fresh: `<dir>/codegraph.db` absent → `codegraph init .` (first run; `<dir>` honors」／217「`CODEGRAPH_DIR`); a regular-file db → `codegraph sync .` (idempotent — init's idempotency is」／218「version-dependent, so the probe never relies on it); a symlinked dir/db or a non-regular db is not touched (index-failed); it never touches `.gitignore` itself (codegraph self-generates `<dir>/.gitignore`).」で 3 行に収まる。**実装不能ではない**。
3. **G11(2)「560-563 は許可行」× §5.4「560-563 は不変」** — 許可であって義務ではないので矛盾しない。かつ 560-563 の自由編集は §5.5 の #66 回帰契約（(a) :560・(b) :562-563 の完全文固定）が塞いでいる。**二重防護として整合**。
4. **G11(3) 行 3 の生成式 × G4 の残骸検査** — 旧 :3 は `... (not model-invocable), and emits one ...` を含み、`replace("(not model-invocable)", "(not started by the audit itself yet)")` が成立する（実体で確認）。生成後の行は G4 の禁止 5 語をいずれも含まない。**整合**。
5. **4 フィールド NUL 受け渡し × `set -uo pipefail`** — 実機検証:
   ```
   { IFS= read -r -d "" A; ... D; } < <(printf "en abled\0my bin\0.code graph\0'.code graph'\0")
   → A=[en abled] B=[my bin] C=[.code graph] D=['.code graph']
   ```
   内部空白を保持し 4 回読みが成立する。入力が空でも `read` は変数を空文字で**定義する**（`X=[] defined-ok`）ので `set -u` で落ちる経路も無い。**実装可能**。
6. **G13 削除 × A2／§8／§5.7 引数** — `--ignored-manifest` の残存参照は無し（grep 済み）。A2 の fixture 一覧も G13 行が削除され G1〜G12 に揃っている。**整合**。
7. **U+0085 追加 × §5.1 の実装指示** — §5.1 が指示する trim 文字クラスは**剥がす側の明示列挙**なので、U+0085 を明記しなくても正しい実装は自動的に「剥がさない」。N12 の表だけが検査対象を増やした形で、実装と検査は整合する（§5.1 の理由文の不備は N-5）。

---

## 3. 非ブロッキング所見（新規 5 件）

### N-1 §2 の入力資料一覧に `:216-217` が残っている（1 行修正・折り込み推奨）

- **file:line** — `PLAN.md:21`「加えて `SKILL.md:560-563` … と `:216-217`（#65 分岐説明）」。§5.3・§7・G11 は 216-218 に更新済みで、ここだけ rev.6 のまま。
- **影響** — worker が §2 を先に読むと許可範囲を 216-217 と誤認し、G11 で落ちてから §5.3 に気づく。
- **推奨** — `:216-217` を `:216-218` に直す。

### N-2 `CODEGRAPH_DIR` override は `digestExclude` で除外できない（ADOPTION に 1 句・折り込み推奨）

- **根拠（実測）** — `skills/audit/scripts/tree-digest.py:12` `KNOWN_ROOTS = {".mdq", ".codegraph", "graphify-out", ".cocoindex_code"}` は**固定リテラル集合**で、`skills/audit/references/config-schema.md:29` も受理接頭辞を `.claude/state`, `.claude/worktrees`, `.mdq`, `.codegraph`, `graphify-out`, `.cocoindex_code` に固定している。`CODEGRAPH_DIR=.codegraph-win` の索引ディレクトリは `digestExclude` に載せられず、tree digest に混入して索引更新のたびに digest が変わる。
- **これは本版が作る欠陥ではない**（現行版でも codegraph 自身が env を尊重して `.codegraph-win` に書くため同じ状態）。ただし v0.15.1 の ADOPTION ブロックは「`CODEGRAPH_DIR` 尊重」を**宣伝する**版なので、読者が override を新規採用して digest 不安定に当たる導線ができる。
- **推奨** — ADOPTION v0.15.1 ブロック (1) の末尾に 1 句だけ追加する: 「ただし `digestExclude` の受理接頭辞は `.codegraph` 固定のため、`CODEGRAPH_DIR` で改名した索引ディレクトリは digest から除外できない（#63 で追跡）」。en/ja 対訳の完全一致テストにもそのまま乗る。

### N-3 A2 の G11 fixture は (3) を検査していない

- **file:line** — `PLAN.md:139`「G11 SKILL.md の行 3 の直後に frontmatter 行を 1 行挿入（総行数不変の確認）」。この fixture は G11(1)(2) を発火させるが、**(3) の期待文字列照合**（行 3 の生成式・行 778 のリテラル）は一度も発火しない。
- **推奨** — G11 だけ fixture を 2 つにする（挿入 1 件＋「行 778 の 1 文字を変える」1 件）。A2 の趣旨（各検査が常に PASS でないことの実証）を G11 の 3 条件すべてに広げるために必要で、追加コストは 1 回の実測のみ。

### N-4 `ascii()` は引用符を含む（分岐表の stderr 文言との差）

- **根拠（実測）** — `python3 -c "print(ascii('foo\nbar'), ascii('索引'))"` → `'foo\nbar'` と `'索引'`。**前後に単引用符が付く**。
- **影響** — 分岐表の行 1・2 の stderr は `codegraph dir <DIRNAME> is a symlink; ...` と書かれているが、実際は `codegraph dir '.codegraph-win' is a symlink; ...` になる。N14 の検査（1 行・ASCII・エスケープ表現を含む）は通るので機能上の問題は無いが、B2（差分全行読解）で boss が「表と違う」と誤って差し戻す余地がある。
- **推奨** — §5.1 に「`ascii()` は前後に `'` を付ける。stderr 表記は `codegraph dir '<esc>' is a symlink` の形になる」と 1 文だけ添える（実装は変えない）。

### N-5 §5.1 の理由文が U+0085 を落としている（記述のみ）

- **file:line** — `PLAN.md:41`「Python の `str.strip()` は使わない — `\x1c`〜`\x1f` を余分に剥がし U+FEFF を剥がさない」。実測では `P∖J = {U+001C, U+001D, U+001E, U+001F, U+0085}`。N12 の表（:81）は U+0085 を含むよう更新済みなので**検査は正しい**が、理由文だけ 4 文字のままで不整合。
- **推奨** — 「`\x1c`〜`\x1f` と U+0085 を余分に剥がし」に直す（実装指示は明示列挙なので挙動は変わらない）。

---

## 4. 参考: rev.7 で変わらなかった前提の再確認

- G1 の下限 `N ≥ 654` は依然成立する。ベースラインは R1 で実測済み（`Ran 630 tests` / `OK` / skip 0）で、G13 廃止はテスト本数に影響しない。S-2 で trim 表を維持したため probe の増分（18 状態・≥38 本）も rev.6 と同じ。
- `config-schema.md:283` の `.codegraph/.gitignore` と `:29` の digestExclude 記述は許可範囲外なので既定名のまま残る。既定利用者には真であり、**放置で正しい**（N-2 の 1 句を入れるなら ADOPTION 側で足りる）。
- R1 で「シロ」と裁定した 3 つの組み合わせ（PRECLOSED×close 対象×resume ／ export×U+FFFD×N12 fixture ／ G8×G10×§7 配列）は rev.7 で該当箇所が変更されていないため、裁定は維持される。

---

## 5. 検証した項目 / していない項目

**検証した（実測）**: rev.6→rev.7 の全差分 70 行、`PLAN.md` 内の `G13`／`manifest`／`216-217`／`difflib` の残存参照、`SKILL.md`・`config-schema.md` の版文字列 0 件、`SKILL.md` の `.codegraph` 参照が 216-218 のみであること、`config-schema.md:29,280-283` の実体、`tree-digest.py:12` の `KNOWN_ROOTS`、4 フィールド NUL read イディオムの実挙動（`set -uo pipefail` 下・空入力時の変数定義を含む）、`ascii()` の引用符付き出力、G11(3) の生成式が旧 :3 に対して成立すること。

**検証していない**: gate.py・release-handoff.sh の実物（未作成）、A2 の各 fixture の実発火、A3 の実機再現、rev.7 反映後のフルスイート（PLAN 変更のみで tests は未変更のため R1 の 630/OK がそのまま有効）。
