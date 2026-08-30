boss レビュー（差し戻し R3）。R2 は boss が 713 tests OK・CT 実数一致を追認した。最終 `codex exec review`（別セッション、Sol high）が P2 を 2 件指摘し、boss も妥当と判断した。以下を修正せよ。git 操作はしない（作業ツリーは boss がステージ済み）。

## R3-1 [P2] shell 消費者が config JSON 全体を単一の実行引数で渡している
- 対象: `ax-probe.sh`（:57 付近の `python3 -c '...' "$CONFIG_JSON"`）、`codex-probe.sh`、`codegraph-probe.sh`、`graphify-probe.sh`、`cocoindex-probe.sh`、`mdq-index.sh`（DECISION と roots の 2 箇所）、`compute-baseline.sh`（ANCHOR_PATH／GLOBS_JSON／最終 python の 3 箇所）。
- 問題: `impactMap` 等で有効な config が OS の単一引数上限（Linux の MAX_ARG_STRLEN = 128 KiB）を超えると `python3 -c` が `Argument list too long` で起動できず、その失敗が検査されないため probe が空の bin を `not-installed` 等として返し、設定された検査が黙って無効化される。
- 修正: (a) config JSON は **stdin** で渡す（`printf '%s' "$CONFIG_JSON" | python3 -c '... json.load(sys.stdin) ...'`。既に stdin を使う箇所があれば一時ファイル経由でよい）。(b) 各 `python3 -c` の終了コードを検査し、非 0 なら stderr にメッセージを出して **exit 2**（黙って退化しない）。`sealed_config.py --print` 自体の呼び出しは変更しない。
- テスト: `tests/test_v016_contracts.py` に「300 KiB 超の有効 config（大きな `impactMap`）で 7 本の shell 消費者が一致 sha で正常 exit 0 かつ JSON を返す」ケースを追加（CT-2 の対と同じ fixture で config を膨らませる）。CT-1(d) の「`sealed_config.py` をちょうど 1 回」「`json.load(open(` 無し」は維持。

## R3-2 [P2] gate の `config_signature` が読取と別の stat で取られる
- 対象: `decide-verdict.py:944` 付近 `config_signature = state_signature(config_path)`（`load_sealed_config()` の後）。
- 問題: 読取完了〜stat の隙間に config が変更されると、判定は封印内容、signature は新内容の状態になり、以後変更が無ければ最終確認（`state_unchanged`）を通過して履歴・判定を書き込める。
- 修正: `sealed_config.load_sealed_config` に、読取に使った **同じ fd の `os.fstat`** から signature を返す経路を追加（例: `load_sealed_config(path, expected_sha, with_signature=True) -> (raw, doc, signature)`。signature の形式は decide-verdict の `state_signature` と同一の組（ino/size/mtime_ns 等）にし、さらに fd の inode と `os.lstat(path)` の inode 一致を検査、不一致は `SealedConfigMismatch` 扱い）。gate はこの signature を `config_signature` に使う。`--taint-observed` 経路と他の消費者は変更不要。
- テスト: `tests/test_decide_verdict.py` か `test_v016_contracts.py` に、CT-2b の sitecustomize 機構で「gate の config 読取直後・signature 取得前に config を差し替える」ケースを追加し、gate が `config-changed` で REFUSED（taint 記録）になることを assert。`tests/test_sealed_config.py` に signature 返却の単体テスト。

## 報告
最後にフルスイートを 1 回実行し `Ran N tests` と `OK` を verbatim で。R3-1/R3-2 の対応内容・該当 file:line・検証を列挙。PLAN に無い判断が必要なら停止して報告。
