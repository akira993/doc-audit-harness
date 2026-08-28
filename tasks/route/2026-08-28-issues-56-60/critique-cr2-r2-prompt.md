あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

## 前回指摘との対応（自己申告）— PLAN-cr2.md は rev.2（同じパスを再読）
- CR2-1: 反映。接尾辞対象を {completed, execution-failed} に。
- CR2-2: 反映。表 5 行の左辺条件句を SKILL に literal で書き、契約テストで文言と順序を固定。
- CR2-3: 反映。mdq disabled は `bin` 無しの例外を schema 文と PLAN に明記。
- CR2-4: 反映。既定名置換は「disabled かつ bin 不正」のみ。妥当カスタム bin はそのまま（DoD に追加）。
- CR2-5: 反映。CLI 3 probe にも同じ境界値表（33 文字 ×2、surrogate、内部スペース／非 ASCII／引用符の正例）。sentinel 不起動（負例）と stub 起動 1 回（正例）を分離。
- CR2-6: 反映。伝送は `sys.stdout.buffer` へ UTF-8 直書き（graph・CLI 復号側とも）、`PYTHONIOENCODING=ascii` 環境の非 ASCII 正例を 6 probe に。
- CR2-7: 反映。schema と ADOPTION §7 ① に「non-UTF-8-encodable」。
- CR2-8: 反映。`test_codex_probe.py:233` は引用符・バックスラッシュ・内部スペースの正例に置換、改行は sentinel 付き負例へ。
- CR2-9: 反映。先頭 `-` 禁止を撤回、6 probe の `command -v` を `command -v -- "$BIN"` に。
- CR2-10: 反映。§8 に「ef995f0 の §7 段落に指定 2 置換＋⑦ 追加を施した期待段落との完全一致＋段落外差分 0」の python 片。
- CR2-11: 反映。§8 で SKILL の CM literal を抽出しキー集合完全一致。
- CR2-12: 反映。§8 の AST 片で「return 後の文 0」「必須メソッド名集合」を機械判定。
- CR2-13: 反映。symlink の `addCleanup`。

## 依頼
rev.2 を再批判せよ。前回指摘の再指摘は不要。新規は CR2-N（続番 14〜）、根拠と推奨 1 つ。特に (1) `command -v --` の Bash 3.2 での挙動と `"$BIN" --version` 等の後続呼び出し（bin が `-x` のとき）、(2) `sys.stdout.buffer` 直書きと既存の `read -r STATE BIN` ／base64 経路の整合、(3) CLI probe 判定表 23 ID の `len(CASES)` と既存 20 ID との整合（`bin_nul` は 33 文字走査と重複してよいか）、(4) ADOPTION 期待段落の生成規則が en/ja とも一意に定まるか。
最後に「計画自体の欠陥」と「worker 指示で吸収できる細部」を区分し、無ければ「rev.2 で実装承認」と明言せよ。
