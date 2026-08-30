あなたは docaudit v0.16.0 の実装者（worker）。boss（Fable/Opus）が確定した計画 `tasks/route/2026-08-30-issues-59-63-65-66/PLAN.md`（v8、Sol 5 往復＋Opus 敵対レビュー 3 往復で承認済み）を **全文読んでから**実装せよ。PLAN の §1（目的・脅威境界）、§5（成果物 S1〜S14）、§9（registry・真理値表・eligibility 表・期待値）が仕様である。PLAN に書かれていない設計判断が必要になったら、勝手に決めず報告せよ。

作業前にメタ認知を一度行う。この依頼で引っ張られそうなバイアス（例: 「テストを通すために検査を緩める」「call site の一部だけ直して registry を合わせる」）を 1〜2 行で自己申告してから始める。

## 事前確認（実装前に必ず）
- `git branch --show-current` が `fix/v0.16.0-issues-63-59` であること（boss が作成済み）。git の書き込み操作（add/commit/checkout/stash 等）は一切行わない。ファイル編集のみ。
- `python3 -m unittest discover -s tests` の基線が `Ran 655 tests / OK` であることを実測し報告に含める。

## 実装順序（推奨）
1. S1 `sealed_config.py`（モジュール＋CLI）と `tests/test_sealed_config.py`。
2. S2/S3: Python 10 本・shell 7 本・open-run（S4）・decide-verdict（S5 の `--taint-observed`）・seal-run。§9.1 の「フラグ」「読み」「mismatch exit」列を厳守。shell は config 読みを `sealed_config.py --print` 1 回に統合。
3. S6 SKILL.md: `CONFIG_SHA` 導出、22 call site への付与、§9.2 の getter 13 行（変数名・default・mode を表どおり）、harness 互換表、停止規約、decline 再 open（**散文のまま。literal な `open-run.py` 行を追加しない**）、Guardrails。
4. S8〜S11: evidence `file`/`promptVariant`/`carryForwardSha`、`docaudit_paths.normalize_finding_path`、`docaudit_cache.parse_history_document`（4 reader で共用: resolve-impact / plan-dispatch / gate / codex-review-plan）、`phase4Runs` record・trim 規則・flip 計測・carry-forward。
5. S7/S12/S13: 文書（ADOPTION en/ja・README・config-schema.md）と版 bump・engine-shas。
6. S14: `tests/test_v016_contracts.py`（CT-1〜CT-7、CT-2b、CT-3b、CT-4b/4c/4d、CT-5b）と既存テスト更新。CT-2b の sitecustomize は **`builtins.open` と `os.open` の両方**をフックすること（`os.open` 単独では `json.load(open())` を捕捉できないことを boss 側で実測済み）。

## Opus レビューからの補足（PLAN 改訂不要、実装時に守ること）
- CT-2／CT-2b の対象集合（K=21）に `import-audit-scope.py` を含めない。同スクリプトの既存 `--expect-config-sha` は write-path の楽観排他で、不一致は exit 4（:486-488）、`--write` では config を 2 回読む。registry の「既存・対象外」行のとおり。
- open-run の通常 open: exit 6（acceptance 要求）は **lock 作成前**に判定する。`O_CREAT|O_EXCL` の「先行」は「既存 lock の存在プローブ＝既存なら無条件 exit 4」の意味であり、exit 6 で orphan lock を残してはならない（CT-4c が全組み合わせで lock の有無を assert する）。
- decline 再 open は散文のまま（literal な `open-run.py` 行を追加しない。追加が必要と判断したら実装せず報告）。

## 完了条件（PLAN §6 をそのまま転記）
1. `python3 -m unittest discover -s tests` 全 green（基線 655 以上）。boss が再実行して追認する。
2. CT-1 出力 `call sites N／exempt M／getters G／scripts K／observers O` が §9.5 の期待値（N=22／M=3／G=13／K=21／O=19）と一致。worker の実測が異なる場合は実装を変えるのではなく **報告**し、boss が registry（PLAN §9）を改訂する。
3. CT-2 出力 `対象 K 本を検査` が K と一致し、各本に一致／不一致の対がある。
4. `grep -n 'json.load(open' skills/audit/scripts/*.sh` のヒットが 0、`skills/audit/SKILL.md` の残ヒットが `ANCHOR_PATH=` 行（封印前）の 1 行のみ（残ヒット全件を用途付きで報告）。
5. `grep -n '"\$CFG"' skills/audit/SKILL.md | grep -v 'CONFIG_SHA'` の残りが exemption 3 行（`ANCHOR_PATH=`・`import-audit-scope.py --check`・`decide-verdict.py`）のみ。
6. `python3 -m py_compile skills/audit/scripts/*.py`、`bash -n skills/audit/scripts/*.sh` が exit 0。
7. `0.15.1` の残存は履歴節・過去版参照のみ（一覧報告）。engine-shas.json 0.16.0 entry が `generic-layers.py` の実 sha と一致（test_scaffold）。
8. 報告は各 CT の出力実数と `git diff --stat` を含む。

## 変更範囲（PLAN §7 をそのまま転記）
**許可**: `skills/audit/SKILL.md`、`skills/audit/scripts/**`（新規 `sealed_config.py` 含む）、`skills/audit/references/config-schema.md`、`skills/audit/references/engine-shas.json`（0.16.0 entry のみ）、`.claude-plugin/plugin.json`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`README.md`、`tests/**`。

**禁止**: `skills/init/**`、`agents/**`、`skills/audit/references/codex-review-output.schema.json`、`skills/audit/references/workflow-template.js`、`skills/audit/scripts/scaffold.py` のテンプレート文字列（engine 複製の読み込み部は不変。command/skill テンプレートは変更しない）、`.claude/**`、`tasks/**`、`.github/**`、`.gitignore`、git 操作全般。**許可外ファイルの変更が必要になった場合は、修正せず報告のみせよ（boss が別途扱う）。** 隣接コードのリファクタ・整形・無関係な文言修正は禁止。

## 検証コマンド一式（PLAN §8 をそのまま転記。すべて実行し、出力の要点を報告に含める）
```sh
python3 -m unittest discover -s tests
python3 -m unittest tests.test_v016_contracts -v
python3 -m unittest tests.test_sealed_config -v
python3 -m py_compile skills/audit/scripts/*.py
bash -n skills/audit/scripts/*.sh
grep -n '"\$CFG"' skills/audit/SKILL.md | grep -v 'CONFIG_SHA'
grep -n 'json.load(open' skills/audit/scripts/*.sh skills/audit/SKILL.md
grep -rn '0\.15\.1' --exclude-dir=tasks --exclude-dir=node_modules --exclude-dir=.git .
git diff --stat
```

## 報告形式
最初の一文で「完了／未完了（何が）」を言う。次に: (1) 完了条件 1〜8 の各実測値（テスト件数、CT-1/CT-2 の出力行を verbatim）、(2) PLAN と実装が食い違った点・PLAN に無い判断をした点（無ければ「なし」）、(3) 許可外ファイルの変更が必要と判断した箇所（修正せず列挙）、(4) `git diff --stat`。テストの失敗・スキップは隠さず出力ごと報告する。検証していないことを検証済みと書かない。
