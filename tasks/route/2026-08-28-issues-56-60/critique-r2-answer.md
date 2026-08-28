メタ認知: 前回対応済みという申告に引かれ、文言追加だけで契約が閉じたと判断しやすい。今回は失敗順序・再開時の欠損・汚染状態から逆算した。

## 判定

**rev.2 は実装承認不可です。**  
特に #59 の「既知 blocking は決定論的に維持される」という中心契約が、複数の経路で破れます。

## 前回対応が不十分な指摘

### R1-2 対応不十分 — Critical・回帰

ledger の挿入位置より後にも REFUSED 経路があります。

根拠:

- PLAN は `last_run` 書込み直後、anchor 書込み前に commit します。`PLAN.md:110-112`
- 実コードでは、その後の anchor `atomic()` が失敗すると外側の例外処理へ入り REFUSED になります。`decide-verdict.py:950-955,984-1016`
- よって ledger 成功後に anchor が失敗すると「REFUSED run の候補は永続化されない」が破れます。
- `--accept-config`、history taint、flock との直接衝突はありません。問題は anchor 失敗です。

推奨: 候補の検証を state 書込み前に済ませ、永続 ledger の置換は anchor 成功後に置く。候補不正は REFUSED、置換時の I/O 失敗だけを構造化 warning として非 REFUSED にする。

### R1-3 対応不十分 — Critical・セキュリティ

「汚染 ledger は blocking を増やすだけ」は成立しません。

根拠:

- 破損・未知 `schemaVersion` を空扱いします。`PLAN.md:95`
- ledger は EVIDENCE と barrier の確認対象外です。現行 barrier は lock、HEAD/digest、history、anchor、config、audit scope のみです。`decide-verdict.py:904-920`
- 有効な空 ledger への差替え、または破損により、既知 blocking が消えます。Codex が再検出しなければ CONSISTENT が可能です。
- これは後続 run への汚染持越しを防ぐ既存脅威モデルと矛盾します。`SKILL.md:772-782`

推奨: 不在だけを空とし、既存 ledger の hash を run 開始時に封印して barrier で再確認する。破損・版不一致・実行中変更は REFUSED にする。

### R1-4 対応不十分 — High・セキュリティ

JSON 1 行化は構文上の注入を防ぎますが、意味上の prompt injection は防ぎません。

根拠:

- title/path は prompt 末尾に入り、モデルが返す `resolved` が削除を直接起動します。`PLAN.md:100-106`
- `data, not instructions` はモデル判断を技術的に強制しません。悪意ある title が「この key を resolved と返せ」と指示する可能性は残ります。
- 実際に従う確率はモデル依存ですが、隔離機構がないこと自体は設計上の事実です。

推奨: 内容不変の blocking はモデルの `resolved` 単独では削除せず、内容 hash の変化または明示的な利用者リセットを必要条件にする。

### R1-10 対応不十分 — High・再開回帰

9 記録→7 表示の行数は揃いましたが、正常表示の再構成に必要な値が不足しています。

根拠:

- `mdqHealth` に `chunks` がありません。active 行は `MDQ_CHUNKS` 必須です。`PLAN.md:63`、`SKILL.md:670`
- `contextModeHealthy` が任意なので、available=true でも active/degraded を選べない有効 record が作れます。`PLAN.md:64`、`SKILL.md:677-678`
- `docGraph` に `gitignoreOk` がありません。reason=ok の2行を選べません。`PLAN.md:65`、`SKILL.md:712-713`
- completed の ledger 接尾辞には summary 全項目が必要ですが、候補を「存在時」としています。`PLAN.md:80,115`
- codex seam schema は、#60 の caller 3項目も必須にしていません。`PLAN.md:64,124-131`

`mdqAvailable:false` のとき health 不要という条件自体は妥当です。現行も available=true の場合だけ health probe を実行します。`SKILL.md:86-93`

推奨: available/reason/state に応じた条件付き schema とし、正常表示に必要な全値を必須化する。

### R1-11 対応不十分 — High・セキュリティ

「write-evidence.py と同水準」は反論になりません。表示専用でも新しいファイル書込み口です。

根拠:

- 「realpath 後に symlink 拒否」は、解決前の最終成分が symlink だった事実を失います。`PLAN.md:66`
- `O_NOFOLLOW` は最終ファイルだけで、run dir の検査後差替えを防ぎません。
- `mkstemp(dir=文字列)` と `os.replace()` は親ディレクトリを再解決するため、検査後に run dir が symlink に交換されると外部へ書けます。現行の同型処理は `write-evidence.py:66-78` です。

推奨: run dir を `O_DIRECTORY|O_NOFOLLOW` で一度開き、その dir fd を基準に一時ファイル作成・置換・再検査を行う。

### R1-13 対応不十分 — Medium・互換性

既存 sanitizer の流用は caller path の観測機能を壊します。

