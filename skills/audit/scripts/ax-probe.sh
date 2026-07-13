#!/usr/bin/env bash
# ax-probe.sh — Phase-0 preflight: detect the `ax` CLI (structured web/API extraction)
# for doc-impact-verifier's read-only external-URL corroboration seam (mdq-pattern:
# conditional-force). If ax is present, bind AX_AVAILABLE/AX_BIN so the verifier may
# corroborate doc claims against upstream URLs. If ax is absent / disabled, emit
# axAvailable:false and let the audit continue unaffected (external checks unavailable
# is never a FAIL reason). Output: single-line JSON.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: no network use — `ax --version` prints the local binary's own version and
# does not fetch a URL.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# webExtract.enabled (default true) + webExtract.bin (default "ax"); tolerate a
# missing/invalid config by falling back to defaults.
ENABLED="1"; BIN="ax"
if [[ -n "$CONFIG" ]]; then
  IFS=$'\t' read -r ENABLED BIN < <(python3 -c '
import json,sys
e=True; b="ax"
try:
    w=(json.load(open(sys.argv[1])).get("webExtract") or {})
    e=bool(w.get("enabled",True)); b=str(w.get("bin","ax") or "ax")
except Exception:
    pass
print(("1" if e else "0")+"\t"+b)
' "$CONFIG")
fi
[[ -n "$BIN" ]] || BIN="ax"
[[ -n "$ENABLED" ]] || ENABLED="1"
# JSON-safe copy of BIN for echoing into the JSON (BIN comes from user config).
BIN_J="$(printf '%s' "$BIN" | tr -d '"\\' | tr -d '[:cntrl:]')"

if [[ "$ENABLED" != "1" ]]; then
  printf '{"axAvailable":false,"axBin":"%s","axVersion":null,"reason":"disabled-by-config"}\n' "$BIN_J"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '{"axAvailable":false,"axBin":"%s","axVersion":null,"reason":"not-installed"}\n' "$BIN_J"
  exit 0
fi

# `ax --version` reports the local binary version only — no network call.
VERSION="$("$BIN" --version 2>/dev/null | tr -d '\r' | head -n1)"
VERSION_J="$(printf '%s' "$VERSION" | tr -d '"\\' | tr -d '[:cntrl:]')"
printf '{"axAvailable":true,"axBin":"%s","axVersion":"%s","reason":"ok"}\n' "$BIN_J" "$VERSION_J"
exit 0
