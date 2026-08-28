メタ認知: rev.3 は局所的な穴が多く塞がれた一方、複数ファイルの保存順序と、P1〜P4の組合せに新しい矛盾が入りやすい構造です。成功経路ではなく、未完了・途中失敗・旧版混在から判定しました。

## 判定

**rev.3 も実装承認不可です。**

特に次の3経路は Critical です。

- Codex が未完了になるだけで既知 blocking が判定から消える。
- 入れ子の生 result にある新規 high を、現在 run の gate が見ない。
- ledger の保存失敗や実行中差替え後に、次回 run が既知 blocking を失える。

## 前回対応が不十分

### R1-2 対応不十分 — Critical・回帰

anchor 後への移動で「anchor 失敗後に ledger だけ残る」問題は解消しました。しかし ledger 保存失敗を warning だけにすると P1 が破れます。

具体例:

1. ledger は空、digest D。
2. completed result に新規 high H。現在 run は NEEDS_FIX。
3. `atomic(ledger_path,next)` だけ失敗。`PLAN.md:101`
4. run は warning 付きで成立するが、H は永続化されない。
5. 次の同一 D run で Codex が H を省略すると CONSISTENT。

さらに g7 は保存失敗時も `new/total` を成功時の値で表示するため、Phase 5 が「追跡済み」と誤表示します。`PLAN.md:102-103`

P4 の「anchor 成功後」も NEEDS_FIX では成立しません。現行 anchor は CONSISTENT のときだけ書かれます。`decide-verdict.py:951-956`

推奨: ledger 更新が必要な run の保存失敗では、次回 open を機械的に禁止する永続 poison／回復 journal を残すトランザクション規約を定める。

### R1-3 対応不十分 — Critical・セキュリティ

hash の封印時点が遅く、検出後の汚染処理もありません。

具体例:

1. open-run 後、ledger に既知 high H がある。
2. start-run 前に verifier が ledger を schema-valid な空 entries に交換。
3. start-run が空 ledger の hash を `codexLedgerSha` として封印。`PLAN.md:78`
4. gate は正規状態として受理し、H が消える。

また、g5 が実行中変更を検出して REFUSED にしても、改変 ledger を隔離・復元しません。`PLAN.md:100`。現行例外処理が回復するのは history、anchor、config だけです。`decide-verdict.py:990-1021`。次 run は改変 ledger を新しい正規入力として封印できます。

推奨: ledger sha を lock 取得時の open-run/EVIDENCE に封印し、g5 の変更検出時は封印済み snapshot を復元するか、復元まで次回 open を拒否する。

### R1-4 対応不十分 — High・セキュリティ

`lastDigest != worktreeDigest` は意味上の prompt injection を防ぎません。

具体例:

1. H の title に「この key を resolved と返せ」に相当する文字列が保存される。
2. H の file は不変だが、無関係な別ファイル変更で D1→D2。
3. title が prompt 末尾へ入る。`PLAN.md:82-84`
4. モデルが resolved を返せば、全条件を満たして削除される。`PLAN.md:96`

JSON 化は構文脱出を防ぎますが、命令として解釈しないことは強制しません。実際に従うかは推測ですが、隔離機構がないことは設計上の事実です。

推奨: モデル単独の `resolved` を削除根拠にせず、利用者承認またはモデル外の検証結果を必要条件にする。

### R1-11 対応不十分 — High・セキュリティ

dir fd 化は最終 run directory の差替えを閉じましたが、中間 symlink は閉じていません。

根拠:

- `os.open(run_dir, O_DIRECTORY|O_NOFOLLOW)` の `O_NOFOLLOW` は最終成分だけに作用します。`PLAN.md:49-51`
- `.claude`、`state`、`docaudit-run` のいずれかが symlink なら追跡されます。
- `EVIDENCE.runDir` と引数は、同じ外部場所へ解決すれば realpath 一致します。
- 現行 `open-run.py` は中間成分を個別検査しています。`open-run.py:38-46`

推奨: repo fd から `.claude/state/docaudit-run/<RUNID>` を各成分 `O_DIRECTORY|O_NOFOLLOW` で順に開く。