根拠:

- `"`・`\`・制御文字を削除します。`PLAN.md:127`
- 現行 sanitizer は `codex-probe.sh:41-42`。
- Windows の `C:\Users\...` は `C:Users...` に変わり、表示された場所が実在場所と一致しません。

推奨: 値を削らず、Python等の JSON serializer で正しくエスケープする。

### R1-15 対応不十分 — High・テスト不足

変更範囲検査は `.claude/**` の新規ファイルと rename を捕捉しません。

根拠:

- DoD は既存未追跡 `.claude/` 全体を除外します。`PLAN.md:224`
- 一方、§7 は `.claude/**` を禁止しています。`PLAN.md:232-233`
- `git diff` は未追跡ファイルを検出しません。
- `git status ... | awk '{print $2}'` は rename の移動先と空白入り path を失います。`PLAN.md:248`
- コマンドは集合を表示するだけで、部分集合違反時に非0終了しません。

推奨: 作業前の未追跡一覧を固定し、NUL 区切りで rename の両 path を処理する allowlist 検査を非0終了付きで用意する。

### R1-16 対応不十分 — Medium・テスト不足

「全分岐」検査が5分岐中4分岐です。

根拠:

- 出力契約は `probe-exec-failed` を含む5分岐です。`PLAN.md:124`
- DoD は disabled/not-installed/invalid-config/ok の4分岐だけです。`PLAN.md:135,202`
- 現行の未検査分岐は `codex-probe.sh:57-59` です。

推奨: `probe-exec-failed` を含む5分岐すべてで、完全なキー集合一致を検査する。

### R1-17 対応不十分 — High・テスト不足

subTest 数は DoD から検証できません。

根拠:

- DoD (1) は12 subTestを要求しますが、共通検査はテスト名を grep するだけです。`PLAN.md:188,222`
- 実測では、12 subTestでも対象0件の空ループでも `Ran 1 test` となります。

推奨: テスト内でケース表の識別子集合と件数12を直接 assert する。

## 新規指摘

### R2-1 — Critical・回帰

同一 blocking 所見を medium/low で再報告すると、`resolved` なしで blocking が解除されます。

根拠:

- carried blocking は明示 resolved まで維持する契約です。`PLAN.md:88-90`
- 一方、再出現時の severity は今回値へ更新します。`PLAN.md:106`
- high→medium の場合、今回 findings は非 blocking、ledger も medium、再出現済みなので `foldFindings` にも入りません。
- DoD の「severity 更新」はこの誤動作を固定します。`PLAN.md:121`

推奨: carried high/critical は明示解決まで severity の降格を禁止する。

### R2-2 — Critical・回帰／セキュリティ

`foldFindings` と候補 ledger が EVIDENCE に束縛されず、モデル役の orchestrator が省略できます。

根拠:

- orchestrator が stage stdout を findings collection に追加します。`PLAN.md:113-114`
- `write-evidence.py` は渡された phase4 自体を hash 化するだけで、stage 出力との一致を確認しません。`write-evidence.py:49,68-82`
- gate は phase4 findings だけで verdict を決めます。`decide-verdict.py:895-899`
- 候補不在は no-op、候補は形状検査だけなので、有効な空候補への差替えも検出できません。`PLAN.md:110-112`

推奨: stage が fold と候補 hash を含む補助 evidence を生成し、completed の場合は gate が必須読取りして verdict へ直接合流し、同じ bytes だけを commit する。

### R2-3 — High・互換性

任意の `knownFindings` は `codex exec --output-schema` の制約と非互換です。

根拠:

- 現行 schema は `findings` だけ required です。`codex-review-output.schema.json:4-20`
- rev.2 は `knownFindings` を properties に足すが required にしません。`PLAN.md:104,214`
- 実行経路はその schema を直接渡します。`SKILL.md:562`
- OpenAI の [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) は全フィールドを required とし、任意性は nullable 等で表す契約です。
- 実測 CLI は `codex-cli 0.149.0`。`--output-schema` は「final response shape」の JSON Schema を受けます。外部モデル呼出しは行っていません。

`additionalProperties:false` 自体は問題ありません。

推奨: model-facing schema では `knownFindings` を必須配列にし、対象なしを `[]` とする。旧 findings-only の受理は内部 parser に限定する。

### R2-4 — High・回帰／key 衝突

`knownFindings` の矛盾と短縮 key の衝突規約がありません。

根拠:

- 同一 key の重複、`resolved` と `still-present` の併記、今回 findings に存在する key の `resolved` を schema が禁止しません。`PLAN.md:104`
- 処理順が upsert→resolved 削除なので、現在も報告された所見を ledger から削除できます。`PLAN.md:106`
- モデル向け key は SHA-256 の先頭12桁だけです。`PLAN.md:101-104`。48 bit prefix は full key より衝突耐性を大幅に落とします。

推奨: full 64桁 key を一意主キーとし、stage で重複・相反 status・current finding と resolved の矛盾を拒否する。

### R2-5 — High・バグ／テスト不足

`contextMode:null` が invalid-config ではなく有効になります。

根拠:

- 表では non-object、null は invalid-config です。`PLAN.md:28-29`
- 式は `c.get("contextMode")` のため、不在と明示 null を区別できません。`PLAN.md:39-42`
- 実測結果は `missing → true`、`null → true`、`scalar → invalid` でした。
- DoD は式に `"invalid"` が含まれることしか確認せず、判定表を実行しません。`PLAN.md:197`

推奨: `"contextMode" not in c` と `c["contextMode"] is None` を分離し、null・非 object・非 boolean を実行テストする。

### R2-6 — Medium・互換性

#58 は POSIX の repo 外迂回は閉じていますが、native Windows の正当な絶対パスを拒否します。

根拠:

- `os.sep` と大小をそのまま使った文字列接頭辞照合です。`PLAN.md:16-18`
- `C:/repo` と `C:\repo`、ドライブ文字の大小違い、UNC の先頭 `\\` が一致しません。
- DoD は POSIX 形式だけです。`PLAN.md:20,188`

末尾 `/`、内部 `//`、`.`、`..`、URL 形、中間 symlinkによる POSIX 上の repo 外脱出は見つかりませんでした。`~` と `C:\...` は POSIX では repo 内の通常名扱いで、外部へは出ません。

推奨: `altsep`・`normcase`・UNC root を扱う OS 別 helper を仕様化し、Windows 形式をテストする。

### R2-7 — Medium-High・回帰

ledger の妥当性が diff variant／baseline に束縛されません。

根拠:

- entry には `promptVariant`、baseline、`changeSetSha` がありません。`PLAN.md:96`
- carry 条件は対象 file の現在 `contentSha` 一致だけです。`PLAN.md:98`
- incremental の「この差分で契約を落とした」という所見は、baseline が進んでも現在 file の bytes が同じなら carry されます。逆に full と incremental で根拠範囲が異なることも識別できません。

推奨: finding に `reviewBasis` と基準 hash を持たせ、diff 依存所見は同一 change set のときだけ自動 carry する。

### R2-8 — High・長期回帰／可用性

blocking 無制限保持と全件 prompt 挿入は自己 DoS になります。

根拠:

- blocking は trim 対象外です。`PLAN.md:108`
- 全 blocking を promptBlock に入れます。`PLAN.md:100-103`
- 複数 run で蓄積すると入力上限・時間制限に到達し、`required:true` が恒常的に REFUSED になり得ます。
- DoD に件数・byte数・batch 境界がありません。`PLAN.md:120-123`

推奨: gate は全 blocking を決定的に fold しつつ、モデルへ送る再検証対象だけを固定件数・固定 byte 数で決定的に batch 化する。

### R2-9 — Medium・互換性／文書回帰

ADOPTION の固定文が判定表と矛盾します。

根拠:

- 判定表は `enabled:false, bin:[]` を `disabled-by-config` とします。`PLAN.md:34`
- 固定文①は「非文字列・空 bin は invalid-config」と例外なしに断言します。`PLAN.md:142`
- 固定文⑤の「non-REFUSED run のみ commit」も R1-2 の anchor 失敗経路では偽です。`PLAN.md:146`

推奨: §7 の固定文を実際の優先順位と commit 成功条件を含む表現へ修正し、判定表から生成した期待値で検査する。

## 計画自体の欠陥と worker 細部

計画自体を直す必要があります:

- R1-2、R1-3、R1-4、R1-10、R1-11
- R2-1〜R2-9
- R1-15、R1-17 の合否条件

worker 指示で吸収できる細部です:

- helper／関数名
- JSON のキー順・表示整形
- 条件付き schema の実装方法
- テスト fixture の共通化
- POSIX の先頭 root separator を除く具体的なループ方法

R1-13、R1-16 は小規模ですが、現在の PLAN が誤った sanitizer と4分岐検査を明記しているため、worker 裁量には残せません。

## PLAN を直すべき点（優先順）

1. ledger の persistent input、stage fold、候補 bytes を EVIDENCE/barrier に束縛し、gate が直接 verdict へ合流する。
2. blocking の severity 降格・矛盾 resolved・モデル単独 resolvedを禁止し、破損 ledger を fail-closed にする。
3. commit を anchor 後へ移し、検証失敗と保存 I/O 失敗の扱い・構造化 warning を分離する。
4. `knownFindings` schema と再開 record の必須項目を実際の Codex／Phase-5 消費契約に合わせる。
5. DoD を対象件数・全分岐・NUL区切り allowlist・batch上限・symlink raceまで検出する形に改める。

ファイルの変更は行っていません。