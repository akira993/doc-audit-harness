#!/usr/bin/env bash
# codex-probe.sh — Phase-0 preflight: detect the `codex` CLI (plain `codex exec`,
# no plugin dependency) for docaudit's Phase-4 adversarial Codex review seam
# (ax-pattern: conditional-force). If codex is present, bind
# CODEX_REVIEW_AVAILABLE/CODEX_REVIEW_BIN so Phase 4 may run a Codex review. If
# codex is absent / disabled, emit codexReviewAvailable:false and let the audit
# continue unaffected — codex being unavailable is never a FAIL reason (though a
# *completed* codex review's critical/high findings can be, per spec §5.4).
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: no network use — `codex --version` and `codex exec --help` inspect only the
# local binary and do not start a model invocation.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# codexReview.enabled (default true) + codexReview.bin (default "codex"); tolerate a
# missing/invalid config by falling back to defaults.
ENABLED="1"; BIN="codex"
if [[ -n "$CONFIG" ]]; then
  IFS=$'\t' read -r ENABLED BIN < <(python3 -c '
import json,sys
e=True; b="codex"
try:
    w=(json.load(open(sys.argv[1])).get("codexReview") or {})
    e=bool(w.get("enabled",True)); b=str(w.get("bin","codex") or "codex")
except Exception:
    pass
print(("1" if e else "0")+"\t"+b)
' "$CONFIG")
fi
[[ -n "$BIN" ]] || BIN="codex"
[[ -n "$ENABLED" ]] || ENABLED="1"
# JSON-safe copy of BIN for echoing into the JSON (BIN comes from user config).
BIN_J="$(printf '%s' "$BIN" | tr -d '"\\' | tr -d '[:cntrl:]')"

if [[ "$ENABLED" != "1" ]]; then
  printf '{"codexReviewAvailable":false,"codexReviewBin":"%s","codexReviewVersion":null,"probeCommands":[],"reason":"disabled-by-config"}\n' "$BIN_J"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '{"codexReviewAvailable":false,"codexReviewBin":"%s","codexReviewVersion":null,"probeCommands":[],"reason":"not-installed"}\n' "$BIN_J"
  exit 0
fi

# `codex --version` reports the local binary version only — no network call.
VERSION="$("$BIN" --version 2>/dev/null | tr -d '\r' | head -n1)"
VERSION_J="$(printf '%s' "$VERSION" | tr -d '"\\' | tr -d '[:cntrl:]')"
if ! "$BIN" exec --help >/dev/null 2>&1; then
  printf '{"codexReviewAvailable":false,"codexReviewBin":"%s","codexReviewVersion":"%s","probeCommands":["%s --version","%s exec --help"],"reason":"probe-exec-failed"}\n' "$BIN_J" "$VERSION_J" "$BIN_J" "$BIN_J"
  exit 0
fi
printf '{"codexReviewAvailable":true,"codexReviewBin":"%s","codexReviewVersion":"%s","probeCommands":["%s --version","%s exec --help"],"reason":"ok"}\n' "$BIN_J" "$VERSION_J" "$BIN_J" "$BIN_J"
exit 0