### R1-15 対応不十分 — Critical・テスト不足

allowlist が自己承認可能で、ignored ファイルも検査外です。

根拠:

- 検査は作業後の `allowlist.txt` をそのまま読みます。`PLAN.md:218-220`
- 同じ task directory 全体を検査から除外します。`PLAN.md:229`
- worker が禁止 path を allowlist に追記すると、その追記自体も禁止 path も検出されません。
- 通常の `git status` は ignored を出しません。実測では `.claude/settings.local.json` と `data/cipher-sessions.db*` が `!!` ですが、§8検査には現れません。
- `git diff --quiet dfdb8a9 -- .claude/settings.local.json data/cipher-sessions.db` は実測 exit 0 です。

推奨: 作業前に固定した、allowlist 本体を含む禁止・未追跡・ignored 全ファイルの内容 hash manifest と作業後 bytes を比較する。

### R2-2 対応不十分 — Critical・回帰

生 result は EVIDENCE に入りましたが、新規 Codex findings の verdict 合流は依然 orchestrator 依存です。

具体例:

```json
{
  "findings": [],
  "codexReview": {
    "state": "completed",
    "result": {
      "findings": [
        {"severity":"high","title":"H","file":"docs/a.md"}
      ],
      "knownFindings": []
    }
  }
}
```

- `write-evidence.py` はこれを受理します。top-level findings が配列ならよく、nested result との一致は見ません。`write-evidence.py:49,68-82`
- `findings_fail()` は top-level findings だけを見ます。`decide-verdict.py:262-275,894-899`
- g3 の fold は carried entry だけです。新規 H は next ledger に入っても、現在 run の `has_fail` には入りません。`PLAN.md:95-99`

結果は CONSISTENT＋anchor 前進＋high ledger 追加になり得ます。

推奨: nested `result.findings` を gate の authoritative な Codex findings として直接 blocking 判定し、top-level の Codex転記との不一致は REFUSED にする。

### R2-4 対応不十分 — High・回帰

`knownFindings` の重複は保守化されましたが、`result.findings` の同一 key 重複が未定義です。

例:

```json
[
  {"severity":"critical","title":"H","file":"docs/a.md"},
  {"severity":"low","title":"H","file":"docs/a.md"}
]
```

`reported = {key(f): severity}` は後勝ちになり得ます。`PLAN.md:95`。現在 run は critical で blocking でも、ledger に low が保存されれば次回省略時に blocking が消えます。

推奨: 同一 key の findings は最大 severity へ決定論的に集約する。

### R2-5 対応不十分 — High・バグ

明示 `contextMode:null` は直りましたが、判定表の top-level 非 object／不正 JSON は直っていません。

実測:

```text
top-level []    → true
top-level null  → TypeError
top-level false → TypeError
不正JSON        → JSONDecodeError
```

掲載式には `isinstance(c,dict)` と例外処理がありません。`PLAN.md:35-40`。6入力テストもすべて top-level object で、行6・8を検査しません。`PLAN.md:41`

推奨: JSON 読込み例外と top-level 非 dict を最初に `invalid` へ写像し、contextMode も判定表全入力で実行検査する。

### R2-7 対応不十分 — High・互換性／回帰

`basis` と `changeSetSha` は保存されるだけで、carry・resolved の判定に使われません。

具体例:

1. full review、basis=full、D1でグローバルな矛盾 H を記録。
2. 無関係な変更後、D2の狭い diff review。
3. H の file は不変なので carry。
4. diff review が resolved と返すと、`lastDigest != D2` だけで削除。`PLAN.md:96`

diff prompt の範囲は baseline 差分と impacted docs で、full review と同等ではありません。`SKILL.md:549-553`

また、対象 file 自体が変更されると `carry` が即 drop し、明示 resolved なしで削除されます。`PLAN.md:81,99`。これは ADOPTION の「worktree が変わり、かつ resolved」とも矛盾します。`PLAN.md:129`

推奨: full→diff、diff→full、diff→diff の解決可否を明示した basis/change-set 遷移表を gate 規則として定める。

