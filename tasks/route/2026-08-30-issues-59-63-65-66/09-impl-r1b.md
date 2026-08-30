未完了（複製版 `generic-layers.py` の封印処理について boss 裁定待ち）です。全担当を停止しました。

問題は次のとおりです。

- `generic-layers.py` は単独でプロジェクト側の `scripts/check-docs.py` に複製されます。
- S1 の `sealed_config.py` を通常の読み込みで利用すると、複製先に同ファイルがないため `ModuleNotFoundError` になります。
- PLAN は複製版にも `--expect-config-sha` を要求しますが、依存ファイルの配置方法は定めていません。

選択肢は以下です。

1. `generic-layers.py` 内に必要最小限の封印読取処理を内包する。
2. 複製時に `sealed_config.py` も配置するよう `scaffold.py` を変更する。これは現行の禁止範囲に抵触します。
3. 複製版の起動時だけ plugin 側 scripts を探索先として渡し、封印処理を読み込ませる。SKILL のコマンド形が PLAN にない追加判断になります。

どの方式を採用するかご指定ください。現在は途中までの変更が作業ツリーにあり、全体検証は未実施です。