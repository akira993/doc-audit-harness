Release notesを指定文へ更新し、検証はすべて通過しました。commitは実施していません。

- `bash -n`: exit 0
- handoffテスト: `Ran 18 tests in 10.519s` — `OK`
- 必須語8件: すべて残存

最終Release notes全文:

```text
docaudit v0.14.0.

- Approved commit: $APPROVED_SHA
- Closes #57, #58, #60.
- Partially addresses #56 (stage 1) and #59 (operational note); both remain open.
- Ships invalid-config semantics for the indexing / contextMode / webExtract / codexReview keys, display-only Phase-0 probe persistence in $RUN_DIR/phase0-probes.json, caller CODEX_HOME / auth.json visibility in the codex probe, and absolute --config/--scope paths for import-audit-scope.py (see ADOPTION §7 for v0.14.0 behavior changes).
```