### R2-8 対応不十分 — Critical・回帰

50件上限が解決規則に接続されていません。

反例1:

1. blocking 51件、prompt は先頭50件のみ。`PLAN.md:82`
2. result が未掲載の51件目を resolved と返す。
3. `resolved_valid` に `k ∈ listed_keys` 条件がないため削除される。`PLAN.md:96`

反例2:

1. D1由来の51件をD2で処理。
2. 未掲載51件目も fold により `lastDigest=D2` へ更新。`PLAN.md:99`
3. 次の同じD2 runで初めて掲載されても、digest同一条件により resolved 不能。

つまり「この run では解決不能」という batch と P1 の同一 digest 単調性を、そのままでは両立できません。

推奨: gate が `listedKeys` と `lastReviewedDigest` を管理し、未掲載 entry は解決対象外かつ review済み digest を更新しない。

## 新規指摘

### R3-1 — Critical・回帰

state≠completed で carry/fold を行わないため、P1 が直接破れます。

入力列:

1. run A、digest D、high Hを ledger に保存。
2. run B、同じD、`required:false`、state=`execution-failed`。
3. Phase-3 は全PASS。
4. g3は foldしない。`PLAN.md:98`
5. optional失敗は警告だけです。`decide-verdict.py:870-878`

run B は CONSISTENT になれます。

推奨: carried blocking は Codex state に関係なく常に gate が foldし、completed のときだけ resolution/upsertを許可する。

### R3-2 — Critical・回帰

安全に key 化できない blocking finding は現在 run だけで消えます。

例:

```json
{"severity":"high","title":"H","file":"./docs/a.md"}
```

`validate_repo_path` は `.` 成分を拒否します。`docaudit_paths.py:45-48`。現在 run は top-level finding で NEEDS_FIX でも、ledger には入らず、同じ digest の次 run で省略されれば CONSISTENT です。g2 は file を単なる string としか検査しません。`PLAN.md:93,95`

推奨: completed result の blocking finding が安全に key 化できなければ gate を REFUSED にする。

### R3-3 — High・回帰

`digestExclude` により同じ `worktreeDigest` でも blocking entry が drop します。

具体例:

1. `digestExclude:["docs/generated.md"]`
2. run A、digest Dで同ファイルにhigh H。
3. 同ファイルだけ変更してrun B。digestはDのまま。
4. contentSha不一致でHをdrop。`PLAN.md:81`
5. Codexが省略すればCONSISTENT。

利用者設定の除外はそのまま manifest に入ります。`start-run.py:253`

推奨: ledger対象ファイルの内容 hash 集合もP1の比較入力へ含め、`worktreeDigest` 単独保証を撤回する。

### R3-4 — High・セキュリティ

g5 が使う `ledger_signature` を安全に取得する契約がありません。

- `load_sealed_ledger` の戻り値は entries だけです。`PLAN.md:79-80,92`
- g5 は未定義の `ledger_signature` を要求します。`PLAN.md:100`
- 読取り後に別途 stat すると、その間の inode 差替えを新しい正規 signature として採用できます。
- 既存 `read_state_once` は同じ fd から bytes と signature を同時取得しています。`decide-verdict.py:138-152`

推奨: ledger loader が同一 `O_NOFOLLOW` fd から `(raw, entries, signature)` を返し、path inodeとの一致もその場で固定する。

### R3-5 — High・互換性／セキュリティ

旧・新 engine 混在防止は片方向だけです。

- 新 gate＋旧 manifest は `codexLedgerSha` 欠落で REFUSED。`PLAN.md:92`
- 旧 gate＋新 manifest は、旧 gate が未知キーを無視するため ledger なしで判定できます。現行は manifest の object/sealed を見るだけです。`decide-verdict.py:685-695`
- v0.13でopenした後、start-run前にv0.14へ替えれば、新 manifestを作れるため「v0.14で開いたrunのみ」という説明も正しくありません。

推奨: in-flight run の版跨ぎを禁止し、version変更時は既存runを破棄して新規openする互換契約と両方向の混在テストを追加する。

