# docaudit — プロンプト集

> 🌐 English version: [PROMPTS.md](PROMPTS.md)

Claude Code に docaudit の監査を依頼するための、用途別 copy-paste プロンプト集。各プロンプトは
単一の文章ではなく XML タグ（`<task>`, `<context>`, `<scope>`, `<change>`, `<constraints>`,
`<report>`）で指示を構造化している。Claude は自由文よりも構造化タグの方が正確に読み取れる
——「どこが task で、どこが背景情報で、どこが絶対に守るべき制約か」を、境界を推測するのでは
なく明示的に区別できるからだ。これは Anthropic 自身のプロンプト設計指針にも沿っている:
[Claude prompting best
practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
を参照。角括弧・例示の値（ドキュメント名、変更内容など）は自分のものに置き換えてから貼り付け
ること。以下のパターンはすべて docaudit がインストール済みであることを前提とし、パターン 5 を
除き対象 repo に `.claude/doc-audit.json` が既に存在することも前提とする。

---

## 1. 通常の差分監査

コード・設定・ドキュメントを編集した後の、日常運用のデフォルト。前回のクリーンな監査 anchor
以降の変更で影響を受けたドキュメントだけを検証する。

```
<task>
このリポジトリで docaudit の incremental な監査を実行してください。
</task>
<context>
日常運用のチェックです。前回のクリーンな監査 anchor 以降の変更で影響を受けたドキュメントが、
現在のコード・設定とまだ整合しているか検証してください。
</context>
<constraints>
report-only です。ファイルは一切編集せず、verdict と findings のみ出力してください。
</constraints>

/docaudit:audit を実行してください
```

## 2. リリース前フルスイープ

リリースタグを打つ前（または大きな変更をまとめて入れた後）に、anchor 以降の差分だけでなく
ドキュメント全体を検証する。

```
<task>
リリース前に、ドキュメント全体を対象とした full（whole-corpus）監査を実行してください。
</task>
<context>
これからリリースを切ります。anchor 以降の変更だけでなく、すべてのドキュメントを現在の
ソースと突き合わせて検証してください。
</context>
<constraints>
report-only です。ファイルは一切編集しないでください。
</constraints>

/docaudit:audit --full を実行してください
```

---

## 3. スコープ限定監査

今は特定のサブシステムや一部のドキュメントだけを気にしたいときに使う。`/docaudit:audit` には
スコープ／パス指定の引数はなく、常に impacted set 全体を解決する — incremental では
`impactMap` の mapped、opt-in の `regression` 再検証、heuristic を合わせ、利用可能なら graphify/semantic 候補で補完し、
`--full` では `docGlobs` の全文書を含める。そのためスコープ絞り込みはプロンプト側で行う ——
`<scope>` に対象のドキュメント／サブシステムを名指しし、その verdict を要約で明示的に
報告させる。

```
<task>
ドキュメント監査を実行し、以下 scope のドキュメントには特に注意を払ってください。
</task>
<context>
docaudit 自体にはスコープ指定機能はなく、常にその時点の変更集合に対する impacted set
全体を監査します。以下の scope は、その中でも特にダブルチェックして結果を明示的に報告
してほしいドキュメントを示すためのものであり、それ以外の発見事項を省略する指示ではあり
ません。
</context>
<scope>
docs/api-reference.md, docs/adoption.md, および src/api/** 配下すべて
</scope>
<constraints>
report-only です。ファイルは一切編集しないでください。
</constraints>

/docaudit:audit を実行し、<scope> に列挙した各ドキュメントが impacted set に含まれていたか、
その verdict は何だったかをレポート内で明示的に確認してください
```

---

## 4. 変更影響の事前確認

これから入れる（または既に入れた）特定の変更について、どのドキュメントが影響を受けるか、
それらがまだ整合しているかを直前・直後に確認する。

```
<task>
特定の変更が、どのドキュメントに影響するかを確認し、その変更内容と照らして検証してください。
</task>
<change>
src/api/auth.py で REST エンドポイント POST /v1/login を POST /v1/sessions にリネームしました。
</change>
<constraints>
report-only です。ファイルは一切編集せず、影響を受けるドキュメントとその verdict のみ
列挙してください。
</constraints>

/docaudit:audit を実行し、上記 <change> の影響を受けるドキュメントがこの変更と整合しているか
どうかをレポート内で明示的に指摘してください
```

---

## 5. 初期導入

対象リポジトリに `.claude/doc-audit.json` がまだ存在しない、初回のセットアップ依頼。
`/docaudit:init` は必ずドラフト config を提示し、明示的な承認を待ってから書き込む
——承認なしに書き込まれることはない。

```
<task>
このリポジトリに docaudit をセットアップしてください。
</task>
<context>
このリポジトリにはまだ .claude/doc-audit.json がありません。リポジトリを inventory し、
config のドラフトを作成してください。
</context>
<constraints>
各キーの根拠を 1 行ずつ添えた完全なドラフト config を提示し、私が明示的に承認するまで
何も書き込まないでください。
</constraints>

/docaudit:init を実行してください
```

プロジェクト固有のレイヤスキル雛形も生成してほしい場合は、上記コマンドに `--scaffold` を
付ける（`/docaudit:init --scaffold`）。generic な format/existence/semantic fallback に
頼らずに済む。

---

## 6. 定期実行・非対話運用

スケジュール実行や loop、CI 的な起動など、無人で docaudit が呼ばれる状況を想定したプロンプト
——実行中に確認を挟んで止まることができない前提。

```
<task>
docaudit の監査を、無人・非対話のチェックとして実行してください。
</task>
<context>
これはスケジュール／定期実行です。実行中に質問へ答えたり、何かを承認したりできる人は
いません。
</context>
<constraints>
質問はしないでください——リポジトリに既にある情報だけで最善の判断をしてください。
report-only です。ファイルは一切編集しないでください。.claude/doc-audit.json が
存在しない場合は、作成しようとせずレポートにその旨を記載してください。
</constraints>
<report>
roll-up verdict、impacted docs とその per-doc verdict、non-blocking な警告を簡潔に
返してください。
</report>

/docaudit:audit を実行してください
```

---

## 7. ハーネス構造を入れて初回監査まで進める

docaudit の導入時に、リポジトリ内へ `/check-docs`、`doc-lint`、
`scripts/check-docs.py` の構造も用意したい場合に使う。`init` は既存のドキュメントツールを
調べ、統合・調整・そのまま利用・新規導入のどれにするかを質問する。

```
<task>
このリポジトリに docaudit とローカルのドキュメントハーネスを導入し、初回の full 監査まで
進めてください。
</task>
<context>
既存のドキュメントツールを調べ、適切な構造が無ければ /check-docs、doc-lint、
scripts/check-docs.py を新規に導入してください。
</context>
<constraints>
書き込む前にハーネスの選択肢と config を提示し、承認を得てください。導入後は config と、
コミットが必要な生成物 3 本を列挙してください。init 中に既存ドキュメントは変更しないでください。
</constraints>
<report>
承認済みファイルを書き込んだ後、最初の全コーパス監査を実行し、verdict、pre-flight の結果、
修正が必要なドキュメントを報告してください。
</report>

/docaudit:init --harness を実行し、その後 /docaudit:audit --full を実行してください
```

---

## 8. pre-flight で修正してから監査する

安価な全量チェックで修正可能な FAIL が見つかり、承認したドキュメントだけを直してから
本監査へ進みたい場合に使う。

```
<task>
docaudit を実行し、pre-flight で FAIL が見つかった場合は、本監査の前に修正を提案してください。
</task>
<context>
ローカルのドキュメントハーネスは設定済みです。各ドキュメントの詳細検証より先に、決定論的な
全量チェックを実行したいです。
</context>
<constraints>
pre-flight が失敗した場合、findings と修正候補のドキュメントパスを示した後でのみ
「修正して監査」を選んでください。docaudit の範囲検査で許可されたパスだけを編集し、ADR、
decisions、logs、.claude 配下、承認集合外のファイルは変更しないでください。修正後に
pre-flight を再実行し、範囲外変更が検出されたら停止してください。
</constraints>
<report>
pre-flight での選択と最終 findings、その後の監査 verdict を報告してください。
</report>

/docaudit:audit を実行してください
```

---

## 9. 既存の audit-scope.json を取り込む

別の監査ツールが既に `audit-scope.json` を生成しており、対応する `impactMap` を docaudit に
生成させる場合に使う。importer は由来情報を記録するため、生成された `auditScope` metadata は
手編集しない。

```
<task>
このリポジトリの既存 audit-scope.json を docaudit の設定へ取り込んでください。
</task>
<constraints>
書き込む前に設定変更案を示して承認を得てください。生成された auditScope metadata と impactMap
entry は手編集しないでください。
</constraints>

/docaudit:init --import-audit-scope を実行してください
```
