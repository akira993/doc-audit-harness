# docaudit v0.13.0 — Issues #39〜#44

## 対応内容

### #39 — 回帰文書の再確認と判定変化の可視化

前回失敗した文書を任意で再確認できるようにし、由来と内容不変時の判定変化を記録します。

### #40 — 影響範囲の推定を見える化

推定対象が過剰に広がった際の警告と、文書パス由来の語を除く設定を追加しました。

### #41 — Phase 3 の見落としやすい範囲を明記

複数文書の食い違い、対象外参照、手順の実行可能性を、横断的な確認で補う範囲として文書化しました。

### #42 — 厳格な Codex review

`codexReview.required` により、必要な確認が実行されなかった場合は完了扱いにしない運用を選べます。

### #43 — 文書確認エンジンの修正

リスト継続行、リンク内改行、未使用処理の3点を修正しました。

### #44 — 監査対象の取り込み

監査対象の正本から影響範囲設定を生成・照合し、ずれがあれば監査を停止します。

## 互換性への影響

- 判定を拒否する条件が増え、実行記録には `provenance`、`auditScopeSha`、`impactSha` が加わります。
- 版をまたいで実行中の作業は `--break-lock` が必要です。
- Phase 3/4 は封印済み記録を経由して読み、Codex の配布処理は `--evidence` が必須です。
- Phase 4 の Codex 行は4状態で表示され、文書確認エンジンには3つの修正が入っています。
- `regressionRecheck`、`excludeDocPathTokens`、`codexReview.required`、`auditScope` は既定では無効または未設定です。

## テスト

着手前 368 件（2026-08-27 main）から、完了後 485 件へ増加しました。フルスイートは
485 件すべて成功し、skip は 0 件です。

## リリース引き継ぎ

```bash
tasks/route/2026-08-27-issues-39-44-v0.13.0/release-handoff.sh <merge-sha> <pr>
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