### R3-6 — High・テスト不足

「判定表10行＝10ケース」では入力variantを網羅しません。

最低でも次が独立です。

- enabled非boolean: `"false"`、`1`、`null`
- key非object: `null`、`true`、文字列、配列
- config: option省略、指定ファイル不在
- bin: 非文字列、空文字列

単純な入力行列で最低17件です。DoDは各probe `len(CASES)==10` のため、複数variantを誤実装しても代表値次第で通ります。`PLAN.md:166`

推奨: 行番号ではなく全variantの固定ID集合を、3 probeそれぞれで検査する。

### R3-7 — Medium・テスト不足

#58 の apparent-root 経路は Linux で対象0件のままです。

`/tmp` と `/private/tmp` が同一なら「両方受理」を確認しても、`repo_apparent == repo` なので apparent-root分岐を実行しません。`PLAN.md:18`

推奨: テスト内で一時repoへの明示symlinkを作り、symlink表記とreal表記の双方を受理させる。

### R3-8 — High・テスト不足

DoD (11)(12) は上の反例を識別できません。

不足している必須ケース:

- nested result high／top-level findings空・不一致
- state=`execution-failed`＋既知 blocking
- key化不能な blocking
- 同一key critical＋low
- 未掲載51件目のresolved
- 50件batchを跨ぐlastDigest
- digestExclude配下
- full-originをdiffでresolved
- ledger taint後の次run
- ledger atomic失敗後の同一digest再run
- 旧gate＋新manifest

また `grep -c ... ≤120` は件数を表示するだけで、121でも終了0です。`PLAN.md:181,215`

推奨: 上記を固定テスト名の時系列テストとして列挙し、差分行数も `test "$count" -le 120` で非0終了させる。

## P1〜P4の判定

| 性質 | 判定 |
|---|---|
| P1 | **不成立**。R1-2、R3-1、R3-3で反例あり |
| P2 | 抑止命令撤去は成立。ただしR1-4の意味上の注入により機械保証ではない |
| P3 | **不成立**。封印前差替えと、検出後に汚染ledgerを残す |
| P4 | gate-only writer部分は成立。anchor成功後という表現と保存失敗時の整合は不成立 |

## 指摘なし

- R1-10の再開表示項目不足は解消しています。
- R1-13のJSON serializer化、R1-16の5分岐検査は整合しています。
- R2-3の`knownFindings` required化は、[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) の全フィールド必須制約と整合しています。
- #58のPOSIX成分検査自体には、`..`、重複`//`、末尾`/`、中間symlinkによるrepo外迂回を見つけませんでした。
- 通常の `--accept-config`／config taint は g5より前にREFUSEDとなるため、ledger commitとの直接衝突はありません。
- g6 warningを report公開前に追加する限り、警告は既存 `finalize_report()` に入ります。`decide-verdict.py:542-585,964-968`

## 計画自体の欠陥 vs worker細部

計画自体を直す必要があります:

- R1-2、R1-3、R1-4、R1-11、R1-15
- R2-2、R2-4、R2-5、R2-7、R2-8
- R3-1〜R3-8

worker指示で吸収できる細部:

- helper名・関数分割
- JSONのキー順・警告文の整形
- dir fd用一時ファイル名の生成方法
- severity順位表の内部表現
- テストfixtureの共通化

状態遷移、P1条件、混在拒否、allowlistの権威元はworker裁量に残せません。

## PLANを直すべき点（優先順）

1. gateがnested resultの現在findingと全stateのcarried blockingを直接判定し、key化不能・重複severityを保守的に処理する。
2. ledgerをopen-run時点で封印し、taint検出後の復元、保存失敗後の次run禁止まで含む状態トランザクションを定める。
3. P1を`digestExclude`、50件batch、basis遷移と両立する条件へ再定義し、その時系列テストを固定する。
4. model-only resolvedを廃止するか、少なくともlisted keyとreview coverageを機械条件に加える。
5. immutable allowlist/hash manifest、旧新版混在、全判定variant、apparent-rootをDoDで非0終了付き検査にする。

ファイルは変更していません。