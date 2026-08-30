boss 裁定: **方式 1 を採用**。`generic-layers.py` は `sealed_config` を import せず、必要最小限の封印読取（`os.open(O_NOFOLLOW)` で 1 回読み → `"sha256:"+sha256(raw)` を `--expect-config-sha` と比較 → 不一致は exit 7＋stderr `sealed-config-mismatch: expected <sha> observed <sha>`、フラグ省略時は検証なしで従来どおり）を **ファイル内に内包**する。理由: 複製先（project の `scripts/check-docs.py`）は単独ファイルで動く契約であり、scaffold（禁止範囲）と SKILL のコマンド形を変えない。

追加要件:
- 内包実装は `sealed_config.py` と同じ exit code・stderr 文言・読み 1 回（CT-2b の `builtins.open`/`os.open` 計測で 1 回）であること。`tests/test_sealed_config.py` か `test_v016_contracts.py` に「`generic-layers.py` を temp project の `scripts/check-docs.py` へ単独コピーし、(a) フラグ無しで従来どおり動く、(b) 一致 sha で動く、(c) 不一致 sha で exit 7＋token」の 3 ケースを置く（CT-2 の #10 に相当）。
- `sealed_config.py` の実装と内包実装の重複は許容する（単独ファイル契約のため）。ただし内包実装のロジックは 20 行程度に留め、`sealed_config.py` の CLI 機能（`--get`/`--print`/`--raw`）は複製しない。
- PLAN §9.1 #9/#10 の「任意フラグ」「読み 1 回」「mismatch exit 7」はそのまま。

作業を再開し、全体を完成させてから 08-impl-sol.md の「完了条件」「検証コマンド一式」「報告形式」に従って報告せよ。PLAN に無い判断が新たに必要になったら同様に停止して報告してよい。
