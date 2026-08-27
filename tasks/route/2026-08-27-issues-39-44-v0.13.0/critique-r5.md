あなたは実装者ではなく厳格なレビュアーである。修正はまだ行わないこと。バグ・回帰・セキュリティ・互換性・テスト不足のみを指摘せよ

# ラウンド 5（最終ラウンド）

`tasks/route/2026-08-27-issues-39-44-v0.13.0/PLAN.md` を rev.5 に更新した。R4 の 18 指摘との対応を自己申告する。
これが批判の最終ラウンドである。rev.5 を読み直し、残る指摘を**必ず**次の 2 区分に分けて締めること:
(A) 計画自体の欠陥（PLAN を直してから実装すべきもの）／(B) worker 指示で吸収できる細部（実装プロンプトへ転記できる
1〜2 行の指示文）。新規指摘が無ければ「新規指摘なし」と明記せよ。

## R4 指摘との対応（自己申告）

1. 封印後 manifest の照合: codex-dispatch は `--evidence` を受け、起動前に manifest の sha256 が `EVIDENCE.manifest` と一致することを照合、不一致は子プロセス 0 回で非 0 終了。SKILL workflow 経路は seal 直後に manifest を読み直し `manifest.provenance` から DISPATCH entries を組む（古い保持値を使わない旨を明記）（§6、§10 #39）。
2. `impactSha` は dispatch.json 内のみ。EVIDENCE のキー集合は変えない（§10 #39、§7）。
3. Phase 4 手順 3 を排他的 3 分岐（full+required → 実行／full+optional → skip／incremental → baseline 検査後に実行）の順序で記述し、full+required が skip より前、baseline 検査不要、model/retry/state 処理は共有。契約テストは出現順序を検査（§6 #42、§10 #42）。
4. `--write` の順序: lock 取得 → lock 内で config/scope を読み直し expect SHA 照合 → 生成 → 原子置換 → 解放（§9）。
5. 初回 init: `--base-config <draft>` を受け、lock 内で auto 項目を加えた完成 config を一度で原子作成（中間状態を公開しない）（§9）。
6. flock 直後に fd/path の inode 一致確認、不一致は無変更で停止（§9）。
7. CR/LF: **代替案**。compute-baseline.sh は変更しない（全利用者への互換性影響を避け、§0「非導入プロジェクト無影響」を維持）。importer と Phase 0 の `--check`（毎 audit 実行）が tracked path の CR/LF を fail-closed 拒否 → audit-scope 導入プロジェクトでは後から追加された改行名も次回 audit 開始前に停止する（§9）。
8. check-verdicts は exit 0 の診断契約を維持（provenance を `manifestMismatch` に含めるのみ）。REFUSED は gate に集約（§6、§10）。
9. `auditScope` metadata 型契約（object、`path` repo 内 relative、`sha256` 64hex、`rules` int ≥ 0、`importedAt` 文字列）、違反は error で停止（§9、§6 (vi)）。
10. `source` 互換試験を (viii) として復活（§6）。
11. 同期先 preflight は「正規化した同期先が承認済み skills root の期待パスと一致・非 symlink・書込可能」に変更（§12）。
12. 全成功・再開ケースで tag → approved SHA、Release の tagName/title/body 必須要素を検査。`test_release_handoff.py` は 0.13.0 のみ参照（§12）。
13. 全 SHA を再計算して整合させ provenance のみ `unknown` の sealed fixture で enum 専用 reason を検査（§6）。
14. 2 つの `--doc-glob` にだけ属する影響先を各 1 件用意し両方受理を assert（§6 (vi)）。
15. 二回実行の再開表（no→y、EOF→y、`git push --tags`／`gh release create`／`gh release view`／Issue close 3 件目の各失敗 → 再実行。run 別呼出回数と最終状態を別々に検査）（§12）。
16. `docCorpus == 0` → `heuristicSaturation = 0.0`・warning なし・正常終了（§6、§10 #40）。
17. Phase 5 audit-scope status 行を削除（§9）。
18. 例外経路も finally で inode 照合つき解放、原子置換失敗注入で lock 不在を検査（§9、§6 (v)）。
費用対効果: EVIDENCE 直下 impactSha・check-verdicts 非 0・Phase 5 行の 3 点を削除。`heuristicSaturation` の 3 桁丸めは
表示規則として残す（比較は丸め前）。

## 今回特に見てほしい点

- (a) #7 代替案の妥当性: Phase 0 `--check` は audit-scope 導入プロジェクトでのみ走る。非導入プロジェクトでは改行名の
  取り扱いは現状維持（既存の限界）。この線引きが Issue の目的と整合するか。
- (b) 「排他的 3 分岐」の契約テストが、SKILL 本文の順序だけで到達可能性を判別できるか（他に判別手段があるか）。
- (c) `--base-config` 経路: draft を `mktemp` に置く指示が init SKILL で実行可能か（Write tool は repo 外に書けるか。
  書けない場合の代替: draft を stdin で渡す `--base-config -`）。
- (d) 全体を通して、まだ「対象 0 件で合格」「正誤どちらでも通る」検査が残っていないか。

出力形式: 番号・重大度・根拠・推奨 1 つ。最後に (A)/(B) の区分（B は指示文形式）。
