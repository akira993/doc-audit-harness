# S1b 実装報告 — Issue #54

S1b は実装済みで、指定した対象テスト 94 件と構文確認はすべて成功しました。全体テストはこの実行環境の30秒制限で完了結果を取得できなかったため、boss が再実行する必要があります。

## 変更ファイルと要旨

- `skills/audit/scripts/graphify-probe.sh`、`codegraph-probe.sh`、`cocoindex-probe.sh`: key-gated の設定判定、`not-configured`/`invalid-config`、固定 JSON 形状、全分岐 exit 0 を実装。CocoIndex は `settings.yml` マーカーと `.gitignore` 変化の非復元検出を追加。
- `skills/audit/SKILL.md`: Phase 0 の JSON 捕捉・reason 束縛、reason 列挙、CocoIndex の安全説明、Phase 5 の reason 排他表示を更新。
- `skills/audit/references/config-schema.md`、`docs/ADOPTION.md`、`docs/ADOPTION.ja.md`、`skills/init/SKILL.md`: 3 seam をキー必須の説明に統一し、`settings.yml` と新しい状態を記載。
- `tests/test_graphify_probe.py`、`tests/test_codegraph_probe.py`、`tests/test_cocoindex_probe.py`: 設定判定、外部プログラム非起動、`settings.yml`、`.gitignore` 変化のテストを追加。
- `tests/test_v0132_contracts.py`: DoD (9)〜(14)、§0-4 B1、schema の `minScore` 文言を契約テスト化。

## DoD 検証

| 項目 | 実行コマンド | 実測結果 |
|---|---|---|
| (8) | `python3 -m unittest tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe` | 51 tests, OK |
| (9) | `python3 -m unittest tests.test_v0132_contracts` | 13 tests, OK（reason 列挙の完全一致を含む） |
| (10), (10b) | `python3 -m unittest tests.test_v0132_contracts` | OK（Phase 5 の排他表示、Phase 0 の JSON reason 束縛） |
| (11) | `python3 -m unittest tests.test_v0132_contracts` | OK（`not-configured` は対象 OMIT 3 か所のみ） |
| (12) | `python3 -m unittest tests.test_cocoindex_probe tests.test_v0132_contracts` | 34 tests, OK（legacy directory と schema 文言を含む） |
| (13) | `python3 -m unittest tests.test_cocoindex_probe` | 21 tests, OK（変更、生成、失敗優先の3ケース） |
| (14) | `python3 -m unittest tests.test_v0132_contracts` | 13 tests, OK（5文書の `settings.yml` マーカー） |
| §0-4 B1 | `python3 -m unittest tests.test_v0132_contracts` | OK（3 seam の自動使用表現なし） |
| (20) | `python3 -m unittest discover -s tests -t .` | 30秒で完了結果を取得できず。代替として下記94 tests は OK。boss がフルを実行すること。 |
| (21) | `bash -n skills/audit/scripts/graphify-probe.sh skills/audit/scripts/cocoindex-probe.sh skills/audit/scripts/codegraph-probe.sh`、`python3 -m py_compile tests/test_graphify_probe.py tests/test_cocoindex_probe.py tests/test_codegraph_probe.py tests/test_v0132_contracts.py`、`git diff --check` | すべて成功 |
| (22) | `git status --short` | S1b の許可済み12ファイルと、この承認済み報告書のみ変更。`?? .claude/` は既存の対象外項目。 |

## テスト実行結果

```text
python3 -m unittest -v tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe tests.test_v0132_contracts tests.test_v013_contracts tests.test_v0131_docs_contracts tests.test_impact_supplement
Ran 94 tests in 7.722s
OK
```

## 未対応・判断事項

- S2（版番号更新、ADOPTION §7 の v0.13.2 段落、handoff）は対象外のため変更していません。
- 全体テストは30秒制限により未確定です。対象テストの成功結果を残し、フル実行は boss に委ねます。
- `?? .claude/` は指示どおり対象外で、変更していません。

## boss 差し戻し 1 への対応

`skills/init/SKILL.md` の mdq 説明で、意味論を変えてしまう `opt-in indexing` という表現を撤回しました。mdq は本版でも、導入済みならキー不在時を含め既定で有効であり、`enabled:false` で無効化できる、という従来どおりの説明に修正しました。

再発防止の学び: 段落単位の文書契約を通すために禁止語を言い換える場合も、同じ段落にある対象外 seam の意味論を変更してはならない。対象外 seam は、元の動作条件を完全に保った同義表現だけを使う。

修正後に次を実行し、`Ran 64 tests in 6.352s`、`OK` を確認しました。

```text
python3 -m unittest -v tests.test_v0132_contracts tests.test_graphify_probe tests.test_cocoindex_probe tests.test_codegraph_probe
```

## 最終レビュー P2 への対応

`.gitignore` の指紋計算から `shasum` と `awk` への依存を除き、Python 3 標準の `hashlib.sha256` に置き換えました。指紋の計算が失敗するか空の結果になった場合は `ccc index` の実行前に停止し、`semanticSearchAvailable:false`、`reason:index-failed` として継続可能な状態へ落とし、stderr には説明を1行だけ出します。実行後の指紋計算に失敗した場合も `ok` にはせず、同じく `index-failed` とします。

`shasum` が失敗する偽物を PATH の先頭に置いても `.gitignore` の追記を `gitignore-modified` として検出できるテストと、指紋計算自体が失敗した場合に `ccc index` を起動しないテストを追加しました。

実測結果:

```text
bash -n skills/audit/scripts/cocoindex-probe.sh
成功

rg -n 'shasum' skills/audit/scripts/cocoindex-probe.sh
0件

python3 -m unittest -v tests.test_cocoindex_probe tests.test_v0132_contracts
Ran 37 tests in 3.840s
OK
```
